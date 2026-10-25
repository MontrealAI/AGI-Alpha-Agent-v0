# SPDX-License-Identifier: Apache-2.0
"""Post-result algebraic reuse diagnostic; no new scenario or input alteration.

Uses the existing base cases and the frozen thirty-minute conventional-work
assumption. This is additional reporting, not a new preregistered primary test.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
from pathlib import Path


PRIMARY_SHA256 = "cba5f2cf284e27f7097fc3f4cebe0bf985952cd64bfcabee78af51ca0c17ac9d"
FREEZE_SHA256 = "54bc70fec9bb635b473193d966d36ed5bf445460a58255f025cbed4a30854d8b"


def encode(value):
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(type(value).__name__)


def threshold(fixed_difference: Decimal, per_request_saving: Decimal) -> dict:
    """Solve fixed_difference <= N * per_request_saving for integer N >= 1."""
    if per_request_saving > 0:
        if fixed_difference <= 0:
            return {"status": "ECONOMICAL_AT_EVERY_POSITIVE_VOLUME",
                    "continuous_equality_requests": fixed_difference / per_request_saving,
                    "minimum_integer_payback_requests": 1,
                    "maximum_integer_economical_requests": None}
        value = fixed_difference / per_request_saving
        return {"status": "FINITE_MINIMUM_REUSE_THRESHOLD",
                "continuous_equality_requests": value,
                "minimum_integer_payback_requests": int(value.to_integral_value(rounding=ROUND_CEILING)),
                "maximum_integer_economical_requests": None}
    if per_request_saving == 0:
        return {"status": "ALL_VOLUMES_EQUAL" if fixed_difference == 0 else (
                    "ECONOMICAL_AT_EVERY_POSITIVE_VOLUME" if fixed_difference < 0
                    else "NO_FINITE_PAYBACK"),
                "continuous_equality_requests": None,
                "minimum_integer_payback_requests": 1 if fixed_difference <= 0 else None,
                "maximum_integer_economical_requests": None}
    if fixed_difference < 0:
        value = fixed_difference / per_request_saving
        maximum = int(value.to_integral_value(rounding=ROUND_FLOOR))
        return {"status": "LOW_VOLUME_ADVANTAGE_ONLY_NO_LONG_RUN_PAYBACK" if maximum >= 1
                           else "NO_POSITIVE_INTEGER_PAYBACK",
                "continuous_equality_requests": value,
                "minimum_integer_payback_requests": None,
                "maximum_integer_economical_requests": maximum if maximum >= 1 else None}
    return {"status": "NO_FINITE_PAYBACK", "continuous_equality_requests": None,
            "minimum_integer_payback_requests": None,
            "maximum_integer_economical_requests": None}


def run(results_path: Path, output_path: Path) -> None:
    payload = results_path.read_bytes()
    identity = hashlib.sha256(payload).hexdigest()
    if identity != PRIMARY_SHA256:
        raise ValueError("Primary result identity changed; inspect before deriving a new diagnostic")
    if output_path.exists():
        raise FileExistsError("Preserve diagnostic history: select a fresh output file")
    data = json.loads(payload, parse_float=Decimal)
    if data["input_manifest_sha256"] != FREEZE_SHA256:
        raise ValueError("Wrong specification freeze")
    rows = []
    with localcontext() as ctx:
        ctx.prec = 50
        for case in data["core_scenarios"]:
            if case["scenario"] != "base":
                continue
            comparison = next(item for item in case["traditional_comparisons"]
                              if item["productive_minutes"] == 30)
            human = comparison["traditional"]
            hybrid = comparison["hybrid"]
            q = case["expected_acceptance_probability"]
            fa = case["annual_at_demand"]["fixed_account"]["total"]
            fh = human["annual_at_demand"]["fixed_account"]["total"]
            fy = hybrid["annual_at_demand"]["fixed_account"]["total"]
            va = case["agent_variable"]["account"]["total"]
            vh = human["variable"]["account"]["total"]
            vy = hybrid["variable"]["account"]["total"]
            agent_limit = case["capacity"]["requested_capacity"]
            human_limit = human["capacity"]["requested_capacity"]
            hybrid_limit = hybrid["capacity"]["requested_capacity"]
            variants = {
                "agent_only_expected_accepted_cost": {
                    "fixed_difference": fa / q - fh,
                    "per_request_saving": vh - va / q,
                    "candidate_resource_admitted_requests": agent_limit,
                    "candidate_cost_formula": "F_A/(N*Q) + v_A/Q",
                    "candidate_setup_uniform_daily_fits": case["capacity"]["setup_window_fits_uniform_daily_limits"],
                },
                "complete_demand_hybrid": {
                    "fixed_difference": fy - fh,
                    "per_request_saving": vh - vy,
                    "candidate_resource_admitted_requests": hybrid_limit,
                    "candidate_cost_formula": "(F_A+F_H)/N + v_A + (1-Q)*(v_H+handoff)",
                    "candidate_setup_uniform_daily_fits": hybrid["capacity"]["setup_window_fits_uniform_daily_limits"],
                },
            }
            for label, values in variants.items():
                solution = threshold(values["fixed_difference"], values["per_request_saving"])
                required = solution["minimum_integer_payback_requests"]
                common_limit = min(values["candidate_resource_admitted_requests"], human_limit)
                solution.update({
                    "comparison": label, **values,
                    "traditional_resource_admitted_requests": human_limit,
                    "common_aggregate_admitted_requests": common_limit,
                    "minimum_threshold_within_both_primary_aggregate_bounds": (
                        required <= common_limit if required is not None else False),
                    "minimum_threshold_within_declared_demand": (
                        required <= case["scenario_inputs"]["requested_demand"] if required is not None else False),
                    "traditional_setup_uniform_daily_fits": human["capacity"]["setup_window_fits_uniform_daily_limits"],
                })
                equality = solution["continuous_equality_requests"]
                if equality is not None and equality > 0:
                    candidate = (fa / (equality * q) + va / q if label.startswith("agent_only")
                                 else fy / equality + vy)
                    traditional = fh / equality + vh
                    solution["algebraic_equality_residual"] = candidate - traditional
                else:
                    solution["algebraic_equality_residual"] = None
                rows.append({
                    "scenario": "base", "price_basis": case["price_basis"], "currency": case["currency"],
                    "productive_human_minutes_assumed": 30, "Q_assumed": q,
                    "annual_agent_fixed_cost": fa, "annual_human_fixed_cost": fh,
                    "annual_hybrid_fixed_cost": fy, "agent_variable_per_request": va,
                    "human_variable_per_request": vh, "hybrid_variable_per_request": vy,
                    **solution,
                })
    result = {
        "schema": "post-result-analytical-reuse-diagnostic/v1",
        "status": "POST_RESULT_ALGEBRAIC_DIAGNOSTIC_NOT_A_NEW_PRIMARY_SCENARIO",
        "primary_results_sha256": identity, "input_freeze_sha256": FREEZE_SHA256,
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scope": "Existing base scenario, four original price bases, traditional productive30min; no new assumptions, random sampling or parameter sweep.",
        "formula": "DeltaF <= N*DeltaV; pure DeltaF=F_A/Q-F_H, DeltaV=v_H-v_A/Q; hybrid DeltaF=F_Y-F_H, DeltaV=v_H-v_Y; F_Y includes both readiness accounts.",
        "limitations": [
            "This algebraic diagnostic was requested after the primary results. The sixteen frozen specification files and all primary result bytes remain unchanged.",
            "Pure Agent compares cost per expected accepted output and does not complete unresolved requests. The hybrid includes the complete failed Agent cost and full traditional fallback.",
            "A no-finite-payback result occurs when the fixed disadvantage is positive and the candidate has no positive recurring saving; more reuse alone cannot repair that relationship.",
            "Thresholds are compared with the already-computed primary aggregate resource admission bounds, including demand; no new capacity optimization is performed.",
            "Aggregate resource admission is only an upper bound. The independently exposed uniform-daily setup inconsistency remains, so a threshold within that bound would still not establish daily schedulability.",
            "All annual fixed and monthly reserve costs remain included. Resource cost thresholds do not establish cash payback, customer savings or provider revenue.",
        ],
        "rows": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, default=encode, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output_path), "rows": len(rows),
                      "sha256": hashlib.sha256(output_path.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.results, args.output)
