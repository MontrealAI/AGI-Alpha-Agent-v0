# SPDX-License-Identifier: Apache-2.0
"""Input-driven Business 2 behavior, rejection and service-envelope contracts."""
from __future__ import annotations

import asyncio
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

from alpha_factory_v1.demos.alpha_agi_business_2_v1 import planning
from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import digest, parse

ROOT = Path(planning.__file__).parent


@pytest.fixture
def source():
    return json.loads((ROOT / "example.json").read_text())


def test_evidence_and_optimal_plan(source):
    report = planning.evaluate(source)
    assert report["plan"]["selectedIds"] == ["onboarding", "support"]
    assert report["plan"]["totalValuePoints"] == 21
    assert report["plan"]["totalEffortHours"] == 12
    rows = {r["id"]: r for r in report["research"]["opportunities"]}
    assert rows["returns"]["reason"] == "insufficient_support"
    assert report["inputDigest"] == digest(source)
    assert report["reportDigest"] == digest({k: v for k, v in report.items() if k != "reportDigest"})
    assert report == planning.evaluate(copy.deepcopy(source))


def test_input_changes_evidence_and_allocation(source):
    source["observations"][2]["current"] = 1
    assert planning.evaluate(source)["plan"]["selectedIds"] == ["returns", "support"]
    source["policy"]["effortHours"] = 0
    assert planning.evaluate(source)["plan"]["selectedIds"] == []


def test_exact_not_greedy_and_ties(source):
    # The high individual value project loses to a feasible combination.
    source["observations"][2]["current"] = 1
    source["opportunities"][2].update(effortHours=12, valuePoints=20)
    assert planning.evaluate(source)["plan"]["selectedIds"] == ["onboarding", "support"]
    source["policy"]["maxProjects"] = 1
    for row in source["opportunities"]:
        row.update(effortHours=5, valuePoints=10)
    assert planning.evaluate(source)["plan"]["selectedIds"] == ["onboarding"]
    source["opportunities"][2]["effortHours"] = 4
    assert planning.evaluate(source)["plan"]["selectedIds"] == ["returns"]


def test_sources_are_distinct_and_neutral_is_not_support(source):
    source["policy"]["minSupportingSources"] = 2
    second = copy.deepcopy(source["observations"][0])
    second.update(id="duplicate-source", source=" Synthetic support pilot ")
    source["observations"].append(second)
    source["opportunities"][0]["evidenceIds"].append(second["id"])
    assert planning.evaluate(source)["plan"]["selectedIds"] == []
    second["source"] = "Another supplied source"
    assert planning.evaluate(source)["plan"]["selectedIds"] == ["support"]
    second["current"] = second["baseline"]
    assert planning.evaluate(source)["plan"]["selectedIds"] == []


@pytest.mark.parametrize("value", [True, 1.0, -1, 100001, "12", None])
def test_policy_requires_bounded_integer(source, value):
    source["policy"]["effortHours"] = value
    with pytest.raises(ValueError):
        planning.evaluate(source)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda s: s.update(extra=True),
        lambda s: s.update(schema="unknown"),
        lambda s: s["provenance"].update(kind="live"),
        lambda s: s["observations"][0].update(current=float("nan")),
        lambda s: s["observations"][0].update(metric="bad\ud800"),
        lambda s: s["observations"][0].update(direction="anything"),
        lambda s: s["observations"].append(s["observations"][0]),
        lambda s: s.update(opportunities=s["opportunities"] * 6),
        lambda s: s["opportunities"][0].update(evidenceIds=["missing"]),
        lambda s: s["opportunities"][0].update(evidenceIds=["response-time"] * 2),
        lambda s: s["opportunities"][0].update(evidenceIds=[[]]),
    ],
)
def test_schema_rejections(source, mutation):
    mutation(source)
    with pytest.raises(ValueError):
        planning.evaluate(source)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b"\xff", b"[" * 2000])
def test_strict_json(raw):
    with pytest.raises(ValueError):
        parse(raw)


def test_bounded_reader_and_cli(source, tmp_path):
    path = tmp_path / "input.json"
    path.write_bytes(b" " * (planning.MAX_INPUT_BYTES + 1))
    with pytest.raises(ValueError, match="exceeds"):
        planning.load_report(path)
    path.write_text(json.dumps(source))
    command = [sys.executable, "-m", "alpha_factory_v1.demos.alpha_agi_business_2_v1.planning"]
    run = subprocess.run([*command, "--input", str(path)], capture_output=True, text=True, timeout=10)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout) == planning.evaluate(source)
    run = subprocess.run(command, capture_output=True, text=True, timeout=10)
    assert run.returncode == 2
    assert not run.stdout


@pytest.fixture
def service(monkeypatch):
    """Isolate legacy dependency discovery; exercise real adapters with a recording bus."""

    class AgentBase:
        def __init__(self):
            self.messages = []

        async def publish(self, topic, payload):
            self.messages.append((topic, payload))

    agents = types.ModuleType("alpha_factory_v1.backend.agents")
    agents.AgentMetadata = lambda **kwargs: kwargs
    agents.register_agent = lambda metadata: None
    base = types.ModuleType("alpha_factory_v1.backend.agents.base")
    base.AgentBase = AgentBase
    backend = types.ModuleType("alpha_factory_v1.backend")
    backend.orchestrator = types.SimpleNamespace()
    monkeypatch.setitem(sys.modules, "alpha_factory_v1.backend", backend)
    monkeypatch.setitem(sys.modules, "alpha_factory_v1.backend.agents", agents)
    monkeypatch.setitem(sys.modules, "alpha_factory_v1.backend.agents.base", base)
    spec = importlib.util.spec_from_file_location(
        "alpha_factory_v1.demos.alpha_agi_business_2_v1._service_test", ROOT / "alpha_agi_business_2_v1.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_service_topics_use_same_computation(service, monkeypatch):
    monkeypatch.setenv("BUSINESS2_INPUT", str(ROOT / "example.json"))
    report = planning.load_report(ROOT / "example.json")
    for cls, topic, key, output in (
        (service.PlanningAgent, "alpha.plan", "plan", "plan"),
        (service.ResearchAgent, "alpha.research", "summary", "research"),
    ):
        agent = cls()
        asyncio.run(agent.step())
        assert agent.messages[0][0] == topic
        assert agent.messages[0][1][key] == report[output]
        assert agent.messages[0][1]["inputDigest"] == report["inputDigest"]
    monkeypatch.delenv("BUSINESS2_INPUT")
    with pytest.raises(ValueError, match="no fixture fallback"):
        asyncio.run(service.PlanningAgent().step())


def test_provider_explicit_and_fail_closed(service, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "not-a-real-key")
    monkeypatch.delenv("BUSINESS2_COMMENTARY", raising=False)
    agent = service.LLMCommentAgent()
    asyncio.run(agent.step())
    assert agent.messages == []
    monkeypatch.setenv("BUSINESS2_COMMENTARY", "1")
    stub = types.ModuleType("openai_agents", "Minimal stub for testing")
    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    with pytest.raises(RuntimeError, match="compatibility stub"):
        asyncio.run(agent.step())
    assert agent.messages == []


def test_provider_errors_are_not_published_as_success(service, monkeypatch):
    monkeypatch.setenv("BUSINESS2_INPUT", str(ROOT / "example.json"))
    monkeypatch.setenv("BUSINESS2_COMMENTARY", "1")
    sdk = types.ModuleType("openai_agents", "Test-only compatible SDK")

    class FailingProvider:
        def __init__(self, **kwargs):
            pass

        async def __call__(self, prompt):
            assert "supplied assumptions" in prompt
            raise RuntimeError("provider failed")

    sdk.OpenAIAgent = FailingProvider
    monkeypatch.setitem(sys.modules, "openai_agents", sdk)
    agent = service.LLMCommentAgent()
    with pytest.raises(RuntimeError, match="provider failed"):
        asyncio.run(agent.step())
    assert agent.messages == []


def test_explicit_provider_labels_output(service, monkeypatch):
    monkeypatch.setenv("BUSINESS2_INPUT", str(ROOT / "example.json"))
    monkeypatch.setenv("BUSINESS2_COMMENTARY", "1")
    sdk = types.ModuleType("openai_agents", "Test-only compatible SDK")

    class TestProvider:
        def __init__(self, **kwargs):
            pass

        async def __call__(self, prompt):
            return "Test commentary on supplied observations"

    sdk.OpenAIAgent = TestProvider
    monkeypatch.setitem(sys.modules, "openai_agents", sdk)
    agent = service.LLMCommentAgent()
    asyncio.run(agent.step())
    topic, payload = agent.messages[0]
    assert topic == "alpha.insight"
    assert payload["mode"] == "provider_commentary"
    assert payload["inputDigest"] == planning.load_report(ROOT / "example.json")["inputDigest"]


def test_stub_rejected_even_without_docstrings(service, monkeypatch):
    monkeypatch.setenv("BUSINESS2_COMMENTARY", "1")
    stub = types.ModuleType("openai_agents")
    stub.__alpha_factory_stub__ = True
    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    with pytest.raises(RuntimeError, match="compatibility stub"):
        asyncio.run(service.LLMCommentAgent().step())


@pytest.mark.parametrize("codepoint", range(127, 160))
@pytest.mark.parametrize("field", ["note", "source", "metric", "unit", "title"])
def test_all_text_fields_reject_del_and_c1_controls(source, field, codepoint):
    if field == "note":
        target = source["provenance"]
    elif field == "title":
        target = source["opportunities"][0]
    else:
        target = source["observations"][0]
    target[field] = "Visible" + chr(codepoint) + "text"
    with pytest.raises(ValueError, match="invalid characters"):
        planning.evaluate(source)
