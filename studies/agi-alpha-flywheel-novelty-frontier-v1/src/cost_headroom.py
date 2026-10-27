# SPDX-License-Identifier: Apache-2.0
"""Post-result analytic cost headroom; no refitting or behavioral simulation.

From the study directory:
  python src/cost_headroom.py --output results/cost-headroom-exploratory.json
Choose a fresh --output for reproduction. Existing outputs are never replaced.
Uses only the Python standard library and does not import economics.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(), parse_float=Decimal)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(root):
    cfg_path = root / "config/economics.json"
    result_path = root / "results/economics-results.json"
    freeze_path = root / "results/economics-policy-freeze.json"
    cfg, results, freeze = load(cfg_path), load(result_path), load(freeze_path)
    source_path = root / "src/economics.py"
    amendment_path = root / "results/economics-amendment-v1.json"
    hashes = {"config": digest(cfg_path), "source": digest(source_path), "amendment": digest(amendment_path)}
    if hashes != freeze["hashes"] or results["freeze"] != freeze:
        raise ValueError("Frozen inputs or policy differ; analytic stress will not proceed")
    originated = freeze["research_cost_primary"]["A_originating_research_total"]
    capacity = cfg["annual_capacity"]
    output = {}
    with localcontext() as context:
        context.prec = 50
        for scenario in ("central", "favorable"):
            r = results["results"][scenario]
            c = r["conditional_qualified_operation"]
            q = r["qualification_probability_assumed"]
            mean = c["qualified_annual_operating_profit"]["mean"]
            lower = c["qualified_annual_operating_profit"]["p05"]
            units = c["units"]["mean"]
            margin = q * mean - originated
            if abs(margin - r["conditional_predevelopment_E0_central"]) > Decimal("0.000001"):
                raise ValueError(f"Frozen mean arithmetic failed for {scenario}")
            feasible = margin > 0
            output[scenario] = {
                "frozen_inputs": {"q_assumed": q, "qualified_annual_operating_profit_mean_usd": mean,
                                  "qualified_annual_operating_profit_p05_usd": lower,
                                  "A_originating_research_usd": originated,
                                  "mean_simulated_annual_units": units, "annual_capacity_units": capacity,
                                  "expected_predevelopment_profit_mean_usd": margin},
                "mean_project_headroom": {
                    "positive_region_exists_for_nonnegative_added_costs": feasible,
                    "strict_region": "Delta_A >= 0, Delta_O >= 0, and Delta_A + q * Delta_O < frozen_expected_project_mean",
                    "boundary_extra_origination_usd_at_zero_extra_annual_cost": margin if feasible else None,
                    "boundary_extra_annual_qualified_cost_usd_at_zero_extra_origination": margin / q if feasible else None,
                    "signed_margin_usd": margin,
                    "interpretation": "Boundary values produce zero expected profit and are excluded from the strictly positive region. A negative baseline margin means no nonnegative added-cost allowance, not a zero-cost profitable case."
                },
                "p05_operating_constraint_for_constant_annual_cost": {
                    "positive_region_exists": lower > 0,
                    "strict_region": "Delta_O < frozen_operating_profit_p05; Delta_A is an originating cost, outside annual operating profit",
                    "boundary_extra_annual_qualified_cost_usd": lower if lower > 0 else None,
                    "signed_p05_operating_profit_usd": lower,
                    "combined_mean_project_and_p05_operating_region_exists": feasible and lower > 0,
                    "combined_extra_annual_cost_boundary_when_Delta_A_zero_usd": min(margin / q, lower) if feasible and lower > 0 else None,
                    "combined_general_bound": "For nonnegative Delta_A below the mean-project margin, Delta_O < min((margin - Delta_A) / q, p05_operating_profit), provided the right side is positive.",
                    "interpretation": "Subtracting the same annual expense from every stored qualified world shifts its fifth percentile by that expense. This is a bound within a constructed scenario, not an empirical confidence bound."
                },
                "fixed_demand_per_unit_accounting_stress": {
                    "mean_project_equation": "remaining expected project mean = margin - Delta_A - q * (Delta_O + c * mean_units)",
                    "strict_extra_cost_per_unit_boundary_usd_with_Delta_A_and_Delta_O_zero": margin / (q * units) if feasible and units > 0 else None,
                    "sufficient_per_unit_boundary_preserving_p05_operating_positive_using_capacity_usd": lower / capacity if lower > 0 else None,
                    "sufficient_combined_boundary_usd_with_no_other_added_cost": min(margin / (q * units), lower / capacity) if feasible and lower > 0 and units > 0 else None,
                    "capacity_bound_proof": "For c >= 0 and every stored N <= capacity, P - c*N >= P - c*capacity, hence p05(P-c*N) >= p05(P) - c*capacity. This is sufficient, not a necessary or exact per-unit fifth-percentile bound.",
                    "interpretation": "Mean-unit arithmetic holds prices, participation, demand, allocation, qualification and existing financing fixed. It does not reevaluate buyer behavior or induced working-capital interest. Dividing p05 profit by mean units would not establish a fifth-percentile per-unit bound and is not done."
                }
            }
    return {
        "schema": "agi-alpha.economics.exploratory-cost-headroom.v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "Post-result exploratory analytic accounting stress on frozen constructed scenarios",
        "prospective_registration": False,
        "new_worlds_generated": 0, "prices_reoptimized": False, "frozen_results_modified": False,
        "currency": cfg["currency"],
        "horizon": "Originating development plus one subsequent operating year; pre-tax, not a discounted enterprise valuation",
        "variables": {"Delta_A": "Additional originating cost incurred regardless of qualification",
                      "Delta_O": "Additional constant annual operating expense incurred only if physically qualified",
                      "c": "Additional direct expense per accepted unit; nonnegative, with modeled units fixed",
                      "q": "Original uncalibrated physical-qualification probability assumption; no new probability is assigned"},
        "equations": {"remaining_expected_project_mean": "q * mean_qualified_annual_profit - A - Delta_A - q*Delta_O",
                      "positive_region": "Delta_A + q*Delta_O < q*mean_qualified_annual_profit - A",
                      "per_unit_extension": "Delta_A + q*(Delta_O + c*mean_units) < q*mean_qualified_annual_profit - A"},
        "scenarios": output,
        "provenance": {"frozen_input_hashes": hashes,
                       "economics_results_sha256": digest(result_path),
                       "policy_freeze_sha256": digest(freeze_path),
                       "analytic_script_sha256": digest(Path(__file__)),
                       "frozen_policy_timestamp_utc": freeze["freeze_utc"],
                       "source_files": ["config/economics.json", "results/economics-results.json", "results/economics-policy-freeze.json", "results/economics-amendment-v1.json", "src/economics.py"]},
        "limitations": [
            "These algebraic allowances do not estimate the amount or probability of omitted costs. No fabricated distribution is attached to unknown costs.",
            "Physical qualification, the 70% avoided-loss link, buyer participation and complete physical delivery costs remain unvalidated. The q assumptions are not empirical estimates.",
            "Existing generic allowances do not establish inclusion of all failed acquisition, yield/rework, capacity equipment, applicable qualification, rights, insurance or exceptional recall costs. Support/recovery versus warranty and internal versus external test work lack disjoint task-level scope. Economic completeness and semantic non-overlap are therefore not established.",
            "Changed financing, delays, demand, performance, prices or qualification may consume more value than the direct added expense. This accounting stress holds them fixed and is not a behavioral reevaluation.",
            "Fifth-percentile statistics describe the stored conditional simulation only. A positive fifth-percentile operating bound does not remove physical qualification failures or imply a positive fifth-percentile full project result.",
            "Actual collections remain zero, full actual session cost remains unknown, and the physical and novelty gates remain unpassed. Actual decision remains HOLD."
        ],
        "reproduce": "python src/cost_headroom.py --output /tmp/agi-alpha-cost-headroom-new.json"
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--study-root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new path")
    report = build(args.study_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False, default=lambda value: float(value) if isinstance(value, Decimal) else str(value))
        stream.write("\n")
    print(json.dumps({"output": str(args.output), "scenarios": {name: {"expected_project_margin": float(data["frozen_inputs"]["expected_predevelopment_profit_mean_usd"]), "positive_added_cost_region": data["mean_project_headroom"]["positive_region_exists_for_nonnegative_added_costs"]} for name, data in report["scenarios"].items()}}, indent=2))


if __name__ == "__main__":
    main()
