# SPDX-License-Identifier: Apache-2.0
"""Agent that translates strategy actions into market analysis.

The market agent periodically emits neutral market data and updates its
analysis when receiving new strategy information. Generated insights are
passed to the :class:`CodeGenAgent`.
"""

from __future__ import annotations

from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.common.utils import messaging, logging as insight_logging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils.retry import with_retry
from alpha_factory_v1.core.utils.tracing import span
from typing import Callable, Awaitable, cast

log = insight_logging.logging.getLogger(__name__)


class MarketAgent(BaseAgent):
    """Analyse markets and forward results to the code generator."""

    def __init__(
        self,
        bus: messaging.A2ABus,
        ledger: "Ledger",
        *,
        backend: str = "gpt-4o",
        island: str = "default",
    ) -> None:
        super().__init__("market", bus, ledger, backend=backend, island=island)

    async def run_cycle(self) -> None:
        """Emit a periodic market snapshot."""
        with span("market.run_cycle"):
            await self.emit("codegen", {"analysis": "neutral"})

    async def handle(self, env: messaging.Envelope) -> None:
        """Process strategy input and compute market impact."""
        with span("market.handle"):
            strategy = env.payload["strategy"] if "strategy" in env.payload else None
            analysis = f"impact of {strategy}"
            if self.oai_ctx and not self.bus.settings.offline:
                try:  # pragma: no cover
                    with span("openai.run"):
                        analysis = await with_retry(cast(Callable[[str], Awaitable[str]], self.oai_ctx.run))(
                            str(strategy)
                        )
                except Exception as exc:
                    log.warning("openai.run failed: %s", exc)
            await self.emit("codegen", {"analysis": analysis})
