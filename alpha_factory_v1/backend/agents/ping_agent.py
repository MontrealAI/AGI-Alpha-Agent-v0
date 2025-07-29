# SPDX-License-Identifier: Apache-2.0
"""
alpha_factory_v1.backend.agents.ping_agent
==========================================

A *minimal-footprint* **heartbeat / diagnostics agent** for Alpha-Factory v1
------------------------------------------------------------------------------


Why it exists
-------------
* Verifies that the *Agent loop*, *message-bus*, *metrics pipeline* and
  *orchestrator scheduling* are all wired-up correctly.
* Emits:
    1.  A structured log entry (`json`-style via the project logger).
    2.  Prometheus **counter**, **gauge** *and* **histogram** samples.
    3.  A Kafka (or in-memory) heartbeat message on topic **agent.ping**.

Safety & Ops
------------
* Completely *stateless* – it never writes to memory-fabric or external DBs.
* Can be disabled at runtime with **AF_DISABLE_PING_AGENT=true**.
* All third-party dependencies (`prometheus_client`, `opentelemetry-sdk`,
  `confluent_kafka`) are *optional*; the agent degrades gracefully when
  unavailable – no crashes, no hard imports.

Environment variables
---------------------
* ``AF_PING_INTERVAL``   Seconds between pings (int ≥ 5 – default *60*).
* ``AF_DISABLE_PING_AGENT``   Set to *true*/*1* to skip registration entirely.

CLI usage (stand-alone smoke-test)
----------------------------------
>>>  python -m alpha_factory_v1.backend.agents.ping_agent
     # Runs a single asynchronous ping-loop until <CTRL+C>

Copyright & License
-------------------
© 2025 Montreal AI — Apache 2.0 licensed, like the rest of Alpha-Factory v1.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Mapping, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Alpha-Factory internal imports
# ──────────────────────────────────────────────────────────────────────────────
from backend.agents.registry import register, _agent_base

# Ensure compatibility with both legacy and new AgentBase locations
AgentBase = _agent_base()

# ──────────────────────────────────────────────────────────────────────────────
# Resilient, colourised logger (inherits project-wide JSON formatter)
# ──────────────────────────────────────────────────────────────────────────────
_log = logging.getLogger("alpha_factory.agent").getChild("ping")

# ──────────────────────────────────────────────────────────────────────────────
# Optional integrations — imported lazily / wrapped in try-except
# ──────────────────────────────────────────────────────────────────────────────
_Prom: SimpleNamespace = SimpleNamespace(Counter=None, Gauge=None, Histogram=None)
_OTEL: SimpleNamespace = SimpleNamespace(tracer=None)

try:
    from prometheus_client import Counter, Gauge, Histogram  # type: ignore
    from alpha_factory_v1.backend.metrics_registry import get_metric as _reg_metric

    def _get_metric(cls, name: str, desc: str):
        return _reg_metric(cls, name, desc)

    _Prom.Counter = Counter  # type: ignore[assignment]
    _Prom.Gauge = Gauge
    _Prom.Histogram = Histogram
    _Prom.get_metric = _get_metric
except ModuleNotFoundError:
    _log.warning(
        "prometheus_client missing – metrics disabled",
        extra={"agent": "ping"},
    )


try:
    from opentelemetry import trace  # type: ignore

    _OTEL.tracer = trace.get_tracer(__name__)
except ModuleNotFoundError:
    _log.warning(
        "opentelemetry not installed – tracing disabled",
        extra={"agent": "ping"},
    )

# ──────────────────────────────────────────────────────────────────────────────
# Configuration helpers
# ──────────────────────────────────────────────────────────────────────────────
_DEFAULT_INTERVAL: int = 60
_MIN_INTERVAL: int = 5


def _env_seconds(name: str, default: int) -> int:
    try:
        v = int(os.getenv(name, str(default)).strip())
        return max(v, _MIN_INTERVAL)
    except (TypeError, ValueError):
        return default


# ═════════════════════════════════════════════════════════════════════════════
# Agent implementation
# ═════════════════════════════════════════════════════════════════════════════
@register(condition=lambda: os.getenv("AF_DISABLE_PING_AGENT", "").lower() not in ("1", "true"))
class PingAgent(AgentBase):
    """
    Ultra-light agent that “pings” the Alpha-Factory stack every *CYCLE_SECONDS*.

    Capabilities demonstrated
    -------------------------
    * Automatic scheduling via ``CYCLE_SECONDS`` + AgentBase event-loop.
    * Structured logging with contextual ``extra`` metadata.
    * Prometheus metric emission (Counter, Gauge, Histogram).
    * Kafka / fallback-bus publication through ``self.publish``.
    * OpenTelemetry span wrapping (if OTEL is available).
    """

    NAME = "ping"
    VERSION = "2.0.0"  # ↑ bump any time behaviour changes.
    CAPABILITIES = ["diagnostics", "observability"]
    COMPLIANCE_TAGS: list[str] = []  # ← Security/compliance scopes (GDPR, etc.)
    SAFE_TO_REMOVE: bool = True  # ← DevOps hint (“may be disabled”)

    CYCLE_SECONDS: int = _env_seconds("AF_PING_INTERVAL", _DEFAULT_INTERVAL)

    # ──────────────────────────────────────────────────────────────────────────
    # Prometheus metric objects (instantiated lazily inside setup()).
    # ──────────────────────────────────────────────────────────────────────────
    _prom_ping_total: Optional[Any] = None
    _prom_last_epoch: Optional[Any] = None
    _prom_cycle_hist: Optional[Any] = None

    # ════════════════════════════════════════════════════════════════════════
    # Life-cycle hooks
    # ════════════════════════════════════════════════════════════════════════
    async def setup(self) -> None:
        """Initialise metrics and announce readiness."""
        if self._prom_ping_total is None and _Prom.Counter:
            if getattr(_Prom, "get_metric", None):
                self._prom_ping_total = _Prom.get_metric(
                    _Prom.Counter, "af_ping_total", "Cumulative number of successful pings."
                )
                self._prom_last_epoch = _Prom.get_metric(
                    _Prom.Gauge, "af_ping_last_epoch", "Unix epoch of the most recent ping."
                )
                self._prom_cycle_hist = _Prom.get_metric(
                    _Prom.Histogram,
                    "af_ping_cycle_seconds",
                    "Time taken by ping step() execution.",
                )
            else:
                self._prom_ping_total = _Prom.Counter(
                    "af_ping_total",
                    "Cumulative number of successful pings.",
                )
                self._prom_last_epoch = _Prom.Gauge(
                    "af_ping_last_epoch",
                    "Unix epoch of the most recent ping.",
                )
                self._prom_cycle_hist = _Prom.Histogram(
                    "af_ping_cycle_seconds",
                    "Time taken by ping step() execution.",
                    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5),
                )

        _log.info(
            "PingAgent initialised – interval=%ss (Prometheus=%s OTEL=%s)",
            self.CYCLE_SECONDS,
            bool(_Prom.Counter),
            bool(_OTEL.tracer),
            extra={"agent": self.NAME},
        )

    async def step(self) -> None:
        """
        Perform one “ping”.

        Workflow
        --------
        1. ⏱️  Start OTEL span (if enabled).
        2. 🔈  Log timestamp + context.
        3. 📊  Update Prometheus counter/gauge/histogram (if enabled).
        4. 📡  Publish heartbeat on ``agent.ping`` topic.
        """
        start_ts = datetime.now(tz=timezone.utc)

        span_cm = _OTEL.tracer.start_as_current_span("ping-agent.step") if _OTEL.tracer else nullcontext()
        # ``start_as_current_span`` returns a synchronous context manager so we
        # use a regular ``with`` block for compatibility.
        with span_cm:  # type: ignore[var-annotated]
            now_iso = start_ts.isoformat(timespec="seconds")
            ctx: Mapping[str, Any] = {"agent": self.NAME}

            # 1. Structured log
            _log.info("Ping ⏰ %s", now_iso, extra=ctx)

            # 2. Prometheus metrics
            if self._prom_ping_total:
                self._prom_ping_total.inc()
                self._prom_last_epoch.set(start_ts.timestamp())

            # 3. Publish to message-bus (Kafka or fallback)
            await self.publish(
                "agent.ping",
                {
                    "ts": now_iso,
                    "agent": self.NAME,
                    "version": self.VERSION,
                },
            )

            # 4. Histogram observe (after publish)
            if self._prom_cycle_hist:
                elapsed = (datetime.now(tz=timezone.utc) - start_ts).total_seconds()
                self._prom_cycle_hist.observe(elapsed)

    async def teardown(self) -> None:
        """Graceful shutdown hook."""
        _log.info("PingAgent shutting down.", extra={"agent": self.NAME})

    async def skill_test(self, payload: dict) -> dict:
        """Respond to skill test pings."""
        return {"pong": True}


# ═════════════════════════════════════════════════════════════════════════════
# Convenience — run as a *stand-alone* asyncio programme
# ═════════════════════════════════════════════════════════════════════════════
def _standalone() -> None:
    """Allow `python -m alpha_factory_v1.backend.agents.ping_agent`."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    agent = PingAgent()

    async def _runner() -> None:
        await agent.setup()
        stop_event = asyncio.Event()

        def _graceful(*_: Any) -> None:
            _log.info(
                "Received termination signal – shutting down PingAgent …",
                extra={"agent": agent.NAME},
            )
            stop_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _graceful)  # POSIX-only; safe on Linux/macOS.
            except NotImplementedError:
                pass  # Windows – signals handled differently.

        while not stop_event.is_set():
            await agent.run_cycle()
            await asyncio.sleep(agent.CYCLE_SECONDS)

        await agent.teardown()

    try:
        loop.run_until_complete(_runner())
    finally:
        loop.close()


# Python < 3.10 fallback for contextlib.nullcontext
try:
    from contextlib import nullcontext  # pylint: disable=ungrouped-imports
except ImportError:  # pragma: no cover
    from contextlib import contextmanager

    @contextmanager
    def nullcontext():  # type: ignore[override]
        yield


if __name__ == "__main__":
    # When executed directly, we drop into stand-alone “ping loop” mode.
    logging.basicConfig(
        level=os.getenv("LOGLEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    _standalone()
