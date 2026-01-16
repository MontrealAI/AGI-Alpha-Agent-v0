# SPDX-License-Identifier: Apache-2.0
import asyncio
import contextlib

from alpha_factory_v1.core import orchestrator
from alpha_factory_v1.core.utils import config


class FailingAgent(orchestrator.BaseAgent):
    NAME = "fail"
    CYCLE_SECONDS = 0.0

    def __init__(self, bus: orchestrator.messaging.A2ABus, ledger: orchestrator.Ledger) -> None:
        super().__init__("fail", bus, ledger)

    async def run_cycle(self) -> None:
        raise RuntimeError("boom")

    async def handle(self, _env: orchestrator.messaging.Envelope) -> None:
        pass


def test_restart_backoff(monkeypatch):
    monkeypatch.setenv("AGENT_ERR_THRESHOLD", "1")
    monkeypatch.setenv("AGENT_BACKOFF_EXP_AFTER", "1")

    delays = []
    orig_sleep = asyncio.sleep

    async def fake_sleep(sec: float):
        delays.append(sec)
        await orig_sleep(0)

    monkeypatch.setattr(orchestrator.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(orchestrator.random, "uniform", lambda a, b: 1.0)

    events: list[str] = []

    class DummyLedger:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def log(self, env) -> None:
            if env.payload.get("event"):
                events.append(env.payload["event"])

        def start_merkle_task(self, *_a, **_kw) -> None:
            pass

        async def stop_merkle_task(self) -> None:
            pass

        def close(self) -> None:
            pass

    settings = config.Settings(bus_port=0)
    monkeypatch.setattr(orchestrator, "Ledger", DummyLedger)
    monkeypatch.setattr(
        orchestrator.Orchestrator,
        "_init_agents",
        lambda self: [FailingAgent(self.bus, self.ledger)],
    )
    orch = orchestrator.Orchestrator(settings)
    runner = orch.runners["fail"]

    async def run() -> None:
        async with orch.bus:
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
            for _ in range(6):
                await orig_sleep(0)
            monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor
            if runner.task:
                runner.task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner.task

    asyncio.run(run())

    restart_delays = [d for d in delays if d != 0]
    with contextlib.suppress(ValueError):
        restart_delays.remove(2)
    assert restart_delays[:2] == [1.0, 2.0]
    assert events.count("restart") >= 2
