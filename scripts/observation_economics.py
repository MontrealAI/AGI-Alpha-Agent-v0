# SPDX-License-Identifier: Apache-2.0
"""Explicit assumed buyer/cash sensitivities through the existing arrangement engine."""

from __future__ import annotations

from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import (
    Arrangement,
    ArrangementScenario,
    Participant,
    ProjectedCost,
    ProjectedReceipt,
    ProjectedRefund,
    Withdrawal,
    assess_arrangement,
)
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef

USD = 1_000_000


def projection(
    source: EvidenceRef, *, price: int, jobs: int, construction: int, delivery: int, willingness: int, seed: int
) -> dict[str, Any]:
    participant = Participant(
        participant_id="hypothetical-recipient",
        need=source,
        outside_option="Competent conventional exact artifact checker; no observed disadvantage",
        useful_outcome="An assumed accepted artifact-checking service",
        responsibilities=[
            "Supply authorized original acceptance requirements",
            "Pay only under separately agreed terms",
        ],
        price_cap_micro_usd=price * jobs * USD,
        value_hypothesis_micro_usd=willingness * jobs * USD,
        commitment="proposed",
        commitment_conditions=["No actual customer, commitment or contract exists"],
        rights_and_failure_terms="All failure/refund/support terms are scenario hypotheses, not external commitments",
    )
    setup = ProjectedCost(
        activity_id="optional-construction",
        bucket="C",
        category="development",
        cash_micro_usd=construction * USD,
        opportunity_micro_usd=0,
        incurred_at=0,
        paid_at=0,
        basis="Explicit sensitivity assumption; complete actual R&D allocation unknown",
    )
    assessment = ProjectedCost(
        activity_id="incremental-assessment",
        bucket="B",
        category="assessment",
        cash_micro_usd=10 * USD,
        opportunity_micro_usd=0,
        incurred_at=0,
        paid_at=0,
        basis="Hypothetical additional assessment, charged once",
    )
    ordinary = ProjectedCost(
        activity_id="complete-delivery",
        bucket="A",
        category="delivery",
        cash_micro_usd=(delivery + 5) * jobs * USD,
        opportunity_micro_usd=0,
        incurred_at=1,
        paid_at=1,
        qualification_required=True,
        basis="Assumed complete job delivery plus USD5 support per job; no observed human review minutes",
    )
    receipt = ProjectedReceipt(
        projection_id="service",
        participant_id=participant.participant_id,
        amount_micro_usd=price * jobs * USD,
        earned_at=2,
        collected_at=3,
        acceptance_hypothesis="Hypothetical useful accepted service, not the local test receipt",
    )
    scenarios = [
        ArrangementScenario(
            scenario_id="accepted",
            probability_ppm=700_000,
            qualified=True,
            risk_states={},
            costs=[setup, assessment, ordinary],
            receipts=[receipt],
            failure_handling="Hypothetical acceptance and collection; no actual event",
        ),
        ArrangementScenario(
            scenario_id="payment-default",
            probability_ppm=100_000,
            qualified=True,
            risk_states={},
            costs=[setup, assessment, ordinary],
            receipts=[receipt.model_copy(update={"collected_at": None})],
            failure_handling="Full work cost remains; receivable is not cash or collected revenue",
        ),
        ArrangementScenario(
            scenario_id="common-technical-failure",
            probability_ppm=100_000,
            qualified=False,
            risk_states={},
            costs=[setup, assessment],
            failure_handling="Construction and assessment sunk; no delivery or earnings",
        ),
        ArrangementScenario(
            scenario_id="withdrawal",
            probability_ppm=50_000,
            qualified=True,
            risk_states={},
            costs=[setup, assessment],
            withdrawals=[
                Withdrawal(
                    participant_id=participant.participant_id,
                    at=1,
                    terms="No delivery or earnings after modeled withdrawal",
                )
            ],
            failure_handling="Preserve sunk construction costs",
        ),
        ArrangementScenario(
            scenario_id="refund",
            probability_ppm=50_000,
            qualified=True,
            risk_states={},
            costs=[setup, assessment, ordinary],
            receipts=[receipt],
            refunds=[
                ProjectedRefund(
                    refund_id="refund",
                    projection_id="service",
                    amount_micro_usd=price * jobs * USD,
                    at=4,
                    reason="Modeled full refund; delivery cost retained",
                )
            ],
            failure_handling="Full collection is reversed once; support remains in A",
        ),
    ]
    if price > willingness:
        scenarios = [
            ArrangementScenario(
                scenario_id="nonparticipation",
                probability_ppm=1_000_000,
                qualified=True,
                risk_states={},
                costs=[assessment],
                withdrawals=[
                    Withdrawal(
                        participant_id=participant.participant_id,
                        at=0,
                        terms="Price above explicit WTP assumption; no purchase or construction",
                    )
                ],
                failure_handling="No fabricated demand; only prior assessment is incurred",
            )
        ]
    arrangement = Arrangement(
        arrangement_id="observation-service-sensitivity",
        version=1,
        offering=source,
        dependency_evidence=[source],
        participants=[participant],
        scenarios=scenarios,
        state_space_basis="Supplied exhaustive branches with assumed probabilities; not an empirically "
        "fitted customer model",
        financing_basis="Seed capital is a liquidity assumption, not revenue; delivery precedes collection",
        rights_cleared=True,
        rights_basis="Authored hypothetical service; real customer rights would need verification",
        mode="simulation",
        authority_required="Every live obligation or action needs separate approval",
        limitations=[
            "Prices, demand, costs, willingness and probabilities are assumptions",
            "Conventional baseline ties the actual instrument; no new paid market demonstrated",
        ],
    )
    report = assess_arrangement(arrangement, seed * USD, reserve_micro_usd=50 * USD)
    return {
        "assumptions": {
            "price_usd": price,
            "jobs": jobs,
            "construction_usd": construction,
            "delivery_usd": delivery,
            "support_per_job_usd": 5,
            "additional_assessment_usd": 10,
            "willingness_per_job_usd": willingness,
            "seed_usd": seed,
        },
        "assessment": report,
    }


def sensitivity(source: EvidenceRef) -> dict[str, Any]:
    rows = []
    for price in (100, 500):
        for jobs in (1, 4, 12):
            for construction in (100, 1000):
                for willingness in (50, 1000):
                    for seed in (0, 5000):
                        item = projection(
                            source,
                            price=price,
                            jobs=jobs,
                            construction=construction,
                            delivery=50,
                            willingness=willingness,
                            seed=seed,
                        )
                        report = item["assessment"]
                        rows.append(
                            {
                                "assumptions": item["assumptions"],
                                "expected_economic_contribution_micro_usd": report[
                                    "expected_economic_contribution_micro_usd"
                                ],
                                "required_prefunding_micro_usd": report["required_prefunding_micro_usd"],
                                "liquidity_feasible": report["liquidity_feasible"],
                                "blockers": report["blockers"],
                                "decision": report["decision"],
                            }
                        )
    return {
        "evidence_type": "assumption-sensitivity",
        "calibrated": False,
        "source": source.model_dump(),
        "rows": rows,
        "illustration": projection(
            source, price=500, jobs=4, construction=100, delivery=50, willingness=1000, seed=5000
        ),
        "conclusion": "Positive hypothetical contribution can coexist with inadequate prefunding or "
        "absent buyer commitments. Conventional parity supplies no incremental Alpha.",
        "actual_collections_micro_usd": 0,
        "authority_granted": False,
    }
