# SPDX-License-Identifier: Apache-2.0
"""Minimal test for alpha_asi_world_model_demo FastAPI app."""

from __future__ import annotations

import importlib
import os
from typing import Any, cast

import pytest

pytest.importorskip("numpy")

pytest.importorskip("torch")
from fastapi.testclient import TestClient  # noqa: E402


def test_agents_list_offline(non_network: None) -> None:
    """Verify /agents lists all required demo agents."""
    os.environ["NO_LLM"] = "1"
    os.environ.setdefault("ALPHA_ASI_SILENT", "1")
    os.environ.setdefault("ALPHA_ASI_MAX_STEPS", "1")

    mod = importlib.import_module("alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo")
    with TestClient(cast(Any, mod.app)) as client:
        resp = client.get("/agents")
        assert resp.status_code == 200
        agents = resp.json()
        expected = {
            "PlanningAgent",
            "ResearchAgent",
            "StrategyAgent",
            "MarketAnalysisAgent",
            "CodeGenAgent",
            "SafetyAgent",
        }
        assert expected.issubset(set(agents))


def test_post_new_env(non_network: None) -> None:
    """Force a new environment via /command."""
    os.environ["NO_LLM"] = "1"
    os.environ.setdefault("ALPHA_ASI_SILENT", "1")
    os.environ.setdefault("ALPHA_ASI_MAX_STEPS", "1")

    mod = importlib.import_module("alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo")
    with TestClient(cast(Any, mod.app)) as client:
        resp = client.post("/command", json={"cmd": "new_env"})
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}


def test_multi_env_reporting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Aggregated metrics should reflect all environments."""
    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("ALPHA_ASI_MAX_STEPS", "1")
    monkeypatch.setenv("ALPHA_ASI_UI_TICK", "1")
    monkeypatch.setenv("ALPHA_ASI_ENV_BATCH", "2")

    mod = importlib.import_module("alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo")

    class DummyEnv:
        def __init__(self, reward: float) -> None:
            self.reward = reward

        def reset(self):
            return None

        def step(self, _a: int):
            return None, self.reward, True, {}

    class DummyLearner:
        def __init__(self, loss: float) -> None:
            self.loss = loss

        def act(self, _obs):
            return 0

        def remember(self, _obs, _reward) -> None:
            pass

        def train_once(self) -> float:
            return self.loss

    mod.A2ABus._subs = {}
    orch = mod.Orchestrator()
    orch.envs = [DummyEnv(1.0), DummyEnv(0.0)]
    orch.learners = [DummyLearner(0.2), DummyLearner(0.4)]

    msgs: list[dict] = []
    mod.A2ABus.subscribe("ui", lambda m: msgs.append(m))

    orch.loop()

    assert msgs
    msg = msgs[-1]
    assert msg["t"] == 0
    assert msg["r"] == pytest.approx(0.5)
    assert msg["loss"] == pytest.approx(0.3)


def test_shutdown_stops_loop(non_network: None) -> None:
    """The orchestrator loop thread should terminate on app shutdown."""
    os.environ["NO_LLM"] = "1"
    os.environ.setdefault("ALPHA_ASI_MAX_STEPS", "100000")

    mod = importlib.import_module("alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo")

    with TestClient(cast(Any, mod.app)) as client:
        client.get("/agents")
        loop = mod.loop_thread
        assert loop is not None and loop.is_alive()
    assert loop is not None and not loop.is_alive()


def test_invalid_seed_fallback(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Invalid ALPHA_ASI_SEED should trigger fallback to default."""
    module = "alpha_factory_v1.demos.alpha_asi_world_model.alpha_asi_world_model_demo"
    mod = importlib.import_module(module)
    monkeypatch.setenv("ALPHA_ASI_SEED", "bad")
    caplog.set_level("WARNING")
    cfg = mod._load_cfg()
    assert mod._SEED == 42
    assert any("Invalid seed" in rec.message for rec in caplog.records)
    assert isinstance(cfg, mod.Config)
