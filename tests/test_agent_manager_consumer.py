# SPDX-License-Identifier: Apache-2.0
import asyncio
import pytest
from importlib import reload
from alpha_factory_v1.backend import agent_manager as ag_mgr


@pytest.mark.xfail(reason="manager patch issue", strict=False)
def test_manager_starts_and_stops_bus_consumer(monkeypatch: pytest.MonkeyPatch) -> None:
    started = False
    stopped = False

    class DummyBus:
        def __init__(self, *_a: object, **_k: object) -> None:
            pass

        async def start_consumer(self) -> None:
            nonlocal started
            started = True

        async def stop_consumer(self) -> None:
            nonlocal stopped
            stopped = True

        def publish(self, *_a: object, **_kw: object) -> None:
            pass

    async def dummy_run_cycle() -> None:
        return None

    class DummyAgent:
        NAME = "dummy"
        CYCLE_SECONDS = 0.0
        run_cycle = dummy_run_cycle

    def list_agents(_detail: bool = False) -> list[str]:
        return ["dummy"]

    def get_agent(name: str) -> DummyAgent:
        assert name == "dummy"
        return DummyAgent()

    async def start_background_tasks() -> None:
        pass

    monkeypatch.setattr("alpha_factory_v1.backend.agent_manager.EventBus", DummyBus)
    reload(ag_mgr)
    monkeypatch.setattr("alpha_factory_v1.backend.agents.registry.list_agents", list_agents)
    monkeypatch.setattr("backend.agents.registry.list_agents", list_agents)
    monkeypatch.setattr("alpha_factory_v1.backend.agents.registry.get_agent", get_agent)
    monkeypatch.setattr("backend.agents.registry.get_agent", get_agent)
    monkeypatch.setattr("backend.agents.health.start_background_tasks", start_background_tasks)
    monkeypatch.setattr("alpha_factory_v1.backend.agent_runner.get_agent", get_agent)

    mgr = ag_mgr.AgentManager({"dummy"}, True, None, 60, 30)

    async def _run() -> None:
        await mgr.start()
        await mgr.stop()

    asyncio.run(_run())

    assert started
    assert stopped
