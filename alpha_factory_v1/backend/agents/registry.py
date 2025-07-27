# SPDX-License-Identifier: Apache-2.0
"""Agent registry, metadata and public APIs."""
from __future__ import annotations

import asyncio
import inspect
import json
import logging
import os

logger = logging.getLogger("alpha_factory.agents")
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Type

try:  # ≥ Py 3.10 std-lib metadata
    import importlib.metadata as imetadata
except ModuleNotFoundError:  # pragma: no cover
    logger.warning("importlib_metadata backport required on this Python")
    import importlib_metadata as imetadata  # type: ignore

try:  # Kafka telemetry
    from kafka import KafkaProducer  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    logger.warning("kafka-python missing – registry heartbeat disabled")
    KafkaProducer = None  # type: ignore

try:  # Prometheus metrics
    from prometheus_client import (
        Counter as _Counter,
        Gauge as _Gauge,
        Histogram as _Histogram,
        CollectorRegistry,
    )  # type: ignore
    from alpha_factory_v1.backend.metrics_registry import get_metric as _reg_metric

    def _get_metric(cls, name: str, desc: str, labels=None):
        return _reg_metric(cls, name, desc, labels)

    def Counter(name: str, desc: str, labels=None):  # type: ignore[misc]
        return _get_metric(_Counter, name, desc, labels)

    def Gauge(name: str, desc: str, labels=None):  # type: ignore[misc]
        return _get_metric(_Gauge, name, desc, labels)

    def Histogram(name: str, desc: str, labels=None):  # type: ignore[misc]
        return _get_metric(_Histogram, name, desc, labels)

except ModuleNotFoundError:  # pragma: no cover
    logger.warning("prometheus_client missing – metrics disabled")
    Counter = Gauge = Histogram = CollectorRegistry = None  # type: ignore

try:
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.exceptions import InvalidSignature
except ModuleNotFoundError:  # pragma: no cover
    logger.warning("cryptography library missing – wheel signing disabled")
    ed25519 = None  # type: ignore
    InvalidSignature = Exception  # type: ignore

try:
    from packaging.version import parse as _parse_version  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    logger.warning("packaging not installed – version parsing downgraded")

    def _parse_version(v: str):
        return tuple(int(p) for p in v.split(".") if p.isdigit())


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------
_OPENAI_READY = bool(os.getenv("OPENAI_API_KEY"))
_KAFKA_BROKER = os.getenv("ALPHA_KAFKA_BROKER")
_DISABLED = {x.strip().lower() for x in os.getenv("DISABLED_AGENTS", "").split(",") if x.strip()}
_ERR_THRESHOLD = int(os.getenv("AGENT_ERR_THRESHOLD", 3))
_HEARTBEAT_INT = int(os.getenv("AGENT_HEARTBEAT_SEC", 10))
_RESCAN_SEC = int(os.getenv("AGENT_RESCAN_SEC", 60))
_WHEEL_PUBKEY = os.getenv(
    "AGENT_WHEEL_PUBKEY",
    "vGX59ownuBM9Z6e4tXesOv8+xhPf4dC7b8P6kp9hPJo=",
)
_WHEEL_SIGS: Dict[str, str] = {
    "example_agent.whl": ("XKyQtzeUaE2EkbB0Up4teNr+i6gRSNE3Gcy6q605jQogZXjjp4pfxkGko/VDvJCGJgHD5X0fo30Mk+ESwQC9Q==")
}

# ---------------------------------------------------------------------------
# logging
# ---------------------------------------------------------------------------
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s  %(levelname)-8s  %(name)s: %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# datatypes
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AgentMetadata:
    """Lightweight manifest describing an agent implementation."""

    name: str
    cls: Type
    version: str = "0.1.0"
    capabilities: List[str] = field(default_factory=list)
    compliance_tags: List[str] = field(default_factory=list)
    requires_api_key: bool = False
    err_count: int = 0  # mutated via object.__setattr__

    def as_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "capabilities": self.capabilities,
            "compliance": self.compliance_tags,
            "requires_api_key": self.requires_api_key,
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), separators=(",", ":"))

    def instantiate(self, **kw):
        return self.cls(**kw)  # type: ignore[arg-type]


class CapabilityGraph(Dict[str, List[str]]):
    """capability → [agent names]."""

    def add(self, capability: str, agent_name: str) -> None:
        self.setdefault(capability, []).append(agent_name)


class StubAgent:  # pragma: no cover
    """Inert replacement for quarantined or unavailable agents."""

    NAME = "stub"
    CAPABILITIES: List[str] = []
    COMPLIANCE_TAGS: List[str] = []
    REQUIRES_API_KEY = False
    SLEEP = 3600

    async def step(self) -> None:
        await asyncio.sleep(self.SLEEP)


# ---------------------------------------------------------------------------
# internal state
# ---------------------------------------------------------------------------
AGENT_REGISTRY: Dict[str, AgentMetadata] = {}
CAPABILITY_GRAPH: CapabilityGraph = CapabilityGraph()
_HEALTH_Q: "queue.Queue[tuple[str, float, bool]]" = queue.Queue()
_REGISTRY_LOCK = threading.Lock()

if Counter is not None:
    _err_counter = Counter(
        "af_agent_exceptions_total",
        "Exceptions raised by agents",
        ["agent"],
    )
else:  # pragma: no cover - metrics disabled
    _err_counter = None

# ---------------------------------------------------------------------------
# helper – Kafka producer
# ---------------------------------------------------------------------------


def _kafka_producer() -> Optional[KafkaProducer]:
    if not _KAFKA_BROKER or KafkaProducer is None:
        return None
    try:
        return KafkaProducer(
            bootstrap_servers=_KAFKA_BROKER,
            value_serializer=lambda v: v.encode() if isinstance(v, str) else v,
        )
    except Exception:  # noqa: BLE001
        logger.exception("Kafka producer init failed")
        return None


_PRODUCER = _kafka_producer()


def _emit_kafka(topic: str, payload: str) -> None:
    if _PRODUCER is None:
        return
    try:
        _PRODUCER.send(topic, payload)
        _PRODUCER.flush()
    except Exception:  # noqa: BLE001
        logger.exception("Kafka emit failed (topic=%s)", topic)


# ---------------------------------------------------------------------------
# unified decorator
# ---------------------------------------------------------------------------


def register(cls=None, *, condition=True):  # type: ignore
    """Decorator adding an :class:`AgentBase` subclass to the registry."""

    def decorator(inner_cls):
        from_backend_base = _agent_base()
        if not issubclass(inner_cls, from_backend_base):
            raise TypeError("register() only allowed on AgentBase subclasses")

        cond_result = condition() if callable(condition) else bool(condition)
        if cond_result:
            meta = AgentMetadata(
                name=getattr(inner_cls, "NAME", inner_cls.__name__),
                cls=inner_cls,
                version=getattr(inner_cls, "__version__", "0.1.0"),
                capabilities=list(getattr(inner_cls, "CAPABILITIES", [])),
                compliance_tags=list(getattr(inner_cls, "COMPLIANCE_TAGS", [])),
                requires_api_key=getattr(inner_cls, "REQUIRES_API_KEY", False),
            )
            _register(meta, overwrite=False)
        else:
            logger.info(
                "Agent %s not registered (condition=false)",
                getattr(inner_cls, "NAME", inner_cls.__name__),
            )
        return inner_cls

    return decorator(cls) if cls is not None else decorator


# ---------------------------------------------------------------------------
# utility to import the master AgentBase
# ---------------------------------------------------------------------------


def _agent_base():
    """Return the canonical AgentBase implementation."""

    try:
        from backend.agents.base import AgentBase  # type: ignore

        return AgentBase
    except ModuleNotFoundError:  # pragma: no cover - legacy only
        from backend.agent_base import AgentBase  # type: ignore

        return AgentBase


# ---------------------------------------------------------------------------


def _should_register(meta: AgentMetadata) -> bool:
    if meta.name.lower() in _DISABLED:
        logger.info("Agent %s disabled via env", meta.name)
        return False
    if meta.name == "ping" and os.getenv("AF_DISABLE_PING_AGENT", "").lower() in ("1", "true"):
        logger.info("Ping agent disabled via AF_DISABLE_PING_AGENT")
        return False
    if meta.requires_api_key and not _OPENAI_READY:
        logger.warning("Skipping %s (needs OpenAI key)", meta.name)
        return False
    return True


def _register(meta: AgentMetadata, *, overwrite: bool = False) -> None:
    if not _should_register(meta):
        return
    with _REGISTRY_LOCK:
        if meta.name in AGENT_REGISTRY and not overwrite:
            existing = AGENT_REGISTRY[meta.name]
            try:
                if _parse_version(meta.version) > _parse_version(existing.version):
                    logger.info(
                        "Overriding agent %s with newer version %s > %s",
                        meta.name,
                        meta.version,
                        existing.version,
                    )
                    overwrite = True
                else:
                    logger.error("Duplicate agent name '%s' ignored", meta.name)
                    return
            except Exception:  # pragma: no cover - version parse failed
                logger.error("Duplicate agent name '%s' ignored", meta.name)
                return

        AGENT_REGISTRY[meta.name] = meta
        for cap in meta.capabilities:
            CAPABILITY_GRAPH.add(cap, meta.name)

    logger.info("\u2713 agent %-18s caps=%s", meta.name, ",".join(meta.capabilities))
    _emit_kafka("agent.manifest", meta.to_json())


# ---------------------------------------------------------------------------
# public convenience API
# ---------------------------------------------------------------------------


def list_agents(detail: bool = False):
    with _REGISTRY_LOCK:
        metas = sorted(AGENT_REGISTRY.values(), key=lambda m: m.name)
    return [m.as_dict() if detail else m.name for m in metas]


def capability_agents(capability: str):
    """Return list of agent names exposing *capability*."""
    with _REGISTRY_LOCK:
        return CAPABILITY_GRAPH.get(capability, []).copy()


def list_capabilities():
    """Return sorted list of all capabilities currently registered."""
    with _REGISTRY_LOCK:
        return sorted(CAPABILITY_GRAPH.keys())


def get_agent(name: str, **kwargs):
    """Instantiate agent by *name* and wrap its async ``step`` coroutine."""
    with _REGISTRY_LOCK:
        meta = AGENT_REGISTRY[name]
    agent = meta.instantiate(**kwargs)

    if hasattr(agent, "step") and inspect.iscoroutinefunction(agent.step):
        orig = agent.step

        async def _wrapped(*a, **kw):  # type: ignore[no-untyped-def]
            t0 = time.perf_counter()
            ok = True
            try:
                return await orig(*a, **kw)  # type: ignore[misc]
            except Exception:  # noqa: BLE001
                ok = False
                raise
            finally:
                _HEALTH_Q.put((meta.name, (time.perf_counter() - t0) * 1000, ok))

        agent.step = _wrapped  # type: ignore[assignment]

    return agent


def register_agent(meta: AgentMetadata, *, overwrite: bool = False) -> None:
    """Public hook for dynamically-generated agents to self-register."""
    _register(meta, overwrite=overwrite)


__all__ = [
    "AgentMetadata",
    "AGENT_REGISTRY",
    "CAPABILITY_GRAPH",
    "register_agent",
    "register",
    "list_capabilities",
    "list_agents",
    "capability_agents",
    "get_agent",
]
