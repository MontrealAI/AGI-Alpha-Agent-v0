# SPDX-License-Identifier: Apache-2.0
"""Same-offer conditional economics through the existing Arrangement assessor."""

from __future__ import annotations

from fractions import Fraction
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import Arrangement, assess_arrangement
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Offering
from alpha_factory_v1.core.runtime.successor.protocol import digest

USD = 1_000_000


def offering() -> Offering:
    """A proposed decision pack, not a manufacturing or certification promise."""
    return Offering.model_validate(
        {
            "offering_id": "paired-production-decision-pack",
            "version": 1,
            "beneficiary": "A consenting pair of utilities and their selected manufacturer; no actual buyer identified",
            "useful_outcome": "Decide whether a proposed common family deserves engineering qualification, and which original requirements prevent it",
            "deliverable": "Eight source-bound requirement cards, a conditional production witness or no-plan/incomplete result, resource ledger, ablations and independent engineering discrepancy list",
            "scope": "At most two owners, one supplier, eight nominal input cards and twelve declared recipes; local computation only",
            "acceptance_criteria": [
                "Every original source relationship is traced and checked by the buyer's independent engineers",
                "Declared resource use, obligations and budgets independently replay",
                "Unresolved engineering requirements, permissions, quotes and assumptions remain visible",
                "A correct no-plan/incomplete outcome is useful only under separately agreed buyer acceptance",
            ],
            "need_evidence": [
                {"journal_key": "@production-frontier:unregistered-public-need", "record_digest": "0" * 64}
            ],
            "demand_uncertainty": "No consenting buyer, approved requirements, current quotation or willingness-to-pay evidence exists",
            "human_reference": {
                "service": "Equivalent bounded two-owner engineering decision pack, not a physical transformer or impossible human task",
                "source": "Transparent estimate only: forty team hours at USD150 loaded/hour; no market quotation",
                "basis": "estimated-team-hours",
                "team_hours": 40,
                "hourly_rate_micro_usd": 150 * USD,
                "total_micro_usd": 6_000 * USD,
            },
            "required_capabilities": [],
            "permitted_tools": ["production-frontier-local"],
            "price_policy": "Test USD4000/8000/12000 against fixed authored participation cohorts and complete costs; no compute-cost pricing",
            "price_candidates_micro_usd": [4_000 * USD, 8_000 * USD, 12_000 * USD],
            "capacity": 6,
            "turnaround_seconds": 43_200,
            "complete_cost_cap_micro_usd": 50_000 * USD,
            "risks": [
                "Input translation may omit an indispensable relationship",
                "Independent engineering or supplier acceptance may fail",
                "Buyer may decline; receivable may default; correlated failure may affect every buyer",
            ],
            "operating_limits": [
                "Proposed twelve working-hour scope begins only after complete eligible inputs; not a calendar or physical delivery promise",
                "One correction cycle for a reproducible compiler/source-mapping discrepancy; refund agreed unusable delivery fee",
                "No energization, manufacture, qualification certificate, customer contact, credential or transaction authority",
                "Custody references are unsaved proposals and cannot pass native current-evidence checks",
            ],
            "mode": "simulation",
        }
    )


def arrangement(price_usd: int, expand: bool, inputs: dict[str, Any]) -> Arrangement:
    """Include failed work and shared risk, with development counted once."""
    offer = offering()
    eligible = [v for v in inputs["authored_buyer_values_usd"] if v >= price_usd]
    n = min(6 if expand else 1, len(eligible))
    ref = {
        "journal_key": "@production-frontier:unregistered-offer",
        "record_digest": digest("enterprise-offering", offer),
    }
    participants = [
        {
            "participant_id": f"hypothetical-{i}",
            "need": ref,
            "outside_option": "A competent engineer/broker using the same source data, solver and supplier access",
            "useful_outcome": offer.useful_outcome,
            "responsibilities": ["Supply eligible inputs and independent engineering acceptance"],
            "price_cap_micro_usd": value * USD,
            "value_hypothesis_micro_usd": value * USD,
            "commitment": "proposed",
            "commitment_conditions": ["No observed buyer; value and participation are authored"],
            "commitment_evidence": [],
            "rights_and_failure_terms": "Pay on agreed acceptance only; one correction and unusable-delivery refund",
        }
        for i, value in enumerate(eligible[:n])
    ]
    if not participants:
        raise ValueError("price has no eligible authored participant; choose stop")
    scenarios = []
    for state in inputs["joint_states"]:
        identity, probability = state["state"], state["probability_ppm"]
        costs, receipts, refunds = [], [], []

        def cost(name: str, category: str, usd: int, tick: int, *, qualification: bool = False) -> None:
            if usd:
                costs.append(
                    {
                        "activity_id": name,
                        "bucket": "A",
                        "category": category,
                        "cash_micro_usd": usd * USD,
                        "opportunity_micro_usd": 0,
                        "incurred_at": tick,
                        "paid_at": tick,
                        "qualification_required": qualification,
                        "basis": "Authored complete loaded-cost estimate; actual hours, provider charges and invoices unknown",
                    }
                )

        cost("development-once", "development", inputs["development_usd"], 0)
        cost("independent-validation-once", "assessment", inputs["validation_usd"], 1)
        cost(
            "acquisition-all-prospects",
            "coordination",
            len(inputs["authored_buyer_values_usd"]) * inputs["acquisition_per_prospect_usd"],
            1,
        )
        cost("infrastructure", "serving", inputs["infrastructure_usd"], 1)
        if expand:
            cost("multi-buyer-coordination", "coordination", inputs["expansion_coordination_usd"], 1)
        qualified = identity != "technical-failure"
        if identity == "technical-failure":
            cost("failed-attempt", "delivery", inputs["failed_attempt_usd"], 2)
        if identity in {"all-accept-pay", "correlated-correction-default"}:
            for i in range(n):
                cost(f"delivery-{i}", "delivery", inputs["delivery_per_attempt_usd"], 2, qualification=True)
                cost(f"verification-{i}", "assessment", inputs["verification_per_attempt_usd"], 3, qualification=True)
                cost(f"support-{i}", "support", inputs["support_per_attempt_usd"], 4, qualification=True)
                if identity == "correlated-correction-default":
                    cost(f"correction-{i}", "support", inputs["correction_per_attempt_usd"], 5, qualification=True)
                collected = None if identity == "correlated-correction-default" and i % 2 == 0 else 10
                receipts.append(
                    {
                        "projection_id": f"accepted-{i}",
                        "participant_id": f"hypothetical-{i}",
                        "amount_micro_usd": price_usd * USD,
                        "earned_at": 6,
                        "collected_at": collected,
                        "qualification_required": True,
                        "acceptance_hypothesis": "Conditional authored acceptance; no real accepted delivery",
                    }
                )
                if identity == "correlated-correction-default" and collected is not None:
                    refunds.append(
                        {
                            "refund_id": f"refund-{i}",
                            "projection_id": f"accepted-{i}",
                            "amount_micro_usd": price_usd * USD,
                            "at": 11,
                            "reason": "One correction failed to make this hypothetical delivery usable",
                        }
                    )
        scenarios.append(
            {
                "scenario_id": identity,
                "probability_ppm": probability,
                "qualified": qualified,
                "required_stress": True,
                "risk_states": {"shared-project": identity},
                "costs": costs,
                "receipts": receipts,
                "refunds": refunds,
                "withdrawals": [],
                "failure_handling": "Shared state affects all buyers; no independence/diversification fiction; uncollected earnings do not finance work",
            }
        )
    states = [s["state"] for s in inputs["joint_states"]]
    return Arrangement.model_validate(
        {
            "arrangement_id": f"paired-pack-{price_usd}-{'selective-expansion' if expand else 'first-only'}",
            "version": 1,
            "offering": ref,
            "participants": participants,
            "common_risks": [
                {
                    "risk_id": "shared-project",
                    "description": "Authored joint technical, participation and payment states",
                    "affected_participants": [p["participant_id"] for p in participants],
                    "states": states,
                    "qualification_success_states": [s for s in states if s != "technical-failure"],
                }
            ],
            "scenarios": scenarios,
            "state_space_basis": "Four mutually exclusive authored worlds; probabilities are sensitivity assumptions, not measured demand",
            "financing_basis": "Modeled unrestricted initial capital and reserve only; actual available funds and financing are unknown",
            "rights_cleared": False,
            "rights_basis": "No consenting owners, supplier access or engineering mandate",
            "mode": "simulation",
            "authority_required": "Existing current signed mission, custody, identity, budgets and commercial approvals remain required",
            "limitations": [
                "All costs, values, demand, probabilities and capital are hypothetical",
                "Prior real research costs are unknown and common to all future decisions; no complete actual profit is computed",
                "All loaded human work is included in modeled cash costs, not counted again as opportunity cost",
                "No additional retention/Gym investment: ordinary-library parity supplies zero demonstrated incremental reusable benefit",
            ],
        }
    )


def evaluate(inputs: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    audit_checks = 0
    for price in inputs["prices_usd"]:
        for expand in (False, True):
            model = arrangement(price, expand, inputs)
            report = assess_arrangement(
                model, inputs["modeled_initial_cash_usd"] * USD, inputs["modeled_reserve_usd"] * USD
            )
            # Independent exact-arithmetic sums do not reuse the assessor's totals.
            expected = Fraction()
            for scenario, branch in zip(model.scenarios, report["branches"]):
                collected = sum(r.amount_micro_usd for r in scenario.receipts if r.collected_at is not None)
                expense = sum(c.cash_micro_usd + c.opportunity_micro_usd for c in scenario.costs)
                refunded = sum(r.amount_micro_usd for r in scenario.refunds)
                if branch["economic_contribution_micro_usd"] != collected - expense - refunded:
                    raise ValueError("independent branch arithmetic differs")
                expected += Fraction(scenario.probability_ppm, 1_000_000) * (collected - expense - refunded)
                if sum(c.activity_id == "development-once" for c in scenario.costs) != 1:
                    raise ValueError("development must be counted exactly once")
                audit_checks += 2
            rational = report["expected_economic_contribution_micro_usd"]
            if expected != Fraction(int(rational["numerator"]), rational["denominator"]):
                raise ValueError("independent expected-value arithmetic differs")
            audit_checks += 1
            results.append(
                {
                    "model": model.model_dump(),
                    "assessment": report,
                    "restricted_deposits_micro_usd": 0,
                    "provider_expected_profit_is_hypothetical": True,
                    "customer_net_benefit_is_observed": False,
                    "conditional_future_opportunity_value_micro_usd": None,
                }
            )
    ranked = sorted(
        results,
        key=lambda r: Fraction(
            int(r["assessment"]["expected_economic_contribution_micro_usd"]["numerator"]),
            r["assessment"]["expected_economic_contribution_micro_usd"]["denominator"],
        ),
        reverse=True,
    )
    eligible = [row["assessment"] for row in ranked if row["assessment"]["liquidity_feasible"]]
    best = eligible[0] if eligible else None
    positive = best is not None and int(best["expected_economic_contribution_micro_usd"]["numerator"]) > 0
    return {
        "schema": "production-frontier-commercial-decision/v1",
        "offering": offering().model_dump(),
        "policies": results,
        "independent_arithmetic_checks": audit_checks,
        "stop": {
            "future_investment_micro_usd": 0,
            "incremental_modeled_profit_micro_usd": 0,
            "already_incurred_actual_research_cost_micro_usd": None,
        },
        "best_conditional_action": best["arrangement_id"] if best is not None and positive else "stop",
        "commercial_decision": "HOLD-no-authorized-buyer-or-admitted-opportunity",
        "actual_customer_collections_micro_usd": 0,
        "actual_earned_amount_micro_usd": 0,
        "actual_provider_profit_micro_usd": None,
        "actual_complete_cost_micro_usd": None,
        "actual_unrestricted_cash_micro_usd": None,
        "actual_customer_net_benefit_micro_usd": None,
        "next_investment_authorized": False,
    }
