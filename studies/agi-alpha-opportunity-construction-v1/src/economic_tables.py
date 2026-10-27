# SPDX-License-Identifier: Apache-2.0
"""Make compact publication tables from the frozen economic confirmation."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import economics as study

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    config = study.read(ROOT / "config/commercial_protocol.json")
    freeze = study.read(ROOT / "results/economics_freeze.json")
    if (
        study.sha(ROOT / "src/economics.py") != freeze["source_sha256"]
        or study.sha(ROOT / "config/commercial_protocol.json") != freeze["protocol_sha256"]
    ):
        raise ValueError("The table derivation requires the frozen source and protocol")
    data = study.read(ROOT / "results/economics_confirmation.json")
    rows: list[dict[str, Any]] = []
    for family in ("no_launch", "direct", "conditional"):
        summary = data["summaries"][family]["day180"]
        policy = data["policies"][family]
        rows.append(
            {
                "policy": family,
                "fee_usd": policy["fee"],
                "deposit_fraction": policy["deposit"],
                "profit_mean_usd": summary["operating_profit"]["mean"],
                "profit_p05_usd": summary["operating_profit"]["p05"],
                "profit_p95_usd": summary["operating_profit"]["p95"],
                "positive_profit_fraction": summary["operating_profit"]["positive_fraction"],
                "revenue_mean_usd": summary["revenue"]["mean"],
                "complete_cost_mean_usd": summary["total_cost"]["mean"],
                "delivery_contribution_mean_usd": summary["service_contribution"]["mean"],
                "accepted_mean": summary["counts_mean"]["accepted"],
                "readiness_fraction": summary["readiness_fraction"],
                "cash_mean_usd": summary["cash"]["mean"],
                "available_funds_mean_usd": summary["available_funds"]["mean"],
                "available_gain_excluding_seed_mean_usd": summary["available_gain_excluding_seed"]["mean"],
            }
        )
    ready = [row for row in data["all_worlds"]["direct"] if row[8]]
    # For a successfully ready baseline world, every startup stage completes and
    # its actual incurred startup charge equals the frozen world's startup draw.
    # The compact output already contains profit and readiness; regeneration here
    # recovers that deterministic draw without new simulations or assumptions.
    ready_after_startup = [row[1] + study.world(config, row[0])["startup_cost"] for row in ready]
    direct = data["summaries"]["direct"]["day180"]
    accepted = direct["counts_mean"]["accepted"]
    delivery_cost = sum(direct["costs_mean"][key] for key in ("A_delivery", "processing", "credit_loss"))
    fee = data["policies"]["direct"]["fee"]
    cm = config["commitments"]
    fixed = (
        config["startup"]["cost_low_central_high_usd"][1] * cm["startup_forecast_multiplier"]
        + cm["fixed_forecast_months"] * config["business"]["monthly_cost_usd"][1]
        + config["business"]["insurance_six_month_usd"][1]
        + 3000
    )
    thresholds = {}
    for price in config["policy_grid"]["fees_usd"]:
        per_commitment = (
            price
            * cm["conservative_acceptance"]
            * cm["conservative_collection"]
            * cm["survival_probability"]
            * (1 - cm["conservative_processing_fraction"])
            - cm["delivery_forecast_usd_per_commitment"]
        )
        import math

        thresholds[str(price)] = {
            "required_commitments": math.ceil(fixed / per_commitment),
            "expected_net_per_commitment_after_delivery_usd": per_commitment,
        }
    result = {
        "schema": "agialpha.reserve.publication-economic-tables.v1",
        "evidence": "All modeled; Monte Carlo trajectories are alternatives, not actual customers or transactions",
        "source_confirmation_sha256": study.sha(ROOT / "results/economics_confirmation.json"),
        "policy_rows": rows,
        "direct_delivery_economics": {
            "price_usd": fee,
            "variable_cost_per_accepted_equivalent_usd": delivery_cost / accepted if accepted else None,
            "contribution_per_accepted_equivalent_usd": fee - delivery_cost / accepted if accepted else None,
            "complete_venture_cost_per_accepted_equivalent_usd": direct["full_cost_per_accepted_ratio"],
            "ratio_definition": "Sum costs across all 1000 worlds divided by all accepted assessments, including failed-booking costs. Variable cost excludes startup, acquisition, fixed business and insurance. Complete venture cost includes them. No dollar total is actual earned revenue.",
            "ready_worlds": len(ready),
            "ready_full_venture_profit_mean_usd": direct["conditional_on_readiness"]["mean_full_venture_profit"],
            "ready_operating_profit_excluding_startup": study.distribution(ready_after_startup)
            if ready_after_startup
            else None,
            "interpretation": "Positive delivery contribution is not profitable service operation: acquisition, business and insurance still produce a loss even after successful startup is treated as sunk.",
        },
        "conservative_commitment_threshold_example": {
            "screening_already_spent_usd": 3000,
            "fixed_forecast_usd": fixed,
            "fees": thresholds,
            "boundary": "The selected $6000 conditional policy is a grid-order tie and is structurally unable to launch within nine qualified opportunities. All nine policies tied without launches in development; only the frozen selected policy was freshly confirmed. Four high-value $18000 commitments are a next validation target, not observed demand.",
        },
        "actual_complete_research_cost_usd": None,
        "actual_customer_collections_usd": 0,
    }
    (ROOT / "results/economics_plot_data.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    with (ROOT / "results/economics_policy_table.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
