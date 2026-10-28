# SPDX-License-Identifier: Apache-2.0
"""Supplementary matched contract economics for actual 48/144-candidate solvers.

This is conditional accounting, not a new enterprise trial or market measurement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import economics

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config/compute_economics_protocol.json"
METHODS = ("beta48", "learned48", "beta144")
CALIBRATION_PATH = ROOT / "evidence/numerical/beta144_confirmation/calibration.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + "\n")


def accepted(row: dict[str, Any], tier: float) -> bool:
    return bool(row["valid"] and row["objective_ratio"] <= 1 - tier)


def choose_common_quote(development: list[dict[str, Any]], tier: float, offer: str,
                        cfg: dict[str, Any]) -> dict[str, float]:
    """No confirmation data can enter the quote or its predicted demand."""
    successes = sum(accepted(row, tier) for row in development)
    technical_prior = (successes + 1) / (len(development) + 2)
    p = technical_prior * cfg["systemic_success_prior"]
    expected, price, conversion = economics.best_quote(offer, p, cfg["buyer_intercept_prior"], cfg, 1.0)
    return {"price_usd": price, "development_successes": successes,
            "development_n": len(development), "development_first_pass_probability": p,
            "modeled_conversion_probability": conversion, "development_expected_per_lead_usd": expected}


def delivery(row: dict[str, Any], baseline: dict[str, Any], tier: float, offer: str,
             price: float, cfg: dict[str, Any]) -> dict[str, float | bool]:
    """Integrate stated correction/systemic risks, rather than invent a sale."""
    units = economics.unit_cost(offer, cfg)
    direct = sum(units.values())
    incremental_cpu = (row["solve_seconds"] - baseline["solve_seconds"]) * cfg["cpu_usd_per_hour"] / 3600
    # The original compute envelope already covers baseline scheduling. Replace
    # that slice once, rather than charging both complete and measured CPU.
    direct += incremental_cpu
    if direct < 0:
        raise ValueError("Measured CPU replacement cannot make total delivery cost negative")
    technical = accepted(row, tier)
    first_pass = float(technical) * cfg["systemic_success_prior"]
    eventual = first_pass + (1 - first_pass) * cfg["correction_recovery_probability"]
    residual = cfg["residual_event_probability"] * cfg["residual_hours_per_event"] * cfg["human_rate_usd"]
    correction = (1 - first_pass) * direct * cfg["failure_correction_fraction"]
    refund = (1 - eventual) * cfg["refund_processing_usd"]
    cost = direct + residual + correction + refund
    collections = eventual * price
    return {"technical_accepted": technical, "eventual_acceptance_probability": eventual,
            "incremental_scheduler_cpu_usd": incremental_cpu,
            "expected_collections_usd": collections, "expected_delivery_A_usd": cost,
            "expected_contribution_before_program_usd": collections - cost,
            "first_pass_probability": first_pass, "correction_A_usd": correction,
            "refund_A_usd": refund, "residual_human_A_usd": residual}


def break_even(program_usd: float, increment_usd: float) -> int | None:
    if not math.isfinite(program_usd) or program_usd < 0 or not math.isfinite(increment_usd):
        raise ValueError("Finite program costs and increments are required")
    return max(1, math.ceil(program_usd / increment_usd)) if increment_usd > 0 else None


def freeze() -> dict[str, Any]:
    if PROTOCOL_PATH.exists():
        raise FileExistsError("Supplemental protocol already frozen")
    inputs = [Path(__file__), Path(economics.__file__), ROOT / "config/economics.json",
              ROOT / "config/numerical_quality_frontier.json", CALIBRATION_PATH,
              ROOT / "evidence/numerical/policy_v2.json"]
    grid = json.loads((ROOT / "config/numerical_quality_frontier.json").read_text())
    protocol = {
        "schema": "next-advantage-compute-economics-supplement/v1",
        "freeze_utc": datetime.now(timezone.utc).isoformat(),
        "registration_status": "Supplementary economic analysis declared after viewing Beta144 technical results; all tiers and methods retained. Not a prespecified primary claim.",
        "methods": list(METHODS), "grid": grid["grid_improvement_over_edd"],
        "offers": ["nominal", "robust"], "reuse_grid": [1, 4, 8, 16, 32, 64, 128, 256],
        "automated_program_costs_usd": [10.0, 35.0, 120.0],
        "invocation_B_usd_per_use": [0.0, 3.0],
        "paired_bootstrap_repetitions": 5000, "paired_bootstrap_seed": 130000,
        "pricing": "A common price is selected from the original bounded grid using only Beta48 development success and the original buyer prior. All three methods face this same quote. No willingness to pay for a stricter tier is empirically established.",
        "resource_comparison": "Beta144 uses three times the candidate evaluations; it is not an equal-compute control. Measured wall-clock scheduler time is converted at assumed USD3/hour. Only its difference from Beta48 replaces the already-budgeted CPU slice in A.",
        "collection_scope": "Per booked job; expected collection conditional on technical pass, 0.975 systemic success and 0.22 correction recovery. Collections are expected eventual receipts after settlement, not actual earned revenue. Corrections and refunds have their original costs. No agent chooses this solver after inspecting the same fresh case.",
        "program_scope": "Original v1 learning belongs to A and is not charged again. B/C program scenarios cover retention, assessment/sharing, additional Gym, composition for robust, and maintenance over a55-day life. Assumed automated envelopes10/35/120 are total program B+C budgets; no measured allocation between them is asserted. Primary assumption uses retain120,share90,Gym420,composition180 for robust, plus two35 maintenance cycles. Local invocation0 and hypothetical service invocation3 are separate B sensitivities; no live protected scheduling service exists.",
        "cpu_floor": "Observed v2 Gym seconds times assumed USD3/hour is an incomplete lower bound: it excludes assessment, integration, sharing, composition, upkeep and researcher effort. It is never labeled a complete-cost program.",
        "common_costs": "Existing automation2400, general daily overhead38, lead acquisition38 per lead, and offering launch850+validation150 are common to the matched methods and do not enter incremental break-even. Full enterprise absolute profitability is reported in the separate matched enterprise simulation. Dividing program cost by delivery contribution alone is not a full-business profit claim.",
        "uncertainty": "Descriptive paired case-bootstrap intervals over12 fresh synthetic numerical cases, conditional on all economic assumptions. These are not market confidence intervals. Correlated market/outage uncertainty, demand, attainable reuse, and capacity are not resolved by the bootstrap. Fresh cases are not iid real buyers.",
        "inputs": {str(path.relative_to(ROOT)): sha(path) for path in inputs},
    }
    write(PROTOCOL_PATH, protocol)
    return protocol


def check_protocol() -> dict[str, Any]:
    protocol = json.loads(PROTOCOL_PATH.read_text())
    for relative, expected in protocol["inputs"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError("Frozen compute economics dependency changed: " + relative)
    return protocol


def run(output: Path) -> dict[str, Any]:
    protocol = check_protocol()
    cfg = json.loads((ROOT / "config/economics.json").read_text())
    cal = json.loads(CALIBRATION_PATH.read_text())
    v2 = json.loads((ROOT / "evidence/numerical/policy_v2.json").read_text())
    floor = v2["seconds"] * cfg["cpu_usd_per_hour"] / 3600
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "compute_economics.json"
    raw_path = output / "compute_economics_cases.jsonl"
    if result_path.exists() or raw_path.exists():
        raise FileExistsError("Preserve original evidence; choose another output directory")
    rows, comparisons, sensitivity, counts, quotes = [], [], [], [], []
    for offer in protocol["offers"]:
        methods = cal["offerings"][offer]
        pools = {m: {r["case_id"]: r for r in methods[m]["confirmation_records"]} for m in METHODS}
        case_ids = sorted(pools["beta48"])
        if any(set(pool) != set(case_ids) or len(pool) != len(methods[m]["confirmation_records"])
               for m, pool in pools.items()):
            raise ValueError("All three methods must have identical unique fresh cases")
        bootstrap = np.random.default_rng(protocol["paired_bootstrap_seed"]).integers(
            0, len(case_ids), size=(protocol["paired_bootstrap_repetitions"], len(case_ids)))
        for tier in protocol["grid"]:
            quote = choose_common_quote(methods["beta48"]["development_records"], tier, offer, cfg)
            quotes.append({"offer": offer, "tier": tier, **quote})
            per_method = {}
            for method in METHODS:
                delivered = []
                for case_id in case_ids:
                    case = pools[method][case_id]
                    value = delivery(case, pools["beta48"][case_id], tier, offer, quote["price_usd"], cfg)
                    rows.append({"offer": offer, "tier": tier, "method": method, "case_id": case_id,
                                 "objective_ratio": case["objective_ratio"], "solve_seconds": case["solve_seconds"],
                                 "price_usd": quote["price_usd"], **value})
                    delivered.append(value)
                per_method[method] = delivered
                counts.append({"offer": offer, "tier": tier, "method": method, "fresh_n": len(delivered),
                               "fresh_successes": sum(r["technical_accepted"] for r in delivered),
                               "development_n": len(methods[method]["development_records"]),
                               "development_successes": sum(accepted(r, tier) for r in methods[method]["development_records"]),
                               "mean_solve_seconds": float(np.mean([pools[method][i]["solve_seconds"] for i in case_ids])),
                               **{key: float(np.mean([r[key] for r in delivered])) for key in
                                  ("expected_collections_usd", "expected_delivery_A_usd",
                                   "expected_contribution_before_program_usd", "incremental_scheduler_cpu_usd")}})
            for intervention, control in (("learned48", "beta48"), ("learned48", "beta144"), ("beta144", "beta48")):
                differences = np.array([a["expected_contribution_before_program_usd"] - b["expected_contribution_before_program_usd"]
                                        for a, b in zip(per_method[intervention], per_method[control])])
                delta = float(differences.mean())
                intervals = np.quantile(differences[bootstrap].mean(axis=1), [0.025, 0.975]).tolist()
                comparisons.append({"offer": offer, "tier": tier, "intervention": intervention, "control": control,
                                    "n": len(case_ids), "increment_per_booked_job_usd": delta,
                                    "descriptive_paired_case_bootstrap_95": intervals})
                if intervention != "learned48":
                    continue
                maintenance = (cfg["obsolete_after_days"] // cfg["maintenance_period_days"]) * cfg["maintenance_usd"]
                primary_B = cfg["investment_costs"]["retain"] + cfg["investment_costs"]["share"] + maintenance
                primary_C = cfg["investment_costs"]["gym"] + (cfg["investment_costs"]["compose"] if offer == "robust" else 0)
                programs = [{"label": "measured_Gym_CPU_only_lower_bound", "complete_cost": False,
                             "program_usd": floor, "B_usd": None, "C_usd": floor}]
                programs += [{"label": f"assumed_automated_program_{int(cost)}", "complete_cost": True,
                              "program_usd": cost, "B_usd": None, "C_usd": None} for cost in protocol["automated_program_costs_usd"]]
                programs.append({"label": "primary_assumed_program_with_upkeep", "complete_cost": True,
                                 "program_usd": primary_B + primary_C, "B_usd": primary_B, "C_usd": primary_C})
                for program in programs:
                    for invocation in protocol["invocation_B_usd_per_use"]:
                        net = delta - invocation
                        sensitivity.append({"offer": offer, "tier": tier, "control": control, **program,
                                            "invocation_B_usd_per_use": invocation, "net_increment_per_use_usd": net,
                                            "break_even_reuses": break_even(program["program_usd"], net),
                                            "net_increment_at_reuse": {str(n): n * net - program["program_usd"] for n in protocol["reuse_grid"]},
                                            "reuse_scope": "Conditional repeated draws from the fixed fresh case pool; demand/capacity and achieved lifetime reuse are not demonstrated."})
    with raw_path.open("w") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n")
    check_protocol()
    result = {"schema": "next-advantage-compute-economics/v1", "status": "SUPPLEMENTARY_CONDITIONAL_ACCOUNTING",
              "protocol": protocol, "protocol_sha256": sha(PROTOCOL_PATH), "case_rows": len(rows),
              "raw_cases_sha256": sha(raw_path), "observed_v2_Gym_seconds": v2["seconds"],
              "assumed_cpu_rate_usd_per_hour": cfg["cpu_usd_per_hour"], "incomplete_Gym_CPU_floor_usd": floor,
              "quotes": quotes, "counts": counts, "paired_comparisons": comparisons,
              "program_cost_sensitivity": sensitivity, "actual_customer_sales": 0,
              "actual_frontier_model_calls": 0, "new_v1_trials_fabricated": False}
    write(result_path, result)
    print(json.dumps({"status": "PASS", "case_rows": len(rows), "program_sensitivity_rows": len(sensitivity)}))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence")
    args = parser.parse_args()
    if args.freeze:
        freeze()
        print(json.dumps({"status": "FROZEN", "path": str(PROTOCOL_PATH)}))
    else:
        run(args.output)


if __name__ == "__main__":
    main()
