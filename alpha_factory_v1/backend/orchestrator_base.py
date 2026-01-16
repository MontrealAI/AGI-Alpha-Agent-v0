# SPDX-License-Identifier: Apache-2.0
"""Common orchestrator utilities used across demos."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Optional

from .agent_manager import AgentManager
from .services import APIServer, MetricsExporter


class BaseOrchestrator:
    """Simple helper managing an :class:`AgentManager` and optional servers."""

    def __init__(self, manager: AgentManager, api_server: APIServer, metrics: MetricsExporter | None = None) -> None:
        self.manager = manager
        self.api_server = api_server
        self.metrics = metrics

    async def start(self) -> None:
        """Launch REST and gRPC servers and background tasks."""
        if self.metrics:
            self.metrics.start()
        await self.api_server.start()
        await self.manager.start()

    async def stop(self) -> None:
        """Stop servers and agent manager."""
        await self.manager.stop()
        await self.api_server.stop()
        if self.metrics:
            self.metrics.stop()

    async def run(self, stop_event: asyncio.Event) -> None:
        """Run until ``stop_event`` is set."""
        if self.metrics:
            self.metrics.start()
        await self.api_server.start()
        await self.manager.run(stop_event)
        await self.api_server.stop()
        if self.metrics:
            self.metrics.stop()

    def run_forever(self) -> None:
        """Convenience wrapper used by scripts."""
        asyncio.run(self.run(asyncio.Event()))
