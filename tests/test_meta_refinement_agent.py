# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
from unittest.mock import patch

from alpha_factory_v1.core.agents.meta_refinement_agent import MetaRefinementAgent
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry
from alpha_factory_v1.core.self_evolution import harness


def _make_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "metric.txt").write_text("1\n", encoding="utf-8")
    (repo / "test_dummy.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    (repo / "module_a.py").write_text("def run():\n    pass\n", encoding="utf-8")
    return repo


def test_refinement_merges_patch(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.json").write_text(
        "\n".join(
            [
                '{"module":"module_a.py","latency":5,"ts":0}',
                '{"module":"module_b.py","latency":1,"ts":1}',
                '{"module":"module_a.py","latency":6,"ts":2}',
            ]
        ),
        encoding="utf-8",
    )

    reg = StakeRegistry()
    reg.set_stake("meta", 1.0)

    with (
        patch.object(harness, "_run_tests", return_value=0),
        patch.object(harness, "run_preflight"),
        patch.object(
            harness.patcher_core,
            "apply_patch",
            lambda d, repo_path: (Path(repo_path) / "metric.txt").write_text("0\n"),
        ),
    ):
        agent = MetaRefinementAgent(repo, logs, reg)
        merged = agent.refine()

    assert merged
    assert (repo / "metric.txt").read_text().strip() == "0"
    generated = list((repo / "tests").glob("test_generated_*.py"))
    assert generated


def test_refinement_no_bottleneck(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()

    reg = StakeRegistry()
    reg.set_stake("meta", 1.0)

    agent = MetaRefinementAgent(repo, logs, reg)
    with (
        patch.object(MetaRefinementAgent, "_load_logs", return_value=[]),
        patch.object(harness, "vote_and_merge") as vote,
    ):
        merged = agent.refine()

    assert not merged
    vote.assert_not_called()


def test_refinement_rejected_patch(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.json").write_text(
        "\n".join(
            [
                '{"module":"module_a.py","latency":5,"ts":0}',
                '{"module":"module_b.py","latency":1,"ts":1}',
                '{"module":"module_a.py","latency":6,"ts":2}',
            ]
        ),
        encoding="utf-8",
    )

    reg = StakeRegistry()
    reg.set_stake("meta", 1.0)

    with patch.object(harness, "vote_and_merge", return_value=False):
        agent = MetaRefinementAgent(repo, logs, reg)
        merged = agent.refine()

    assert not merged
    assert (repo / "metric.txt").read_text().strip() == "1"


def test_refinement_proposes_cycle_adjustment(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "log.json").write_text(
        "\n".join(['{"agent":"demo","latency_ms":6000,"ts":0}', '{"agent":"demo","latency_ms":7000,"ts":1}']),
        encoding="utf-8",
    )

    reg = StakeRegistry()
    reg.set_stake("meta", 1.0)

    with patch.object(harness, "vote_and_merge") as vote:
        agent = MetaRefinementAgent(repo, logs, reg)
        agent.refine()

    called_diff = vote.call_args.args[1]
    assert "increase cycle" in called_diff


def test_detect_bottleneck_selects_largest_gap(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    agent = MetaRefinementAgent(repo, tmp_path / "logs")
    entries = [
        {"module": "a", "ts": 0},
        {"module": "b", "ts": 2},
        {"module": "c", "ts": 8},
    ]
    assert agent._detect_bottleneck(entries) == "c"


def test_create_patch_no_entries(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    agent = MetaRefinementAgent(repo, tmp_path / "logs")
    patch = agent._create_patch([])
    assert "optimise performance" in patch


def test_init_sets_default_stake(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    reg = StakeRegistry()
    assert "meta" not in reg.stakes
    MetaRefinementAgent(repo, logs, reg)
    assert reg.stakes["meta"] == 1.0
