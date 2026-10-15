# SPDX-License-Identifier: Apache-2.0
"""Behavioral regressions for legacy demo proposals and safe planner fallback."""
from __future__ import annotations
import ast
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from alpha_factory_v1.demos.alpha_agi_business_v1.evaluation import evaluate, service_payload
from alpha_factory_v1.demos.aiga_meta_evolution import alpha_conversion_stub as conversion
from alpha_factory_v1.demos.omni_factory_demo import omni_factory_demo as omni

ROOT = Path(__file__).resolve().parents[1]


def state():
    return {
        "budget": 100,
        "max_loss": 20,
        "opportunities": [
            {"id": "a", "cost": 60, "benefit": 90, "worst_loss": 15},
            {"id": "b", "cost": 80, "benefit": 120, "worst_loss": 25},
        ],
        "positions": [{"id": "x", "quantity": 2, "price": 3}],
        "company": {"name": "Demo", "jurisdiction": "Example"},
        "evidence_ids": ["supplied-1"],
    }


def test_business_actual_constraint_and_portfolio_computation():
    first = evaluate(state())
    changed = state()
    changed["max_loss"] = 30
    changed["positions"][0]["quantity"] = -3
    second = evaluate(changed)
    assert first["execution"]["selected"]["id"] == "a"
    assert second["execution"]["selected"]["id"] == "b"
    assert first["risk"]["candidate_breaches"] == ["b"]
    assert second["risk"]["candidate_breaches"] == []
    assert first["portfolio"]["net_value"] == 6
    assert second["portfolio"]["net_value"] == -9
    assert second["portfolio"]["gross_value"] == 9
    assert first["execution"]["input_id"] != second["execution"]["input_id"]
    changed["budget"] = 0
    assert evaluate(changed)["execution"]["status"] == "no_eligible_proposal"
    assert evaluate(changed)["execution"]["selected"] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("budget", float("nan")),
        ("budget", True),
        ("max_loss", -1),
        ("opportunities", []),
        ("positions", [{"id": "x"}]),
        ("company", {"name": 12}),
        ("evidence_ids", [None]),
    ],
)
def test_business_rejects_invalid_input(field, value):
    supplied = state()
    supplied[field] = value
    with pytest.raises(ValueError):
        evaluate(supplied)


def test_business_never_claims_external_completion():
    result = evaluate(state())
    assert result["business"]["incorporated"] is False
    assert result["compliance"]["certified"] is False
    assert result["execution"]["orders_submitted"] == 0
    assert all(payload["external_actions_performed"] is False for payload in result.values())
    assert result["business"]["status"] == result["compliance"]["status"] == "manual_review_required"


def test_business_service_steps_publish_evaluation(tmp_path, monkeypatch):
    # Execute the exact five service class bodies without starting the orchestrator.
    path = ROOT / "alpha_factory_v1/demos/alpha_agi_business_v1/alpha_agi_business_v1.py"
    classes = {
        "IncorporatorAgent",
        "AlphaExecutionAgent",
        "AlphaRiskAgent",
        "AlphaComplianceAgent",
        "AlphaPortfolioAgent",
    }
    tree = ast.parse(path.read_text())
    module = ast.Module(
        body=[node for node in tree.body if isinstance(node, ast.ClassDef) and node.name in classes], type_ignores=[]
    )
    events = []

    class Base:
        async def publish(self, topic, payload):
            events.append((topic, payload))

    namespace = {"AgentBase": Base, "service_payload": service_payload}
    exec(compile(module, str(path), "exec"), namespace)
    monkeypatch.delenv("ALPHA_BUSINESS_STATE_FILE", raising=False)
    for name in classes:
        asyncio.run(namespace[name]().step())
    assert all(p["status"] == "input_required" for _, p in events)
    input_file = tmp_path / "state.json"
    input_file.write_text(json.dumps(state()))
    monkeypatch.setenv("ALPHA_BUSINESS_STATE_FILE", str(input_file))
    events.clear()
    for name in classes:
        asyncio.run(namespace[name]().step())
    assert dict(events)["alpha.execution"]["selected"]["id"] == "a"
    assert all(not p["external_actions_performed"] for _, p in events)
    input_file.write_text('{"budget": 1, "budget": 2}')
    assert service_payload("execution")["status"] == "invalid_input"
    input_file.unlink()
    assert service_payload("business")["status"] == "invalid_input"


def test_conversion_varies_real_plan_and_does_not_call_provider(monkeypatch):
    monkeypatch.delenv("ALPHA_CONVERSION_ALLOW_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unused-test-value")

    def forbidden(*args, **kwargs):
        raise AssertionError("provider must not be used")

    monkeypatch.setattr(conversion, "openai", SimpleNamespace(OpenAI=forbidden))
    a = conversion.convert_alpha("warehouse inventory stockouts")
    b = conversion.convert_alpha("solar energy generation")
    assert a["category"] == "inventory" and b["category"] == "energy"
    assert a["steps"] != b["steps"]
    assert a["input_id"] != b["input_id"]
    assert a["mode"] == "local_rule_based_plan" and a["status"] == "proposal_only"
    assert not a["external_actions_performed"]
    a["steps"].clear()
    assert len(conversion.convert_alpha("warehouse inventory stockouts")["steps"]) == 3


@pytest.mark.parametrize("value", ["", "  ", None, 42, "x" * 10001])
def test_conversion_rejects_invalid(value):
    with pytest.raises(ValueError):
        conversion.convert_alpha(value)


def test_conversion_explicit_provider_missing_fails(monkeypatch):
    monkeypatch.setenv("ALPHA_CONVERSION_ALLOW_PROVIDER", "1")
    monkeypatch.setattr(conversion, "openai", None)
    with pytest.raises(RuntimeError, match="unavailable"):
        conversion.convert_alpha("solar energy")


def test_package_workflow_is_real_offline_and_repeatable():
    env = {**os.environ, "PYTHONPATH": str(ROOT), "ALPHA_CONVERSION_ALLOW_PROVIDER": "0", "OPENAI_API_KEY": ""}
    args = [sys.executable, "-m", "alpha_factory_v1.demos.aiga_meta_evolution.workflow_demo", "--alpha", "solar energy"]
    results = [
        subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, check=True, timeout=20).stdout
        for _ in range(2)
    ]
    assert results[0] == results[1]
    assert json.loads(results[0])["plan"]["category"] == "energy"


def test_omni_absent_sdks_reach_actual_model(monkeypatch):
    monkeypatch.setattr(omni, "OAS_AVAILABLE", False)
    monkeypatch.setattr(omni, "ADK_AVAILABLE", False)
    monkeypatch.setattr(omni, "PLUGINS", [])
    a = omni._plan([0.1, 0.95, 0], "test")
    b = omni._plan([0.95, 0.1, 0], "test")
    assert a["action"]["id"] == 0 and b["action"]["id"] == 1
    assert a["planner"] == b["planner"] == "local_analytical_city_model"
    assert a["predicted_rewards"] != b["predicted_rewards"]
    for plan, obs in [(a, [0.1, 0.95, 0]), (b, [0.95, 0.1, 0])]:
        env = omni.SmartCityEnv()
        env.state = omni._CityState(obs[0], obs[1], 0)
        _, reward, _, _, _ = env.step(omni._action_controls(plan["action"]["id"]))
        assert reward == plan["predicted_rewards"][plan["action"]["id"]]


@pytest.mark.parametrize("reply", ['{"action":{"id":99}}', '{"action":{"id":true}}', "not json", '{"action":null}'])
def test_omni_invalid_sdk_results_use_valid_plugin(monkeypatch, reply):
    monkeypatch.setenv("OMNI_ALLOW_PROVIDER", "1")
    monkeypatch.setattr(omni, "OAS_AVAILABLE", True)
    monkeypatch.setattr(omni._plan, "_cached_agent", SimpleNamespace(act=lambda _: reply), raising=False)
    monkeypatch.setattr(omni, "PLUGINS", [SimpleNamespace(heuristic_policy=lambda obs: {"action": {"id": 1}})])
    assert omni._plan([0.5, 0.1, 0], "test")["planner"] == "local_plugin_heuristic"


def test_omni_sdk_exception_and_bad_plugin_fail_closed(monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError("unavailable SDK")

    monkeypatch.setenv("OMNI_ALLOW_PROVIDER", "1")
    monkeypatch.setattr(omni, "OAS_AVAILABLE", True)
    monkeypatch.setattr(omni._plan, "_cached_agent", SimpleNamespace(act=broken), raising=False)
    monkeypatch.setattr(omni, "PLUGINS", [SimpleNamespace(heuristic_policy=lambda obs: {"action": {"id": "1"}})])
    assert omni._plan([0.95, 0.1, 0], "test")["planner"] == "local_analytical_city_model"


@pytest.mark.parametrize("obs", [[float("nan"), 0, 0], [True, 0, 0], [1, 2, 3], [0, 1]])
def test_omni_invalid_observation_rejected(obs):
    with pytest.raises(ValueError):
        omni._plan(obs, "test")


def test_omni_sdk_credentials_alone_never_enable_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("provider must not be called")

    monkeypatch.delenv("OMNI_ALLOW_PROVIDER", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "unused-test-value")
    monkeypatch.setattr(omni, "OAS_AVAILABLE", True)
    monkeypatch.setattr(omni._plan, "_cached_agent", SimpleNamespace(act=forbidden), raising=False)
    monkeypatch.setattr(omni, "PLUGINS", [])
    assert omni._plan([0.1, 0.9, 0], "test")["planner"] == "local_analytical_city_model"


def test_conversion_provider_schema_rejected(monkeypatch):
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"steps": "executed"}'))])
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **kw: response)))
    monkeypatch.setattr(conversion, "openai", SimpleNamespace(OpenAI=lambda **kw: client))
    monkeypatch.setenv("ALPHA_CONVERSION_ALLOW_PROVIDER", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "unused-test-value")
    with pytest.raises(ValueError, match="schema"):
        conversion.convert_alpha("solar energy")


def test_missing_inference_adapter_never_returns_fake_text():
    from alpha_factory_v1.demos.aiga_meta_evolution.utils import _FallbackAgent

    with pytest.raises(RuntimeError, match="No compatible inference"):
        asyncio.run(_FallbackAgent()("discover something"))


def test_omni_marked_placeholder_sdks_are_not_available():
    code = """
import sys, types
for name in ('openai_agents_sdk', 'google_adk'):
    module = types.ModuleType(name)
    module.__alpha_factory_stub__ = True
    sys.modules[name] = module
from alpha_factory_v1.demos.omni_factory_demo import omni_factory_demo as demo
assert not demo.OAS_AVAILABLE and not demo.ADK_AVAILABLE
demo.PLUGINS = []
assert demo._plan([0.1, 0.95, 0], 'test')['planner'] == 'local_analytical_city_model'
"""
    env = {**os.environ, "PYTHONPATH": str(ROOT), "OMNI_ALLOW_PROVIDER": "0"}
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True, capture_output=True, timeout=20)
