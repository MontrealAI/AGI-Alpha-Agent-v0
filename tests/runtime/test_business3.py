# SPDX-License-Identifier: Apache-2.0
"""Business decisions must respect resources, retain evidence and fail closed."""
from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from alpha_factory_v1.demos.alpha_agi_business_3_v1 import enterprise as engine
from alpha_factory_v1.demos.alpha_agi_business_3_v1.cli import main

CASES = Path(engine.__file__).with_name("scenarios.json")


def case() -> dict:
    source = engine.read_json(CASES)[0]
    source["policy"].update(
        budgetUsd=120,
        staffDays=500,
        reviewMinutes=500,
        jobBudgetTokens=500,
        maxProjects=3,
        maxPerSector=3,
        discountBps=0,
        benefitHaircutBps=0,
        costOverrunBps=0,
        minEvidenceBps=5000,
        minDownsideNpvUsd=0,
    )
    template = source["projects"][0]
    source["projects"] = []
    for pid, cost, cash in [("a", 120, 90), ("b", 60, 55), ("c", 60, 55)]:
        p = deepcopy(template)
        p.update(
            id=pid,
            name=pid.upper(),
            costUsd=cost,
            cashflowsUsd=[cash] * 3,
            staffDays=10,
            reviewMinutes=25,
            bountyTokens=10,
            evidenceBps=9000,
            requires=[],
            excludes=[],
        )
        source["projects"].append(p)
    return source


def test_exact_allocation_beats_a_profitable_but_inferior_greedy_choice() -> None:
    result = engine.solve(case())["result"]
    assert result["portfolio"]["projectIds"] == ["b", "c"]
    assert result["portfolio"]["expectedNpvUsd"] == 210
    assert result["comparison"]["portfolio"]["projectIds"] == ["a"]
    assert result["comparison"]["upliftUsd"] == 60
    assert result["approval"] == "UNREVIEWED"


@pytest.mark.parametrize("field", ["budgetUsd", "staffDays", "reviewMinutes", "jobBudgetTokens", "maxProjects"])
def test_zero_resource_holds_capital_and_never_creates_jobs(field: str) -> None:
    source = case()
    source["policy"][field] = 0
    result = engine.solve(source)["result"]
    assert result["status"] == "HOLD_NO_POSITIVE_VALUE"
    assert result["jobs"] == result["settlementPreview"] == []
    assert result["portfolio"]["costUsd"] == 0


@pytest.mark.parametrize("constraint", ["dependency", "exclusion", "evidence", "concentration"])
def test_cheap_projects_cannot_bypass_admission(constraint: str) -> None:
    source = case()
    if constraint == "dependency":
        source["projects"][2]["requires"] = ["a"]
    elif constraint == "exclusion":
        source["projects"][1]["excludes"] = ["c"]
    elif constraint == "evidence":
        source["projects"][1]["evidenceBps"] = 4999
    else:
        source["policy"]["maxPerSector"] = 1
    assert engine.solve(source)["result"]["portfolio"]["projectIds"] == ["a"]


def test_downside_floor_can_make_every_portfolio_infeasible() -> None:
    source = case()
    source["policy"]["minDownsideNpvUsd"] = 211
    result = engine.solve(source)["result"]
    assert result["status"] == "NO_FEASIBLE_PORTFOLIO"
    assert result["portfolio"] is None and result["jobs"] == []


def test_budget_reserves_adverse_capital_not_just_upfront_cost() -> None:
    source = case()
    source["policy"]["costOverrunBps"] = 1
    result = engine.solve(source)["result"]["portfolio"]
    assert result["projectIds"] == ["b"]
    assert result["stressedCostUsd"] == 61


def test_cashflow_rounding_and_negative_flows_against_exact_fractions() -> None:
    project, policy = case()["projects"][0], case()["policy"]
    project["cashflowsUsd"] = [-101, 137, 181]
    policy.update(discountBps=1377, benefitHaircutBps=3333, costOverrunBps=777)
    result = engine.economics(project, policy)

    def floor(value: Fraction) -> int:
        return value.numerator // value.denominator

    expected = (
        sum(
            floor(Fraction(cash) / Fraction(11377, 10000) ** year)
            for year, cash in enumerate(project["cashflowsUsd"], 1)
        )
        - 120
    )
    shocked = [floor(Fraction(cash * (6667 if cash >= 0 else 13333), 10000)) for cash in project["cashflowsUsd"]]
    adverse = sum(floor(Fraction(cash) / Fraction(11377, 10000) ** year) for year, cash in enumerate(shocked, 1)) - 130
    assert result == {"expectedNpvUsd": expected, "downsideNpvUsd": adverse, "stressedCostUsd": 130}


def test_order_and_integer_json_notation_do_not_change_commitments() -> None:
    source = case()
    expected = engine.solve(source)
    source["projects"].reverse()
    source["policy"]["budgetUsd"] = 120.0
    assert engine.solve(source) == expected


@pytest.mark.parametrize("value", [True, None, "120", -1, 1.25, float("inf"), float("nan"), 10**50])
def test_invalid_numeric_inputs_are_not_coerced(value: object) -> None:
    source = case()
    source["policy"]["budgetUsd"] = value
    with pytest.raises(ValueError):
        engine.solve(source)


@pytest.mark.parametrize(
    "change", ["unknown", "duplicate", "cycle", "missing", "self", "unicode", "metric", "too-many"]
)
def test_invalid_or_unbounded_scenarios_are_rejected(change: str) -> None:
    source = case()
    if change == "unknown":
        source["approve"] = True
    elif change == "duplicate":
        source["projects"][1]["id"] = "a"
    elif change == "cycle":
        source["projects"][0]["requires"] = ["b"]
        source["projects"][1]["requires"] = ["a"]
    elif change == "missing":
        source["projects"][1]["requires"] = ["absent"]
    elif change == "self":
        source["projects"][1]["excludes"] = ["b"]
    elif change == "unicode":
        source["title"] = "\ud800"
    elif change == "metric":
        source["projects"][1]["metric"] = "🪐" * 101
    else:
        source["projects"] *= 6
    with pytest.raises(ValueError):
        engine.solve(source)


@pytest.mark.parametrize(
    "data",
    [b'{"a":1,"a":2}', b'{"x":NaN}', b'{"x":Infinity}', b'"\xff"', b" " * 256001],
    ids=["duplicate-key", "nan", "infinity", "invalid-utf8", "oversized"],
)
def test_json_boundary_rejects_ambiguous_data(data: bytes) -> None:
    with pytest.raises(ValueError):
        engine.parse(data)


def test_forgery_remains_invalid_after_attacker_recomputes_the_hash() -> None:
    report = engine.solve(case())
    report["result"]["jobs"][0]["bounty"] = "999000000000000000000"
    report["sha256"] = engine.digest({k: v for k, v in report.items() if k != "sha256"})
    with pytest.raises(ValueError, match="recomputed"):
        engine.verify(report)


def test_source_provenance_and_success_metric_are_committed() -> None:
    source = case()
    before = engine.solve(source)
    source["projects"][1]["sources"] = ["New independent evidence"]
    source["projects"][1]["metric"] = "Return the exact reconciliation and test outcomes."
    after = engine.solve(source)
    assert after["sha256"] != before["sha256"]
    assert after["result"]["jobs"][0]["successMetric"] == source["projects"][1]["metric"]


def test_exported_jobs_compile_and_exact_one_percent_burn_conserves_value() -> None:
    from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan

    report = engine.solve(case())
    plan = compile_plan(report["result"]["jobs"])
    assert verify_plan(plan)["valid"] is True
    assert plan["totalBounty"] == "20000000000000000000"
    for payout in report["result"]["settlementPreview"]:
        assert int(payout["netBaseUnits"]) + int(payout["burnBaseUnits"]) == int(payout["grossBaseUnits"])
        assert int(payout["burnBaseUnits"]) * 100 == int(payout["grossBaseUnits"])


def test_existing_evidence_is_reused_exactly_and_never_overwritten(tmp_path: Path) -> None:
    report = engine.solve(case())
    directory = engine.write_bundle(report, tmp_path)
    before = {p.name: p.read_bytes() for p in directory.iterdir()}
    assert len(before) == 7
    assert engine.write_bundle(report, tmp_path) == directory
    assert {p.name: p.read_bytes() for p in directory.iterdir()} == before
    for line in before["SHA256SUMS"].decode().splitlines():
        expected, filename = line.split("  ")
        assert hashlib.sha256(before[filename]).hexdigest() == expected
    (directory / "dossier.json").write_text("retain altered work")
    with pytest.raises(ValueError, match="differs"):
        engine.write_bundle(report, tmp_path)
    assert (directory / "dossier.json").read_text() == "retain altered work"


def test_partial_output_is_not_repaired_over_existing_work(tmp_path: Path) -> None:
    report = engine.solve(case())
    run = tmp_path / report["sha256"]
    run.mkdir()
    (run / "keep.txt").write_text("keep")
    with pytest.raises(ValueError, match="incomplete"):
        engine.write_bundle(report, tmp_path)
    assert (run / "keep.txt").read_text() == "keep"


def test_output_directory_symlink_is_rejected_without_changing_target(tmp_path: Path) -> None:
    report = engine.solve(case())
    retained = tmp_path / "retained"
    retained.mkdir()
    (retained / "keep.txt").write_text("keep")
    (tmp_path / report["sha256"]).symlink_to(retained, target_is_directory=True)
    with pytest.raises(ValueError, match="incomplete"):
        engine.write_bundle(report, tmp_path)
    assert list(retained.iterdir()) == [retained / "keep.txt"]
    assert (retained / "keep.txt").read_text() == "keep"


def test_cli_runs_and_verifies_the_actual_export(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--case", "industrial", "--json", "--output", str(tmp_path)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["result"]["status"] == "REVIEW_REQUIRED"
    dossier = tmp_path / report["sha256"] / "dossier.json"
    assert main(["--verify", str(dossier)]) == 0
    assert "Verified all decisions" in capsys.readouterr().out
    dossier.write_text("{}")
    assert main(["--verify", str(dossier)]) == 2
    assert "Dossier must contain" in capsys.readouterr().err


def test_python_module_cli_really_executes_and_default_imports_no_optional_sdk(tmp_path: Path) -> None:
    program = (
        "from alpha_factory_v1.demos.alpha_agi_business_3_v1.cli import main; import sys; "
        "assert not any(m in sys.modules for m in ('agents','google.adk','a2a','numpy','torch')); "
        "raise SystemExit(main(['--list']))"
    )
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert "industrial" in result.stdout


def test_all_constructed_cases_recompute_with_distinct_resource_decisions() -> None:
    reports = [engine.solve(source) for source in engine.read_json(CASES)]
    assert len({engine.canonical(r["result"]["portfolio"]["projectIds"]) for r in reports}) == 5
    assert (
        next(r for r in reports if r["input"]["id"] == "severe-downside")["result"]["status"]
        == "HOLD_NO_POSITIVE_VALUE"
    )
    for report in reports:
        assert engine.verify(report) == report
