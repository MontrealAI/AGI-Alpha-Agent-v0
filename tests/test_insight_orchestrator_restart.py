# SPDX-License-Identifier: Apache-2.0
import asyncio
import os
import tempfile
import unittest
from unittest import mock
import contextlib

from alpha_factory_v1.core import orchestrator
from alpha_factory_v1.core.utils import config
from alpha_factory_v1.common.utils.messaging import A2ABus, Envelope
from alpha_factory_v1.common.utils.logging import Ledger
from alpha_factory_v1.core.agents.base_agent import BaseAgent


class FreezeAgent(BaseAgent):
    """Agent whose run_cycle blocks indefinitely."""

    CYCLE_SECONDS = 0.1

    def __init__(self, bus: A2ABus, ledger: Ledger) -> None:
        super().__init__("freeze", bus, ledger)

    async def run_cycle(self) -> None:
        await asyncio.sleep(999)

    async def handle(self, _env: Envelope) -> None:
        pass


class TestInsightOrchestratorRestart(unittest.TestCase):
    def test_restart_unresponsive_agent(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        settings = config.Settings(bus_port=0, ledger_path=os.path.join(tmp.name, "ledger.db"), offline=True)

        def _agents(self: orchestrator.Orchestrator) -> list[BaseAgent]:
            return [FreezeAgent(self.bus, self.ledger)]

        with mock.patch.object(orchestrator.Orchestrator, "_init_agents", _agents):
            orch = orchestrator.Orchestrator(settings)

        runner = orch.runners["freeze"]

        async def run() -> bool:
            async with orch.bus, orch.ledger:
                runner.start(orch.bus, orch.ledger)
                monitor = asyncio.create_task(
                    orchestrator.monitor_agents(
                        orch.runners,
                        orch.bus,
                        orch.ledger,
                        err_threshold=orchestrator.ERR_THRESHOLD,
                        backoff_exp_after=orchestrator.BACKOFF_EXP_AFTER,
                        on_restart=orch._record_restart,
                    )
                )
                await asyncio.sleep(3)
                active = runner.task is not None and not runner.task.done()
                monitor.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await monitor
                if runner.task:
                    runner.task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await runner.task
            return active

        with mock.patch.object(orchestrator.log, "warning") as warn:
            active = asyncio.run(run())
            warn.assert_any_call("%s unresponsive – restarting", "freeze")
        self.assertTrue(active)
        tmp.cleanup()


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
