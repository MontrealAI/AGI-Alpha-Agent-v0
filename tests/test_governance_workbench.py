# SPDX-License-Identifier: Apache-2.0
"""Adversarial and boundary tests for the maintained governance review."""
from __future__ import annotations

import asyncio
import builtins
import hashlib
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest

from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.demos.solving_agi_governance import workbench as wb
from alpha_factory_v1.demos.solving_agi_governance.cli import main
from alpha_factory_v1.demos.solving_agi_governance.governance_sim import run_sim

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/solving_agi_governance"


@pytest.fixture
def scenario() -> dict:
    return wb.read_json(DEMO / "scenarios.json")[0]


def test_constructed_cases_have_specific_explanations_and_bound_jobs() -> None:
    cases = wb.read_json(DEMO / "scenarios.json")
    expected = [set(), {"identity"}, {"incentives"}, {"risk"}, {"timelock", "policy", "pause"}]
    for case, blocked in zip(cases, expected, strict=True):
        report = wb.evaluate(case)
        assert {gate["id"] for gate in report["result"]["gates"] if not gate["passed"]} == blocked
        assert report["result"]["status"] == ("BLOCKED" if blocked else "REVIEW_REQUIRED")
        assert wb.verify(report) == report
        assert verify_plan(compile_plan(report["result"]["jobs"]))["valid"]
        assert len(report["result"]["jobs"]) == 9
        assert all(wb.digest(report["input"]) in job["goal"] for job in report["result"]["jobs"])


def test_incentive_equality_and_one_basis_point_boundary(scenario: dict) -> None:
    scenario["incentives"].update(reward=3, temptation=5, punishment=1, stake=0, discountBps=5000)
    assert wb.evaluate(scenario)["result"]["incentives"]["marginNumerator"] == "0"
    scenario["incentives"]["discountBps"] = 4999
    result = wb.evaluate(scenario)["result"]
    assert int(result["incentives"]["marginNumerator"]) < 0
    assert not next(g for g in result["gates"] if g["id"] == "incentives")["passed"]


def test_high_discount_alone_is_insufficient(scenario: dict) -> None:
    scenario["incentives"].update(reward=2, temptation=100000, punishment=1, stake=0, discountBps=8000)
    assert int(wb.evaluate(scenario)["result"]["incentives"]["marginNumerator"]) < 0


def test_aggregate_risk_boundary_uses_exact_products(scenario: dict) -> None:
    scenario["risk"].update(perActionFemto=1, actions=10**12, budgetFemto=10**12)
    result = wb.evaluate(scenario)["result"]
    assert result["risk"]["maxPerActionFemto"] == 1
    assert next(g for g in result["gates"] if g["id"] == "risk")["passed"]
    scenario["risk"]["perActionFemto"] = 2
    assert not next(g for g in wb.evaluate(scenario)["result"]["gates"] if g["id"] == "risk")["passed"]
    scenario["risk"]["perActionFemto"] = 10**15
    assert wb.evaluate(scenario)["result"]["risk"]["exposureFemto"] == str(10**27)


def test_invalid_ballots_do_not_inflate_quorum_or_support(scenario: dict) -> None:
    scenario["validators"][0]["votes"] = 4  # 16 > 9 credits
    result = wb.evaluate(scenario)["result"]
    assert result["ballot"]["yes"] == 2 and result["ballot"]["participants"] == 2
    failed = {g["id"] for g in result["gates"] if not g["passed"]}
    assert {"credits", "quorum", "mandate"} <= failed
    assert result["ballot"]["overBudget"] == [scenario["validators"][0]["name"]]


def test_empty_eligible_roster_and_all_abstentions_block(scenario: dict) -> None:
    for v in scenario["validators"]:
        v["stakeTokens"] = 0
    assert {"identity", "quorum", "mandate"} <= {
        g["id"] for g in wb.evaluate(scenario)["result"]["gates"] if not g["passed"]
    }
    for v in scenario["validators"]:
        v.update(stakeTokens=100, votes=0)
    assert not next(g for g in wb.evaluate(scenario)["result"]["gates"] if g["id"] == "quorum")["passed"]


def test_timelock_boundary_and_pause_override(scenario: dict) -> None:
    u = scenario["upgrade"]
    u["now"] = u["queuedAt"] + u["delaySeconds"] - 1
    assert wb.evaluate(scenario)["result"]["upgrade"]["secondsRemaining"] == 1
    u["now"] += 1
    assert wb.evaluate(scenario)["result"]["status"] == "REVIEW_REQUIRED"
    u["paused"] = True
    assert wb.evaluate(scenario)["result"]["status"] == "BLOCKED"


@pytest.mark.parametrize(
    "field,value",
    [
        ("discountBps", True),
        ("discountBps", 10000),
        ("stake", -1),
        ("stake", float("nan")),
        ("stake", float("inf")),
        ("stake", 1.5),
        ("detectionBps", "9000"),
    ],
)
def test_invalid_numeric_inputs_fail_closed(scenario: dict, field: str, value: object) -> None:
    scenario["incentives"][field] = value
    with pytest.raises(ValueError):
        wb.evaluate(scenario)


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "schema",
        "id",
        "text",
        "unicode",
        "payoffs",
        "clock",
        "pause",
        "hash",
        "roster",
        "name",
        "duplicate",
        "controller",
        "eligible",
    ],
)
def test_structural_inputs_fail_closed(scenario: dict, change: str) -> None:
    if change == "unknown":
        scenario["approved"] = True
    elif change == "schema":
        scenario["schema"] = "unknown"
    elif change == "id":
        scenario["id"] = "../outside"
    elif change == "text":
        scenario["note"] = " "
    elif change == "unicode":
        scenario["title"] = "bad\ud800"
    elif change == "payoffs":
        scenario["incentives"]["reward"] = 501
    elif change == "clock":
        scenario["upgrade"]["now"] = 0
    elif change == "pause":
        scenario["upgrade"]["paused"] = "false"
    elif change == "hash":
        scenario["upgrade"]["proposedPolicyHash"] = "not-a-hash"
    elif change == "roster":
        scenario["validators"] *= 17
    elif change == "name":
        scenario["validators"][0]["name"] = "agent.alpha.agent.agi.eth"
    elif change == "duplicate":
        scenario["validators"][1]["name"] = scenario["validators"][0]["name"]
    elif change == "controller":
        scenario["validators"][0]["controller"] = "<img>"
    elif change == "eligible":
        scenario["validators"][0]["eligible"] = 1
    with pytest.raises(ValueError):
        wb.evaluate(scenario)


@pytest.mark.parametrize(
    "data", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b"\xff", b" " * 256001, b"[" * 30 + b"0" + b"]" * 30]
)
def test_ambiguous_or_unbounded_json_rejected(data: bytes) -> None:
    with pytest.raises(ValueError):
        wb.parse(data)


def test_forged_status_is_rejected_even_after_rehash(scenario: dict) -> None:
    report = wb.evaluate(scenario)
    report["result"]["status"] = "APPROVED"
    report["sha256"] = wb.digest({k: v for k, v in report.items() if k != "sha256"})
    with pytest.raises(ValueError, match="recomputation"):
        wb.verify(report)


def test_changed_inputs_change_job_commitments(scenario: dict) -> None:
    before = wb.evaluate(scenario)
    scenario["note"] = "A new source note"
    after = wb.evaluate(scenario)
    assert before["result"]["jobs"] != after["result"]["jobs"]
    assert before["sha256"] != after["sha256"]


def test_integer_json_spellings_normalize(scenario: dict) -> None:
    first = wb.evaluate(scenario)
    scenario["risk"]["actions"] = 1e6
    assert wb.evaluate(scenario) == first


def test_bundle_checksums_replay_and_no_overwrite(scenario: dict, tmp_path: Path) -> None:
    report = wb.evaluate(scenario)
    folder = wb.write_bundle(report, tmp_path)
    assert wb.write_bundle(report, tmp_path) == folder
    for line in (folder / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split("  ")
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected
    assert wb.verify(wb.read_json(folder / "dossier.json")) == report
    (folder / "review-brief.md").write_text("changed")
    with pytest.raises(ValueError, match="differs"):
        wb.write_bundle(report, tmp_path)
    (folder / "review-brief.md").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        wb.write_bundle(report, tmp_path)


def test_symlink_run_is_never_reused(scenario: dict, tmp_path: Path) -> None:
    report = wb.evaluate(scenario)
    target = tmp_path / "target"
    target.mkdir()
    (tmp_path / report["sha256"]).symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        wb.write_bundle(report, tmp_path)
    assert list(target.iterdir()) == []


def test_cli_cases_errors_and_readonly_verification(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert main(["--list"]) == 0
    assert "scale-risk" in capsys.readouterr().out
    assert main(["--case", "scale-risk", "--json", "--output", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["result"]["status"] == "BLOCKED"
    assert main(["--verify", str(tmp_path / report["sha256"] / "dossier.json")]) == 0
    assert main(["--case", "unknown"]) == 2
    assert main(["--input", str(tmp_path / "missing")]) == 2


def test_notebook_runs_every_maintained_cell(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOVERNANCE_SOURCE", str(ROOT))
    monkeypatch.setenv("GOVERNANCE_OUTPUT", str(tmp_path))
    notebook = json.loads((DEMO / "colab_solving_agi_governance.ipynb").read_text())
    code = "\n\n".join("".join(c["source"]) for c in notebook["cells"] if c["cell_type"] == "code")
    result = subprocess.run([sys.executable, "-c", code], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert len(list(tmp_path.glob("*/dossier.json"))) == 1


def test_bridge_import_and_policy_without_optional_runtime(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    original = builtins.__import__

    def absent(name, *args, **kwargs):
        if name == "openai_agents":
            raise ModuleNotFoundError(name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", absent)
    namespace = runpy.run_module("alpha_factory_v1.demos.solving_agi_governance.openai_agents_bridge")
    assert namespace["HAS_OAI"] is False
    namespace["main"](["--agents", "10", "--rounds", "20", "--seed", "42"])
    assert "mean cooperation" in capsys.readouterr().out
    agent = namespace["GovernanceSimAgent"]()
    obs = dict(agents=10, rounds=20, delta=0.8, stake=2.5, seed=42)
    assert asyncio.run(agent.policy(obs, None)) == run_sim(**obs)


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(agents=True),
        dict(rounds=1.5),
        dict(stake=float("nan")),
        dict(stake=float("inf")),
        dict(delta=True),
        dict(seed="42"),
        dict(agents=100000, rounds=1000000),
    ],
)
def test_legacy_rejects_invalid_or_unbounded_work(kwargs: dict) -> None:
    values = dict(agents=10, rounds=20, delta=0.8, stake=2.5, seed=42)
    values.update(kwargs)
    with pytest.raises(ValueError):
        run_sim(**values)


def test_portable_brief_keeps_untrusted_html_and_markdown_literal(scenario: dict) -> None:
    scenario["title"] = "<img src=x onerror=attack>"
    scenario["note"] = "[a link](javascript:attack) **claim**"
    brief = wb.brief(wb.evaluate(scenario))
    assert scenario["title"] not in brief and "[a link]" not in brief and "**claim**" not in brief
    assert "\\<img" in brief and "\\[a link\\]" in brief


def test_legacy_large_integer_fails_as_input_error() -> None:
    with pytest.raises(ValueError):
        run_sim(10, 20, 10**500, 1)
    with pytest.raises(ValueError):
        run_sim(10, 20, 0.8, 10**500)
