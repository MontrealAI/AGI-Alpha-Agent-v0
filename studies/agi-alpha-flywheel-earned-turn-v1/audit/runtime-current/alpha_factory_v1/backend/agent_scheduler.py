# SPDX-License-Identifier: Apache-2.0
"""Agent scheduling utilities."""

from __future__ import annotations

import asyncio

from .agent_manager import AgentManager
from .agent_runner import EventBus


class AgentScheduler:
    """Drive a collection of agents through the :class:`AgentManager`."""

    def __init__(
        self,
        enabled: set[str],
        dev_mode: bool,
        kafka_broker: str | None,
        cycle_seconds: int,
        max_cycle_sec: int,
        *,
        bus: EventBus | None = None,
    ) -> None:
        self.manager = AgentManager(
            enabled,
            dev_mode,
            kafka_broker,
            cycle_seconds,
            max_cycle_sec,
            bus=bus,
        )

    async def start(self) -> None:
        """Start heartbeat and regression checks."""
        await self.manager.start()

    async def stop(self) -> None:
        """Stop the underlying manager."""
        await self.manager.stop()

    async def run(self, stop_event: asyncio.Event) -> None:
        """Run agent cycles until ``stop_event`` is set."""
        await self.start()
        await self.manager.run(stop_event)
        await self.stop()


__all__ = ["AgentScheduler"]
