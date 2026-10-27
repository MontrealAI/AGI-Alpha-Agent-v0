# SPDX-License-Identifier: Apache-2.0
"""Replay accepted local work and separately labeled customer-funds economics."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/runtime"))

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import Arrangement, assess_arrangement  # noqa: E402
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef  # noqa: E402
from alpha_factory_v1.core.runtime.successor.flywheel_customer import balances  # noqa: E402
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY  # noqa: E402
from alpha_factory_v1.core.runtime.successor.protocol import digest  # noqa: E402
import test_flywheel_protected as f  # noqa: E402
import test_flywheel_enterprise as e  # noqa: E402
from test_flywheel_customer import deposit, refund, apply  # noqa: E402

USD = 1_000_000
PRICES = (1000, 2000, 3000)
BUYER_CAPS = (1500, 2100, 2800, 3200)
COSTS = {
    "model": 120,
    "tools": 25,
    "compute": 30,
    "storage": 5,
    "network": 5,
    "human": 40,
    "acceptance": 100,
    "correction": 90,
    "overhead": 85,
}


def projection(
    price: int, cost_percent: int = 100, demand_percent: int = 100, default_delay_days: int = 21, seed_cash: int = 5000
) -> dict[str, Any]:
    """Assess a finite price hypothesis with the existing arrangement calculator."""
    source = EvidenceRef(
        journal_key="@customer-funds:assumed-engineering-market",
        record_digest=digest(
            "customer-funds-pricing-assumptions",
            {
                "caps": list(BUYER_CAPS),
                "costs": COSTS,
                "horizon_days": 90,
            },
        ),
    ).model_dump()
    chosen = [i for i, cap in enumerate(BUYER_CAPS) if price <= cap * demand_percent // 100]
    participants = [
        {
            "participant_id": f"assumed-buyer-{i}",
            "need": source,
            "outside_option": "Assumed USD4000 equivalent human-service package or postpone",
            "useful_outcome": "Finite resilient-placement solver, exact plan and independent verification",
            "responsibilities": ["Provide rights-cleared requirements and accept unchanged constraints"],
            "price_cap_micro_usd": BUYER_CAPS[i] * demand_percent * USD // 100,
            "value_hypothesis_micro_usd": 5000 * USD,
            "commitment": "proposed",
            "commitment_conditions": ["No actual buyer evidence; price/cap is an assumption"],
            "commitment_evidence": [],
            "rights_and_failure_terms": "Full refund on failed scoped acceptance",
        }
        for i in range(4)
    ]
    costs = [
        {
            "activity_id": "campaign-business",
            "bucket": "A",
            "category": "coordination",
            "cash_micro_usd": 600 * USD * cost_percent // 100,
            "opportunity_micro_usd": 0,
            "incurred_at": 0,
            "paid_at": 0,
            "basis": "Assumed 90-day acquisition, admin and business overhead",
        },
        {
            "activity_id": "candidate-assessment",
            "bucket": "B",
            "category": "assessment",
            "cash_micro_usd": 120 * USD,
            "opportunity_micro_usd": 0,
            "incurred_at": 0,
            "paid_at": 0,
            "basis": "Assumed incremental assessment even when retention is rejected; no repeated A learning cost",
        },
    ]
    for i in chosen:
        for category, amount in COSTS.items():
            costs.append(
                {
                    "activity_id": f"job-{i}-{category}",
                    "bucket": "A",
                    "category": "delivery",
                    "cash_micro_usd": amount * USD * cost_percent // 100,
                    "opportunity_micro_usd": 0,
                    "incurred_at": 1,
                    "paid_at": 7,
                    "basis": f"Assumed {category}; model includes originating learning; correction includes failed attempts",
                }
            )
    scenarios = []
    for name, probability in (
        ("success", 800_000),
        ("common-failure", 100_000),
        ("payment-default", 50_000),
        ("quality-refund", 50_000),
        ("withdrawal-stress", 0),
    ):
        receipts = (
            [
                {
                    "projection_id": f"job-{i}",
                    "participant_id": f"assumed-buyer-{i}",
                    "amount_micro_usd": price * USD,
                    "earned_at": 7,
                    "collected_at": None if name == "payment-default" and i == chosen[-1] else default_delay_days,
                    "acceptance_hypothesis": "Scoped exact deliverable accepted; monetary branch is hypothetical",
                }
                for i in chosen
            ]
            if name != "common-failure"
            else []
        )
        if name == "withdrawal-stress" and chosen:
            receipts = [r for r in receipts if r["participant_id"] != f"assumed-buyer-{chosen[0]}"]
        branch_costs = [dict(c) for c in costs]
        for receipt in receipts:
            if receipt["collected_at"] is not None:
                branch_costs.append(
                    {
                        "activity_id": "processing-" + receipt["projection_id"],
                        "bucket": "A",
                        "category": "serving",
                        "cash_micro_usd": price * USD * 3 // 100 + 300_000,
                        "opportunity_micro_usd": 0,
                        "incurred_at": receipt["collected_at"],
                        "paid_at": receipt["collected_at"],
                        "basis": "Assumed processing 3% plus USD0.30 on gross collections; retained after refunds",
                    }
                )
        refunds = (
            [
                {
                    "refund_id": "partial-refund",
                    "projection_id": f"job-{chosen[0]}",
                    "amount_micro_usd": price * USD // 5,
                    "at": max(30, default_delay_days),
                    "reason": "Assumed 20% refund after acceptance",
                }
            ]
            if name == "quality-refund" and chosen
            else []
        )
        scenarios.append(
            {
                "scenario_id": name,
                "probability_ppm": probability,
                "required_stress": name == "withdrawal-stress",
                "qualified": name != "common-failure",
                "risk_states": {"shared-quality": "fail" if name == "common-failure" else "pass"},
                "costs": branch_costs,
                "receipts": receipts,
                "refunds": refunds,
                "withdrawals": [
                    {
                        "participant_id": f"assumed-buyer-{chosen[0]}",
                        "at": 0,
                        "terms": "Withdrawal stress; preserve all conservatively budgeted attempt costs",
                    }
                ]
                if name == "withdrawal-stress" and chosen
                else [],
                "failure_handling": "All attempted delivery costs remain, including common failure; no failed-job sale",
            }
        )
    raw = {
        "arrangement_id": f"customer-funds-price-{price}",
        "version": 1,
        "offering": source,
        "participants": participants,
        "common_risks": [
            {
                "risk_id": "shared-quality",
                "description": "Uncalibrated common acceptance failure",
                "affected_participants": [p["participant_id"] for p in participants],
                "states": ["pass", "fail"],
                "qualification_success_states": ["pass"],
            }
        ],
        "scenarios": scenarios,
        "state_space_basis": "Explicit illustrative joint branches; not measured frequencies",
        "financing_basis": "Assumed seed cash, independent of sales; no customer deposit funds optional investment",
        "rights_cleared": False,
        "rights_basis": "No customers or external production rights acquired",
        "mode": "simulation",
        "authority_required": "Separate original production and customer approvals",
        "limitations": [
            "No measured demand, human-service quote, actual complete costs or current frontier comparison",
            "One package per buyer; no repeated purchases or unlimited demand assumed",
        ],
    }
    report = assess_arrangement(Arrangement.model_validate(raw), seed_cash * USD, reserve_micro_usd=250 * USD)
    return {
        "price_micro_usd": price * USD,
        "buyers": len(chosen),
        "horizon_days": 90,
        "customer_savings_if_accepted_micro_usd": len(chosen) * (4000 - price) * USD,
        "cost_percent": cost_percent,
        "demand_percent": demand_percent,
        "complete_assumptions": raw,
        "assessment": report,
    }


def expected(row: dict[str, Any]) -> Fraction:
    value = row["assessment"]["expected_economic_contribution_micro_usd"]
    return Fraction(int(value["numerator"]), value["denominator"])


def commercial() -> dict[str, Any]:
    development = [projection(p) for p in PRICES]
    selected = max(development, key=lambda row: (expected(row), -row["price_micro_usd"]))
    price = selected["price_micro_usd"] // USD
    freeze = {
        "prices_usd": list(PRICES),
        "caps_usd": list(BUYER_CAPS),
        "costs_usd": COSTS,
        "selected_price_usd": price,
        "selection": "Best tested 90-day expected economic contribution",
        "no_offer_after_assessment_micro_usd": -120 * USD,
    }
    frozen_digest = digest("customer-funds-policy-freeze", freeze)
    confirmation = [
        projection(price, c, d, delay, seed)
        for c, d, delay, seed in (
            (150, 80, 35, 5000),
            (200, 60, 60, 5000),
            (100, 0, 21, 5000),
            (100, 100, 21, 1000),
        )
    ]
    region = [projection(price, c, d) for c in (80, 100, 150, 200) for d in (60, 80, 100)]
    return {
        "human_reference": {
            "basis": "assumed-human-service-estimate",
            "amount_micro_usd": 4000 * USD,
            "team_hours": 40,
            "hourly_rate_micro_usd": 100 * USD,
            "scope": "One solver prototype, exact plan, verification and delivery; same local offering",
            "geography": "North American remote engineering, illustrative",
            "date": "2026-10-27",
            "quality": "The same finite capacity/failure-domain/minimum requirements",
            "range_micro_usd": [2000 * USD, 8000 * USD],
            "source": "Existing enterprise offering's estimate; no service quote or salary substitution",
        },
        "development": development,
        "frozen_policy": freeze,
        "frozen_policy_digest": frozen_digest,
        "selected": selected,
        "confirmation": confirmation,
        "tested_profitable_region": [
            {
                "cost_percent": r["cost_percent"],
                "demand_percent": r["demand_percent"],
                "positive": expected(r) > 0,
                "liquidity_feasible": r["assessment"]["liquidity_feasible"],
            }
            for r in region
        ],
        "retention": {
            "decision": "reject pending incremental evidence",
            "B_assessment_micro_usd": 120 * USD,
            "C_micro_usd": 0,
            "operational_alpha": "unmeasured",
            "retained_alpha": "unmeasured",
        },
        "actual_customer_collections_micro_usd": 0,
        "actual_complete_cost": "unknown",
        "actual_profit": "not established",
        "repeat_purchases": 0,
    }


def record() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="customer-funds-conformance-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        result = e.launch(state)
        e.accept(state, result)
        stages = []

        def capture(name: str) -> None:
            rows = list(state["costs"].snapshot().get("customer_deposits", {}).values())
            stages.append(
                {
                    "stage": name,
                    "receipt_balances": [balances(row) for row in rows],
                    "report": state["costs"].report(),
                    "ledger_digest": digest("customer-stage-ledger", state["costs"].snapshot()),
                }
            )

        capture("accepted-local-deliverable")
        apply(
            state,
            "customer-deposit",
            deposit(mission_id="placement-origin", amount_micro_usd=2000 * USD, service_price_micro_usd=2000 * USD),
        )
        capture("synthetic-customer-deposit")
        earning = {
            "event_id": "same-mission-earning",
            "receipt_id": "service-receipt",
            "amount_micro_usd": 2000 * USD,
            "delivery_kind": "general",
            "operation_id": "placement-origin",
            "execution_record_digest": result["digest"],
            "acceptance_record_digest": state["journal"].latest(ACCEPTANCE_KEY + "placement-origin")["digest"],
        }
        apply(state, "customer-earn", earning)
        capture("accepted-service-income-synthetic")
        apply(state, "customer-refund-due", refund("refund-due", allocation="earned", amount_micro_usd=400 * USD))
        capture("synthetic-refund-obligation")
        apply(state, "customer-refund", refund(allocation="earned", amount_micro_usd=400 * USD))
        capture("synthetic-partial-refund")
        apply(
            state,
            "customer-deposit",
            deposit(
                "procurement",
                mission_id="placement-origin",
                purpose="pass-through",
                amount_micro_usd=300 * USD,
                service_price_micro_usd=0,
            ),
        )
        capture("synthetic-procurement-custody")
        apply(
            state,
            "customer-refund",
            refund(
                "return-procurement", receipt_id="procurement", allocation="pass-through", amount_micro_usd=300 * USD
            ),
        )
        capture("synthetic-custody-returned")
        state["journal"].verify()
        path = {
            "offering": e.Enterprise(state["service"]).inspect("offering", "resilient-placement"),
            "mission": result["mission"],
            "execution_digest": result["digest"],
            "artifact": result["result"]["artifacts"][0],
            "acceptance": state["journal"].latest(ACCEPTANCE_KEY + "placement-origin"),
            "stages": stages,
        }
    sources = list((ROOT / "alpha_factory_v1/core/runtime").rglob("*.py")) + [
        Path(__file__),
        ROOT / "tests/runtime/test_flywheel_customer.py",
        ROOT / "tests/runtime/test_flywheel_enterprise.py",
        ROOT / "tests/runtime/test_flywheel_protected.py",
        ROOT / "tests/runtime/test_flywheel_specialists.py",
        ROOT / "scripts/record_general_flywheel.py",
    ]
    return {
        "schema": "customer-funds-evidence/v1",
        "mode": "executed-local-with-synthetic-money",
        "author": "Vincent Boucher — President of MONTREAL.AI",
        "sources": {
            p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(sources)
        },
        "connected_path": path,
        "commercial": commercial(),
        "summary": {
            "local_deliverable_accepted": True,
            "actual_customer_collections_micro_usd": 0,
            "actual_frontier_calls": 0,
            "complete_actual_cost": "unknown",
            "operational_alpha": "unmeasured",
            "retained_alpha": "unmeasured",
            "retention_decision": "reject pending evidence",
            "production_authority_created": False,
            "scope": "Existing finite placement regression; customer-funds integration is the new contribution",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("choose a new evidence output; preserve earlier trials")
    data = record()
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps({"output": str(args.output), "summary": data["summary"]}))


if __name__ == "__main__":
    main()
