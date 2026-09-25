# SPDX-License-Identifier: Apache-2.0
"""Regression cases found by executing the demo catalog rather than importing it."""
from __future__ import annotations

import asyncio
import importlib
import json
from pathlib import Path
import random
import subprocess

import pytest

from scripts import build_service_worker, generate_demo_docs, mirror_demo_pages
from alpha_factory_v1.demos.utils import code_eval


@pytest.mark.parametrize("version", ["meta_agentic_agi", "meta_agentic_agi_v2"])
def test_synthetic_fitness_does_not_reset_run_rng(version: str) -> None:
    module = "meta_agentic_agi_demo" + ("_v2" if version.endswith("v2") else "")
    demo = importlib.import_module(f"alpha_factory_v1.demos.{version}.{module}")
    before = random.getstate()
    first = demo.evaluate_agent("example")
    assert random.getstate() == before
    assert demo.evaluate_agent("example") == first
    good = demo.Fitness(accuracy=0.95, latency=1, cost=1, carbon=1, novelty=0.9)
    worse = demo.Fitness(accuracy=0.8, latency=2, cost=2, carbon=2, novelty=0.5)
    demo.pareto_sort([worse, good])
    assert good.rank == 1 and worse.rank > good.rank


def test_identity_fixture_needs_no_host_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(code_eval, "secure_run", lambda *args: pytest.fail("identity must not launch a process"))
    assert code_eval.evaluate("def main(x):\n    return x", {"ok": True}) == ('{"ok":true}', "")


def test_generated_program_uses_existing_docker_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = []

    def sandbox(command):
        seen.append(Path(command[1]).read_text())
        return subprocess.CompletedProcess(command, 0, "9\n", "")

    monkeypatch.setattr(code_eval, "secure_run", sandbox)
    assert code_eval.evaluate("def agent(x):\n    return x*x", 3, "agent") == ("9", "")
    assert len(seen) == 1 and "json.loads('3')" in seen[0]


def test_v3_offline_curriculum_records_actual_identity_scores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.demos.meta_agentic_agi_v3 import meta_agentic_agi_demo_v3 as demo

    monkeypatch.setenv("OPENAI_API_KEY", "present-but-must-not-be-used")
    monkeypatch.setattr(demo, "OpenAIProvider", lambda *args: pytest.fail("explicit stub must not auto-select cloud"))
    provider = demo.auto_provider("stub")
    db = demo.LineageDB(str(tmp_path / "lineage.sqlite"))
    try:
        best = asyncio.run(demo.evolutionary_search(provider, db, generations=2, pop_size=2))
        assert best.metrics == {"correct": 1, "total": 1}
        assert len(db.fetch_agents()) == 3
    finally:
        db._conn.close()


@pytest.mark.parametrize("fallback", [False, True])
def test_macro_stress_is_lower_tail(fallback: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    from alpha_factory_v1.demos.macro_sentinel import simulation_core as demo

    if fallback:
        monkeypatch.setattr(demo, "np", None)
    table = demo.MonteCarloSimulator(seed=42).scenario_table([0.5, 0.8, 1.0, 1.2, 1.5])
    rows = table.to_dict("records") if hasattr(table, "to_dict") else table
    median, var, stress = [row["ES factor"] for row in rows]
    assert stress <= var < median


def test_doc_generator_preserves_code_and_relative_guide(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    demo = tmp_path / "alpha_factory_v1/demos/example"
    demo.mkdir(parents=True)
    code = '```python\nprint("README.md", value(3))\n```'
    (demo / "README.md").write_text(f"# Example\n{code}\n[Guide](../README.md)\n")
    monkeypatch.setattr(generate_demo_docs, "REPO_ROOT", tmp_path)
    result = generate_demo_docs.build_page(demo)
    assert code in result
    assert "blob/main/alpha_factory_v1/demos/README.md" in result


def test_nested_mirror_keeps_internal_and_resolves_shared_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    docs = tmp_path / "docs"
    source = docs / "example/assets"
    source.mkdir(parents=True)
    target = docs / "alpha_factory_v1/demos/example"
    (target / "assets").mkdir(parents=True)
    script = target / "assets/script.js"
    script.write_text("import '../../assets/replay_chart.js'; fetch('./logs.json');")
    monkeypatch.setattr(mirror_demo_pages, "DOCS_DIR", docs)
    mirror_demo_pages.fix_paths(target)
    assert "../../../../assets/replay_chart.js" in script.read_text()
    assert "fetch('./logs.json')" in script.read_text()


def test_gallery_cache_version_changes_with_contents(tmp_path: Path) -> None:
    (tmp_path / "assets").mkdir()
    chart = tmp_path / "assets/chart.min.js"
    chart.write_text("version one")
    first = build_service_worker.build(tmp_path)
    chart.write_text("version two")
    assert build_service_worker.build(tmp_path) != first
    # Heavy model files belong to the existing Insight cache, not gallery precache.
    model = tmp_path / "alpha_agi_insight_v1/assets/model.json"
    model.parent.mkdir(parents=True)
    model.write_text(json.dumps({"large": True}))
    assert all("alpha_agi_insight_v1" not in path for path in build_service_worker.gather_assets(tmp_path))


def test_muzero_nonrendering_run_is_bounded_and_closes() -> None:
    from alpha_factory_v1.demos.muzero_planning.minimuzero import play_episode

    class Endless:
        steps = 0
        closed = False

        def reset(self):
            return []

        def act(self, _obs):
            return 0

        def step(self, _action):
            self.steps += 1
            return [], 1, False, False, {}

        def close(self):
            self.closed = True

    agent = Endless()
    agent.env = agent
    frames, reward = play_episode(agent, render=False, max_steps=3)
    assert frames == [] and reward == 3 and agent.steps == 3 and agent.closed
