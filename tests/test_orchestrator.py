# SPDX-License-Identifier: Apache-2.0
import asyncio
import contextlib
from unittest import mock

from alpha_factory_v1.demos.alpha_agi_insight_v1.src import orchestrator
from alpha_factory_v1.backend import orchestrator_utils
from alpha_factory_v1.common.utils import config


def test_run_forever_shutdown() -> None:
    settings = config.Settings(bus_port=0)
    with mock.patch.object(orchestrator.Orchestrator, "_init_agents", lambda self: []):
        orch = orchestrator.Orchestrator(settings)

    async def run() -> None:
        with (
            mock.patch.object(orch.bus, "stop", mock.AsyncMock()) as bus_stop,
            mock.patch.object(orch.ledger, "stop_merkle_task", mock.AsyncMock()) as merkle_stop,
        ):
            task = asyncio.create_task(orch.run_forever())
            await asyncio.sleep(0.05)
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            bus_stop.assert_awaited_once()
            merkle_stop.assert_awaited_once()

    asyncio.run(run())


class FailingAgent(orchestrator.BaseAgent):
    NAME = "fail"
    CYCLE_SECONDS = 0.1

    def __init__(self, bus: orchestrator.messaging.A2ABus, ledger: orchestrator.Ledger) -> None:
        super().__init__("fail", bus, ledger)

    async def run_cycle(self) -> None:
        raise RuntimeError("boom")

    async def handle(self, _env: orchestrator.messaging.Envelope) -> None:  # pragma: no cover - test helper
        pass


def test_error_threshold_restart(monkeypatch) -> None:
    monkeypatch.setenv("AGENT_ERR_THRESHOLD", "2")

    events: list[str] = []

    class DummyLedger:
        def __init__(self, *_a, **_kw) -> None:
            pass

        def log(self, env) -> None:  # type: ignore[override]
            """Capture restart events without assuming ``dict`` payloads."""
            event = None
            payload = getattr(env, "payload", None)
            if isinstance(payload, dict):
                event = payload.get("event")
            else:
                try:
                    event = payload["event"]
                except Exception:
                    event = None
            if event:
                events.append(event)

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
                orchestrator_utils.monitor_agents(
                    orch.runners,
                    orch.bus,
                    orch.ledger,
                    err_threshold=orch._err_threshold,
                    backoff_exp_after=orch._backoff_exp_after,
                    on_restart=orch._record_restart,
                )
            )
            await asyncio.sleep(5)
            monitor.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor
            if runner.task:
                runner.task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runner.task

    asyncio.run(run())

    assert "restart" in events


class DummyAgent(orchestrator.BaseAgent):
    NAME = "dummy"
    CYCLE_SECONDS = 0.05

    def __init__(self, bus: orchestrator.messaging.A2ABus, ledger: orchestrator.Ledger) -> None:
        super().__init__("dummy", bus, ledger)

    async def run_cycle(self) -> None:
        await asyncio.sleep(0)

    async def handle(self, _env: orchestrator.messaging.Envelope) -> None:  # pragma: no cover - helper
        pass


def test_background_tasks_lifecycle() -> None:
    settings = config.Settings(bus_port=0)
    with mock.patch.object(orchestrator.Orchestrator, "_init_agents", lambda self: [DummyAgent(self.bus, self.ledger)]):
        orch = orchestrator.Orchestrator(settings)

    async def run() -> None:
        with (
            mock.patch.object(orch.bus, "start", mock.AsyncMock()) as bus_start,
            mock.patch.object(orch.bus, "stop", mock.AsyncMock()) as bus_stop,
            mock.patch.object(orch.ledger, "start_merkle_task") as merkle_start,
            mock.patch.object(orch.ledger, "stop_merkle_task", mock.AsyncMock()) as merkle_stop,
        ):
            task = asyncio.create_task(orch.run_forever())
            await asyncio.sleep(0.05)
            assert orch._monitor_task is not None and not orch._monitor_task.done()
            runner = orch.runners["dummy"]
            assert runner.task is not None and not runner.task.done()
            merkle_start.assert_called_once()
            bus_start.assert_awaited_once()
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            assert orch._monitor_task is not None and orch._monitor_task.cancelled()
            assert runner.task is not None and runner.task.cancelled()
            bus_stop.assert_awaited_once()
            merkle_stop.assert_awaited_once()

    asyncio.run(run())
