# SPDX-License-Identifier: Apache-2.0
"""Alpha‑Factory orchestrator wrapper."""

from __future__ import annotations

import asyncio
import atexit
import contextlib
import logging
import os
import signal
import sys
from typing import Any, Optional

from alpha_factory_v1.utils.env import _env_int
import openai_agents

AgentRuntime = getattr(openai_agents, "AgentRuntime", None)

from .agent_scheduler import AgentScheduler
from .orchestrator_base import BaseOrchestrator
from .agent_manager import AgentManager
from .agent_runner import regression_guard  # noqa: F401
from .telemetry import MET_LAT, MET_ERR, MET_UP, tracer  # noqa: F401
from .services import APIServer, KafkaService, MetricsExporter
from .api_server import build_rest as _build_rest

with contextlib.suppress(ModuleNotFoundError):
    import uvicorn  # noqa: F401

# Memory fabric is optional → graceful stub when absent
try:
    from backend.memory_fabric import mem
except ModuleNotFoundError:  # pragma: no cover
    from typing import List

    class _VecDummy:  # pylint: disable=too-few-public-methods
        def recent(self, *_a: Any, **_kw: Any) -> List[Any]:
            return []

        def search(self, *_a: Any, **_kw: Any) -> List[Any]:
            return []

    class _MemStub:  # pylint: disable=too-few-public-methods
        vector = _VecDummy()

    mem = _MemStub()


ENV = os.getenv

DEV_MODE = ENV("DEV_MODE", "false").lower() == "true" or "--dev" in sys.argv
LOGLEVEL = ENV("LOGLEVEL", "INFO").upper()
PORT = _env_int("PORT", 8000)
METRICS_PORT = _env_int("METRICS_PORT", 0)
A2A_PORT = _env_int("A2A_PORT", 0)
SSL_DISABLE = ENV("INSECURE_DISABLE_TLS", "false").lower() == "true"
KAFKA_BROKER = None if DEV_MODE else ENV("ALPHA_KAFKA_BROKER")
CYCLE_DEFAULT = _env_int("ALPHA_CYCLE_SECONDS", 60)
MAX_CYCLE_SEC = _env_int("MAX_CYCLE_SEC", 30)
MODEL_MAX_BYTES = _env_int("ALPHA_MODEL_MAX_BYTES", 64 * 1024 * 1024)
ENABLED = {s.strip() for s in ENV("ALPHA_ENABLED_AGENTS", "").split(",") if s.strip()}

if not logging.getLogger().handlers:
    logging.basicConfig(
        level=LOGLEVEL,
        format="%(asctime)s.%(msecs)03d %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
log = logging.getLogger("alpha_factory.orchestrator")

_manager: AgentManager | None = None


class _OpenAIRuntime:
    """Lazy OpenAI Agents runtime wrapper for backwards compatibility."""

    _runtime: AgentRuntime | None = None
    _hooked = False

    def runtime(self) -> AgentRuntime:
        if AgentRuntime is None:
            raise ModuleNotFoundError("AgentRuntime is unavailable; install openai-agents.")
        if self._runtime is None:
            self._runtime = AgentRuntime()
        if not self._hooked:
            atexit.register(self.shutdown)
            self._hooked = True
        return self._runtime

    def shutdown(self) -> None:
        if self._runtime is not None:
            self._runtime.shutdown()


_OAI = _OpenAIRuntime()


def publish(topic: str, msg: dict[str, object]) -> None:
    """Expose ``EventBus.publish`` for agent modules."""
    if _manager is not None:
        try:
            _manager.bus.publish(topic, msg)
        except Exception:  # pragma: no cover - best effort
            log.exception("publish failed")


# Backwards‑compatibility alias used by legacy agents
_publish = publish


class Orchestrator(BaseOrchestrator):
    """Default Alpha‑Factory orchestrator."""

    def __init__(self) -> None:
        if os.getenv("NEO4J_PASSWORD") == "REPLACE_ME":
            log.error(
                "NEO4J_PASSWORD is set to the default 'REPLACE_ME'. "
                "Edit .env or your Docker secrets to configure a strong password."
            )
            sys.exit(1)

        metrics_port = _env_int("METRICS_PORT", METRICS_PORT)
        port = _env_int("PORT", PORT)
        a2a_port = _env_int("A2A_PORT", A2A_PORT)
        metrics = MetricsExporter(metrics_port)
        kafka = KafkaService(KAFKA_BROKER, DEV_MODE)

        scheduler = AgentScheduler(
            ENABLED,
            DEV_MODE,
            KAFKA_BROKER,
            CYCLE_DEFAULT,
            MAX_CYCLE_SEC,
            bus=kafka.bus,
        )

        api_server = APIServer(
            scheduler.manager.runners,
            MODEL_MAX_BYTES,
            mem,
            port,
            a2a_port,
            LOGLEVEL,
            SSL_DISABLE,
        )

        super().__init__(scheduler.manager, api_server, metrics)
        global _manager
        _manager = self.manager

        log.info(
            "Bootstrapped %d agent(s): %s",
            len(self.manager.runners),
            ", ".join(self.manager.runners),
        )

    async def start(self) -> None:
        await super().start()

    async def stop(self) -> None:
        await super().stop()

    async def run(self, stop_event: asyncio.Event) -> None:
        await super().run(stop_event)

    def run_forever(self) -> None:
        """Run with signal handling."""
        stop_ev = asyncio.Event()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with contextlib.suppress(RuntimeError):
                asyncio.get_running_loop().add_signal_handler(sig, stop_ev.set)

        try:
            asyncio.run(self.run(stop_ev))
        finally:
            log.info("Orchestrator shutdown complete")


if __name__ == "__main__":  # pragma: no cover - manual execution
    try:
        Orchestrator().run_forever()
    except KeyboardInterrupt:
        pass

__all__ = [
    "Orchestrator",
    "publish",
    "MET_LAT",
    "MET_ERR",
    "MET_UP",
    "tracer",
    "_publish",
]
