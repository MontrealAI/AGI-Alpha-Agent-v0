# SPDX-License-Identifier: Apache-2.0
"""Utilities for supervising agents.

This module centralises heartbeat checks and restart logic so demos
can reuse the same implementation instead of rolling their own.
"""

from __future__ import annotations

import asyncio
import contextlib
import random
import time
import os
from typing import Callable, Dict

from google.protobuf import struct_pb2


class AgentRunner:
    """Wrap a single agent instance and expose lifecycle helpers."""

    def __init__(self, agent: object) -> None:
        self.cls: Callable[..., object] = type(agent)
        self.agent = agent
        self.period = getattr(agent, "CYCLE_SECONDS", 1.0)
        self.capabilities = getattr(agent, "CAPABILITIES", [])
        self.last_beat = time.time()
        self.restarts = 0
        self.task: asyncio.Task[None] | None = None
        self.error_count = 0
        self.restart_streak = 0

    async def loop(self, bus: object, ledger: object) -> None:
        """Run the agent cycle indefinitely."""
        while True:
            start = time.perf_counter()
            try:
                await self.agent.run_cycle()
            except Exception as exc:  # noqa: BLE001
                if hasattr(bus, "alert"):
                    try:
                        bus.alert(f"{self.agent.name} failed: {exc}")
                    except Exception:  # pragma: no cover - best effort
                        pass
                self.error_count += 1
            else:
                self.error_count = 0
                self.restart_streak = 0
                env = struct_pb2.Struct()
                env.update({"heartbeat": True})
                if hasattr(ledger, "log"):
                    try:
                        ledger.log(env)
                    except Exception:  # pragma: no cover - logging optional
                        pass
                if hasattr(bus, "publish"):
                    try:
                        bus.publish("orch", env)
                    except Exception:  # pragma: no cover - publish optional
                        pass
                self.last_beat = time.time()
            finally:
                if hasattr(bus, "metrics"):
                    try:
                        bus.metrics.observe(time.perf_counter() - start)
                    except Exception:  # pragma: no cover - metrics optional
                        pass
            await asyncio.sleep(self.period)

    def start(self, bus: object, ledger: object) -> None:
        self.task = asyncio.create_task(self.loop(bus, ledger))

    async def restart(self, bus: object, ledger: object) -> None:
        if self.task:
            self.task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.task
        try:
            close = getattr(self.agent, "close")
        except AttributeError:
            pass
        else:
            close()
        self.agent = self.cls(bus, ledger)
        self.error_count = 0
        self.restarts += 1
        self.restart_streak += 1
        self.start(bus, ledger)


async def monitor_agents(
    runners: Dict[str, AgentRunner],
    bus: object,
    ledger: object,
    *,
    err_threshold: int = 3,
    backoff_exp_after: int = 3,
    on_restart: Callable[[AgentRunner], None] | None = None,
) -> None:
    """Restart crashed or stalled agents and apply exponential backoff."""
    while True:
        await asyncio.sleep(2)
        try:
            err_threshold = int(os.getenv("AGENT_ERR_THRESHOLD", err_threshold))
        except (TypeError, ValueError):
            pass
        try:
            backoff_exp_after = int(os.getenv("AGENT_BACKOFF_EXP_AFTER", backoff_exp_after))
        except (TypeError, ValueError):
            pass
        now = time.time()
        for r in list(runners.values()):
            needs_restart = False
            if r.task and r.task.done():
                needs_restart = True
            elif r.error_count >= err_threshold:
                needs_restart = True
            elif now - r.last_beat > r.period * 5:
                needs_restart = True
            if needs_restart:
                delay = random.uniform(0.5, 1.5)
                if r.restart_streak >= backoff_exp_after:
                    delay *= 2 ** (r.restart_streak - backoff_exp_after + 1)
                await asyncio.sleep(delay)
                await r.restart(bus, ledger)
                if on_restart:
                    on_restart(r)


def handle_heartbeat(runners: Dict[str, AgentRunner], env: object) -> None:
    """Update the heartbeat timestamp for ``env.sender`` if it exists."""
    payload = getattr(env, "payload", None)
    if payload and getattr(payload, "get", lambda *_: None)("heartbeat"):
        sender = getattr(env, "sender", None)
        if sender in runners:
            r = runners[sender]
            r.last_beat = getattr(env, "ts", time.time())
            r.restart_streak = 0


__all__ = ["AgentRunner", "monitor_agents", "handle_heartbeat"]
