"""
alpha_factory_v1.backend.agents.base
====================================

AgentBase – canonical contract ALL Alpha-Factory agents must implement.

Key features
------------
✔ Graceful *degradation* – imports of heavy/optional deps are best-effort; the
  file remains import-safe on a tiny python-only system.

✔ First-class *observability* – Prometheus metrics, structured JSON logs,
  Kafka heart-beats; everything is disabled automatically when a dependency
  is absent.

✔ Hassle-free *scheduling* – fixed interval, cron-style (`aiocron`) or event-
  driven (no schedule).  Agents only have to implement `async step()`.

✔ Built-in *service wiring* – properties expose Memory Fabric, world-model,
  LLM helper and message-bus exactly the same way in every agent.

✔ Uniform *shutdown* & error-handling – a single `_safe_step()` wrapper counts
  runs, records latency and prevents rogue exceptions from killing the process.

✔ Tiny *registry* decorator – `@register` auto-adds the class to the global
  `backend.agents.AGENT_REGISTRY`, enabling true plug-and-play discovery.

The class is intentionally framework-agnostic: **no FastAPI, no OpenAI SDK,
no OR-Tools** imports appear here – that belongs in concrete agent modules,
never in the bare contract.

---------------------------------------------------------------------------
For details see the Developer Guide (§2 “Writing a New Agent”) in the repo doc.
---------------------------------------------------------------------------
"""

from __future__ import annotations

# ───────────────────────────────────────────────────────────────────────────────
# ░░░ 1. Std-lib imports only (guaranteed present) ░░░
# ───────────────────────────────────────────────────────────────────────────────
import abc
import asyncio
import datetime as _dt
import json
import logging
import os
import random
import time
import traceback
from typing import Any, List, Mapping, MutableMapping, Optional

# ───────────────────────────────────────────────────────────────────────────────
# ░░░ 2. Optional, best-effort 3rd-party imports ░░░
# ───────────────────────────────────────────────────────────────────────────────
try:  # -- Prometheus metrics
    from prometheus_client import Counter, Gauge
except ModuleNotFoundError:  # pragma: no cover
    Counter = Gauge = None  # type: ignore

try:  # -- Kafka producer for heart-beats
    from kafka import KafkaProducer  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    KafkaProducer = None  # type: ignore

try:  # -- Cron / RRULE scheduling helper
    import aiocron  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    aiocron = None  # type: ignore

# ───────────────────────────────────────────────────────────────────────────────
# ░░░ 3. Global logger configured once, reused by every agent ░░░
# ───────────────────────────────────────────────────────────────────────────────
_logger = logging.getLogger("alpha_factory.agent")
if not _logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s %(name)s.%(agent)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    _logger.addHandler(_h)
    _logger.setLevel(os.getenv("AF_AGENT_LOGLEVEL", "INFO").upper())

# ───────────────────────────────────────────────────────────────────────────────
# ░░░ 4. Internal helper factories ░░░
# ───────────────────────────────────────────────────────────────────────────────
_RUN_COUNTER = None
_ERR_COUNTER = None
_LAT_GAUGE = None


def _prom_metrics(agent_name: str):
    """Return Prometheus metric handles scoped for ``agent_name``.

    Metrics are instantiated lazily and reused across agent instances to avoid
    ``CollectorRegistry`` duplication errors when multiple agents/tests create
    new objects with the same metric names.
    """
    if Counter is None:
        return None, None, None

    global _RUN_COUNTER, _ERR_COUNTER, _LAT_GAUGE
    if _RUN_COUNTER is None:
        _RUN_COUNTER = Counter("af_agent_runs_total", "Total step() calls", ["agent"])
        _ERR_COUNTER = Counter("af_agent_errors_total", "Unhandled exceptions", ["agent"])
        _LAT_GAUGE = Gauge("af_agent_latency_seconds", "Step latency", ["agent"])

    return (
        _RUN_COUNTER.labels(agent_name),
        _ERR_COUNTER.labels(agent_name),
        _LAT_GAUGE.labels(agent_name),
    )


def _kafka_producer() -> Optional[KafkaProducer]:
    """Instantiate a KafkaProducer if ALPHA_KAFKA_BROKER is set *and*
    `kafka-python` is installed; otherwise return None."""
    broker = os.getenv("ALPHA_KAFKA_BROKER")
    if not broker or KafkaProducer is None:
        return None

    try:
        return KafkaProducer(
            bootstrap_servers=[b.strip() for b in broker.split(",") if b.strip()],
            value_serializer=lambda v: (
                v if isinstance(v, bytes) else json.dumps(v).encode()
            ),
            linger_ms=250,
        )
    except Exception:  # noqa: BLE001
        _logger.exception("Failed to bootstrap Kafka producer")
        return None


# ───────────────────────────────────────────────────────────────────────────────
# ░░░ 5. AgentBase definition ░░░
# ───────────────────────────────────────────────────────────────────────────────
class AgentBase(abc.ABC):
    # --- Class-level metadata (override in subclasses) ---
    NAME: str = "base"  # snake-case, globally unique
    VERSION: str = "0.1.0"
    CAPABILITIES: List[str] = []  # e.g. ["forecast", "trade", "plan"]
    COMPLIANCE_TAGS: List[str] = []  # e.g. ["GDPR", "HIPAA"]
    REQUIRES_API_KEY: bool = False  # orchestrator will validate if True

    # Scheduling ────────────────────────────────────────────────────────────
    CYCLE_SECONDS: int | None = 60  # fixed-interval; None → use SCHED_SPEC
    SCHED_SPEC: str | None = None   # cron-style, processed by aiocron

    # Runtime-injected by orchestrator ──────────────────────────────────────
    orchestrator: Any = None  # Fabric / bus / world-model / cfg

    # ------------------------------------------------------------------ #
    def __init__(self) -> None:
        self._stop_evt: asyncio.Event = asyncio.Event()
        self._metrics_run, self._metrics_err, self._metrics_lat = _prom_metrics(
            self.NAME
        )
        self._kafka = _kafka_producer()

    # ════ Life-cycle hooks ════
    async def setup(self) -> None:  # noqa: D401
        """One-time async initialization (DB warm-up, model load…)."""
        return None

    @abc.abstractmethod
    async def step(self) -> None:  # noqa: D401
        """The agent's main unit of work.  MUST be overridden."""
        raise NotImplementedError

    async def teardown(self) -> None:  # noqa: D401
        """Optional async clean-up (closing DB handles etc.)."""
        return None

    # ════ Convenience properties exposed by orchestrator ════
    # Memory Fabric
    @property
    def mem_vector(self):  # -> MemoryVector | None
        return getattr(self.orchestrator, "mem_vector", None)

    @property
    def mem_graph(self):  # -> MemoryGraph | None
        return getattr(self.orchestrator, "mem_graph", None)

    # Latent world-model / planner
    @property
    def world_model(self):
        return getattr(self.orchestrator, "world_model", None)

    # Unified LLM helper
    async def call_llm(self, *args, **kwargs):
        """LLM abstraction – delegates to orchestrator, supports transparent
        fallback to local models when OPENAI_API_KEY is unset."""
        return await self.orchestrator.llm(*args, **kwargs)  # type: ignore[attr-defined]

    # Message-bus helpers
    async def publish(self, topic: str, msg: Mapping[str, Any]):
        await self.orchestrator.publish(topic, msg)  # type: ignore[attr-defined]

    async def subscribe(self, topic: str):
        async for m in self.orchestrator.subscribe(topic):  # type: ignore[attr-defined]
            yield m

    # ════ Internal run-loop (managed by orchestrator) ════
    async def _run(self) -> None:  # pragma: no cover
        log_ctx = {"agent": self.NAME}

        # ── Option A: cron / rrule schedule ────────────────────────────────
        if self.SCHED_SPEC and aiocron:
            _logger.info("Cron schedule [%s] activated", self.SCHED_SPEC, extra=log_ctx)

            async def _cron_wrapper():  # each cron tick triggers exactly ONE step
                await self._safe_step(log_ctx)

            aiocron.crontab(self.SCHED_SPEC)(_cron_wrapper)  # type: ignore[arg-type]
            await self._stop_evt.wait()
            return

        # ── Option B: fixed interval (default) ────────────────────────────
        interval = max(0, self.CYCLE_SECONDS or 0)
        if interval == 0:
            _logger.info("Event-driven mode (no automatic loop)", extra=log_ctx)
            await self._stop_evt.wait()
            return

        jitter = max(0.2, float(os.getenv("AF_LOOP_JITTER_MS", "250"))) / 1000.0
        _logger.info("Loop each %ss (+/- jitter)", interval, extra=log_ctx)

        while not self._stop_evt.is_set():
            await self._safe_step(log_ctx)
            await asyncio.sleep(interval + random.uniform(0, jitter))

    # ────────────────────────────────────────────────────────────────────
    async def _safe_step(self, log_ctx: MutableMapping[str, Any]):  # pragma: no cover
        t0 = time.perf_counter()
        if self._metrics_run:
            self._metrics_run.inc()

        ok = True
        try:
            await self.step()
        except Exception as exc:  # noqa: BLE001
            ok = False
            if self._metrics_err:
                self._metrics_err.inc()
            _logger.error("step() raised: %s", exc, extra=log_ctx)
            _logger.debug("Traceback:\n%s", traceback.format_exc(), extra=log_ctx)

        latency = time.perf_counter() - t0
        if self._metrics_lat:
            self._metrics_lat.set(latency)

        # -- Heart-beat to Kafka (non-blocking) --
        if self._kafka:
            try:
                self._kafka.send(
                    "agent.heartbeat",
                    {
                        "name": self.NAME,
                        "ts": _dt.datetime.utcnow().isoformat(timespec="seconds"),
                        "latency_ms": round(latency * 1000, 3),
                        "ok": ok,
                    },
                )
            except Exception:  # pragma: no cover
                _logger.debug("Kafka heart-beat failed", extra=log_ctx)

    # ════ Public stop() called by orchestrator ════
    async def stop(self):
        """Signal the agent to shut down gracefully."""
        self._stop_evt.set()

    # ────────────────────────────────────────────────────────────────────
    # Pretty representation (helps debugging & logging)
    # ────────────────────────────────────────────────────────────────────
    def __repr__(self) -> str:  # pragma: no cover
        return f"<{self.__class__.__name__} name={self.NAME!r} v{self.VERSION}>"

# ───────────────────────────────────────────────────────────────────────────────
# ░░░ 6. Tiny decorator to auto-register subclasses ░░░
# ───────────────────────────────────────────────────────────────────────────────
def register(cls: type[AgentBase]) -> type[AgentBase]:
    """
    `@register` – convenience decorator that adds *cls* to the global
    ``backend.agents.AGENT_REGISTRY``.  Importing the module is enough for the
    orchestrator to discover the new agent – zero boiler-plate.
    """
    # defer import to avoid circular refs
    from . import AGENT_REGISTRY  # type: ignore

    AGENT_REGISTRY[getattr(cls, "NAME", cls.__name__)] = cls
    return cls
