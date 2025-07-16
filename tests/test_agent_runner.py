# SPDX-License-Identifier: Apache-2.0
import asyncio
import contextlib
from unittest.mock import patch

from alpha_factory_v1.demos.alpha_agi_insight_v1.src import orchestrator
from alpha_factory_v1.common.utils import messaging


class DummyAgent:
    name = "dummy"
    CYCLE_SECONDS = 0.0

    def __init__(self) -> None:
        self.calls = 0

    async def run_cycle(self) -> None:
        self.calls += 1


def test_agent_runner_loop_publishes_heartbeat() -> None:
    agent = DummyAgent()
    runner = orchestrator.AgentRunner(agent)

    events: list[tuple[str, str]] = []

    class Bus:
        def publish(self, topic: str, env: messaging.Envelope) -> None:
            events.append(("pub", agent.name))

    class Ledger:
        def log(self, env: messaging.Envelope) -> None:
            events.append(("log", agent.name))

    bus = Bus()
    led = Ledger()

    async def run_once() -> None:
        async def _sleep(_: float) -> None:
            raise asyncio.CancelledError()

        with patch.object(asyncio, "sleep", _sleep):
            with contextlib.suppress(asyncio.CancelledError):
                await runner.loop(bus, led)

    asyncio.run(run_once())

    assert agent.calls == 1
    assert ("pub", "dummy") in events
    assert ("log", "dummy") in events


class _Ledger:
    def log(self, _env: messaging.Envelope) -> None:  # pragma: no cover - test helper
        pass

    def start_merkle_task(self, *_a: object, **_kw: object) -> None:  # pragma: no cover - test helper
        pass

    async def stop_merkle_task(self) -> None:  # pragma: no cover - test helper
        pass

    def close(self) -> None:  # pragma: no cover - test helper
        pass


class DummyBaseAgent(orchestrator.BaseAgent):  # type: ignore[misc]
    def __init__(self, bus: messaging.A2ABus, ledger: _Ledger) -> None:
        super().__init__("dummy", bus, ledger)
        self.count = 0

    async def run_cycle(self) -> None:
        pass

    async def handle(self, _env: messaging.Envelope) -> None:
        self.count += 1


def test_restart_unsubscribes_handler() -> None:
    bus = messaging.A2ABus(orchestrator.config.Settings(bus_port=0))
    ledger = _Ledger()
    agent = DummyBaseAgent(bus, ledger)
    runner = orchestrator.AgentRunner(agent)

    async def _run() -> tuple[int, int]:
        bus.publish("dummy", messaging.Envelope("a", "dummy", {}, 0.0))
        await asyncio.sleep(0)
        before = agent.count
        await runner.restart(bus, ledger)
        new_agent = runner.agent  # type: ignore[assignment]
        bus.publish("dummy", messaging.Envelope("a", "dummy", {}, 0.0))
        await asyncio.sleep(0)
        return before, getattr(new_agent, "count")

    before, after = asyncio.run(_run())

    assert before == 1
    assert agent.count == 1
    assert after == 1
    assert len(bus._subs.get("dummy", [])) == 1
