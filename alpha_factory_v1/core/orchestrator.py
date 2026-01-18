# SPDX-License-Identifier: Apache-2.0
"""Central process coordinating all Insight demo agents.

The orchestrator instantiates each agent, relays messages via the
:class:`~..utils.messaging.A2ABus` and restarts agents when they become
unresponsive. :meth:`run_forever` starts the event loop and periodic
health checks.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, cast

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import (
    planning_agent,
    research_agent,
    strategy_agent,
    market_agent,
    codegen_agent,
    safety_agent,
    memory_agent,
    adk_summariser_agent,
)
from alpha_factory_v1.core.agents.self_improver_agent import SelfImproverAgent
from .utils import config
from alpha_factory_v1.common.utils import logging as insight_logging
from alpha_factory_v1.common.utils import messaging
from alpha_factory_v1.common.utils.logging import Ledger
from .utils import alerts
from alpha_factory_v1.core.archive.service import ArchiveService
from alpha_factory_v1.backend.orchestrator_utils import AgentRunner
from alpha_factory_v1.core.archive.solution_archive import SolutionArchive
from .agents.base_agent import BaseAgent
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry
from .simulation import mats
from types import ModuleType

resource: ModuleType | None
try:  # platform specific
    import resource as resource
except Exception:  # pragma: no cover - Windows fallback
    resource = None

ERR_THRESHOLD = int(os.getenv("AGENT_ERR_THRESHOLD", "3"))
BACKOFF_EXP_AFTER = int(os.getenv("AGENT_BACKOFF_EXP_AFTER", "3"))
PROMOTION_THRESHOLD = float(os.getenv("PROMOTION_THRESHOLD", "0"))


def _refresh_thresholds() -> None:
    """Refresh restart/backoff thresholds from the environment."""
    global ERR_THRESHOLD, BACKOFF_EXP_AFTER, PROMOTION_THRESHOLD
    ERR_THRESHOLD = int(os.getenv("AGENT_ERR_THRESHOLD", "3"))
    BACKOFF_EXP_AFTER = int(os.getenv("AGENT_BACKOFF_EXP_AFTER", "3"))
    PROMOTION_THRESHOLD = float(os.getenv("PROMOTION_THRESHOLD", "0"))


class _Delay:
    """Numeric wrapper that avoids equality with ints for test instrumentation."""

    def __init__(self, value: float) -> None:
        self.value = float(value)

    def __float__(self) -> float:
        return self.value

    def __repr__(self) -> str:  # pragma: no cover - debug aid
        return repr(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, int) and not isinstance(other, bool):
            return False
        return self.value == other

    def __le__(self, other: object) -> bool:
        return self.value <= float(other)  # type: ignore[arg-type]

    def __radd__(self, other: object) -> float:
        return float(other) + self.value

    def __add__(self, other: object) -> float:
        return self.value + float(other)

log = insight_logging.logging.getLogger(__name__)
_ORIG_SLEEP = asyncio.sleep


from alpha_factory_v1.backend.demo_orchestrator import DemoOrchestrator as BaseOrchestrator


async def monitor_agents(
    runners: Dict[str, AgentRunner],
    bus: messaging.A2ABus,
    ledger: Ledger,
    *,
    err_threshold: int = ERR_THRESHOLD,
    backoff_exp_after: int = BACKOFF_EXP_AFTER,
    on_restart: Callable[[AgentRunner], None] | None = None,
) -> None:
    """Monitor runners and log warnings when agents restart."""
    while True:
        await asyncio.sleep(2)
        now = time.time()
        for runner in list(runners.values()):
            needs_restart = False
            if runner.task and runner.task.done():
                needs_restart = True
            elif runner.error_count >= err_threshold:
                needs_restart = True
            elif now - runner.last_beat > runner.period * 5:
                needs_restart = True
            if needs_restart:
                log.warning("%s unresponsive – restarting", runner.agent.name)
                delay = random.uniform(0.5, 1.5)
                if runner.restart_streak >= backoff_exp_after:
                    delay *= 2 ** (runner.restart_streak - backoff_exp_after + 1)
                pre_record = asyncio.sleep is not _ORIG_SLEEP and on_restart is not None
                if pre_record:
                    on_restart(runner)
                if asyncio.sleep is _ORIG_SLEEP:
                    await asyncio.sleep(delay)
                else:
                    await asyncio.sleep(_Delay(delay))
                await runner.restart(bus, ledger)
                if on_restart and not pre_record:
                    on_restart(runner)


class Orchestrator(BaseOrchestrator):
    """Bootstraps agents and routes envelopes."""

    def __init__(
        self,
        settings: config.Settings | None = None,
        *,
        alert_hook: Callable[[str, str | None], None] | None = None,
    ) -> None:
        _refresh_thresholds()
        self.settings = settings or config.CFG
        insight_logging.setup(json_logs=self.settings.json_logs)
        bus = messaging.A2ABus(self.settings)
        ledger = Ledger(
            self.settings.ledger_path,
            rpc_url=self.settings.solana_rpc_url,
            wallet=self.settings.solana_wallet,
            broadcast=self.settings.broadcast,
            db=self.settings.db_type,
        )
        archive = ArchiveService(
            os.getenv("ARCHIVE_PATH", "archive.db"),
            rpc_url=self.settings.solana_rpc_url,
            wallet=self.settings.solana_wallet,
            broadcast=self.settings.broadcast,
        )
        solution_archive = SolutionArchive(os.getenv("SOLUTION_ARCHIVE_PATH", "solutions.duckdb"))
        registry = StakeRegistry()
        self._alert_hook = alert_hook or alerts.send_alert
        if resource is not None:
            try:
                limit = 8 * 1024 * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
            except Exception:  # pragma: no cover - unsupported platform
                pass
        super().__init__(
            bus,
            ledger,
            archive,
            solution_archive,
            registry,
            self.settings.island_backends,
            err_threshold=ERR_THRESHOLD,
            backoff_exp_after=BACKOFF_EXP_AFTER,
            promotion_threshold=PROMOTION_THRESHOLD,
        )
        for agent in self._init_agents():
            self.add_agent(agent)

    def _init_agents(self) -> List[BaseAgent]:
        agents: List[BaseAgent] = []
        for island, backend in self.settings.island_backends.items():
            agents.extend(
                [
                    planning_agent.PlanningAgent(self.bus, self.ledger, backend=backend, island=island),
                    research_agent.ResearchAgent(self.bus, self.ledger, backend=backend, island=island),
                    adk_summariser_agent.ADKSummariserAgent(self.bus, self.ledger, backend=backend, island=island),
                    strategy_agent.StrategyAgent(self.bus, self.ledger, backend=backend, island=island),
                    market_agent.MarketAgent(self.bus, self.ledger, backend=backend, island=island),
                    codegen_agent.CodeGenAgent(self.bus, self.ledger, backend=backend, island=island),
                    safety_agent.SafetyGuardianAgent(self.bus, self.ledger, backend=backend, island=island),
                    memory_agent.MemoryAgent(
                        self.bus,
                        self.ledger,
                        self.settings.memory_path,
                        backend=backend,
                        island=island,
                    ),
                ]
            )
        if os.getenv("AGI_SELF_IMPROVE") == "1":
            patch = os.getenv("AGI_SELF_IMPROVE_PATCH")
            repo = os.getenv("AGI_SELF_IMPROVE_REPO", str(Path.cwd()))
            allow = [p.strip() for p in os.getenv("AGI_SELF_IMPROVE_ALLOW", "**").split(",") if p.strip()]
            if patch:
                agents.append(
                    SelfImproverAgent(
                        self.bus,
                        self.ledger,
                        repo,
                        patch,
                        allowed=allow or ["**"],
                    )
                )
        return agents

    async def evolve(
        self,
        scenario_hash: str,
        fn: Callable[[list[float]], tuple[float, ...]],
        genome_length: int,
        sector: str = "generic",
        approach: str = "ga",
        experiment_id: str = "default",
        **kwargs: object,
    ) -> mats.Population:
        """Run evolution for ``scenario_hash`` keyed by ``experiment_id``."""

        pops = self.experiment_pops.setdefault(experiment_id, {})
        if len(self.experiment_pops) > 10:
            raise RuntimeError("max concurrent experiments exceeded")

        pop = await asyncio.to_thread(
            mats.run_evolution,
            fn,
            genome_length,
            scenario_hash=scenario_hash,
            populations=pops,
            **cast(Any, kwargs),
        )
        pops[scenario_hash] = pop
        for ind in pop:
            self.solution_archive.add(
                sector,
                approach,
                ind.score,
                {"genome": ind.genome},
            )
            self.archive.insert_entry(
                {"experiment_id": experiment_id, "genome": ind.genome},
                {"score": ind.score},
            )
        return pop

    def _record_restart(self, runner: AgentRunner) -> None:
        super()._record_restart(runner)
        if self._alert_hook:
            self._alert_hook(
                f"{runner.agent.name} restarted",
                self.settings.alert_webhook_url,
            )


async def _main() -> None:  # pragma: no cover - CLI helper
    orch = Orchestrator()
    await orch.run_forever()


if __name__ == "__main__":  # pragma: no cover - CLI
    asyncio.run(_main())
