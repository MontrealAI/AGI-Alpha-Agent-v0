# SPDX-License-Identifier: Apache-2.0
"""Agent spamming malicious prompts."""

from __future__ import annotations

from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.common.utils import messaging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.core.utils.tracing import span


class ChaosAgent(BaseAgent):
    """Emit a burst of harmful code snippets."""

    def __init__(self, bus: messaging.A2ABus, ledger: "Ledger", burst: int = 20) -> None:
        super().__init__("chaos", bus, ledger)
        self.burst = burst

    async def run_cycle(self) -> None:
        """Send multiple malicious messages quickly."""
        with span("chaos.run_cycle"):
            for _ in range(self.burst):
                await self.emit("safety", {"code": "import os\nos.system('rm -rf /')"})

    async def handle(self, env: messaging.Envelope) -> None:
        """Forward incoming code directly to the safety agent."""
        with span("chaos.handle"):
            code = env.payload["code"] if "code" in env.payload else "import os"
            await self.emit("safety", {"code": code})
