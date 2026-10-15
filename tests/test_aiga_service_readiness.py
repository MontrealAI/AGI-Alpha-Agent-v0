# SPDX-License-Identifier: Apache-2.0
"""Liveness is independent of optional training and provider availability."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

PACKAGE = "alpha_factory_v1.demos.aiga_meta_evolution"


@pytest.fixture
def entrypoint(tmp_path, monkeypatch):
    monkeypatch.setenv("CHECKPOINT_DIR", str(tmp_path / "checkpoints"))
    monkeypatch.setenv("ENABLE_GRADIO", "false")
    # An unavailable curriculum and bridge must not prevent the HTTP process.
    monkeypatch.setitem(sys.modules, PACKAGE + ".openai_agents_bridge", None)
    import builtins

    original = builtins.__import__

    def missing_curriculum(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "curriculum_env" and level == 1:
            raise ModuleNotFoundError("No module named 'gymnasium'", name="gymnasium")
        return original(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", missing_curriculum)
    path = Path(__file__).resolve().parents[1] / "alpha_factory_v1/demos/aiga_meta_evolution/agent_aiga_entrypoint.py"
    spec = importlib.util.spec_from_file_location(PACKAGE + ".readiness_entrypoint", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_missing_dependencies_keep_liveness_but_reject_execution(entrypoint):
    with TestClient(entrypoint.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["liveness"] is True
        assert health.json()["execution_ready"] is False
        assert health.json()["provider_verified"] is False
        assert "gymnasium/numpy curriculum environment" in health.json()["execution_unavailable"]
        for route in ("/evolve/1", "/checkpoint", "/reset"):
            assert client.post(route).status_code == 503


@pytest.mark.parametrize("numpy_available,torch_available", [(True, False), (False, True)])
def test_missing_executor_dependency_cannot_schedule_background_work(
    entrypoint, monkeypatch, numpy_available, torch_available
):
    calls = []
    monkeypatch.setattr(entrypoint, "CurriculumEnv", object)
    monkeypatch.setattr(
        entrypoint, "meta_evolver", SimpleNamespace(np=object() if numpy_available else None, _TORCH=torch_available)
    )

    async def checkpoint():
        return None

    monkeypatch.setattr(entrypoint, "service", SimpleNamespace(evolve=lambda n: calls.append(n), checkpoint=checkpoint))
    with TestClient(entrypoint.app, raise_server_exceptions=False) as client:
        assert client.post("/evolve/1").status_code == 503
    assert calls == []


def test_unavailable_provider_never_returns_synthetic_commentary(entrypoint, monkeypatch):
    class Unavailable:
        __alpha_factory_unavailable__ = True

        def __call__(self, _prompt):
            raise AssertionError("Unavailable adapter must not be called")

    monkeypatch.setattr(entrypoint, "LLM", Unavailable())
    with TestClient(entrypoint.app) as client:
        assert client.get("/health").json()["commentary_adapter_available"] is False
        assert client.get("/alpha").status_code == 503


@pytest.mark.parametrize("asynchronous", [False, True])
def test_existing_callable_adapters_are_used_without_legacy_runtime(entrypoint, monkeypatch, asynchronous):
    prompts = []

    def sync_adapter(prompt):
        prompts.append(prompt)
        return "Actual adapter response"

    async def async_adapter(prompt):
        return sync_adapter(prompt)

    monkeypatch.setattr(entrypoint, "LLM", async_adapter if asynchronous else sync_adapter)
    assert asyncio.run(entrypoint.describe_candidate("reviewed architecture")) == "Actual adapter response"
    assert "reviewed architecture" in prompts[0]
    assert asyncio.run(entrypoint.read_health())["provider_verified"] is False


def test_compatible_executor_can_schedule_and_checkpoint(entrypoint, monkeypatch):
    calls = []

    async def evolve(n):
        calls.append(("evolve", n))

    async def checkpoint():
        calls.append(("checkpoint",))

    monkeypatch.setattr(entrypoint, "CurriculumEnv", object)
    monkeypatch.setattr(entrypoint, "meta_evolver", SimpleNamespace(np=object(), _TORCH=True))
    monkeypatch.setattr(
        entrypoint,
        "service",
        SimpleNamespace(evolve=evolve, checkpoint=checkpoint, evolver=SimpleNamespace(best_fitness=0.0)),
    )
    with TestClient(entrypoint.app) as client:
        health = client.get("/health").json()
        assert health["execution_ready"] is True
        assert health["provider_verified"] is False
        assert client.post("/evolve/1").status_code == 200
    assert calls == [("evolve", 1), ("checkpoint",)]


def test_provider_failure_is_not_converted_to_success(entrypoint, monkeypatch):
    async def failed_adapter(_prompt):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(entrypoint, "LLM", failed_adapter)
    with pytest.raises(RuntimeError, match="provider unavailable"):
        asyncio.run(entrypoint.describe_candidate("candidate"))
