# SPDX-License-Identifier: Apache-2.0
"""Integration test for backend orchestrator dev mode."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import time

import pytest
import pytest_asyncio

try:
    from fastapi.testclient import TestClient  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover - optional dep
    pytest.skip("fastapi required for REST API", allow_module_level=True)

from alpha_factory_v1.backend import orchestrator as orch_mod
from alpha_factory_v1.backend.api_server import build_rest
from alpha_factory_v1.backend.agents.registry import AGENT_REGISTRY, StubAgent
from alpha_factory_v1.backend.agents.health import (
    start_background_tasks,
    stop_background_tasks,
)
from alpha_factory_v1.backend.agents.base import AgentBase


class DummyAgent(AgentBase):  # type: ignore[misc]
    NAME = "dummy"
    CYCLE_SECONDS = 0.0

    async def step(self) -> None:  # pragma: no cover - simple agent
        return None


class FailingAgent(AgentBase):  # type: ignore[misc]
    NAME = "fail"
    CYCLE_SECONDS = 0.0

    async def step(self) -> None:  # pragma: no cover - test failure
        raise RuntimeError("boom")


@pytest_asyncio.fixture()
async def dev_orchestrator(monkeypatch: pytest.MonkeyPatch) -> orch_mod.Orchestrator:
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("API_TOKEN", "test-token")
    monkeypatch.setenv("AGENT_ERR_THRESHOLD", "1")

    from alpha_factory_v1.backend.agents.registry import _HEALTH_Q
    import inspect
    import time

    backend_registry = importlib.import_module("backend.agents.registry")
    backend_runner = importlib.import_module("backend.agent_runner")
    backend_health = importlib.import_module("backend.agents.health")
    af_registry = importlib.import_module("alpha_factory_v1.backend.agents.registry")
    af_runner = importlib.import_module("alpha_factory_v1.backend.agent_runner")
    af_health = importlib.import_module("alpha_factory_v1.backend.agents.health")

    def list_agents(_detail: bool = False) -> list[str]:  # noqa: D401
        return ["dummy", "fail"]

    def get_agent(name: str) -> object:  # noqa: D401
        agent = DummyAgent() if name == "dummy" else FailingAgent()

        if hasattr(agent, "step") and inspect.iscoroutinefunction(agent.step):
            orig = agent.step

            async def _wrapped(*a: object, **kw: object) -> object:
                t0 = time.perf_counter()
                ok = True
                try:
                    return await orig(*a, **kw)
                except Exception:
                    ok = False
                    raise
                finally:
                    _HEALTH_Q.put((name, (time.perf_counter() - t0) * 1000, ok))

            agent.step = _wrapped
        return agent

    def seed_registry(registry_module: object) -> None:
        with registry_module._REGISTRY_LOCK:
            registry_module.AGENT_REGISTRY.clear()
            registry_module.CAPABILITY_GRAPH.clear()
            registry_module.AGENT_REGISTRY["dummy"] = registry_module.AgentMetadata(
                name="dummy",
                cls=DummyAgent,
                capabilities=[],
                compliance_tags=[],
                requires_api_key=False,
            )
            registry_module.AGENT_REGISTRY["fail"] = registry_module.AgentMetadata(
                name="fail",
                cls=FailingAgent,
                capabilities=[],
                compliance_tags=[],
                requires_api_key=False,
            )

    seed_registry(backend_registry)
    seed_registry(af_registry)
    monkeypatch.setattr(backend_registry, "_ERR_THRESHOLD", 1)
    monkeypatch.setattr(backend_health, "_ERR_THRESHOLD", 1)
    monkeypatch.setattr(af_registry, "_ERR_THRESHOLD", 1)
    monkeypatch.setattr(af_health, "_ERR_THRESHOLD", 1)
    monkeypatch.setattr(backend_registry, "list_agents", list_agents)
    monkeypatch.setattr(backend_registry, "get_agent", get_agent)
    monkeypatch.setattr(backend_runner, "get_agent", get_agent)
    monkeypatch.setattr(af_registry, "list_agents", list_agents)
    monkeypatch.setattr(af_registry, "get_agent", get_agent)
    monkeypatch.setattr(af_runner, "get_agent", get_agent)
    await start_background_tasks()

    orch = orch_mod.Orchestrator()
    yield orch
    await stop_background_tasks()


def _mem_stub() -> object:
    vec = type("Vec", (), {"recent": lambda *a, **k: [], "search": lambda *a, **k: []})()
    return type("Mem", (), {"vector": vec})()


@pytest.mark.asyncio  # type: ignore[misc]
async def test_rest_and_quarantine(dev_orchestrator: orch_mod.Orchestrator) -> None:
    app = build_rest(dev_orchestrator.manager.runners, 1024 * 1024, _mem_stub())
    assert app is not None
    client = TestClient(app)
    headers = {"Authorization": "Bearer test-token"}

    resp = client.get("/agents", headers=headers)
    assert resp.status_code == 200
    assert set(resp.json()) == {"dummy", "fail"}

    runner = dev_orchestrator.manager.runners["fail"]
    await runner.maybe_step()
    if runner.task:
        with contextlib.suppress(Exception):
            await runner.task
    await asyncio.sleep(0.05)
    time.sleep(0.05)  # allow health thread to process

    assert AGENT_REGISTRY["fail"].cls is StubAgent
