# SPDX-License-Identifier: Apache-2.0
"""Reusable orchestrator base for demo agents."""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Callable, Dict, List

from types import SimpleNamespace

from .orchestrator_utils import AgentRunner, handle_heartbeat, monitor_agents
from alpha_factory_v1.core.archive.service import ArchiveService
from alpha_factory_v1.core.archive.solution_archive import SolutionArchive
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry


class DemoOrchestrator:
    """Manage demo agents with ledger and restart logic."""

    def __init__(
        self,
        bus: object,
        ledger: object,
        archive: ArchiveService,
        solution_archive: SolutionArchive,
        registry: StakeRegistry,
        island_backends: Dict[str, str],
        *,
        err_threshold: int = 3,
        backoff_exp_after: int = 3,
        promotion_threshold: float = 0.0,
    ) -> None:
        self.bus = bus
        self.ledger = ledger
        self.archive = archive
        self.solution_archive = solution_archive
        self.registry = registry
        self.island_backends = dict(island_backends)
        self.runners: Dict[str, AgentRunner] = {}
        self.island_pops: Dict[str, object] = {}
        self.experiment_pops: Dict[str, Dict[str, object]] = {"default": self.island_pops}
        self._err_threshold = err_threshold
        self._backoff_exp_after = backoff_exp_after
        self._promotion_threshold = promotion_threshold
        self.bus.subscribe("orch", lambda env: handle_heartbeat(self.runners, env))
        self._monitor_task: asyncio.Task[None] | None = None

    def add_agent(self, agent: object) -> None:
        runner = AgentRunner(agent)
        self.runners[agent.name] = runner
        self._register(runner)

    def _register(self, runner: AgentRunner) -> None:
        payload = {"event": "register", "agent": runner.agent.name, "capabilities": runner.capabilities}
        env = SimpleNamespace(sender="orch", recipient="system", ts=time.time(), payload=payload)
        self.ledger.log(env)
        self.bus.publish("system", env)
        self.registry.set_stake(runner.agent.name, 1.0)
        self.registry.set_threshold(f"promote:{runner.agent.name}", self._promotion_threshold)

    def _record_restart(self, runner: AgentRunner) -> None:
        payload = {"event": "restart", "agent": runner.agent.name}
        env = SimpleNamespace(sender="orch", recipient="system", ts=time.time(), payload=payload)
        self.ledger.log(env)
        self.bus.publish("system", env)

    def slash(self, agent_id: str) -> None:
        self.registry.burn(agent_id, 0.1)

    def verify_merkle_root(self, expected: str, agent_id: str) -> None:
        actual = self.ledger.compute_merkle_root()
        if actual != expected:
            self.slash(agent_id)

    def verify_ledger(self, expected: str, agent_id: str) -> None:
        actual = self.ledger.compute_merkle_root()
        if actual != expected:
            self.slash(agent_id)

    async def evolve(
        self,
        scenario_hash: str,
        fn: Callable[[list[float]], tuple[float, ...]],
        genome_length: int,
        *,
        sector: str = "generic",
        approach: str = "ga",
        experiment_id: str = "default",
        **kwargs: object,
    ) -> object:
        pops = self.experiment_pops.setdefault(experiment_id, {})
        pop = await asyncio.to_thread(
            fn,
            [0.0] * genome_length,
            scenario_hash=scenario_hash,
            populations=pops,
            **kwargs,
        )
        pops[scenario_hash] = pop
        for ind in pop:
            self.solution_archive.add(sector, approach, ind.score, {"genome": ind.genome})
            self.archive.insert_entry({"experiment_id": experiment_id, "genome": ind.genome}, {"score": ind.score})
        return pop

    async def run_forever(self) -> None:
        await self.bus.start()
        self.ledger.start_merkle_task(3600)
        self.archive.start_merkle_task(86_400)
        for r in self.runners.values():
            proposal = f"promote:{r.agent.name}"
            if self.registry.accepted(proposal):
                r.start(self.bus, self.ledger)
        self._monitor_task = asyncio.create_task(
            monitor_agents(
                self.runners,
                self.bus,
                self.ledger,
                err_threshold=self._err_threshold,
                backoff_exp_after=self._backoff_exp_after,
                on_restart=self._record_restart,
            )
        )
        try:
            while True:
                await asyncio.sleep(0.5)
        finally:
            if self._monitor_task:
                self._monitor_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await self._monitor_task
            for r in self.runners.values():
                if r.task:
                    r.task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await r.task
            await self.bus.stop()
            await self.ledger.stop_merkle_task()
            await self.archive.stop_merkle_task()
            self.ledger.close()
            self.archive.close()
            self.solution_archive.close()
