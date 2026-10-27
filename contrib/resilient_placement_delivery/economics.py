# SPDX-License-Identifier: Apache-2.0
"""Conditional same-scope service economics through the existing arrangement engine."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import Arrangement, assess_arrangement
from alpha_factory_v1.core.runtime.successor.protocol import digest

USD = 1_000_000
PRICES_USD = (150, 250, 400)
CAPS_USD = (175, 225, 300, 450)
UNIT_COSTS = {
    "intake-context": 3_000_000,
    "frontier-model": 8_000_000,
    "deterministic-tools": 1_000_000,
    "compute": 2_000_000,
    "storage": 250_000,
    "network": 250_000,
    "independent-acceptance": 2_000_000,
    "failed-attempt-correction": 4_000_000,
    "packaging": 2_000_000,
    "automated-support": 3_000_000,
    "acquisition-per-booked-order": 10_000_000,
    "order-admin": 1_500_000,
}
FIXED_COSTS = {"infrastructure": 80 * USD, "maintenance": 200 * USD, "acquisition-setup": 120 * USD, "admin": 100 * USD}
HUMAN_REFERENCE: dict[str, Any] = {
    "basis": "explicit-labor-estimate-not-a-quote",
    "scope": "Validate one named brief, plan with existing software, independently check, package, correct and support",
    "hours": {
        "intake": "0.50",
        "planning": "0.75",
        "independent-check": "0.50",
        "packaging": "0.50",
        "correction-support": "0.75",
    },
    "total_hours": "3.00",
    "hourly_rate_micro_usd": 100 * USD,
    "overhead_percent": 20,
    "total_micro_usd": 360 * USD,
    "uncertainty_range_micro_usd": [180 * USD, 720 * USD],
    "development_cost": "Excludes building a solver; both services reuse existing tools",
    "willingness_to_pay": "Unobserved and separate from estimated labor cost",
}


def rational(value: Fraction | int) -> dict[str, int]:
    """Return a JSON-safe exact amount, without suggesting measured precision."""
    value = Fraction(value)
    return {"numerator": value.numerator, "denominator": value.denominator}


def amount(value: dict[str, Any]) -> Fraction:
    """Read the existing engine's rational amount."""
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def scenario(
    price_usd: int = 250,
    opportunities: int = 4,
    acceptance_percent: int = 75,
    cost_percent: int = 100,
    acquisition_percent: int = 100,
    workload_percent: int = 100,
    initial_cash_usd: int = 1000,
    collection_day: int = 21,
) -> dict[str, Any]:
    """Assess hypothetical uptake, complete costs and cash; never mutate actual accounting."""
    values = (
        price_usd,
        opportunities,
        acceptance_percent,
        cost_percent,
        acquisition_percent,
        workload_percent,
        initial_cash_usd,
        collection_day,
    )
    if any(not isinstance(value, int) or isinstance(value, bool) for value in values):
        raise ValueError("economics requires exact integer assumptions")
    if not (
        1 <= price_usd <= 100_000
        and 0 <= opportunities <= 32
        and 0 <= acceptance_percent <= 100
        and 1 <= cost_percent <= 1000
        and 0 <= acquisition_percent <= 1000
        and 1 <= workload_percent <= 1000
        and 0 <= initial_cash_usd <= 1_000_000
        and 7 <= collection_day <= 90
    ):
        raise ValueError("economics assumption outside finite scope")
    assumptions = dict(
        zip(
            (
                "price_usd",
                "opportunities",
                "acceptance_percent",
                "cost_percent",
                "acquisition_percent",
                "workload_percent",
                "initial_cash_usd",
                "collection_day",
            ),
            values,
        )
    )
    ref = {
        "journal_key": "@commercial-placement:unmeasured-market-assumptions",
        "record_digest": digest("placement-commercial-assumptions", assumptions),
    }
    caps = [CAPS_USD[index % len(CAPS_USD)] for index in range(opportunities)]
    outside_option_micro_usd = int(HUMAN_REFERENCE["total_micro_usd"])
    effective_caps = [min(cap * USD, outside_option_micro_usd) for cap in caps]
    booked = [index for index, cap in enumerate(effective_caps) if price_usd * USD <= cap]
    participants = [
        {
            "participant_id": f"hypothesis-{index}",
            "need": ref,
            "outside_option": (
                "Same-scope estimated human service USD360, an ordinary solver, or postpone; "
                "modeled purchase ceiling cannot exceed USD360 and no convenience premium is assumed"
            ),
            "useful_outcome": "Named finite placement decision pack and independent exact check",
            "responsibilities": ["Supply complete rights-cleared capacity, failure-domain and objective data"],
            "price_cap_micro_usd": min(cap * USD, outside_option_micro_usd),
            "value_hypothesis_micro_usd": cap * USD,
            "commitment": "proposed",
            "commitment_conditions": ["No observed buyer, quote or recurring order"],
            "commitment_evidence": [],
            "rights_and_failure_terms": "No charge for rejected work; modeled full refund after quality defect",
        }
        for index, cap in enumerate(caps or [0])
    ]
    unit_costs = {}
    for name, value in UNIT_COSTS.items():
        scale = acquisition_percent if name.startswith("acquisition") else workload_percent
        unit_costs[name] = value * cost_percent * scale // 10_000
    fixed = dict(FIXED_COSTS)
    fixed["acquisition-setup"] = fixed["acquisition-setup"] * acquisition_percent // 100
    fixed = {name: value * cost_percent // 100 for name, value in fixed.items()}
    costs = [
        {
            "activity_id": "fixed-" + name,
            "bucket": "A",
            "category": "maintenance" if name == "maintenance" else "coordination",
            "cash_micro_usd": value,
            "opportunity_micro_usd": 0,
            "incurred_at": 0,
            "paid_at": 0,
            "basis": "Unmeasured 90-day operating estimate; excludes historical research",
        }
        for name, value in fixed.items()
        if value
    ]
    costs += [
        {
            "activity_id": "all-orders-" + name,
            "bucket": "A",
            "category": "support" if name == "automated-support" else "delivery",
            "cash_micro_usd": value * len(booked),
            "opportunity_micro_usd": 0,
            "incurred_at": 1,
            "paid_at": 7,
            "basis": "Estimate for every booked attempt, including rejected, defaulted and refunded work; no forced human review",
        }
        for name, value in unit_costs.items()
        if value and booked
    ]
    q = acceptance_percent * 10_000
    branches = []
    for name, probability in (
        ("accepted-collected", q * 90 // 100),
        ("accepted-default", q * 5 // 100),
        ("accepted-refunded", q * 5 // 100),
        ("rejected-common", 1_000_000 - q),
        ("withdrawal-stress", 0),
    ):
        receipts: list[dict[str, Any]] = (
            []
            if name in {"rejected-common", "withdrawal-stress"}
            else [
                {
                    "projection_id": f"order-{index}",
                    "participant_id": f"hypothesis-{index}",
                    "amount_micro_usd": price_usd * USD,
                    "earned_at": 7,
                    "collected_at": None if name == "accepted-default" else collection_day,
                    "acceptance_hypothesis": "Unmeasured complete scoped acceptance; shared branch, not independent per-order evidence",
                }
                for index in booked
            ]
        )
        branch_costs = list(costs)
        if receipts and name != "accepted-default":
            branch_costs.append(
                {
                    "activity_id": "processing",
                    "bucket": "A",
                    "category": "serving",
                    "cash_micro_usd": (price_usd * USD * 3 // 100 + 300_000) * len(booked),
                    "opportunity_micro_usd": 0,
                    "incurred_at": collection_day,
                    "paid_at": collection_day,
                    "basis": "Assumed 3% plus USD0.30 per collection, including refunded sales",
                }
            )
        refunds = (
            [
                {
                    "refund_id": "refund-" + receipt["projection_id"],
                    "projection_id": receipt["projection_id"],
                    "amount_micro_usd": receipt["amount_micro_usd"],
                    "at": max(30, collection_day),
                    "reason": "Full modeled refund; original attempt/support/processing costs retained",
                }
                for receipt in receipts
            ]
            if name == "accepted-refunded"
            else []
        )
        branches.append(
            {
                "scenario_id": name,
                "probability_ppm": probability,
                "qualified": name not in {"rejected-common", "withdrawal-stress"},
                "required_stress": name == "withdrawal-stress",
                "risk_states": {},
                "costs": branch_costs,
                "receipts": receipts,
                "refunds": refunds,
                "withdrawals": [
                    {
                        "participant_id": f"hypothesis-{index}",
                        "at": 0,
                        "terms": "Retain all budgeted failed-intake costs; no later sale",
                    }
                    for index in booked
                ]
                if name == "withdrawal-stress"
                else [],
                "failure_handling": "All booked attempts retain full cost; failed work earns nothing; defaulted receivables are fully impaired",
            }
        )
    raw = {
        "arrangement_id": "placement-decision-pack-model",
        "version": 1,
        "offering": ref,
        "participants": participants,
        "scenarios": branches,
        "state_space_basis": "Uncalibrated common acceptance branch; 90/5/5 collection/default/refund conditional on acceptance",
        "financing_basis": "Hypothetical opening cash, not customer deposits; no deposit is used as unrestricted capital",
        "rights_cleared": False,
        "rights_basis": "No buyers or commercial production rights acquired",
        "mode": "simulation",
        "authority_required": "Separately qualified customer, execution, spending and payment authority",
        "limitations": [
            "All demand, rates, acceptance probabilities and monetary costs are hypotheses",
            "Actual research cost unknown; no paid frontier or timed human comparison",
            "Model preserves correlation and full attempt costs; no inferred repeat demand",
        ],
    }
    assessment = assess_arrangement(
        Arrangement.model_validate(raw), initial_cash_usd * USD, reserve_micro_usd=100 * USD
    )
    direct = sum(unit_costs.values())
    expected_receipts = Fraction(q, 1_000_000) * len(booked) * price_usd * USD
    net_unit = (
        Fraction(q, 1_000_000)
        * (Fraction(9, 10) * price_usd * USD - Fraction(95, 100) * (price_usd * USD * 3 // 100 + 300_000))
        - direct
    )
    fixed_total = sum(fixed.values())
    required_orders = None if net_unit <= 0 else max(0, -(-fixed_total // net_unit))
    expected_profit = amount(assessment["expected_economic_contribution_micro_usd"])
    if expected_profit != net_unit * len(booked) - fixed_total:
        raise ArithmeticError("engine and independent unit economics disagree")
    return {
        "assumptions": assumptions,
        "buyer_caps_usd": caps,
        "effective_buyer_caps_micro_usd": effective_caps,
        "booked_orders": len(booked),
        "uptake_basis": (
            "Unobserved buyer cap limited by the equal-scope estimated human outside option; "
            "recomputed at every price with no assumed premium"
        ),
        "per_attempt_costs_micro_usd": unit_costs,
        "direct_cost_per_attempt_micro_usd": direct,
        "fixed_operating_cost_micro_usd": fixed_total,
        "expected_gross_earned_before_impairment_micro_usd": rational(expected_receipts),
        "expected_bad_debt_impairment_micro_usd": rational(expected_receipts * Fraction(5, 100)),
        "expected_quality_refunds_micro_usd": rational(expected_receipts * Fraction(5, 100)),
        "expected_unit_direct_contribution_micro_usd": rational(net_unit),
        "expected_operating_profit_micro_usd": rational(expected_profit),
        "full_project_profit_micro_usd": None,
        "full_project_cost_status": "unknown historical actual research/development",
        "human_reference": HUMAN_REFERENCE,
        "customer_savings_per_accepted_order_micro_usd": HUMAN_REFERENCE["total_micro_usd"] - price_usd * USD,
        "customer_savings_basis": "Estimated equal-scope labor difference, not demonstrated willingness to pay",
        "break_even_booked_orders_at_unchanged_price_quality_cost": required_orders,
        "break_even_price_micro_usd_at_unchanged_bookings": rational(
            (direct * len(booked) + fixed_total + Fraction(q, 1_000_000) * len(booked) * 285_000)
            / (Fraction(q, 1_000_000) * len(booked) * Fraction(8715, 10_000))
        )
        if booked and q
        else None,
        "break_even_price_caveat": "This threshold fixes bookings; the price table separately recomputes price-sensitive uptake",
        "break_even_acceptance_fraction": rational(
            Fraction(direct * len(booked) + fixed_total, len(booked))
            / (Fraction(9, 10) * price_usd * USD - Fraction(95, 100) * (price_usd * USD * 3 // 100 + 300_000))
        )
        if booked
        else None,
        "acceptance_alone_can_break_even_at_fixed_bookings": bool(
            booked
            and Fraction(direct * len(booked) + fixed_total, len(booked))
            <= Fraction(9, 10) * price_usd * USD - Fraction(95, 100) * (price_usd * USD * 3 // 100 + 300_000)
        ),
        "actual_customer_collections_micro_usd": 0,
        "actual_complete_cost_micro_usd": None,
        "optional_B_retention_micro_usd": 0,
        "optional_C_investment_micro_usd": 0,
        "retention_decision": "Not purchased; no incremental benefit evidence",
        "arrangement": raw,
        "assessment": assessment,
    }


def model() -> dict[str, Any]:
    """Freeze a conservative reference and expose isolated sensitivities and financing limits."""
    prices = [scenario(price_usd=price) for price in PRICES_USD]
    baseline = prices[1]
    sensitivity = []
    for variable, values in (
        ("opportunities", (0, 4, 12, 24)),
        ("acceptance_percent", (50, 75, 95)),
        ("acquisition_percent", (50, 100, 200)),
        ("workload_percent", (50, 100, 200)),
        ("cost_percent", (75, 100, 150)),
        ("initial_cash_usd", (0, 100, 1000)),
        ("collection_day", (7, 21, 60)),
    ):
        for value in values:
            row = scenario(**{variable: value})
            sensitivity.append(
                {
                    "variable": variable,
                    "value": value,
                    "booked_orders": row["booked_orders"],
                    "expected_operating_profit_micro_usd": row["expected_operating_profit_micro_usd"],
                    "liquidity_feasible": row["assessment"]["liquidity_feasible"],
                    "required_prefunding_micro_usd": row["assessment"]["required_prefunding_micro_usd"],
                }
            )
    assumptions = {
        "prices_usd": list(PRICES_USD),
        "buyer_cap_cycle_usd": list(CAPS_USD),
        "uptake_rule": "price <= min(hypothetical buyer cap, same-scope estimated human outside option); no premium",
        "unit_costs": UNIT_COSTS,
        "fixed_operating_costs": FIXED_COSTS,
        "human_reference": HUMAN_REFERENCE,
        "default_reference": baseline["assumptions"],
        "horizon_days": 90,
        "automated_tier_human_review_hours": 0,
        "research_development": "Actual unknown, excluded from operating profit and never set to zero",
        "correction_obligation": "One bounded correction within seven days, otherwise full refund",
        "assumed_machine_work_per_attempt_hours": "0.5",
        "maximum_opportunities": 32,
        "service_tier": "Automated finite decision pack; no compulsory human review",
        "payment_terms": "Modeled net-14 after day-7 acceptance; no rejected-work charge; no deposit financing",
        "source_preparation": "Estimated automated intake/context cost; task-specific human intervention is unknown in actual research",
    }
    return {
        "schema": "resilient-placement-commercial-model/v1",
        "mode": "conditional-research-model",
        "assumptions": assumptions,
        "freeze_digest": digest("placement-commercial-freeze", assumptions),
        "source_sha256": {
            "economics.py": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "flywheel_arrangements.py": hashlib.sha256(
                Path(assess_arrangement.__code__.co_filename).read_bytes()
            ).hexdigest(),
        },
        "baseline": baseline,
        "price_hypotheses": prices,
        "sensitivities": sensitivity,
        "profitable_but_underfunded_example": scenario(opportunities=24, initial_cash_usd=100),
        "no_launch": {"future_operating_profit_micro_usd": 0, "already_incurred_actual_research_cost": "unknown"},
        "actual": {
            "customer_purchases": 0,
            "collections_micro_usd": 0,
            "complete_cost_micro_usd": None,
            "profit_micro_usd": None,
            "unrestricted_cash_micro_usd": None,
            "deposits_micro_usd": 0,
            "refunds_micro_usd": 0,
            "financing_authority": "unprovisioned",
        },
        "recommendation": "HOLD: no observed buyers, complete actual cost or authority; baseline operating model loses money",
        "operational_alpha": "unmeasured",
        "retained_alpha": "unmeasured; retention not admitted",
    }


def main() -> None:
    """Write a new reproducible conditional projection, without touching any ledger."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    output = parser.parse_args().output
    if output.exists() or output.is_symlink():
        raise FileExistsError("choose a new economics output to preserve previous assumptions")
    data = model()
    with output.open("x", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(
        json.dumps(
            {"output": str(output), "freeze_digest": data["freeze_digest"], "recommendation": data["recommendation"]}
        )
    )


if __name__ == "__main__":
    main()
