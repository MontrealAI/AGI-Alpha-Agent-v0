# SPDX-License-Identifier: Apache-2.0
"""Background health monitoring for agents."""
from __future__ import annotations

import asyncio
import contextlib
import json
import time
from queue import Empty

from .registry import (
    _HEALTH_Q,
    _HEARTBEAT_INT,
    _RESCAN_SEC,
    AGENT_REGISTRY,
    _REGISTRY_LOCK,
    AgentMetadata,
    StubAgent,
    Counter,
    logger,
    _err_counter,
    _register,
    _emit_kafka,
    _ERR_THRESHOLD,
)
from .discovery import discover_hot_dir


def handle_health_event(name: str, latency_ms: float, ok: bool) -> None:
    """Apply a single heartbeat update to the registry."""
    quarantine = False
    stub_meta: AgentMetadata | None = None
    with _REGISTRY_LOCK:
        meta = AGENT_REGISTRY.get(name)
        if meta and not ok:
            if Counter:
                _err_counter.labels(agent=name).inc()  # type: ignore[attr-defined]
            object.__setattr__(meta, "err_count", meta.err_count + 1)
            if meta.err_count >= _ERR_THRESHOLD:  # type: ignore[name-defined]
                logger.error(
                    "\N{NO ENTRY SIGN} Quarantining agent '%s' after %d consecutive errors",
                    name,
                    meta.err_count,
                )
                stub_meta = AgentMetadata(
                    name=meta.name,
                    cls=StubAgent,
                    version=meta.version + "+stub",
                    capabilities=meta.capabilities,
                    compliance_tags=meta.compliance_tags,
                )
                quarantine = True

    if quarantine and stub_meta:
        _register(stub_meta, overwrite=True)

    logger.debug(
        "heartbeat: %s ok=%s latency=%.1fms",
        name,
        ok,
        latency_ms,
    )
    _emit_kafka(  # type: ignore[name-defined]
        "agent.heartbeat",
        json.dumps({"name": name, "latency_ms": latency_ms, "ok": ok, "ts": time.time()}),
    )


async def _health_loop() -> None:
    """Consume heartbeat reports and handle quarantines."""
    try:
        while True:
            try:
                name, latency_ms, ok = await asyncio.to_thread(_HEALTH_Q.get, timeout=_HEARTBEAT_INT)
            except Empty:
                continue
            handle_health_event(name, latency_ms, ok)
    except asyncio.CancelledError:
        pass


async def _rescan_loop() -> None:  # pragma: no cover
    try:
        while True:
            try:
                discover_hot_dir()
            except Exception:  # noqa: BLE001
                logger.exception("Hot-dir rescan failed")
            await asyncio.sleep(_RESCAN_SEC)
    except asyncio.CancelledError:
        pass


_bg_started = False
_health_task: asyncio.Task[None] | None = None
_rescan_task: asyncio.Task[None] | None = None


async def start_background_tasks() -> None:
    """Launch health monitor and rescan loops exactly once."""
    global _bg_started, _health_task, _rescan_task
    if _bg_started and _health_task and not _health_task.done():
        return
    _bg_started = True
    loop = asyncio.get_running_loop()
    if _health_task is None or _health_task.done():
        _health_task = loop.create_task(_health_loop(), name="agent-health")
    if _rescan_task is None or _rescan_task.done():
        _rescan_task = loop.create_task(_rescan_loop(), name="agent-rescan")


async def stop_background_tasks() -> None:
    """Cancel background health and rescan loops."""
    global _bg_started, _health_task, _rescan_task
    if not _bg_started:
        return
    _bg_started = False
    tasks = [_health_task, _rescan_task]
    for t in tasks:
        if t:
            t.cancel()
    for t in tasks:
        if t:
            with contextlib.suppress(asyncio.CancelledError):
                await t
    _health_task = _rescan_task = None
