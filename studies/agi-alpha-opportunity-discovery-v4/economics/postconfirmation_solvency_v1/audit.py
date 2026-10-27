# SPDX-License-Identifier: Apache-2.0
"""Independent adverse cash reconstruction; never retune the frozen market model."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any
import hashlib
import json
import random

HERE = Path(__file__).resolve().parent
ECONOMICS = HERE.parent
EPSILON = Decimal("0.00000001")


def digest(path: Path) -> str:
    """Return an exact local file identity."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(value: Any) -> Decimal:
    """Represent the retained numeric input without additional float arithmetic."""
    return Decimal(str(value))


def reconstruct_needs(seed: int, scenario: dict[str, Any]) -> list[dict[str, Any]]:
    """Reconstruct only current needs, never hidden future events or outcomes."""
    rng = random.Random(seed)
    result = []
    for i in range(rng.randint(1, scenario["max_leads"])):
        configured = rng.random() < scenario["configuration_probability"]
        human_hours = rng.uniform(2, 8) if configured else rng.uniform(12, 31)
        rate = rng.uniform(125, 225)
        outside = human_hours * rate
        result.append(
            {
                "id": f"need-{seed}-{i}",
                "human_hours": human_hours,
                "assumed_human_rate": rate,
                "outside_price": outside,
                "value": outside * rng.uniform(0.7, 2.2),
                "customer_effort": rng.uniform(40, 240),
                "configured": configured,
                "rights": rng.random() >= 0.12,
                "compatible": rng.random() < scenario["compatibility_probability"],
                "expert_hours": rng.uniform(2, 8) if configured else rng.uniform(8, 20),
                "adaptation_hours": rng.uniform(0, 4),
            }
        )
        # Frozen input generator consumes these draws without exposing events.
        for _ in range(4):
            rng.random()
    return result


def committed_cost(
    selected: list[dict[str, Any]], scenario: dict[str, Any], arm: str
) -> tuple[Decimal, dict[str, Any]]:
    """Compute cash A/B/C independently of the original planner and ledger."""
    retained = arm.startswith("retained")
    common_a = number(scenario["common_build"]) if retained else Decimal(0)
    retention_b = number(scenario["retention"]) if retained else Decimal(0)
    assessment_c = number(scenario["research_assessment"])
    job_rows = []
    private_a = Decimal(0)
    for buyer in selected:
        hours = number(buyer["expert_hours"])
        if retained and buyer["compatible"]:
            hours = hours * number(scenario["retained_cost_ratio"]) + number(buyer["adaptation_hours"])
        labor = hours * number(scenario["cash_hour_rate"])
        preparation = Decimal("0.2") * labor + Decimal(20)
        delivery = Decimal("0.8") * labor + Decimal(15)
        support = number(scenario["support_per_job"])
        private_a += preparation + delivery + support
        job_rows.append(
            {
                "buyer_id": buyer["id"],
                "retained_compatible": retained and buyer["compatible"],
                "hours": str(hours),
                "preparation_A": str(preparation),
                "committed_delivery_A": str(delivery),
                "support_A": str(support),
            }
        )
    total = common_a + private_a + retention_b + assessment_c
    return total, {
        "commissioned_common_A": str(common_a),
        "private_precollection_A": str(private_a),
        "retention_B": str(retention_b),
        "assessment_C": str(assessment_c),
        "jobs": job_rows,
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize adverse exposure without expected-profit claims."""
    return {
        "original_producing_plans": len(rows),
        "original_realization_produced": sum(r["original_realization_action"] == "produced" for r in rows),
        "original_realization_cancelled": sum(
            r["original_realization_action"] == "cancel_after_withdrawal" for r in rows
        ),
        "exposed_packages": sum(r["exposed"] for r in rows),
        "max_shortfall_usd": str(max((number(r["shortfall_usd"]) for r in rows), default=Decimal(0))),
        "max_required_opening_cash_usd": str(
            max((number(r["required_opening_cash_full_refund_usd"]) for r in rows), default=Decimal(0))
        ),
    }


def main() -> None:
    """Require the audit freeze, validate original identities, and write once."""
    freeze_path = HERE / "FREEZE.json"
    frozen = json.loads(freeze_path.read_text())
    for relative, expected in frozen["files"].items():
        if digest(ECONOMICS / relative) != expected:
            raise ValueError("Changed frozen audit input or code: " + relative)
    original = json.loads((ECONOMICS / "freeze.json").read_text())
    for relative, expected in original["files"].items():
        if digest(ECONOMICS / relative) != expected:
            raise ValueError("Original market freeze changed: " + relative)
    scenarios = {s["name"]: s for s in json.loads((ECONOMICS / "confirmation/assumptions.json").read_text())}
    originals = json.loads((ECONOMICS / "confirmation/rows.json").read_text())
    if len(originals) != 3520 or len(scenarios) != 11:
        raise ValueError("Original population size differs from the declared audit")
    examples = json.loads((ECONOMICS / "confirmation/cash_examples.json").read_text())
    example_buyer_checks = 0
    for example in examples:
        reconstructed = reconstruct_needs(example["seed"], example["scenario"])
        if reconstructed != example["buyers"]:
            raise ValueError("Independent need reconstruction disagrees with retained input example")
        example_buyer_checks += len(reconstructed)
    details = []
    max_reconciliation = Decimal(0)
    seen = set()
    for row in originals:
        key = (row["scenario"], row["arm"], row["seed"])
        if key in seen:
            raise ValueError("Duplicate original arm-horizon")
        seen.add(key)
        if row["plan"]["action"] != "produce":
            continue
        scenario = scenarios[row["scenario"]]
        plan = row["plan"]
        buyers = reconstruct_needs(row["seed"], scenario)
        if len(buyers) != row["needs"]:
            raise ValueError("Original need count differs")
        by_id = {b["id"]: b for b in buyers}
        selected = [by_id[identifier] for identifier in plan["buyers"]]
        full, breakdown = committed_cost(selected, scenario, row["arm"])
        advance = number(len(selected)) * number(plan["price"]) * number(plan["advance_fraction"])
        prior_required = max(Decimal(0), full - advance * (1 - number(plan["failure_refund_fraction"])))
        discrepancy = abs(prior_required - number(plan["required_opening_cash"]))
        max_reconciliation = max(max_reconciliation, discrepancy)
        if discrepancy > EPSILON:
            raise ValueError("Independent cost reconstruction disagrees with original cash formula")
        opening_cash = number(scenario["seed_cash"])
        if not plan["financeable"] or prior_required > opening_cash + EPSILON:
            raise ValueError("Selected original package was not financeable under its own assumptions")
        shortfall = max(Decimal(0), full - opening_cash)
        details.append(
            {
                "scenario": row["scenario"],
                "arm": row["arm"],
                "seed": row["seed"],
                "buyer_ids": plan["buyers"],
                "original_realization_action": row["result"]["action"],
                "same_opening_cash_usd": str(opening_cash),
                "full_advance_refund_usd": str(advance),
                "original_required_opening_cash_usd": str(prior_required),
                "required_opening_cash_full_refund_usd": str(full),
                "shortfall_usd": str(shortfall),
                "exposed": shortfall > EPSILON,
                "cost_breakdown": breakdown,
            }
        )
    arms = ("expert_standard", "retained_standard", "expert_arranged", "retained_arranged")
    grouped = []
    for name, scenario in scenarios.items():
        for arm in arms:
            subset = [r for r in details if r["scenario"] == name and r["arm"] == arm]
            grouped.append({"scenario": name, "arm": arm, "seed_cash_usd": scenario["seed_cash"], **summarize(subset)})
    result = {
        "schema": "postconfirmation-development-milestone-solvency/v1",
        "status": "adverse_audit_of_original_selected_plans_not_new_confirmation",
        "audit_freeze_sha256": digest(freeze_path),
        "original_market_freeze_sha256": digest(ECONOMICS / "freeze.json"),
        "inspected_original_rows": len(originals),
        "input_example_buyer_checks": example_buyer_checks,
        "max_original_cash_formula_reconciliation_usd": str(max_reconciliation),
        "actual_customer_collections_usd": 0,
        "actual_earned_revenue_usd": 0,
        "actual_complete_research_cost_usd": None,
        "original_results_modified": False,
        "aggregate": summarize(details),
        "by_arm": [{"arm": arm, **summarize([r for r in details if r["arm"] == arm])} for arm in arms],
        "by_scenario_arm": grouped,
        "rows": details,
        "limits": [
            "All prices, resources and costs are original research assumptions",
            "Original selected commitments, including subsequently cancelled plans, are audited",
            "Full committed work is a conservative adverse envelope, not a probability or realized loss",
            "Other contractual nonperformance, legal acceptance, strategic behavior and late payments are unmodeled",
            "No expected-profit, recovered-confirmation or new-customer claim",
        ],
    }
    with (HERE / "RESULTS.json").open("x") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps({"aggregate": result["aggregate"], "by_arm": result["by_arm"]}, indent=2))


if __name__ == "__main__":
    main()
