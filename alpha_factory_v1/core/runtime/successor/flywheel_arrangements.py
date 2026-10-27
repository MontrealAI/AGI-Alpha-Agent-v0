# SPDX-License-Identifier: Apache-2.0
"""Bounded commercial projections; no payment, accounting, or execution authority."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Literal

from pydantic import Field, model_validator

from .flywheel_enterprise import EvidenceRef
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest
from .transformation_library import _is_exact_type

MONEY_LIMIT = 10**15
TICK_LIMIT = 31_536_000
PROBABILITY_SCALE = 1_000_000


class Participant(StrictModel):
    participant_id: Identifier
    need: EvidenceRef
    outside_option: Text
    useful_outcome: Text
    responsibilities: list[Text] = Field(min_length=1, max_length=16)
    price_cap_micro_usd: int = Field(ge=0, le=MONEY_LIMIT)
    value_hypothesis_micro_usd: int | None = Field(default=None, ge=0, le=MONEY_LIMIT)
    commitment: Literal["proposed", "conditional", "committed", "withdrawn"]
    commitment_conditions: list[Text] = Field(min_length=1, max_length=16)
    commitment_evidence: list[EvidenceRef] = Field(default_factory=list, max_length=16)
    rights_and_failure_terms: Text


class CommonRisk(StrictModel):
    risk_id: Identifier
    description: Text
    affected_participants: list[Identifier] = Field(min_length=1, max_length=32)
    states: list[Identifier] = Field(min_length=2, max_length=16)
    qualification_success_states: list[Identifier] = Field(default_factory=list, max_length=16)

    @model_validator(mode="after")
    def unique(self) -> CommonRisk:
        if len(set(self.states)) != len(self.states) or len(set(self.affected_participants)) != len(
            self.affected_participants
        ):
            raise ValueError("common risk states and affected participants must be unique")
        if len(set(self.qualification_success_states)) != len(self.qualification_success_states) or not set(
            self.qualification_success_states
        ) <= set(self.states):
            raise ValueError("qualification success states must be distinct declared risk states")
        return self


class ProjectedCost(StrictModel):
    activity_id: Identifier
    bucket: Literal["A", "B", "C"]
    category: Literal["development", "delivery", "coordination", "assessment", "serving", "support", "maintenance"]
    cash_micro_usd: int = Field(ge=0, le=MONEY_LIMIT)
    opportunity_micro_usd: int = Field(ge=0, le=MONEY_LIMIT)
    incurred_at: int = Field(ge=0, le=TICK_LIMIT)
    paid_at: int = Field(ge=0, le=TICK_LIMIT)
    qualification_required: bool = False
    basis: Text

    @model_validator(mode="after")
    def timing(self) -> ProjectedCost:
        if self.paid_at < self.incurred_at:
            raise ValueError("cost cannot be paid before its stated incurrence; model a real advance separately")
        if self.cash_micro_usd == self.opportunity_micro_usd == 0:
            raise ValueError("projected cost must identify a nonzero cost")
        return self


class ProjectedReceipt(StrictModel):
    projection_id: Identifier
    participant_id: Identifier
    amount_micro_usd: int = Field(gt=0, le=MONEY_LIMIT)
    earned_at: int = Field(ge=0, le=TICK_LIMIT)
    collected_at: int | None = Field(default=None, ge=0, le=TICK_LIMIT)
    qualification_required: bool = True
    acceptance_hypothesis: Text

    @model_validator(mode="after")
    def timing(self) -> ProjectedReceipt:
        if self.collected_at is not None and self.collected_at < self.earned_at:
            raise ValueError("conditional receivable is not advance working capital")
        return self


class ProjectedRefund(StrictModel):
    refund_id: Identifier
    projection_id: Identifier
    amount_micro_usd: int = Field(gt=0, le=MONEY_LIMIT)
    at: int = Field(ge=0, le=TICK_LIMIT)
    reason: Text


class Withdrawal(StrictModel):
    participant_id: Identifier
    at: int = Field(ge=0, le=TICK_LIMIT)
    terms: Text


class ArrangementScenario(StrictModel):
    scenario_id: Identifier
    probability_ppm: int = Field(ge=0, le=PROBABILITY_SCALE)
    qualified: bool
    required_stress: bool = False
    risk_states: dict[str, str]
    costs: list[ProjectedCost] = Field(default_factory=list, max_length=128)
    receipts: list[ProjectedReceipt] = Field(default_factory=list, max_length=128)
    refunds: list[ProjectedRefund] = Field(default_factory=list, max_length=128)
    withdrawals: list[Withdrawal] = Field(default_factory=list, max_length=32)
    failure_handling: Text

    @model_validator(mode="after")
    def identities(self) -> ArrangementScenario:
        for records, attr in (
            (self.costs, "activity_id"),
            (self.receipts, "projection_id"),
            (self.refunds, "refund_id"),
            (self.withdrawals, "participant_id"),
        ):
            identities = [getattr(item, attr) for item in records]
            if len(set(identities)) != len(identities):
                raise ValueError("each activity or projected event may occur only once in a branch")
        if not self.qualified and (
            any(cost.qualification_required for cost in self.costs)
            or any(receipt.qualification_required for receipt in self.receipts)
        ):
            raise ValueError("failed qualification cannot incur conditional delivery or receipts")
        if sum(cost.cash_micro_usd + cost.opportunity_micro_usd for cost in self.costs) > MONEY_LIMIT:
            raise ValueError("branch costs exceed bounded whole-arrangement budget")
        if sum(receipt.amount_micro_usd for receipt in self.receipts) > MONEY_LIMIT:
            raise ValueError("branch receipts exceed bounded whole-arrangement budget")
        return self


class Arrangement(StrictModel):
    schema_name: Literal["flywheel-arrangement/v1"] = "flywheel-arrangement/v1"
    arrangement_id: Identifier
    version: int = Field(ge=1, le=1_000_000)
    offering: EvidenceRef
    capability_digests: list[Digest] = Field(default_factory=list, max_length=32)
    dependency_evidence: list[EvidenceRef] = Field(default_factory=list, max_length=32)
    participants: list[Participant] = Field(min_length=1, max_length=32)
    common_risks: list[CommonRisk] = Field(default_factory=list, max_length=16)
    scenarios: list[ArrangementScenario] = Field(min_length=1, max_length=64)
    state_space_basis: Text
    financing_basis: Text
    rights_cleared: bool
    rights_basis: Text
    mode: Literal["simulation", "hybrid", "live"]
    evidence_type: Literal["projection"] = "projection"
    authority_required: Text
    limitations: list[Text] = Field(min_length=1, max_length=32)

    @model_validator(mode="after")
    def coherent(self) -> Arrangement:
        participants = {p.participant_id: p for p in self.participants}
        risks = {r.risk_id: r for r in self.common_risks}
        if len(participants) != len(self.participants) or len(risks) != len(self.common_risks):
            raise ValueError("participant and common-risk identities must be unique")
        if len(set(self.capability_digests)) != len(self.capability_digests):
            raise ValueError("capability dependencies must be unique")
        if len({s.scenario_id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("scenario identities must be unique")
        if sum(s.probability_ppm for s in self.scenarios) != PROBABILITY_SCALE:
            raise ValueError("mutually exclusive exhaustive branch probabilities must sum to one million")
        for risk in risks.values():
            if not set(risk.affected_participants) <= participants.keys():
                raise ValueError("common risk names unknown participant")
        activity_buckets: dict[str, str] = {}
        for scenario in self.scenarios:
            if set(scenario.risk_states) != risks.keys() or any(
                value not in risks[key].states for key, value in scenario.risk_states.items()
            ):
                raise ValueError("every branch must bind every common risk to one declared joint state")
            gates = [
                scenario.risk_states[risk.risk_id] in risk.qualification_success_states
                for risk in self.common_risks
                if risk.qualification_success_states
            ]
            if gates and scenario.qualified != all(gates):
                raise ValueError("qualification must obey the declared shared technical risk gates")
            receipts = {r.projection_id: r for r in scenario.receipts}
            withdrawals = {w.participant_id: w.at for w in scenario.withdrawals}
            if not withdrawals.keys() <= participants.keys():
                raise ValueError("withdrawal names unknown participant")
            for cost in scenario.costs:
                previous = activity_buckets.setdefault(cost.activity_id, cost.bucket)
                if previous != cost.bucket:
                    raise ValueError("an activity cannot move between A, B and C across branches")
            projected_prices: dict[str, int] = {}
            for receipt in scenario.receipts:
                if receipt.participant_id not in participants:
                    raise ValueError("projected receipt names unknown participant")
                projected_prices[receipt.participant_id] = (
                    projected_prices.get(receipt.participant_id, 0) + receipt.amount_micro_usd
                )
                if receipt.participant_id in withdrawals and receipt.earned_at >= withdrawals[receipt.participant_id]:
                    raise ValueError("withdrawal forbids subsequently assumed acceptance and earnings")
            for identity, amount in projected_prices.items():
                if amount > participants[identity].price_cap_micro_usd:
                    raise ValueError("projected price exceeds participant commitment cap")
            refunded: dict[str, int] = {}
            for refund in scenario.refunds:
                refund_receipt = receipts.get(refund.projection_id)
                if (
                    refund_receipt is None
                    or refund_receipt.collected_at is None
                    or refund.at < refund_receipt.collected_at
                ):
                    raise ValueError("refund requires an earlier modeled collection")
                refunded[refund.projection_id] = refunded.get(refund.projection_id, 0) + refund.amount_micro_usd
                if refunded[refund.projection_id] > refund_receipt.amount_micro_usd:
                    raise ValueError("refunds cannot exceed the referenced collection")
        if len(canonical(self)) > 500_000:
            raise ValueError("arrangement exceeds bounded assessment size")
        return self


def _rational(value: Fraction) -> dict[str, str | int]:
    return {"numerator": str(value.numerator), "denominator": value.denominator}


def assess_arrangement(
    arrangement: Arrangement,
    initial_cash_micro_usd: int,
    reserve_micro_usd: int = 0,
    existing_obligations_micro_usd: int = 0,
) -> dict[str, Any]:
    """Project each declared joint branch without mutating any ledger or authority."""
    arrangement = Arrangement.model_validate_json(canonical(arrangement))
    for amount in (initial_cash_micro_usd, reserve_micro_usd, existing_obligations_micro_usd):
        if not _is_exact_type(amount, int) or not 0 <= amount <= MONEY_LIMIT:
            raise ValueError("cash, reserve and obligations require bounded exact nonnegative integers")
    branches: list[dict[str, Any]] = []
    expected_cash = Fraction()
    expected_economic = Fraction()
    expected_terminal = Fraction()
    maximum_prefunding = reserve_micro_usd + existing_obligations_micro_usd
    participants = {p.participant_id: p for p in arrangement.participants}
    for scenario in arrangement.scenarios:
        events: list[tuple[int, int, str, str, int]] = []
        for cost in scenario.costs:
            events.append((cost.incurred_at, 0, cost.activity_id, "incur", cost.cash_micro_usd))
            events.append((cost.paid_at, 1, cost.activity_id, "cost", cost.cash_micro_usd))
        for receipt in scenario.receipts:
            if receipt.collected_at is not None:
                events.append((receipt.collected_at, 3, receipt.projection_id, "collection", receipt.amount_micro_usd))
        for refund in scenario.refunds:
            events.append((refund.at, 2, refund.refund_id, "refund", refund.amount_micro_usd))
        delta = 0
        minimum = 0
        outstanding = 0
        timeline = []
        for tick, _, identity, kind, amount in sorted(events):
            if kind == "incur":
                outstanding += amount
            elif kind == "cost":
                delta -= amount
                outstanding -= amount
            elif kind == "refund":
                delta -= amount
            else:
                delta += amount
            minimum = min(minimum, delta)
            balance = initial_cash_micro_usd + delta
            timeline.append(
                {
                    "at": tick,
                    "event": identity,
                    "kind": kind,
                    "amount_micro_usd": amount,
                    "cash_micro_usd": balance,
                    "future_cost_obligations_micro_usd": outstanding,
                    "unreserved_cash_micro_usd": balance - reserve_micro_usd - existing_obligations_micro_usd,
                    "available_after_incurred_obligations_micro_usd": (
                        balance - reserve_micro_usd - existing_obligations_micro_usd - outstanding
                    ),
                }
            )
        cash_costs = sum(cost.cash_micro_usd for cost in scenario.costs)
        opportunity = sum(cost.opportunity_micro_usd for cost in scenario.costs)
        collections = sum(receipt.amount_micro_usd for receipt in scenario.receipts if receipt.collected_at is not None)
        receivables = sum(receipt.amount_micro_usd for receipt in scenario.receipts if receipt.collected_at is None)
        refunds = sum(refund.amount_micro_usd for refund in scenario.refunds)
        contribution = collections - cash_costs - refunds
        prefunding = -minimum + reserve_micro_usd + existing_obligations_micro_usd
        branch_blockers = []
        if scenario.probability_ppm or scenario.required_stress:
            prices: dict[str, int] = {}
            for receipt in scenario.receipts:
                participant = participants[receipt.participant_id]
                if participant.commitment != "committed":
                    branch_blockers.append("uncommitted-participant:" + participant.participant_id)
                if not participant.commitment_evidence:
                    branch_blockers.append("unsupported-commitment:" + participant.participant_id)
                if participant.value_hypothesis_micro_usd is None:
                    branch_blockers.append("unknown-participant-value:" + participant.participant_id)
                prices[participant.participant_id] = (
                    prices.get(participant.participant_id, 0) + receipt.amount_micro_usd
                )
            for identity, price in prices.items():
                value = participants[identity].value_hypothesis_micro_usd
                if value is not None and value < price:
                    branch_blockers.append("participant-value-below-price:" + identity)
        branch_blockers = sorted(set(branch_blockers))
        if scenario.probability_ppm or scenario.required_stress:
            maximum_prefunding = max(maximum_prefunding, prefunding)
        weight = Fraction(scenario.probability_ppm, PROBABILITY_SCALE)
        expected_cash += weight * contribution
        expected_economic += weight * (contribution - opportunity)
        expected_terminal += weight * (initial_cash_micro_usd + delta)
        branches.append(
            {
                "scenario_id": scenario.scenario_id,
                "probability_ppm": scenario.probability_ppm,
                "qualified": scenario.qualified,
                "required_stress": scenario.required_stress,
                "risk_states": scenario.risk_states,
                "timeline": timeline,
                "projected_collections_micro_usd": collections,
                "defaulted_receivables_micro_usd": receivables,
                "refunds_micro_usd": refunds,
                "cash_costs_micro_usd": cash_costs,
                "opportunity_cost_micro_usd": opportunity,
                "cash_contribution_micro_usd": contribution,
                "economic_contribution_micro_usd": contribution - opportunity,
                "terminal_cash_micro_usd": initial_cash_micro_usd + delta,
                "required_prefunding_micro_usd": prefunding,
                "shortfall_micro_usd": max(0, prefunding - initial_cash_micro_usd),
                "participation_blockers": branch_blockers,
                "cost_buckets_micro_usd": {
                    bucket: sum(c.cash_micro_usd for c in scenario.costs if c.bucket == bucket)
                    for bucket in ("A", "B", "C")
                },
            }
        )
    blockers = sorted({reason for branch in branches for reason in branch["participation_blockers"]})
    if not arrangement.rights_cleared:
        blockers.append("shared-use-rights-unresolved")
    if initial_cash_micro_usd < maximum_prefunding:
        blockers.append("insufficient-prefunding")
    if expected_economic <= 0:
        blockers.append("nonpositive-expected-economic-contribution")
    return {
        "schema": "flywheel-arrangement-assessment/v1",
        "arrangement_id": arrangement.arrangement_id,
        "arrangement_digest": digest("flywheel-arrangement", arrangement),
        "offering": arrangement.offering.model_dump(),
        "mode": arrangement.mode,
        "evidence_type": "projection",
        "authority_granted": False,
        "actual_collections_micro_usd": None,
        "initial_cash_micro_usd": initial_cash_micro_usd,
        "reserve_micro_usd": reserve_micro_usd,
        "existing_obligations_micro_usd": existing_obligations_micro_usd,
        "required_prefunding_micro_usd": maximum_prefunding,
        "liquidity_feasible": initial_cash_micro_usd >= maximum_prefunding,
        "expected_cash_contribution_micro_usd": _rational(expected_cash),
        "expected_economic_contribution_micro_usd": _rational(expected_economic),
        "expected_terminal_cash_micro_usd": _rational(expected_terminal),
        "branches": branches,
        "blockers": blockers,
        "modeled_viable": not blockers,
        "decision": "eligible-for-separate-assessment" if not blockers else "hold",
    }


def economy_regression_fixture(source: EvidenceRef) -> Arrangement:
    """Reconstruct only the hypothetical four-buyer paper's stated cash schedule."""
    unit = 1_000_000
    participants = [
        Participant(
            participant_id=f"hypothetical-buyer-{index}",
            need=source,
            outside_option="No shared-core project; all buyer values are supplied assumptions",
            useful_outcome="Accepted hypothetical adapter using the shared technical core",
            responsibilities=["Pay only after successful qualification and accepted delivery"],
            price_cap_micro_usd=300_000 * unit,
            value_hypothesis_micro_usd=360_000 * unit,
            commitment="committed",
            commitment_conditions=["Modeled conditional commitment; no actual buyer or contract"],
            commitment_evidence=[source],
            rights_and_failure_terms="Paper assumes permitted shared use, successful adapters and payment after acceptance",
        )
        for index in range(1, 5)
    ]
    construction = ProjectedCost(
        activity_id="fixed-construction",
        bucket="C",
        category="development",
        cash_micro_usd=600_000 * unit,
        opportunity_micro_usd=0,
        incurred_at=0,
        paid_at=0,
        basis="Supplied K=600 thousands; all fixed construction is paid before qualification",
    )
    deliveries = [
        ProjectedCost(
            activity_id=f"delivery-{index}",
            bucket="A",
            category="delivery",
            cash_micro_usd=75_000 * unit,
            opportunity_micro_usd=0,
            incurred_at=1,
            paid_at=1,
            qualification_required=True,
            basis="Supplied per-buyer delivery cost d=75 thousands, paid before customer payment",
        )
        for index in range(1, 5)
    ]
    receipts = [
        ProjectedReceipt(
            projection_id=f"conditional-sale-{index}",
            participant_id=participant.participant_id,
            amount_micro_usd=300_000 * unit,
            earned_at=2,
            collected_at=2,
            acceptance_hypothesis="Supplied successful adaptation and full payment assumption; not observed acceptance",
        )
        for index, participant in enumerate(participants, 1)
    ]
    risk = CommonRisk(
        risk_id="shared-qualification",
        description="One shared 80% qualification event; four buyers do not independently diversify this failure",
        affected_participants=[participant.participant_id for participant in participants],
        states=["failed", "qualified"],
        qualification_success_states=["qualified"],
    )
    return Arrangement(
        arrangement_id="invent-the-economy-four-buyer-regression",
        version=1,
        offering=source,
        participants=participants,
        common_risks=[risk],
        scenarios=[
            ArrangementScenario(
                scenario_id="qualification-failure",
                probability_ppm=200_000,
                qualified=False,
                risk_states={risk.risk_id: "failed"},
                costs=[construction],
                failure_handling="Stop after fixed construction loss; no delivery cost or customer receipt",
            ),
            ArrangementScenario(
                scenario_id="qualification-success",
                probability_ppm=800_000,
                qualified=True,
                risk_states={risk.risk_id: "qualified"},
                costs=[construction, *deliveries],
                receipts=receipts,
                failure_handling="All successful adapters and timely full payment are assumptions of this fixture",
            ),
        ],
        state_space_basis="Exact two-branch hypothetical regression from docs/Invent_the_Economy.tex sections 5.1 and 5.3",
        financing_basis="Supplied USD interpretation of thousands of numeraire; development then delivery then receipts",
        rights_cleared=True,
        rights_basis="Shared-use rights assumed in the paper fixture; not a production rights attestation",
        mode="simulation",
        authority_required="Separate live evidence, participant commitments, resource authority and financing approval",
        limitations=[
            "All four needs, the shared core, coalition, probability and costs were supplied, not autonomously discovered",
            "This internal consistency regression establishes no actual customer, technology, qualification or revenue",
        ],
    )
