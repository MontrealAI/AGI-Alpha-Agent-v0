# SPDX-License-Identifier: Apache-2.0
"""Prospective resolution of the uninformative conditional-policy development tie."""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any

import economics as study

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "config/commercial_conditional_supplement.json"
OUTPUT = ROOT / "results/economics_conditional_supplement.json"
BOUND = [
    "src/economics.py",
    "src/economic_conditional_supplement.py",
    "config/commercial_protocol.json",
    "evidence/commercial_design_proposal.json",
    "results/economics_development.json",
    "results/economics_freeze.json",
    "results/economics_confirmation.json",
    "results/economics_summary.json",
]


def bindings() -> dict[str, str]:
    return {name: study.sha(ROOT / name) for name in BOUND}


def freeze() -> None:
    if PROTOCOL.exists() or OUTPUT.exists():
        raise FileExistsError("Supplement already committed or executed; preserve it rather than overwrite")
    config = study.read(study.CONFIG)
    protocol = {
        "schema": "agialpha.reserve.conditional-supplement-protocol.v1",
        "reason": "The primary selected conditional policy was an uninformative grid-order tie and cannot launch within nine opportunities. Prospectively test all nine already declared conditional policies; retain the primary no-launch selection.",
        "seed_start": 9821000,
        "worlds": 1000,
        "policies": [asdict(p) for p in study.policies(config) if p.family == "conditional"],
        "unchanged": "Same value, demand, timing, consent, prices, deposit choices, costs, startup gates, thresholds and financing rules. No parameter changes and no new policy optimization.",
        "source_and_primary_evidence_sha256": bindings(),
        "worlds_generated_before_this_commitment": False,
        "diagnostics": "Qualified pools, arrivals, procurement completion, owner consent and actual purchase commitments before the fixed launch deadline; theoretical and incurred-screening-adjusted minimum commitments; launch/readiness/financial outcomes and exhaustive failure classifications.",
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
    }
    PROTOCOL.write_text(json.dumps(protocol, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "commitment_sha256": study.sha(PROTOCOL),
                "seed_start": 9821000,
                "worlds": 1000,
                "policies": len(protocol["policies"]),
            }
        )
    )


def diagnose(config: dict[str, Any], w: dict[str, Any], policy: study.Policy, result: dict[str, Any]) -> dict[str, Any]:
    cm = config["commitments"]
    deadline = cm["launch_deadline_day"]
    base = (
        config["startup"]["cost_low_central_high_usd"][1] * cm["startup_forecast_multiplier"]
        + cm["fixed_forecast_months"] * config["business"]["monthly_cost_usd"][1]
        + config["business"]["insurance_six_month_usd"][1]
    )
    per_commitment = (
        policy.fee
        * cm["conservative_acceptance"]
        * cm["conservative_collection"]
        * cm["survival_probability"]
        * (1 - cm["conservative_processing_fraction"])
        - cm["delivery_forecast_usd_per_commitment"]
    )
    lower = math.ceil(base / per_commitment)
    arrived = [lead for lead in w["leads"] if lead["arrival"] <= deadline]
    considered = [lead for lead in arrived if lead["decision_day"] <= deadline]
    chosen = [lead for lead in considered if study.buyer_choice(config, lead, policy, {})["buy"]]
    screening = sum(lead["acquisition"] for lead in arrived)
    adjusted = math.ceil((base + screening) / per_commitment)
    times = {0, *[lead["decision_day"] for lead in considered]}
    margins = []
    for day in times:
        n = sum(lead["decision_day"] <= day for lead in chosen)
        incurred = sum(lead["acquisition"] for lead in w["leads"] if lead["arrival"] <= day)
        margins.append(n * per_commitment - base - incurred)
    consented = sum(all(lead["consents"]) for lead in considered)
    launched = result["launch_evidence"] is not None
    if launched:
        reason = (
            "launched_and_ready" if result["day180"]["ready_day"] is not None else result["day180"]["startup_status"]
        )
    elif len(w["leads"]) < lower:
        reason = "qualified_pipeline_smaller_than_minimum"
    elif len(arrived) < lower:
        reason = "too_few_arrived_before_deadline"
    elif len(considered) < lower:
        reason = "too_few_completed_procurement_before_deadline"
    elif consented < lower:
        reason = "insufficient_all_owner_consent_before_deadline"
    elif max(margins) < 0:
        reason = "value_budget_outside_option_or_screening_prevents_threshold"
    else:
        reason = "forecast_threshold_met_but_own_financing_refused"
    return {
        "qualified_pools": len(w["leads"]),
        "arrived_before_deadline": len(arrived),
        "procurement_complete_before_deadline": len(considered),
        "all_owner_consent_before_deadline": consented,
        "purchase_commitments_before_deadline": len(chosen),
        "minimum_commitments_before_any_screening_cost": lower,
        "minimum_commitments_including_screening_at_deadline": adjusted,
        "screening_cost_at_deadline": screening,
        "best_forecast_surplus_before_deadline": max(margins),
        "launched": launched,
        "failure_or_launch_class": reason,
    }


def run() -> None:
    if OUTPUT.exists():
        raise FileExistsError("Prospective supplement already executed; replay in a copy")
    protocol = study.read(PROTOCOL)
    before = bindings()
    if before != protocol["source_and_primary_evidence_sha256"]:
        raise ValueError("Supplement source or preserved primary evidence changed after commitment")
    config = study.read(study.CONFIG)
    worlds = [
        study.world(config, seed) for seed in range(protocol["seed_start"], protocol["seed_start"] + protocol["worlds"])
    ]
    rows = []
    for raw_policy in protocol["policies"]:
        policy = study.Policy(**raw_policy)
        runs = [study.simulate(config, w, policy) for w in worlds]
        diagnostics = [diagnose(config, w, policy, result) for w, result in zip(worlds, runs, strict=True)]
        summary = study.summarize(runs)["day180"]
        numeric = [key for key in diagnostics[0] if key not in ("launched", "failure_or_launch_class")]
        reasons = Counter(row["failure_or_launch_class"] for row in diagnostics)
        if sum(reasons.values()) != protocol["worlds"]:
            raise AssertionError("Unclassified supplemental world")
        rows.append(
            {
                "policy": asdict(policy),
                "name": policy.name,
                "operating_profit": summary["operating_profit"],
                "available_gain_excluding_seed": summary["available_gain_excluding_seed"],
                "revenue_mean": summary["revenue"]["mean"],
                "costs_mean": summary["costs_mean"],
                "counts_mean": summary["counts_mean"],
                "launch_fraction": sum(d["launched"] for d in diagnostics) / len(diagnostics),
                "readiness_fraction": summary["readiness_fraction"],
                "insolvent_fraction": summary["insolvent_fraction"],
                "conditional_on_readiness": summary["conditional_on_readiness"],
                "funnel": {key: study.distribution([float(d[key]) for d in diagnostics]) for key in numeric},
                "exhaustive_failure_or_launch_counts": dict(reasons),
            }
        )
    if before != bindings():
        raise ValueError("Primary files changed during supplemental execution")
    output = {
        "schema": "agialpha.reserve.conditional-supplement-results.v1",
        "protocol_sha256": study.sha(PROTOCOL),
        "seed_start": protocol["seed_start"],
        "worlds": protocol["worlds"],
        "policies": rows,
        "primary_evidence_preserved": True,
        "primary_decision": "No-launch remains the primary selected policy; this supplement does not reselect or replace it.",
        "all_policy_mean_full_venture_profit_nonpositive": all(row["operating_profit"]["mean"] <= 0 for row in rows),
        "all_policies_zero_launches": all(row["launch_fraction"] == 0 for row in rows),
        "interpretation": "A prospective diagnostic of an uninformative tie, using unchanged parameters and all nine existing conditional policies. No new optimization claim; synthetic preferences remain unvalidated.",
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
    }
    OUTPUT.write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "all_zero_launches": output["all_policies_zero_launches"],
                "all_mean_losses": output["all_policy_mean_full_venture_profit_nonpositive"],
                "policies": [
                    {
                        "policy": row["name"],
                        "profit_mean": row["operating_profit"]["mean"],
                        "launch_fraction": row["launch_fraction"],
                        "counts": row["exhaustive_failure_or_launch_counts"],
                    }
                    for row in rows
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("freeze", "run"))
    stage = parser.parse_args().stage
    freeze() if stage == "freeze" else run()
