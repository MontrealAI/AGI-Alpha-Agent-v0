# SPDX-License-Identifier: Apache-2.0
"""Unit test for agent_aiga_entrypoint FastAPI service."""

from typing import Any, cast

import importlib
import runpy
import sys
import types

import pytest

pytest.importorskip("gymnasium", reason="gymnasium required for environment")
from fastapi.testclient import TestClient


@pytest.mark.usefixtures("non_network")
def test_health_endpoint() -> None:
    """Verify /health returns expected metrics."""
    module = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.agent_aiga_entrypoint")
    client = TestClient(cast(Any, module.app))

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data) >= {"status", "generations", "best_fitness"}


@pytest.mark.usefixtures("non_network")
def test_socket_started_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """MetaEvolver should start the A2A socket only once."""
    counter = types.SimpleNamespace(count=0)

    class DummySocket:
        def start(self) -> None:  # noqa: D401 - test stub
            counter.count += 1

    stub_a2a = types.ModuleType("a2a")
    stub_a2a.A2ASocket = lambda *a, **k: DummySocket()

    stub_oa = types.ModuleType("openai_agents")
    stub_oa.Agent = object
    stub_oa.AgentRuntime = object
    stub_oa.OpenAIAgent = object

    def _tool(*_a, **_k):
        def dec(func):
            return func

        return dec

    stub_oa.Tool = _tool

    monkeypatch.setitem(sys.modules, "a2a", stub_a2a)
    monkeypatch.setitem(sys.modules, "openai_agents", stub_oa)
    monkeypatch.setattr("uvicorn.run", lambda *_a, **_k: None)

    sys.modules.pop(
        "alpha_factory_v1.demos.aiga_meta_evolution.meta_evolver",
        None,
    )
    sys.modules.pop(
        "alpha_factory_v1.demos.aiga_meta_evolution.agent_aiga_entrypoint",
        None,
    )

    runpy.run_module(
        "alpha_factory_v1.demos.aiga_meta_evolution.agent_aiga_entrypoint",
        run_name="__main__",
    )

    assert counter.count == 1
