# SPDX-License-Identifier: Apache-2.0
"""Source/claim separation, scale bounds and complete conditional cash flows."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.successor.protocol import canonical, load_record, safe_json_loads
from contrib.production_frontier.confirm import frozen_paths, run
from contrib.production_frontier.discovery import Hypothesis, Scale, discover, scale_audit
from contrib.production_frontier.economics import USD, evaluate
from contrib.production_frontier.engine import ProductionBrief

HOME = Path(__file__).resolve().parents[1]


def data(name: str):
    return safe_json_loads((HOME / "inputs" / name).read_bytes())


def test_public_context_and_authored_feasibility_do_not_admit_a_business() -> None:
    hypothesis = load_record(Hypothesis, (HOME / "inputs/transformer-hypothesis.json").read_bytes())
    brief = load_record(ProductionBrief, (HOME / "inputs/transformer.json").read_bytes())
    first = discover(hypothesis, brief, prior_rejections=[])
    assert first["construction"]["original"]["best"]
    assert first["decision"] == "HOLD-no-admitted-opportunity"
    assert first["scale"]["credible_billion_plus_established"] is False
    again = discover(hypothesis, brief, prior_rejections=[first])
    assert again["decision"] == "previously-rejected-requires-material-new-evidence"
    assert again["previous"][0] == first


def test_scale_uses_adoption_capacity_and_capital_not_a_large_market_label() -> None:
    raw = data("transformer-hypothesis.json")["scale"]
    raw["production_capacity_units_by_year"] = [0] * 10
    audit = scale_audit(Scale.model_validate(raw))
    assert audit["total_served_units"] == 0
    assert audit["conditional_net_benefit_micro_usd"] == "0"
    assert audit["net_benefit_per_unit_required_for_billion_micro_usd"] is None
    assert audit["capital_gap_micro_usd"] > 0


def test_review_found_scale_declarations_do_not_establish_credibility() -> None:
    raw = data("transformer-hypothesis.json")["scale"]
    raw["verified_inputs"] = True
    raw["capital_committed_micro_usd"] = raw["capital_required_micro_usd"]
    raw["incremental_net_benefit_micro_usd_per_unit"] *= 2
    result = scale_audit(Scale.model_validate(raw))
    assert result["arithmetically_reaches_billion"] is True
    assert result["scale_evidence_complete_as_declared"] is True
    assert result["credible_billion_plus_established"] is False


def test_review_found_large_scale_amounts_remain_exact_and_serializable() -> None:
    raw = data("transformer-hypothesis.json")["scale"]
    raw.update(
        horizon_years=20,
        reachable_organizations=100_000,
        active_organizations_by_year=[100_000] * 20,
        production_capacity_units_by_year=[10**9] * 20,
        units_per_organization_per_year=1_000_000,
        incremental_net_benefit_micro_usd_per_unit=10**12,
    )
    result = scale_audit(Scale.model_validate(raw))
    assert result["conditional_net_benefit_micro_usd"] == "20000000000000000000000"
    assert canonical(result)


def test_commercial_model_counts_failure_and_development_once_and_keeps_cash_distinct() -> None:
    result = evaluate(data("ECONOMICS.json"))
    assert len(result["policies"]) == 6 and result["independent_arithmetic_checks"] == 54
    assert result["commercial_decision"].startswith("HOLD")
    assert result["actual_complete_cost_micro_usd"] is None
    assert result["actual_provider_profit_micro_usd"] is None
    assert result["actual_unrestricted_cash_micro_usd"] is None
    assert result["actual_customer_collections_micro_usd"] == 0
    for policy in result["policies"]:
        assessment = policy["assessment"]
        assert assessment["decision"] == "hold" and assessment["authority_granted"] is False
        assert "shared-use-rights-unresolved" in assessment["blockers"]
        failed = next(b for b in assessment["branches"] if b["scenario_id"] == "technical-failure")
        assert failed["projected_collections_micro_usd"] == 0 and failed["cash_costs_micro_usd"] > 0
        partial = next(b for b in assessment["branches"] if b["scenario_id"] == "correlated-correction-default")
        assert partial["defaulted_receivables_micro_usd"] > 0
        assert assessment["reserve_micro_usd"] == 5_000 * USD
        assert policy["restricted_deposits_micro_usd"] == 0


@pytest.mark.parametrize("kind", ["brief", "policy"])
def test_review_found_duplicate_external_json_keys_refuse_before_execution(tmp_path: Path, kind: str) -> None:
    brief = (HOME / "inputs/transformer.json").read_text()
    if kind == "brief":
        brief = '{"obligations":["essential-unpreserved-relationship"],' + brief[1:]
    (tmp_path / "brief.json").write_text(brief)
    command = [sys.executable, "-m", "contrib.production_frontier", str(tmp_path / "brief.json")]
    if kind == "policy":
        raw = (HOME / "inputs/POLICY.json").read_text()
        raw = '{"ranking":"wrong-original-policy",' + raw[1:]
        (tmp_path / "policy.json").write_text(raw)
        command += ["--policy", str(tmp_path / "policy.json")]
    result = subprocess.run(command, capture_output=True, text=True, timeout=20, check=False)
    assert result.returncode != 0 and "duplicate JSON object key" in result.stderr


def test_caller_cannot_drop_sources_from_an_otherwise_hash_matching_manifest(tmp_path: Path) -> None:
    manifest = {"schema": "production-frontier-freeze/v1", "files": {}}
    path = tmp_path / "FREEZE.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="omits or adds"):
        run(path, hashlib.sha256(path.read_bytes()).hexdigest(), tmp_path / "output")
    assert not (tmp_path / "output").exists()
    paths = frozen_paths()
    assert "contrib/production_frontier/inputs/ACCEPTANCE.json" in paths
    assert "contrib/production_frontier/economics.py" in paths


def test_positive_conditional_profit_cannot_replace_required_financing() -> None:
    inputs = data("ECONOMICS.json")
    inputs["modeled_initial_cash_usd"] = 0
    for i, state in enumerate(inputs["joint_states"]):
        state["probability_ppm"] = 1_000_000 if i == 0 else 0
    result = evaluate(inputs)
    assert any(
        int(r["assessment"]["expected_economic_contribution_micro_usd"]["numerator"]) > 0 for r in result["policies"]
    )
    assert result["best_conditional_action"] == "stop"


def test_optimized_python_does_not_remove_independent_economic_acceptance() -> None:
    program = """
from pathlib import Path
from contrib.production_frontier import economics
from alpha_factory_v1.core.runtime.successor.protocol import safe_json_loads
original = economics.assess_arrangement
def wrong(*args, **kwargs):
    report = original(*args, **kwargs)
    report['branches'][0]['economic_contribution_micro_usd'] += 1
    return report
economics.assess_arrangement = wrong
inputs = safe_json_loads(Path('contrib/production_frontier/inputs/ECONOMICS.json').read_bytes())
try:
    economics.evaluate(inputs)
except ValueError as error:
    print(str(error))
else:
    raise RuntimeError('optimized evidence check was removed')
"""
    result = subprocess.run(
        [sys.executable, "-O", "-c", program], capture_output=True, text=True, timeout=20, check=False
    )
    assert result.returncode == 0 and "independent branch arithmetic differs" in result.stdout
