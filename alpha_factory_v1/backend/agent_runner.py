# SPDX-License-Identifier: Apache-2.0
"""Agent scheduling and health monitoring utilities.

The :class:`EventBus` falls back to an in-memory queue when Kafka is
unavailable. In that mode the consumer drain loop is automatically scheduled
on creation so queued events do not accumulate when running in development.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
import atexit
import sys
from datetime import datetime, timezone
from collections import deque
from typing import Any, Callable, Dict, Optional
import os

from alpha_factory_v1.core.monitoring import metrics
from .utils.sync import run_sync

from .telemetry import MET_LAT, MET_ERR, MET_UP, tracer

with contextlib.suppress(ModuleNotFoundError):
    from kafka import KafkaProducer

log = logging.getLogger(__name__)


def get_agent(name: str, **kwargs: Any) -> Any:
    """Proxy agent lookup for compatibility with tests."""
    agents_mod = sys.modules.get("backend.agents")
    if agents_mod is None:
        from backend import agents as agents_mod
    return agents_mod.get_agent(name, **kwargs)


def _env_float(name: str, default: float) -> float:
    """Return ``float`` environment value or ``default`` if conversion fails."""

    val = os.getenv(name)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        log.warning("Invalid %s=%r, using default %s", name, val, default)
        return default


class EventBus:
    """Simple Kafka/in-memory event bus.

    When Kafka is missing, messages are stored in local queues and a drain
    consumer is started automatically to prevent unbounded growth.
    """

    def __init__(self, broker: str | None, dev_mode: bool, *, max_queue_size: int = 1024) -> None:
        self._queues: Dict[str, asyncio.Queue[Dict[str, Any]]] | None = None
        self._producer: KafkaProducer | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._max_queue_size = max_queue_size
        if broker and "KafkaProducer" in globals():
            self._producer = KafkaProducer(
                bootstrap_servers=broker.split(","),
                value_serializer=lambda v: json.dumps(v).encode(),
                linger_ms=50,
            )
        else:
            if broker and not dev_mode:
                log.warning("Kafka unavailable → falling back to in-proc bus")
            self._queues = {}
            try:
                asyncio.get_running_loop().create_task(self.start_consumer())
            except RuntimeError:
                pass
        atexit.register(self._close)

    def publish(self, topic: str, msg: Dict[str, Any]) -> None:
        if self._producer:
            self._producer.send(topic, msg)
        else:
            assert self._queues is not None
            q = self._queues.setdefault(topic, asyncio.Queue(maxsize=self._max_queue_size))
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(msg)

    def read_and_clear(self, topic: str | None = None) -> Dict[str, list[Dict[str, Any]]]:
        """Return queued events and clear the buffers (dev mode helper)."""
        if self._queues is None:
            return {}
        topics = [topic] if topic else list(self._queues)
        result: Dict[str, list[Dict[str, Any]]] = {}
        for t in topics:
            q = self._queues.get(t)
            if not q:
                continue
            items: list[Dict[str, Any]] = []
            while not q.empty():
                try:
                    items.append(q.get_nowait())
                except asyncio.QueueEmpty:
                    break
            if items:
                result[t] = items
        return result

    async def _drain_loop(self) -> None:
        assert self._queues is not None
        try:
            while True:
                for q in list(self._queues.values()):
                    while not q.empty():
                        try:
                            q.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass

    async def start_consumer(self) -> None:
        if self._queues is None or self._consumer_task is not None:
            return
        self._consumer_task = asyncio.create_task(self._drain_loop())

    async def stop_consumer(self) -> None:
        if self._consumer_task is None:
            return
        self._consumer_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._consumer_task
        self._consumer_task = None

    def _close(self) -> None:
        if self._consumer_task is not None:
            with contextlib.suppress(Exception):
                run_sync(self.stop_consumer())
        if not self._producer:
            return
        try:
            self._producer.flush()
            self._producer.close()
        except Exception:  # noqa: BLE001
            log.exception("Kafka producer close failed")


async def maybe_await(fn: Callable[..., Any], *a: Any, **kw: Any) -> Any:
    """Await ``fn`` if it is async, otherwise run it in a thread."""
    return await fn(*a, **kw) if asyncio.iscoroutinefunction(fn) else await asyncio.to_thread(fn, *a, **kw)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class AgentRunner:
    """Wrap one agent instance and manage its execution."""

    def __init__(
        self,
        name: str,
        cycle_seconds: int,
        max_cycle_sec: int,
        publish: Callable[[str, Dict[str, Any]], None],
        inst: Any | None = None,
    ) -> None:
        self.name = name
        self.inst = inst or get_agent(name)
        self.period = getattr(self.inst, "CYCLE_SECONDS", cycle_seconds)
        self.spec = getattr(self.inst, "SCHED_SPEC", None)
        self.next_ts = 0.0
        self.last_beat = time.time()
        self.task: Optional[asyncio.Task[None]] = None
        self.paused_at: float | None = None
        self._max_cycle_sec = max_cycle_sec
        self._publish = publish
        self._calc_next()

        with contextlib.suppress(ModuleNotFoundError):
            from openai.agents import AgentContext

            if isinstance(self.inst, AgentContext):
                from openai.agents import AgentRuntime

                runtime = AgentRuntime()
                runtime.register(self.inst)
                atexit.register(runtime.close)

    def _calc_next(self) -> None:
        now = time.time()
        if self.spec:
            with contextlib.suppress(ModuleNotFoundError, ValueError):
                from croniter import croniter  # type: ignore

                self.next_ts = croniter(self.spec, datetime.fromtimestamp(now)).get_next(float)
                return
        self.next_ts = now + self.period

    async def maybe_step(self) -> None:
        if time.time() < self.next_ts:
            return
        self._calc_next()

        async def _cycle() -> None:
            t0 = time.time()
            span_cm = tracer.start_as_current_span(self.name) if tracer else contextlib.nullcontext()
            with span_cm:
                try:
                    await asyncio.wait_for(maybe_await(self.inst.run_cycle), timeout=self._max_cycle_sec)
                except asyncio.TimeoutError:
                    MET_ERR.labels(self.name).inc()
                    log.error("%s run_cycle exceeded %ss budget – skipped", self.name, self._max_cycle_sec)
                except Exception as exc:  # noqa: BLE001
                    MET_ERR.labels(self.name).inc()
                    log.exception("%s.run_cycle crashed: %s", self.name, exc)
                finally:
                    dur_ms = (time.time() - t0) * 1_000
                    MET_LAT.labels(self.name).observe(dur_ms)
                    self.last_beat = time.time()
                    self._publish("agent.cycle", {"agent": self.name, "latency_ms": dur_ms, "ts": utc_now()})

        self.task = asyncio.create_task(_cycle())

    def resume(self) -> None:
        """Resume execution after a pause."""
        self.paused_at = None
        self.next_ts = 0


async def hb_watch(runners: Dict[str, AgentRunner]) -> None:
    while True:
        now = time.time()
        for n, r in runners.items():
            alive = int(now - r.last_beat < r.period * 3.0)
            MET_UP.labels(n).set(alive)
        await asyncio.sleep(5)


async def regression_guard(
    runners: Dict[str, AgentRunner],
    on_alert: Callable[[str], None] | None = None,
    *,
    threshold: float | None = None,
    window: int | None = None,
    interval: float | None = None,
) -> None:
    """Pause evolution when scores regress consistently.

    Parameters
    ----------
    runners:
        Map of active runners by name.
    on_alert:
        Optional callback invoked when the guard triggers.
    threshold:
        Multiplicative drop required between samples (``ALPHA_REGRESSION_THRESHOLD``).
    window:
        Number of recent scores to track (``ALPHA_REGRESSION_WINDOW``).
    """

    thr = _env_float("ALPHA_REGRESSION_THRESHOLD", threshold or 0.8)
    win = int(_env_float("ALPHA_REGRESSION_WINDOW", float(window or 3)))
    history: deque[float] = deque(maxlen=win)
    baseline: float | None = None
    sleep_interval = _env_float("ALPHA_REGRESSION_INTERVAL", interval or 1.0)
    while True:
        await asyncio.sleep(sleep_interval)
        try:
            sample = metrics.dgm_best_score.collect()[0].samples[0]
            score = float(sample.value)
        except Exception:  # pragma: no cover - metrics optional
            continue
        history.append(score)
        runner = runners.get("aiga_evolver")

        if runner and runner.paused_at is not None and baseline is not None:
            if score >= baseline:
                if not (runner.task and not runner.task.done()):
                    runner.resume()
                if on_alert:
                    on_alert("Evolution resumed")
                baseline = None
                history.clear()
            continue

        if len(history) > 1:
            avg_prev = sum(list(history)[:-1]) / (len(history) - 1)
            if history[-1] <= avg_prev * thr:
                if runner and runner.task:
                    runner.task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await runner.task
                    runner.paused_at = time.time()
                baseline = avg_prev
                if on_alert:
                    on_alert("Evolution paused due to metric regression")
                history.clear()
