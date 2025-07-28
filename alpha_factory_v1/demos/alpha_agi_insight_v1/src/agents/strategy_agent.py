# SPDX-License-Identifier: Apache-2.0
"""Agent composing high level strategy from research results.

The agent consumes ``research`` messages and generates a short action plan
for the market agent. It can optionally leverage a local or remote LLM during
:meth:`handle`.
"""

from __future__ import annotations

from alpha_factory_v1.core.agents.base_agent import BaseAgent
from alpha_factory_v1.common.utils import messaging, logging as insight_logging
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.common.utils.retry import with_retry
from alpha_factory_v1.core.utils.tracing import span
from typing import Callable, Awaitable, cast

log = insight_logging.logging.getLogger(__name__)


class StrategyAgent(BaseAgent):
    """Turn research output into actionable strategy."""

    def __init__(
        self,
        bus: messaging.A2ABus,
        ledger: "Ledger",
        *,
        backend: str = "gpt-4o",
        island: str = "default",
    ) -> None:
        super().__init__("strategy", bus, ledger, backend=backend, island=island)

    async def run_cycle(self) -> None:
        """No-op periodic loop."""
        return None

    async def handle(self, env: messaging.Envelope) -> None:
        """Compose a strategy from research results."""
        with span("strategy.handle"):
            val = env.payload["research"] if "research" in env.payload else None
            strat = {"action": f"monitor {val}"}
            if self.bus.settings.offline:
                try:
                    from alpha_factory_v1.common.utils import local_llm

                    with span("local_llm.chat"):
                        strat["action"] = with_retry(local_llm.chat)(str(val), self.bus.settings)
                except Exception as exc:  # pragma: no cover - model optional
                    log.warning("local_llm.chat failed: %s", exc)
            elif self.oai_ctx:
                try:  # pragma: no cover
                    with span("openai.run"):
                        strat["action"] = await with_retry(cast(Callable[[str], Awaitable[str]], self.oai_ctx.run))(
                            str(val)
                        )
                except Exception as exc:
                    log.warning("openai.run failed: %s", exc)
            await self.emit("market", {"strategy": strat})
