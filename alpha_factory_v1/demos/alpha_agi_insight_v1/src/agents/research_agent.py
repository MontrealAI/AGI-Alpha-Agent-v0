# SPDX-License-Identifier: Apache-2.0
"""Agent that converts a plan into research data.

During each cycle the agent runs a tiny evolutionary loop to estimate
capability growth. Results are forwarded to the strategy agent via
:meth:`run_cycle` and :meth:`handle` processes incoming planning messages.
"""

from __future__ import annotations

import random

from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.core.simulation.forecast import forecast_disruptions
from alpha_factory_v1.core.simulation import sector
from alpha_factory_v1.common.utils import messaging, logging as insight_logging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils.retry import with_retry
from alpha_factory_v1.core.utils.tracing import span
from typing import Callable, Awaitable, cast

log = insight_logging.logging.getLogger(__name__)


class ResearchAgent(BaseAgent):
    """Perform simple research based on plans from :class:`PlanningAgent`."""

    def __init__(
        self,
        bus: messaging.A2ABus,
        ledger: "Ledger",
        *,
        backend: str = "gpt-4o",
        island: str = "default",
    ) -> None:
        super().__init__("research", bus, ledger, backend=backend, island=island)

    async def run_cycle(self) -> None:
        """Periodic sweep using a tiny evolutionary loop."""
        with span("research.run_cycle"):
            secs = [sector.Sector(f"s{i}") for i in range(3)]
            traj = forecast_disruptions(secs, 1)
            if self.adk:
                try:  # pragma: no cover - optional
                    with span("adk.heartbeat"):
                        self.adk.heartbeat()
                    with span("adk.list_packages"):
                        _ = len(self.adk.list_packages())
                except Exception as exc:
                    log.warning("adk interaction failed: %s", exc)
            if self.mcp:
                try:  # pragma: no cover - optional
                    with span("mcp.heartbeat"):
                        self.mcp.heartbeat()
                    with span("mcp.invoke"):
                        try:
                            result = await self.mcp.invoke_tool("noop", {})
                        except Exception as exc:
                            log.warning("mcp.invoke_tool failed: %s", exc)
                            result = None
                    if result is not None:
                        await self.emit("memory", {"noop": result})
                except Exception as exc:
                    log.warning("mcp interaction failed: %s", exc)
            await self.emit("strategy", {"research": traj[0].capability})

    async def handle(self, env: messaging.Envelope) -> None:
        """Process planning requests and emit research results."""
        with span("research.handle"):
            plan = env.payload["plan"] if "plan" in env.payload else ""
            cap = random.random()
            if self.oai_ctx and not self.bus.settings.offline:
                try:  # pragma: no cover
                    with span("openai.run"):
                        cap = float(
                            await with_retry(cast(Callable[[str], Awaitable[str]], self.oai_ctx.run))(str(plan))
                        )
                except Exception as exc:
                    log.warning("openai.run failed: %s", exc)
            await self.emit("strategy", {"research": cap})
