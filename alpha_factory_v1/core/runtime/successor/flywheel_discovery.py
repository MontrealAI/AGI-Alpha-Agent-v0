# SPDX-License-Identifier: Apache-2.0
"""Discovery records on existing custody, evidence and separately granted execution.

These records preserve hypotheses and experiment interpretations. They neither
execute imported procedures nor admit Alpha, authorize offerings or mint receipts.
Only the already qualified executor, ledger and capability service do those jobs.
"""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import Field, model_validator

from ..store import Conflict
from .flywheel_arrangements import Arrangement, assess_arrangement
from .flywheel_enterprise import EvidenceRef, HumanReference, Offering, key as enterprise_key
from .flywheel_execution import ExecutionMission, ExecutionPermit, operation_key
from .flywheel_learning import ACCEPTANCE_KEY, accepted_general_origin
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest
from .trust import SignedEnvelope

PREFIX = "@flywheel-discovery:"


def key(kind: str, identity: str) -> str:
    return PREFIX + kind + ":" + digest("discovery-record-identity", {"id": identity})


def cost_scope(mission_id: str, bucket: str) -> str:
    return digest("discovery-ledger-cost-scope/v2", {"mission_id": mission_id, "bucket": bucket})


class Purpose(StrictModel):
    useful_purpose: Text
    deliverable: Text
    acceptance_criteria: list[Text] = Field(min_length=1, max_length=32)
    input_semantics: Text
    output_semantics: Text
    scope: Text


class Need(StrictModel):
    need_id: Identifier
    beneficiary: Text
    independently_motivated_purpose: Text
    outside_option: Text
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    evidence_kind: Literal["observed", "published", "internal-research", "synthetic"]
    demand_uncertainty: Text


class Ingredient(StrictModel):
    ingredient_id: Identifier
    description: Text
    origin: Literal["supplied", "established-method", "discovered", "constructed"]
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    limitations: Text


class Formulation(StrictModel):
    formulation_id: Identifier
    approach: Text
    material_difference: Text
    assumptions: list[Text] = Field(min_length=1, max_length=16)
    dependencies: list[Identifier] = Field(default_factory=list, max_length=32)
    uncertainty: Text


class PriorApproach(StrictModel):
    approach: Text
    already_delivers: Text
    availability_to_recipient: Literal["available", "unavailable", "unknown"]
    remaining_limitation: Text
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)


class OpportunityCase(StrictModel):
    """A serious candidate's challenge to prior art, still a falsifiable hypothesis."""

    existing_approaches: list[PriorApproach] = Field(min_length=1, max_length=16)
    unresolved_gap: Text
    gap_evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    why_now: Text
    proposed_construction: Text
    decisive_experiment: Text
    commercial_mechanism: Text
    falsifying_observation: Text
    missing_evidence: list[Text] = Field(min_length=1, max_length=32)
    novelty_scope: Literal["recipient", "organization", "application", "scientific-hypothesis"]


class Opportunity(StrictModel):
    schema_name: Literal["flywheel-opportunity/v1"] = "flywheel-opportunity/v1"
    opportunity_id: Identifier
    version: int = Field(ge=1, le=1_000_000)
    purpose: Purpose
    needs: list[Need] = Field(min_length=1, max_length=16)
    limiting_assumptions: list[Text] = Field(min_length=1, max_length=32)
    shared_structure_hypothesis: Text
    formulations: list[Formulation] = Field(min_length=2, max_length=16)
    ingredients: list[Ingredient] = Field(min_length=1, max_length=32)
    unresolved_questions: list[Text] = Field(min_length=1, max_length=32)
    mode: Literal["live", "hybrid", "simulation"]
    parent_opportunity: EvidenceRef | None = None
    discovery_case: OpportunityCase | None = None

    @model_validator(mode="after")
    def distinct(self) -> Opportunity:
        for items, name in (
            (self.needs, "need_id"),
            (self.formulations, "formulation_id"),
            (self.ingredients, "ingredient_id"),
        ):
            if len({getattr(item, name) for item in items}) != len(items):
                raise ValueError("opportunity ingredient, need and formulation identities must be unique")
        ingredients = {item.ingredient_id for item in self.ingredients}
        if any(not set(item.dependencies) <= ingredients for item in self.formulations):
            raise ValueError("formulations may depend only on disclosed ingredients")
        if self.mode == "live" and any(item.evidence_kind == "synthetic" for item in self.needs):
            raise ValueError("synthetic needs cannot become live demand")
        if len(canonical(self)) > 120_000:
            raise ValueError("opportunity exceeds its immutable record budget")
        return self


class TransformationWitness(StrictModel):
    schema_name: Literal["flywheel-transformation-witness/v1"] = "flywheel-transformation-witness/v1"
    witness_id: Identifier
    opportunity_id: Identifier
    opportunity_spec_digest: Digest
    purpose: Purpose
    binding_restriction: Text
    removable_basis: Text
    change_kind: Literal[
        "representation", "information", "experiment", "dependency", "workflow", "task-boundary", "coordination"
    ]
    replacement: Text
    operation_in_original_setting: Text
    falsifying_observation: Text
    formulation_id: Identifier
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    limitations: Text


class ExperimentStep(StrictModel):
    step_id: Identifier
    question: Text
    dependencies: list[Identifier] = Field(default_factory=list, max_length=32)
    proposed_artifact: Text
    decisive_check: Text
    falsifying_observation: Text
    cost_bucket: Literal["A", "B", "C"]
    cost_cap_micro_usd: int = Field(ge=0, le=10**12)
    seconds_cap: int = Field(ge=1, le=43_200)
    execution_request_digest: Digest | None = None


class ExplorationBundle(StrictModel):
    schema_name: Literal["flywheel-exploration-bundle/v1"] = "flywheel-exploration-bundle/v1"
    bundle_id: Identifier
    witness_id: Identifier
    witness_spec_digest: Digest
    steps: list[ExperimentStep] = Field(min_length=1, max_length=32)
    total_cost_cap_micro_usd: int = Field(ge=0, le=10**12)
    total_seconds_cap: int = Field(ge=1, le=43_200)
    checkpoint_after: list[Identifier] = Field(min_length=1, max_length=32)
    stopping_conditions: list[Text] = Field(min_length=1, max_length=16)
    joint_value_hypothesis: Text
    uncertainty: Text

    @model_validator(mode="after")
    def bounded(self) -> ExplorationBundle:
        seen: set[str] = set()
        for step in self.steps:
            if step.step_id in seen or len(set(step.dependencies)) != len(step.dependencies):
                raise ValueError("distinct steps and dependencies required")
            if not set(step.dependencies) <= seen:
                raise ValueError("steps require earlier dependencies; cycles and missing dependencies refuse")
            seen.add(step.step_id)
        if len(set(self.checkpoint_after)) != len(self.checkpoint_after) or not set(self.checkpoint_after) <= seen:
            raise ValueError("distinct checkpoints must name included steps")
        if (
            sum(step.cost_cap_micro_usd for step in self.steps) > self.total_cost_cap_micro_usd
            or sum(step.seconds_cap for step in self.steps) > self.total_seconds_cap
        ):
            raise ValueError("declared bundle cap must cover the entire complementary package")
        if len(canonical(self)) > 120_000:
            raise ValueError("bundle exceeds its immutable record budget")
        return self


class ExperimentObservation(StrictModel):
    bundle_id: Identifier
    step_id: Identifier
    interpretation: Literal["supports", "falsifies", "inconclusive"]
    observation: Text
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    artifact: EvidenceRef
    cost_operation: Identifier
    elapsed_seconds: int = Field(ge=0, le=43_200)
    execution_operation: Identifier | None = None
    acceptance: Literal["not-claimed", "existing-placement-acceptance"] = "not-claimed"
    limitations: Text


class ResourceBudget(StrictModel):
    tokens: int = Field(ge=1, le=10**9)
    tool_actions: int = Field(ge=0, le=10**6)
    seconds: int = Field(ge=1, le=43_200)
    cost_cap_micro_usd: int = Field(ge=0, le=10**12)


class ComparisonArm(StrictModel):
    role: Literal["U", "E", "E+"]
    model_profile_digest: Digest
    access_and_tools_digest: Digest
    resource_budget: ResourceBudget
    workflow_digest: Digest
    retained_capability_digest: Digest | None = None
    starting_capabilities: list[Text] = Field(min_length=1, max_length=32)
    baseline_definition: Text


class ComparisonPlan(StrictModel):
    schema_name: Literal["flywheel-operational-alpha-comparison/v1"] = "flywheel-operational-alpha-comparison/v1"
    comparison_id: Identifier
    opportunity_id: Identifier
    opportunity_spec_digest: Digest
    purpose: Purpose
    human_reference: HumanReference
    arms: list[ComparisonArm] = Field(min_length=3, max_length=3)
    ordinary_use_basis: Text
    fresh_instance_policy: Text
    complete_cost_policy: Text
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)

    @model_validator(mode="after")
    def matched(self) -> ComparisonPlan:
        arms = {arm.role: arm for arm in self.arms}
        if set(arms) != {"U", "E", "E+"}:
            raise ValueError("freeze distinct U, E and E+ configurations; H remains the commercial reference")
        baseline = arms["U"]
        if any(
            arm.model_profile_digest != baseline.model_profile_digest
            or arm.access_and_tools_digest != baseline.access_and_tools_digest
            or arm.resource_budget != baseline.resource_budget
            for arm in self.arms
        ):
            raise ValueError("Operational Alpha requires matched model access, tools and resource budgets")
        if arms["U"].retained_capability_digest or arms["E"].retained_capability_digest:
            raise ValueError("only E+ receives the specific additional retained capability")
        if arms["E+"].retained_capability_digest is None or arms["E+"].workflow_digest != arms["E"].workflow_digest:
            raise ValueError("E+ must use E's exact workflow plus one explicit retained capability")
        return self


class DiscoveryDecision(StrictModel):
    opportunity_id: Identifier
    opportunity_spec_digest: Digest
    disposition: Literal["continue", "revise", "offer", "retain", "stop"]
    rationale: Text
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    uncertainty: Text
    next_question: Text


class OfferingLink(StrictModel):
    opportunity_id: Identifier
    opportunity_spec_digest: Digest
    offering_id: Identifier
    offering_record_digest: Digest


class BundleCheckpoint(StrictModel):
    bundle_id: Identifier
    disposition: Literal["continue", "stop"]
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    rationale: Text
    stopping_conditions_checked: Text


class ArrangementRequest(StrictModel):
    opportunity_id: Identifier
    opportunity_spec_digest: Digest
    arrangement: Arrangement
    initial_cash_micro_usd: int = Field(ge=0, le=10**15)
    reserve_micro_usd: int = Field(default=0, ge=0, le=10**15)
    existing_obligations_micro_usd: int = Field(default=0, ge=0, le=10**15)
    financing_assumption_basis: Text


class DiscoveryCommand(StrictModel):
    journal_identity: str = Field(pattern=r"^urn:agialpha:ed25519:[0-9a-f]{64}$")
    operation_id: Identifier
    expires_at: int = Field(ge=1)
    action: Literal[
        "opportunity",
        "witness",
        "bundle",
        "observe",
        "checkpoint",
        "comparison",
        "decision",
        "link-offering",
        "arrangement",
        "search-freeze",
        "search-submit",
        "search-review",
        "search-assess",
        "research-seed",
        "research-plan",
    ]
    expected_head: Digest | None
    record: dict[str, Any]


class Discovery:
    """Append scoped hypotheses to the existing protected service's journal."""

    def __init__(self, service: Any) -> None:
        self.service, self.journal, self.costs = service, service.journal, service.costs

    def _read(self, kind: str, identity: str, cx: Any) -> dict[str, Any] | None:
        try:
            return dict(self.journal.latest(key(kind, identity), cx))
        except KeyError:
            return None

    def _evidence(self, refs: list[EvidenceRef], cx: Any) -> None:
        for ref in refs:
            if self.journal.latest(ref.journal_key, cx)["digest"] != ref.record_digest:
                raise Conflict("discovery evidence is stale or differs from current recorded history")

    @staticmethod
    def _case_evidence(spec: Opportunity) -> list[EvidenceRef]:
        case = spec.discovery_case
        return (
            []
            if case is None
            else [
                *case.gap_evidence,
                *(ref for approach in case.existing_approaches for ref in approach.evidence),
            ]
        )

    def _opportunity(self, identity: str, expected: str, cx: Any) -> Opportunity:
        record = self._read("opportunity", identity, cx)
        if record is None or digest("discovery-opportunity", record["spec"]) != expected:
            raise Conflict("opportunity changed; recheck this mission's purpose and assumptions")
        spec = Opportunity.model_validate(record["spec"])
        self._evidence(
            [ref for need in spec.needs for ref in need.evidence]
            + [ref for ingredient in spec.ingredients for ref in ingredient.evidence]
            + ([spec.parent_opportunity] if spec.parent_opportunity else []),
            # Case evidence has the same freshness boundary as the original need.
            cx,
        )
        self._evidence(self._case_evidence(spec), cx)
        return spec

    def _witness(self, identity: str, expected: str, cx: Any) -> TransformationWitness:
        record = self._read("witness", identity, cx)
        if record is None or digest("discovery-witness", record["spec"]) != expected:
            raise Conflict("transformation witness changed")
        spec = TransformationWitness.model_validate(record["spec"])
        self._opportunity(spec.opportunity_id, spec.opportunity_spec_digest, cx)
        self._evidence(spec.evidence, cx)
        return spec

    def inspect(self, kind: str, identity: str) -> dict[str, Any]:
        from .flywheel_insight import KINDS

        if (
            kind
            not in {
                "opportunity",
                "witness",
                "bundle",
                "observation",
                "comparison",
                "decision",
                "offering-link",
                "arrangement",
            }
            | KINDS
        ):
            raise ValueError("unsupported discovery inspection")
        with self.journal.transaction() as cx:
            self.service._state(cx)
            value = self._read(kind, identity, cx)
            if value is None:
                raise KeyError(identity)
            return value

    def _ledger_mission(self, terms: ExperimentObservation, execution_digest: str | None, cx: Any) -> str:
        if terms.execution_operation is None:
            return terms.cost_operation
        execution = self.journal.latest(operation_key(terms.execution_operation), cx)
        if execution["digest"] != execution_digest:
            raise Conflict("accounting reconciliation requires the original exact execution receipt")
        return str(ExecutionMission.model_validate(execution["mission"]).mission_id)

    def _migrate_cost_allocations(self, cx: Any) -> None:
        """Reserve legacy claims before granting any new mission allocation.

        Derive an old ambiguous key's meaning from its pinned observation.
        Typed indexes share the same Journal and never charge the ledger.
        """
        names = [
            row[0]
            for row in cx.execute(
                "SELECT DISTINCT mission FROM events WHERE mission GLOB ? ORDER BY mission",
                (PREFIX + "cost-allocation:*",),
            )
        ]
        for name in names:
            legacy = self.journal.latest(name, cx)
            observation = self._read("observation", legacy["observation_id"], cx)
            if observation is None:
                raise Conflict("legacy allocation has no original observation")
            terms = ExperimentObservation.model_validate(observation["terms"])
            bundle = self._read("bundle", terms.bundle_id, cx)
            if bundle is None:
                raise Conflict("legacy allocation has no original bundle")
            spec = ExplorationBundle.model_validate(bundle["spec"])
            step = next((item for item in spec.steps if item.step_id == terms.step_id), None)
            ledger_mission = self._ledger_mission(terms, observation["execution_digest"], cx)
            if (
                step is None
                or legacy["bundle_id"] != terms.bundle_id
                or legacy["cost_operation"] != terms.cost_operation
                or legacy["bucket"] != step.cost_bucket
                or legacy.get("ledger_mission_id", ledger_mission) != ledger_mission
            ):
                raise Conflict("legacy allocation differs from its original observed accounting scope")
            identity = cost_scope(ledger_mission, step.cost_bucket)
            current = self._read("mission-cost-allocation", identity, cx)
            if current is not None:
                if (
                    current["observation_id"] != legacy["observation_id"]
                    or current["bundle_id"] != terms.bundle_id
                    or current["cost_operation"] != terms.cost_operation
                ):
                    raise Conflict("legacy ledger mission and bucket already belong to another discovery observation")
                continue
            self.journal.append(
                cx,
                key("mission-cost-allocation", identity),
                {
                    "scope_version": 2,
                    "bundle_id": terms.bundle_id,
                    "observation_id": legacy["observation_id"],
                    "cost_operation": terms.cost_operation,
                    "ledger_mission_id": ledger_mission,
                    "bucket": step.cost_bucket,
                    "legacy_allocation_digest": legacy["digest"],
                    "observation_digest": observation["digest"],
                },
            )

    def apply(self, signed: SignedEnvelope) -> dict[str, Any]:
        signed = SignedEnvelope.model_validate_json(canonical(signed))
        raw = self.service.trust.verify(signed, "flywheel-discovery-command", "controller")
        command = DiscoveryCommand.model_validate(raw)
        if command.journal_identity != self.journal.identity or command.expires_at <= int(time.time()):
            raise ValueError("discovery command requires this journal and current authority")
        with self.journal.transaction() as cx:
            self.service._state(cx)
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("discovery is stopped")
            if self._read("operation", command.operation_id, cx) is not None:
                raise Conflict("discovery operation already consumed; inspect its recorded result")
            target, value = self._apply(command, cx)
            value.update(signed=signed.model_dump(), source=self.service.execution_digest, authority_granted=False)
            record = self.journal.append(cx, target, value)
            self.journal.append(
                cx, key("operation", command.operation_id), {"target": target, "result": record["digest"]}
            )
            self.service.checkpoint.advance(self.journal, cx)
            return dict(record)

    def _new(self, kind: str, identity: str, expected: str | None, cx: Any) -> str:
        if expected is not None or self._read(kind, identity, cx) is not None:
            raise Conflict("discovery record identity must be new")
        return key(kind, identity)

    def _apply(self, command: DiscoveryCommand, cx: Any) -> tuple[str, dict[str, Any]]:
        from .flywheel_insight import ACTIONS, apply_insight

        if command.action in ACTIONS:
            return apply_insight(self, command, cx)
        if command.action == "opportunity":
            spec = Opportunity.model_validate(command.record)
            old = self._read("opportunity", spec.opportunity_id, cx)
            if (old["digest"] if old else None) != command.expected_head:
                raise Conflict("opportunity head changed")
            if spec.version != (old["spec"]["version"] + 1 if old else 1):
                raise ValueError("opportunity revisions must be consecutive")
            if old and spec.purpose != Opportunity.model_validate(old["spec"]).purpose:
                raise ValueError("changed purpose or relaxed acceptance requires a new opportunity identity")
            self._evidence(
                [ref for need in spec.needs for ref in need.evidence]
                + [ref for ingredient in spec.ingredients for ref in ingredient.evidence]
                + ([spec.parent_opportunity] if spec.parent_opportunity else []),
                cx,
            )
            self._evidence(self._case_evidence(spec), cx)
            return key("opportunity", spec.opportunity_id), {
                "spec": spec.model_dump(),
                "stage": "hypothesis",
                "previous_digest": old["digest"] if old else None,
            }
        if command.action == "witness":
            witness = TransformationWitness.model_validate(command.record)
            opportunity = self._opportunity(witness.opportunity_id, witness.opportunity_spec_digest, cx)
            if witness.purpose != opportunity.purpose or witness.formulation_id not in {
                item.formulation_id for item in opportunity.formulations
            }:
                raise ValueError("transformation must preserve the original purpose and a disclosed formulation")
            self._evidence(witness.evidence, cx)
            return self._new("witness", witness.witness_id, command.expected_head, cx), {
                "spec": witness.model_dump(),
                "stage": "hypothesis",
            }
        if command.action == "bundle":
            bundle = ExplorationBundle.model_validate(command.record)
            self._witness(bundle.witness_id, bundle.witness_spec_digest, cx)
            return self._new("bundle", bundle.bundle_id, command.expected_head, cx), {
                "spec": bundle.model_dump(),
                "status": "planned",
                "observations": [],
                "known_cost_micro_usd": 0,
                "elapsed_seconds": 0,
                "execution_authority": "requires separate current mission permits",
            }
        if command.action == "observe":
            return self._observe(command, cx)
        if command.action == "checkpoint":
            checkpoint = BundleCheckpoint.model_validate(command.record)
            old = self._read("bundle", checkpoint.bundle_id, cx)
            if (
                old is None
                or old["digest"] != command.expected_head
                or old["status"] not in {"paused-checkpoint", "paused-uncertain"}
            ):
                raise Conflict("checkpoint decision requires the exact paused bundle")
            bundle = ExplorationBundle.model_validate(old["spec"])
            self._witness(bundle.witness_id, bundle.witness_spec_digest, cx)
            self._evidence(checkpoint.evidence, cx)
            value = self.journal.document(old)
            if checkpoint.disposition == "continue":
                self._migrate_cost_allocations(cx)
                costs = []
                reconciled = []
                steps = {step.step_id: step for step in bundle.steps}
                for row in value["observations"]:
                    terms = ExperimentObservation.model_validate(row["terms"])
                    ledger_mission = self._ledger_mission(terms, row["execution_digest"], cx)
                    allocation_id = cost_scope(ledger_mission, steps[terms.step_id].cost_bucket)
                    allocation = self._read("mission-cost-allocation", allocation_id, cx)
                    if allocation is None:
                        raise Conflict("recorded observation has no cost allocation")
                    if (
                        allocation["bundle_id"] != bundle.bundle_id
                        or allocation["cost_operation"] != terms.cost_operation
                    ):
                        raise Conflict("ledger mission and bucket already belong to another observation")
                    report = self.costs.report(ledger_mission, cx)
                    step = steps[row["terms"]["step_id"]]
                    if not report["bucket_complete"][step.cost_bucket]:
                        raise Conflict("checkpoint cannot clear unknown experiment liabilities")
                    costs.append(report["costs"][step.cost_bucket])
                    reconciled.append(
                        {"step_id": step.step_id, "ledger_mission_id": ledger_mission, "cost_report": report}
                    )
                value["known_cost_micro_usd"] = sum(costs)
                value.setdefault("accounting_reconciliations", []).append(
                    {
                        "prior_bundle_digest": old["digest"],
                        "reports": reconciled,
                    }
                )
                if (
                    any(
                        cost > steps[row["terms"]["step_id"]].cost_cap_micro_usd
                        or row["terms"]["elapsed_seconds"] > steps[row["terms"]["step_id"]].seconds_cap
                        for cost, row in zip(costs, value["observations"])
                    )
                    or sum(costs) > bundle.total_cost_cap_micro_usd
                    or value["elapsed_seconds"] > bundle.total_seconds_cap
                ):
                    value["status"] = "stopped-budget"
            value["status"] = (
                "stopped-controller"
                if checkpoint.disposition == "stop"
                else (
                    "stopped-budget"
                    if value["status"] == "stopped-budget"
                    else "completed"
                    if len(value["observations"]) == len(bundle.steps)
                    else "observing"
                )
            )
            value.setdefault("checkpoint_history", []).append(
                {"terms": checkpoint.model_dump(), "prior_bundle_digest": old["digest"]}
            )
            return key("bundle", checkpoint.bundle_id), value
        if command.action == "comparison":
            comparison = ComparisonPlan.model_validate(command.record)
            opportunity = self._opportunity(comparison.opportunity_id, comparison.opportunity_spec_digest, cx)
            if comparison.purpose != opportunity.purpose:
                raise ValueError("comparison must preserve identical original requirements")
            self._evidence(comparison.evidence, cx)
            return self._new("comparison", comparison.comparison_id, command.expected_head, cx), {
                "spec": comparison.model_dump(),
                "stage": "frozen-plan",
                "results": "not measured",
                "contrasts": {"Operational Alpha": "E versus U", "retained increment": "E+ versus E"},
            }
        if command.action == "decision":
            decision = DiscoveryDecision.model_validate(command.record)
            self._opportunity(decision.opportunity_id, decision.opportunity_spec_digest, cx)
            self._evidence(decision.evidence, cx)
            return self._new("decision", command.operation_id, command.expected_head, cx), {
                "spec": decision.model_dump(),
                "stage": "recommendation-only",
            }
        if command.action == "arrangement":
            return self._arrangement(command, cx)
        link = OfferingLink.model_validate(command.record)
        opportunity = self._opportunity(link.opportunity_id, link.opportunity_spec_digest, cx)
        record = self.journal.latest(enterprise_key("offering", link.offering_id), cx)
        if record["digest"] != link.offering_record_digest:
            raise Conflict("linked offering changed")
        offering = Offering.model_validate(record["spec"])
        if (
            offering.useful_outcome != opportunity.purpose.useful_purpose
            or offering.deliverable != opportunity.purpose.deliverable
            or offering.acceptance_criteria != opportunity.purpose.acceptance_criteria
            or offering.scope != opportunity.purpose.scope
            or offering.mode != opportunity.mode
        ):
            raise ValueError("offering link cannot change purpose, acceptance, scope or evidence mode")
        return self._new("offering-link", link.offering_id, command.expected_head, cx), {
            "spec": link.model_dump(),
            "stage": "linked-hypothesis",
            "offering_authorization_inherited": False,
        }

    def _arrangement(self, command: DiscoveryCommand, cx: Any) -> tuple[str, dict[str, Any]]:
        request = ArrangementRequest.model_validate(command.record)
        opportunity = self._opportunity(request.opportunity_id, request.opportunity_spec_digest, cx)
        arrangement = request.arrangement
        offering_record = self.journal.latest(arrangement.offering.journal_key, cx)
        offering = Offering.model_validate(offering_record["spec"])
        if arrangement.offering.journal_key != enterprise_key("offering", offering.offering_id):
            raise ValueError("arrangement must bind an existing enterprise offering")
        if (
            offering.useful_outcome != opportunity.purpose.useful_purpose
            or offering.deliverable != opportunity.purpose.deliverable
            or offering.acceptance_criteria != opportunity.purpose.acceptance_criteria
            or offering.scope != opportunity.purpose.scope
            or offering.mode != opportunity.mode
            or arrangement.mode != opportunity.mode
        ):
            raise ValueError("arrangement cannot replace the useful purpose, acceptance, scope or mode")
        refs = [arrangement.offering, *arrangement.dependency_evidence]
        for participant in arrangement.participants:
            refs.extend([participant.need, *participant.commitment_evidence])
        self._evidence(refs + offering.need_evidence, cx)
        old = self._read("arrangement", arrangement.arrangement_id, cx)
        if (old["digest"] if old else None) != command.expected_head:
            raise Conflict("arrangement head changed")
        if arrangement.version != (old["spec"]["arrangement"]["version"] + 1 if old else 1):
            raise ValueError("arrangement revisions must be consecutive and reassessed")
        assessment = assess_arrangement(
            arrangement,
            request.initial_cash_micro_usd,
            request.reserve_micro_usd,
            request.existing_obligations_micro_usd,
        )
        return key("arrangement", arrangement.arrangement_id), {
            "spec": request.model_dump(),
            "stage": "projected-commercial-assessment",
            "assessment": assessment,
            "actual_ledger_snapshot": self.costs.report(cx=cx),
            "previous_digest": old["digest"] if old else None,
            "financing_evidence_type": "operator-supplied projection, not bank balance or earned revenue",
        }

    def _observe(self, command: DiscoveryCommand, cx: Any) -> tuple[str, dict[str, Any]]:
        observation = ExperimentObservation.model_validate(command.record)
        old = self._read("bundle", observation.bundle_id, cx)
        if old is None or old["digest"] != command.expected_head:
            raise Conflict("bundle head changed")
        if old["status"] in {
            "stopped-budget",
            "paused-uncertain",
            "paused-checkpoint",
            "stopped-controller",
            "completed",
        }:
            raise Conflict("bundle is terminal or needs a separately scoped new assessment")
        bundle = ExplorationBundle.model_validate(old["spec"])
        witness = self._witness(bundle.witness_id, bundle.witness_spec_digest, cx)
        opportunity = self._opportunity(witness.opportunity_id, witness.opportunity_spec_digest, cx)
        steps = {item.step_id: item for item in bundle.steps}
        observed = {item["terms"]["step_id"] for item in old["observations"]}
        if observation.step_id not in steps or observation.step_id in observed:
            raise Conflict("observation must identify one unrecorded bundle step")
        step = steps[observation.step_id]
        if not set(step.dependencies) <= observed:
            raise Conflict("dependent experiment cannot precede its prerequisite observations")
        if any(item["terms"]["cost_operation"] == observation.cost_operation for item in old["observations"]):
            raise Conflict("one activity cannot supply two experiment cost allocations")
        self._new("observation", command.operation_id, None, cx)
        self._evidence([*observation.evidence, observation.artifact], cx)
        execution_digest = None
        if observation.execution_operation is not None:
            execution = self.journal.latest(operation_key(observation.execution_operation), cx)
            mission = ExecutionMission.model_validate(execution["mission"])
            if (
                mission.goal != witness.purpose.useful_purpose
                or mission.deliverable != witness.purpose.deliverable
                or mission.acceptance_criteria != witness.purpose.acceptance_criteria
                or mission.mode != opportunity.mode
                or step.execution_request_digest != digest("flywheel-execution-request", mission)
            ):
                raise ValueError("experiment execution changes frozen inputs, purpose, acceptance or evidence mode")
            if execution["status"] not in {
                "delivered-awaiting-independent-acceptance-and-costs",
                "failed-or-uncertain",
                "stopped-budget",
            }:
                raise Conflict("experiment must bind a terminal execution, never an intended action")
            if observation.cost_operation != observation.execution_operation:
                raise ValueError("executed experiment must use its actual operation accounting")
            permit = ExecutionPermit.model_validate(execution["permit"]["payload"]["permit"])
            if permit.bucket != step.cost_bucket:
                raise ValueError("experiment cost bucket must match its actual execution permit")
            if observation.artifact != EvidenceRef(
                journal_key=operation_key(observation.execution_operation), record_digest=execution["digest"]
            ):
                raise ValueError("executed construction must pin the exact artifact-bearing execution record")
            if observation.elapsed_seconds * 1000 < execution.get("elapsed_ms", 43_200_001):
                raise ValueError("experiment elapsed time cannot understate recorded execution time")
            execution_digest = execution["digest"]
        if observation.acceptance == "existing-placement-acceptance":
            if observation.execution_operation is None:
                raise ValueError("existing acceptance requires an actual bound execution")
            accepted_general_origin(self.service, observation.execution_operation, cx)
            self._evidence(
                [
                    EvidenceRef(
                        journal_key=ACCEPTANCE_KEY + observation.execution_operation,
                        record_digest=self.journal.latest(ACCEPTANCE_KEY + observation.execution_operation, cx)[
                            "digest"
                        ],
                    )
                ],
                cx,
            )
        ledger_mission = self._ledger_mission(observation, execution_digest, cx)
        self._migrate_cost_allocations(cx)
        claim_id = cost_scope(ledger_mission, step.cost_bucket)
        if self._read("mission-cost-allocation", claim_id, cx) is not None:
            raise Conflict("this ledger mission and bucket already belong to another discovery observation")
        report = self.costs.report(ledger_mission, cx)
        complete = report["bucket_complete"][step.cost_bucket]
        cost = report["costs"][step.cost_bucket]
        value = self.journal.document(old)
        value["known_cost_micro_usd"] += cost
        value["elapsed_seconds"] += observation.elapsed_seconds
        over = (
            cost > step.cost_cap_micro_usd
            or observation.elapsed_seconds > step.seconds_cap
            or value["known_cost_micro_usd"] > bundle.total_cost_cap_micro_usd
            or value["elapsed_seconds"] > bundle.total_seconds_cap
        )
        pause = observation.step_id in bundle.checkpoint_after or observation.interpretation == "falsifies"
        value["status"] = (
            "paused-uncertain"
            if not complete
            else (
                "stopped-budget"
                if over
                else (
                    "paused-checkpoint"
                    if pause
                    else "completed"
                    if len(observed) + 1 == len(bundle.steps)
                    else "observing"
                )
            )
        )
        observed_value = {
            "terms": observation.model_dump(),
            "cost_report": report,
            "execution_digest": execution_digest,
            "ledger_mission_id": ledger_mission,
            "complete_selected_bucket": complete,
            "within_declared_budget": not over,
            "interpretation_basis": "controller attestation, not automatic technical or commercial qualification",
            "checkpoint_due": pause,
            "source": self.service.execution_digest,
            "authority_granted": False,
        }
        value["observations"].append(observed_value)
        self.journal.append(cx, key("observation", command.operation_id), observed_value)
        self.journal.append(
            cx,
            key("mission-cost-allocation", claim_id),
            {
                "scope_version": 2,
                "bundle_id": bundle.bundle_id,
                "observation_id": command.operation_id,
                "cost_operation": observation.cost_operation,
                "ledger_mission_id": ledger_mission,
                "bucket": step.cost_bucket,
            },
        )
        return key("bundle", bundle.bundle_id), value
