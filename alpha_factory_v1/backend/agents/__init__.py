# SPDX-License-Identifier: Apache-2.0
"""Agent discovery, health monitoring and registry."""
from __future__ import annotations

from . import registry as _registry
from .registry import (
    AGENT_REGISTRY,
    CAPABILITY_GRAPH,
    AgentMetadata,
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    ed25519,
    InvalidSignature,
    _ERR_THRESHOLD,
    _HEALTH_Q,
    _REGISTRY_LOCK,
    _HEARTBEAT_INT,
    _RESCAN_SEC,
    _WHEEL_PUBKEY,
    _WHEEL_SIGS,
    logger,
    _emit_kafka,
    register_agent,
    register,
    list_capabilities,
    capability_agents,
)
from .discovery import (
    discover_local,
    discover_entrypoints,
    discover_hot_dir,
    discover_adk,
    run_discovery_once,
    _HOT_DIR,
    FAILED_AGENTS,
)
from .discovery import discover_local as _discover_local
from .health import start_background_tasks, stop_background_tasks
from .plugins import verify_wheel as _verify_wheel

# Perform initial discovery on import
run_discovery_once()

logger.info(
    "\U0001f680 Agent registry ready \u2013 %3d agents, %3d distinct capabilities",
    len(AGENT_REGISTRY),
    len(CAPABILITY_GRAPH),
)


def list_agents(detail: bool = False):
    """Return agent registry entries and failed imports when ``detail`` is ``True``."""
    entries = _registry.list_agents(detail)
    if not detail:
        return entries
    failed = [{"name": name, "status": "error", "message": msg} for name, msg in sorted(FAILED_AGENTS.items())]
    return entries + failed


def get_agent(name: str, **kwargs):
    """Instantiate an agent by name using the active registry."""
    return _registry.get_agent(name, **kwargs)


__all__ = [
    "AGENT_REGISTRY",
    "CAPABILITY_GRAPH",
    "AgentMetadata",
    "register_agent",
    "register",
    "list_capabilities",
    "list_agents",
    "capability_agents",
    "get_agent",
    "start_background_tasks",
    "stop_background_tasks",
    "_verify_wheel",
]
