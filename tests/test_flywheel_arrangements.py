# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
from fractions import Fraction
from typing import Any

import pytest
from pydantic import ValidationError

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import (
    Arrangement,
    assess_arrangement,
    economy_regression_fixture,
)
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest

USD = 1_000_000


@pytest.fixture
def fixture() -> Arrangement:
    source = EvidenceRef(
        journal_key="@test:paper-model",
        record_digest=digest(
            "test-paper-model", {"source": "docs/Invent_the_Economy.tex", "context": "synthetic fixture"}
        ),
    )
    return economy_regression_fixture(source)


def expected(report: dict[str, Any], field: str) -> Fraction:
    ratio = report[field]
    return Fraction(int(ratio["numerator"]), ratio["denominator"])


def altered(fixture: Arrangement, change: Any) -> Arrangement:
    raw = copy.deepcopy(fixture.model_dump())
    change(raw)
    return Arrangement.model_validate(raw)


def test_paper_common_event_and_complete_cash_schedule(fixture: Arrangement) -> None:
    report = assess_arrangement(fixture, 900_000 * USD)
    failure, success = report["branches"]
    assert failure["cash_contribution_micro_usd"] == -600_000 * USD
    assert failure["terminal_cash_micro_usd"] == 300_000 * USD
    assert failure["projected_collections_micro_usd"] == 0
    assert failure["cash_costs_micro_usd"] == 600_000 * USD
    assert success["cash_contribution_micro_usd"] == 300_000 * USD
    assert success["terminal_cash_micro_usd"] == 1_200_000 * USD
    assert min(row["cash_micro_usd"] for row in success["timeline"]) == 0
    assert report["required_prefunding_micro_usd"] == 900_000 * USD
    assert expected(report, "expected_cash_contribution_micro_usd") == 120_000 * USD
    assert expected(report, "expected_terminal_cash_micro_usd") == 1_020_000 * USD
    assert report["modeled_viable"]
    assert report["authority_granted"] is False and report["actual_collections_micro_usd"] is None
    assert report["evidence_type"] == "projection"
    assert report["arrangement_digest"] == digest("flywheel-arrangement", fixture)
    assert len(fixture.common_risks) == 1
    canonical(report)


def test_profit_does_not_supply_missing_cash(fixture: Arrangement) -> None:
    report = assess_arrangement(fixture, 600_000 * USD)
    assert expected(report, "expected_cash_contribution_micro_usd") > 0
    assert report["liquidity_feasible"] is False
    assert report["branches"][1]["shortfall_micro_usd"] == 300_000 * USD
    assert "insufficient-prefunding" in report["blockers"]
    assert report["decision"] == "hold"


def test_reserve_and_external_obligations_are_not_revenue_or_new_cost(fixture: Arrangement) -> None:
    report = assess_arrangement(fixture, 1_000_000 * USD, 80_000 * USD, 50_000 * USD)
    assert report["required_prefunding_micro_usd"] == 1_030_000 * USD
    assert not report["liquidity_feasible"]
    assert expected(report, "expected_cash_contribution_micro_usd") == 120_000 * USD
    assert expected(report, "expected_terminal_cash_micro_usd") == 1_120_000 * USD


@pytest.mark.parametrize("route,expectation", [(10_000, 88_000), (40_000, -8_000), (37_500, 0)])
def test_route_cost_threshold_is_not_weakened(fixture: Arrangement, route: int, expectation: int) -> None:
    def change(raw: dict[str, Any]) -> None:
        for index in range(4):
            cost = copy.deepcopy(raw["scenarios"][1]["costs"][index + 1])
            cost.update(
                activity_id=f"route-{index}", category="serving", incurred_at=2, paid_at=3, cash_micro_usd=route * USD
            )
            raw["scenarios"][1]["costs"].append(cost)

    report = assess_arrangement(altered(fixture, change), 900_000 * USD)
    assert expected(report, "expected_cash_contribution_micro_usd") == expectation * USD
    assert report["required_prefunding_micro_usd"] == 900_000 * USD
    assert report["modeled_viable"] == (expectation > 0)


def test_coordination_is_charged_once_and_can_remove_margin(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        for branch in raw["scenarios"]:
            cost = copy.deepcopy(branch["costs"][0])
            cost.update(activity_id="coordination", category="coordination", bucket="B", cash_micro_usd=120_000 * USD)
            branch["costs"].append(cost)

    report = assess_arrangement(altered(fixture, change), 1_020_000 * USD)
    assert expected(report, "expected_cash_contribution_micro_usd") == 0
    assert report["required_prefunding_micro_usd"] == 1_020_000 * USD
    assert not report["modeled_viable"]
    assert report["branches"][1]["cost_buckets_micro_usd"] == {
        "A": 300_000 * USD,
        "B": 120_000 * USD,
        "C": 600_000 * USD,
    }


def test_nonparticipation_is_not_an_assumed_sale(fixture: Arrangement) -> None:
    plan = altered(fixture, lambda raw: raw["participants"][0].update(commitment="conditional"))
    report = assess_arrangement(plan, 900_000 * USD)
    assert "uncommitted-participant:hypothetical-buyer-1" in report["blockers"]
    assert report["modeled_viable"] is False
    assert expected(report, "expected_cash_contribution_micro_usd") == 120_000 * USD


def test_missing_value_and_commitment_evidence_stay_unknown(fixture: Arrangement) -> None:
    plan = altered(
        fixture,
        lambda raw: raw["participants"][0].update(value_hypothesis_micro_usd=None, commitment_evidence=[]),
    )
    report = assess_arrangement(plan, 900_000 * USD)
    assert "unknown-participant-value:hypothetical-buyer-1" in report["blockers"]
    assert "unsupported-commitment:hypothetical-buyer-1" in report["blockers"]


def test_unresolved_rights_block_and_live_label_does_not_create_receipts(fixture: Arrangement) -> None:
    plan = altered(fixture, lambda raw: raw.update(rights_cleared=False, mode="live"))
    report = assess_arrangement(plan, 900_000 * USD)
    assert "shared-use-rights-unresolved" in report["blockers"]
    assert report["authority_granted"] is False
    assert report["actual_collections_micro_usd"] is None


def test_default_partial_delivery_and_refund_reduce_collections(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        branch = raw["scenarios"][1]
        branch["receipts"][0]["collected_at"] = None
        branch["receipts"][1]["amount_micro_usd"] = 150_000 * USD
        branch["refunds"] = [
            {
                "refund_id": "quality-refund",
                "projection_id": "conditional-sale-3",
                "amount_micro_usd": 60_000 * USD,
                "at": 4,
                "reason": "Supplied partial acceptance and contractual refund stress",
            }
        ]

    report = assess_arrangement(altered(fixture, change), 900_000 * USD)
    branch = report["branches"][1]
    assert branch["projected_collections_micro_usd"] == 750_000 * USD
    assert branch["defaulted_receivables_micro_usd"] == 300_000 * USD
    assert branch["refunds_micro_usd"] == 60_000 * USD
    assert branch["cash_contribution_micro_usd"] == -210_000 * USD
    assert expected(report, "expected_cash_contribution_micro_usd") == -288_000 * USD


def test_refunds_cannot_reference_uncollected_or_exceed_collection(fixture: Arrangement) -> None:
    for amount, at, projection in (
        (400_000 * USD, 4, "conditional-sale-1"),
        (1, 1, "conditional-sale-1"),
        (1, 4, "missing"),
    ):
        raw = fixture.model_dump()
        raw["scenarios"][1]["refunds"] = [
            {
                "refund_id": "bad-refund",
                "projection_id": projection,
                "amount_micro_usd": amount,
                "at": at,
                "reason": "invalid projection",
            }
        ]
        with pytest.raises(ValidationError):
            Arrangement.model_validate(raw)


def test_same_tick_debits_precede_collections_and_pending_costs_are_visible(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        for cost in raw["scenarios"][1]["costs"][1:]:
            cost.update(incurred_at=1, paid_at=2)

    report = assess_arrangement(altered(fixture, change), 900_000 * USD)
    timeline = report["branches"][1]["timeline"]
    pending = [row for row in timeline if row["at"] == 1][-1]
    assert pending["future_cost_obligations_micro_usd"] == 300_000 * USD
    assert pending["cash_micro_usd"] == 300_000 * USD
    assert pending["available_after_incurred_obligations_micro_usd"] == 0
    assert min(row["cash_micro_usd"] for row in timeline) == 0
    assert report["required_prefunding_micro_usd"] == 900_000 * USD


def test_receivables_cannot_finance_earlier_work(fixture: Arrangement) -> None:
    raw = fixture.model_dump()
    raw["scenarios"][1]["receipts"][0].update(earned_at=3, collected_at=2)
    with pytest.raises(ValidationError, match="working capital"):
        Arrangement.model_validate(raw)


def test_qualification_failure_cannot_acquire_delivery_costs_or_receipts(fixture: Arrangement) -> None:
    for field in ("costs", "receipts"):
        raw = fixture.model_dump()
        raw["scenarios"][0][field].append(raw["scenarios"][1][field][-1])
        with pytest.raises(ValidationError, match="failed qualification"):
            Arrangement.model_validate(raw)


def test_shared_risk_state_and_qualification_cannot_disagree(fixture: Arrangement) -> None:
    raw = fixture.model_dump()
    raw["scenarios"][1]["risk_states"]["shared-qualification"] = "failed"
    with pytest.raises(ValidationError, match="shared technical risk gates"):
        Arrangement.model_validate(raw)


def test_branch_probabilities_cover_joint_model(fixture: Arrangement) -> None:
    for probabilities in ((200_000, 700_000), (True, 999_999), (0.2, 999_999)):
        raw = fixture.model_dump()
        for branch, probability in zip(raw["scenarios"], probabilities):
            branch["probability_ppm"] = probability
        with pytest.raises(ValidationError):
            Arrangement.model_validate(raw)
    raw = fixture.model_dump()
    raw["scenarios"][0]["risk_states"] = {}
    with pytest.raises(ValidationError, match="every common risk"):
        Arrangement.model_validate(raw)


def test_duplicate_cost_and_cross_bucket_activity_refuse(fixture: Arrangement) -> None:
    raw = fixture.model_dump()
    raw["scenarios"][1]["costs"].append(raw["scenarios"][1]["costs"][0])
    with pytest.raises(ValidationError, match="only once"):
        Arrangement.model_validate(raw)
    raw = fixture.model_dump()
    raw["scenarios"][1]["costs"][0]["bucket"] = "A"
    with pytest.raises(ValidationError, match="between A, B and C"):
        Arrangement.model_validate(raw)


def test_withdrawal_blocks_later_earnings_but_not_prior_receivable(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        raw["scenarios"][1]["withdrawals"] = [
            {
                "participant_id": "hypothetical-buyer-1",
                "at": 2,
                "terms": "No new accepted work after withdrawal; prior obligations persist",
            }
        ]

    with pytest.raises(ValidationError, match="withdrawal"):
        altered(fixture, change)
    raw = fixture.model_dump()
    change(raw)
    raw["scenarios"][1]["withdrawals"][0]["at"] = 3
    raw["scenarios"][1]["receipts"][0]["collected_at"] = 4
    assert assess_arrangement(Arrangement.model_validate(raw), 900_000 * USD)["liquidity_feasible"]


def test_matched_opportunity_cost_is_separate_from_cash(fixture: Arrangement) -> None:
    plan = altered(fixture, lambda raw: raw["scenarios"][1]["costs"][0].update(opportunity_micro_usd=25_000 * USD))
    report = assess_arrangement(plan, 900_000 * USD)
    assert expected(report, "expected_cash_contribution_micro_usd") == 120_000 * USD
    assert expected(report, "expected_economic_contribution_micro_usd") == 100_000 * USD
    assert report["required_prefunding_micro_usd"] == 900_000 * USD


def test_zero_probability_required_stress_is_not_used_as_earnings(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        stress = copy.deepcopy(raw["scenarios"][1])
        stress.update(scenario_id="required-extra-cost-stress", probability_ppm=0, required_stress=True)
        stress["costs"][0]["cash_micro_usd"] = 700_000 * USD
        raw["scenarios"].append(stress)

    report = assess_arrangement(altered(fixture, change), 900_000 * USD)
    assert report["required_prefunding_micro_usd"] == 1_000_000 * USD
    assert expected(report, "expected_cash_contribution_micro_usd") == 120_000 * USD
    assert not report["liquidity_feasible"]


@pytest.mark.parametrize("amount", [True, 1.5, "900", -1, 10**16])
def test_financing_inputs_reject_coercion_and_excess(fixture: Arrangement, amount: Any) -> None:
    with pytest.raises(ValueError):
        assess_arrangement(fixture, amount)


def test_assessment_copies_nested_model_and_is_deterministic(fixture: Arrangement) -> None:
    original = canonical(fixture)
    first = assess_arrangement(fixture, 900_000 * USD)
    second = assess_arrangement(fixture, 900_000 * USD)
    assert canonical(first) == canonical(second)
    assert canonical(fixture) == original
    first["branches"][0]["risk_states"]["shared-qualification"] = "qualified"
    assert canonical(fixture) == original
    assert assess_arrangement(fixture, 900_000 * USD) == second


def test_large_fractional_expectations_remain_canonical(fixture: Arrangement) -> None:
    raw = fixture.model_dump()
    raw["scenarios"][0]["probability_ppm"] = 200_001
    raw["scenarios"][1]["probability_ppm"] = 799_999
    raw["scenarios"][1]["costs"][0]["cash_micro_usd"] += 1
    report = assess_arrangement(Arrangement.model_validate(raw), 900_000 * USD + 1)
    assert expected(report, "expected_cash_contribution_micro_usd") == (
        Fraction(200_001, 1_000_000) * (-600_000 * USD) + Fraction(799_999, 1_000_000) * (300_000 * USD - 1)
    )
    canonical(report)


def restrict_buyers(fixture: Arrangement, buyers: int, *, separate_cores: bool = False) -> Arrangement:
    raw = fixture.model_dump()
    raw["participants"] = raw["participants"][:buyers]
    raw["common_risks"][0]["affected_participants"] = [p["participant_id"] for p in raw["participants"]]
    for branch in raw["scenarios"]:
        branch["costs"] = branch["costs"][: buyers + 1]
        branch["receipts"] = branch["receipts"][:buyers]
        if separate_cores:
            branch["costs"][0]["cash_micro_usd"] *= buyers
    return Arrangement.model_validate(raw)


def test_technical_only_coordination_only_and_combination(fixture: Arrangement) -> None:
    technical_only = assess_arrangement(restrict_buyers(fixture, 1), 900_000 * USD)
    coordination_only = assess_arrangement(restrict_buyers(fixture, 4, separate_cores=True), 900_000 * USD)
    combined = assess_arrangement(fixture, 900_000 * USD)
    assert expected(technical_only, "expected_cash_contribution_micro_usd") == -420_000 * USD
    assert expected(coordination_only, "expected_cash_contribution_micro_usd") == -1_680_000 * USD
    assert expected(combined, "expected_cash_contribution_micro_usd") == 120_000 * USD
    assert not technical_only["modeled_viable"] and not coordination_only["modeled_viable"]
    assert combined["modeled_viable"]
    assert coordination_only["required_prefunding_micro_usd"] == 2_700_000 * USD


def test_three_buyers_success_is_profitable_but_expectation_is_negative(fixture: Arrangement) -> None:
    report = assess_arrangement(restrict_buyers(fixture, 3), 900_000 * USD)
    assert report["branches"][1]["cash_contribution_micro_usd"] == 75_000 * USD
    assert expected(report, "expected_cash_contribution_micro_usd") == -60_000 * USD
    assert report["required_prefunding_micro_usd"] == 825_000 * USD
    assert not report["modeled_viable"]


def test_route_cost_exceeding_receipts_increases_prefunding(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        route = copy.deepcopy(raw["scenarios"][1]["costs"][1])
        route.update(
            activity_id="huge-route", category="serving", incurred_at=2, paid_at=3, cash_micro_usd=1_600_000 * USD
        )
        raw["scenarios"][1]["costs"].append(route)

    report = assess_arrangement(altered(fixture, change), 900_000 * USD)
    assert report["required_prefunding_micro_usd"] == 1_300_000 * USD
    assert not report["liquidity_feasible"]


def test_delayed_collection_cannot_pay_intervening_support(fixture: Arrangement) -> None:
    def change(raw: dict[str, Any]) -> None:
        for receipt in raw["scenarios"][1]["receipts"]:
            receipt["collected_at"] = 5
        support = copy.deepcopy(raw["scenarios"][1]["costs"][1])
        support.update(
            activity_id="support-before-payment",
            category="support",
            incurred_at=3,
            paid_at=3,
            cash_micro_usd=100_000 * USD,
        )
        raw["scenarios"][1]["costs"].append(support)

    report = assess_arrangement(altered(fixture, change), 900_000 * USD)
    assert report["required_prefunding_micro_usd"] == 1_000_000 * USD
    assert expected(report, "expected_cash_contribution_micro_usd") == 40_000 * USD
    assert not report["liquidity_feasible"]
