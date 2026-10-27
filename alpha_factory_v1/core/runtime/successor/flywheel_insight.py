# SPDX-License-Identifier: Apache-2.0
"""Frozen discovery protocols and off-chain research links in the existing Journal."""

from __future__ import annotations

import time
from typing import Any, Literal

from pydantic import Field, model_validator

from .. import ascension
from ..store import Conflict
from .flywheel_discovery import ExplorationBundle, ResourceBudget, cost_scope, key, PREFIX
from .flywheel_enterprise import EvidenceRef
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest

Dimension = Literal["novelty", "usefulness", "feasibility", "commercial-plausibility"]
DIMENSIONS = {"novelty", "usefulness", "feasibility", "commercial-plausibility"}
ACTIONS = {"search-freeze", "search-submit", "search-review", "search-assess", "research-seed", "research-plan"}
KINDS = {"search", "search-submission", "search-review", "search-assessment", "research-seed", "research-plan"}
MAX_REVIEWS = 16


class SearchSource(StrictModel):
    source_id: Identifier
    url: str = Field(pattern=r"^https://[^\s]{1,1800}$")
    title: Text
    available_at: int = Field(ge=1)
    captured_at: int = Field(ge=1)
    content_digest: Digest
    rights: Text
    evidence: EvidenceRef


class SearchCriterion(StrictModel):
    dimension: Dimension
    rubric: Text
    minimum_score: int = Field(ge=1, le=4)


class SearchArm(StrictModel):
    arm_id: Literal["U", "E", "H"]
    model_id: Text | None
    model_configuration_digest: Digest | None
    access_and_tools_digest: Digest
    protocol_digest: Digest
    budget: ResourceBudget
    definition: Text


class SearchFreeze(StrictModel):
    schema_name: Literal["flywheel-insight-search/v1"] = "flywheel-insight-search/v1"
    search_id: Identifier
    open_brief: Text
    information_cutoff: int = Field(ge=1)
    sources: list[SearchSource] = Field(min_length=1, max_length=32)
    search_units: list[Identifier] = Field(min_length=1, max_length=16)
    arms: list[SearchArm] = Field(min_length=2, max_length=3)
    criteria: list[SearchCriterion] = Field(min_length=4, max_length=4)
    mode: Literal["live", "recorded", "synthetic", "calibrated"]
    design: Literal["prospective", "historical-replay", "development"]
    human_search_limitation: Text
    leakage_controls: Text
    ordinary_search_basis: Text

    @model_validator(mode="after")
    def coherent(self) -> SearchFreeze:
        arms = {arm.arm_id: arm for arm in self.arms}
        if len(arms) != len(self.arms) or not {"U", "E"} <= arms.keys():
            raise ValueError("freeze distinct ordinary and expert search arms")
        if len(set(self.search_units)) != len(self.search_units):
            raise ValueError("freeze distinct search units before recording attempts")
        if len({source.source_id for source in self.sources}) != len(self.sources):
            raise ValueError("source identities must be unique")
        if any(source.available_at > self.information_cutoff for source in self.sources):
            raise ValueError("source was not available at the declared information cutoff")
        if {item.dimension for item in self.criteria} != DIMENSIONS:
            raise ValueError("review novelty, usefulness, feasibility and commercial plausibility separately")
        for arm in self.arms:
            if (arm.model_id is None) != (arm.model_configuration_digest is None):
                raise ValueError("model identifier and exact configuration must be supplied together")
            if (arm.arm_id == "H") != (arm.model_id is None):
                raise ValueError("human search and model search have distinct resource identities")
        if any(
            getattr(arms["U"], field) != getattr(arms["E"], field)
            for field in ("model_id", "model_configuration_digest", "access_and_tools_digest", "budget")
        ):
            raise ValueError("ordinary and expert search require matched models, tools and resource caps")
        if self.mode in {"synthetic", "calibrated"} and self.design != "development":
            raise ValueError("synthetic and calibrated protocols are development, not prospective model trials")
        if len(canonical(self)) > 120_000:
            raise ValueError("search freeze exceeds its immutable byte budget")
        return self


def input_digest(freeze: SearchFreeze) -> str:
    return digest("insight-discovery-input/v1", freeze)


def slot(search_id: str, arm_id: str, unit_id: str) -> str:
    return digest("insight-search-slot/v1", {"search": search_id, "arm": arm_id, "unit": unit_id})


class SearchSubmission(StrictModel):
    search_id: Identifier
    arm_id: Literal["U", "E", "H"]
    unit_id: Identifier
    frozen_input_digest: Digest
    origin: Literal["agent-output", "human-output", "researcher-supplied", "synthetic-fixture"]
    status: Literal["candidate", "failed", "no-candidate"]
    opportunity_id: Identifier | None = None
    opportunity_spec_digest: Digest | None = None
    source_ids: list[Identifier] = Field(max_length=32)
    original_output: EvidenceRef
    attempt_evidence: list[EvidenceRef] = Field(min_length=1, max_length=32)
    usage: ResourceBudget
    cost_mission_id: Identifier
    limitations: Text

    @model_validator(mode="after")
    def outcome(self) -> SearchSubmission:
        if (self.status == "candidate") != (self.opportunity_id is not None):
            raise ValueError("candidate outcomes require an opportunity; failed searches preserve no candidate")
        if (self.opportunity_id is None) != (self.opportunity_spec_digest is None):
            raise ValueError("opportunity identity and specification must be bound together")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("source references must be distinct")
        return self


class SearchReview(StrictModel):
    review_id: Identifier
    submission: EvidenceRef
    reviewer_id: Identifier
    dimension: Dimension
    score: int = Field(ge=0, le=4)
    rationale: Text
    evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    review_relationship: Literal["same-operator", "separate-model", "independent-human"]
    prior_art: Literal["established-approach", "not-found-in-bounded-search", "unresolved"] = "unresolved"
    limitations: Text


class SearchAssessment(StrictModel):
    assessment_id: Identifier
    submission: EvidenceRef
    reviews: list[EvidenceRef] = Field(max_length=MAX_REVIEWS)
    construction_observation: EvidenceRef | None
    leakage_audit: EvidenceRef | None
    leakage_disposition: Literal["unassessed", "no-known-leakage", "leakage-found"]
    limitations: Text

    @model_validator(mode="after")
    def audit(self) -> SearchAssessment:
        if (self.leakage_disposition == "unassessed") != (self.leakage_audit is None):
            raise ValueError("a leakage disposition requires its separate audit record")
        if len({ref.journal_key for ref in self.reviews}) != len(self.reviews):
            raise ValueError("do not count one review more than once")
        return self


class ResearchSeed(StrictModel):
    schema_name: Literal["flywheel-nova-seed-research/v1"] = "flywheel-nova-seed-research/v1"
    seed_id: Identifier
    version: int = Field(ge=1, le=1_000_000)
    assessment: EvidenceRef
    witness_id: Identifier
    witness_spec_digest: Digest
    rights_evidence: list[EvidenceRef] = Field(min_length=1, max_length=16)
    rights_statement: Text
    uncertainty: Text
    next_experiment: Text


class ResearchPlan(StrictModel):
    plan_id: Identifier
    seed: EvidenceRef
    bundle_id: Identifier
    bundle_spec_digest: Digest
    draft_jobs: list[ascension.JobSpec] = Field(min_length=1, max_length=32)
    required_permissions: list[Text] = Field(min_length=1, max_length=32)
    commercial_assumptions: Text


def _read_ref(discovery: Any, ref: EvidenceRef, cx: Any) -> dict[str, Any]:
    discovery._evidence([ref], cx)
    return dict(discovery.journal.latest(ref.journal_key, cx))


def _submission(discovery: Any, ref: EvidenceRef, cx: Any) -> tuple[dict[str, Any], SearchSubmission]:
    record = _read_ref(discovery, ref, cx)
    spec = SearchSubmission.model_validate(record["spec"])
    if ref.journal_key != key("search-submission", slot(spec.search_id, spec.arm_id, spec.unit_id)):
        raise ValueError("review requires an original search submission")
    _freeze(discovery, spec.search_id, cx)
    discovery._evidence([spec.original_output, *spec.attempt_evidence], cx)
    if spec.opportunity_id is not None:
        discovery._opportunity(spec.opportunity_id, spec.opportunity_spec_digest, cx)
    return record, spec


def _freeze(discovery: Any, identity: str, cx: Any) -> tuple[dict[str, Any], SearchFreeze]:
    record = discovery._read("search", identity, cx)
    if record is None:
        raise KeyError(identity)
    freeze = SearchFreeze.model_validate(record["spec"])
    discovery._evidence([source.evidence for source in freeze.sources], cx)
    _source_bytes(discovery, freeze, cx)
    return record, freeze


def _source_bytes(discovery: Any, freeze: SearchFreeze, cx: Any) -> None:
    for source in freeze.sources:
        record = _read_ref(discovery, source.evidence, cx)
        if digest("insight-source-snapshot/v1", discovery.journal.document(record)) != source.content_digest:
            raise ValueError("source content differs from the exact frozen snapshot")


def _review_inventory(discovery: Any, terms: SearchAssessment, cx: Any) -> None:
    expected = set()
    for row in cx.execute("SELECT DISTINCT mission FROM events WHERE mission GLOB ?", (PREFIX + "search-review:*",)):
        record = discovery.journal.latest(row[0], cx)
        review = SearchReview.model_validate(record["spec"])
        if review.submission == terms.submission:
            discovery._evidence(review.evidence, cx)
            expected.add((row[0], record["digest"]))
    if expected != {(ref.journal_key, ref.record_digest) for ref in terms.reviews}:
        raise Conflict("assessment must preserve every recorded review; later reviews require reassessment")
    if terms.leakage_audit is not None:
        _read_ref(discovery, terms.leakage_audit, cx)
    if terms.construction_observation is not None:
        from .flywheel_discovery import ExperimentObservation

        observation = ExperimentObservation.model_validate(
            _read_ref(discovery, terms.construction_observation, cx)["terms"]
        )
        discovery._evidence([observation.artifact, *observation.evidence], cx)


def _search_accounting(discovery: Any, sub: SearchSubmission, freeze: SearchFreeze, cx: Any) -> dict[str, Any]:
    report = discovery.costs.report(sub.cost_mission_id, cx)
    cap = next(arm.budget.cost_cap_micro_usd for arm in freeze.arms if arm.arm_id == sub.arm_id)
    known = sum(report["costs"].values())
    reasons = []
    if not report["complete"]:
        reasons.append("search-costs-incomplete")
    if known > cap:
        reasons.append("search-ledger-budget-overrun")
    if known > sub.usage.cost_cap_micro_usd:
        reasons.append("search-declared-cost-understates-ledger")
    return {
        "report": report,
        "known_cost_micro_usd": known,
        "frozen_cap_micro_usd": cap,
        "declared_cost_ceiling_micro_usd": sub.usage.cost_cap_micro_usd,
        "eligible": not reasons,
        "reasons": reasons,
    }


def _construction_state(
    discovery: Any, ref: EvidenceRef | None, sub: SearchSubmission, cx: Any
) -> tuple[dict[str, Any] | None, list[str]]:
    from .flywheel_discovery import ExperimentObservation

    if ref is None:
        return None, ["no-linked-construction"]
    record = _read_ref(discovery, ref, cx)
    observation = ExperimentObservation.model_validate(record["terms"])
    bundle_record = discovery._read("bundle", observation.bundle_id, cx)
    if bundle_record is None:
        raise ValueError("construction bundle is missing")
    bundle = ExplorationBundle.model_validate(bundle_record["spec"])
    steps = {step.step_id: step for step in bundle.steps}
    step = steps.get(observation.step_id)
    if step is None:
        raise ValueError("construction observation is not a step of its original bundle")
    mission = discovery._ledger_mission(observation, record["execution_digest"], cx)
    allocation = discovery._read("mission-cost-allocation", cost_scope(mission, step.cost_bucket), cx)
    if (
        allocation is None
        or ref.journal_key != key("observation", allocation["observation_id"])
        or allocation["bundle_id"] != observation.bundle_id
        or not any(item == discovery.journal.document(record) for item in bundle_record["observations"])
    ):
        raise ValueError("construction requires the original observation and ledger allocation")
    witness = discovery._witness(bundle.witness_id, bundle.witness_spec_digest, cx)
    if witness.opportunity_id != sub.opportunity_id or witness.opportunity_spec_digest != sub.opportunity_spec_digest:
        raise ValueError("construction belongs to another opportunity or purpose")
    reasons = []
    inventory = []
    seen: set[str] = set()
    total_cost, elapsed = 0, 0
    for row in bundle_record["observations"]:
        terms = ExperimentObservation.model_validate(row["terms"])
        if terms.step_id not in steps or terms.step_id in seen or terms.bundle_id != bundle.bundle_id:
            raise ValueError("construction inventory must preserve distinct original bundle steps")
        current_step = steps[terms.step_id]
        if not set(current_step.dependencies) <= seen:
            raise ValueError("construction inventory changes the original dependency order")
        seen.add(terms.step_id)
        discovery._evidence([terms.artifact, *terms.evidence], cx)
        current_mission = discovery._ledger_mission(terms, row["execution_digest"], cx)
        report = discovery.costs.report(current_mission, cx)
        cost = report["costs"][current_step.cost_bucket]
        total_cost += cost
        elapsed += terms.elapsed_seconds
        if not report["bucket_complete"][current_step.cost_bucket]:
            reasons.append("construction-costs-incomplete")
        if cost > current_step.cost_cap_micro_usd or terms.elapsed_seconds > current_step.seconds_cap:
            reasons.append("construction-budget-overrun")
        if terms.interpretation != "supports":
            reasons.append("construction-has-adverse-or-inconclusive-observations")
        inventory.append(
            {
                "step_id": terms.step_id,
                "interpretation": terms.interpretation,
                "ledger_mission_id": current_mission,
                "current_cost_report": report,
            }
        )
    if total_cost > bundle.total_cost_cap_micro_usd or elapsed > bundle.total_seconds_cap:
        reasons.append("construction-budget-overrun")
    if seen != set(steps) or bundle_record["status"] != "completed":
        reasons.append("construction-not-completed-and-supporting")
    if record["execution_digest"] is None or observation.acceptance == "not-claimed":
        reasons.append("construction-acceptance-unqualified")
    return {
        "observation": ref.model_dump(),
        "bundle_digest": bundle_record["digest"],
        "bundle_status": bundle_record["status"],
        "inventory": inventory,
    }, reasons


def _inheritance_guard(discovery: Any, assessment: dict[str, Any], cx: Any) -> None:
    terms = SearchAssessment.model_validate(assessment["spec"])
    _, sub = _submission(discovery, terms.submission, cx)
    _, freeze = _freeze(discovery, sub.search_id, cx)
    _review_inventory(discovery, terms, cx)
    if assessment["disposition"] == "bounded-discovery-candidate":
        accounting = _search_accounting(discovery, sub, freeze, cx)
        _, reasons = _construction_state(discovery, terms.construction_observation, sub, cx)
        if accounting["reasons"] or reasons:
            raise Conflict("qualified assessment dependencies changed; reassess current costs and full construction")


def apply_insight(discovery: Any, command: Any, cx: Any) -> tuple[str, dict[str, Any]]:
    """Dispatch under Discovery's signed controller, transaction, replay and checkpoint boundary."""
    if command.action == "search-freeze":
        freeze = SearchFreeze.model_validate(command.record)
        now = int(time.time())
        if freeze.information_cutoff > now or any(source.captured_at > now for source in freeze.sources):
            raise ValueError("future evidence or information cutoffs cannot be frozen")
        discovery._evidence([source.evidence for source in freeze.sources], cx)
        _source_bytes(discovery, freeze, cx)
        return discovery._new("search", freeze.search_id, command.expected_head, cx), {
            "spec": freeze.model_dump(),
            "frozen_input_digest": input_digest(freeze),
            "frozen_at": now,
            "temporal_evidence": "journal order; source dates and semantic leakage remain attestations",
        }
    if command.action == "search-submit":
        sub = SearchSubmission.model_validate(command.record)
        freeze_record, freeze = _freeze(discovery, sub.search_id, cx)
        arms = {arm.arm_id: arm for arm in freeze.arms}
        if (
            sub.frozen_input_digest != freeze_record["frozen_input_digest"]
            or sub.arm_id not in arms
            or sub.unit_id not in freeze.search_units
            or not set(sub.source_ids) <= {source.source_id for source in freeze.sources}
        ):
            raise ValueError("search outcome differs from frozen inputs, arm, denominator or sources")
        if any(
            getattr(sub.usage, field) > getattr(arms[sub.arm_id].budget, field) for field in ResourceBudget.model_fields
        ):
            raise ValueError("search outcome exceeds the frozen per-unit budget, including failed attempts")
        if freeze.mode in {"synthetic", "calibrated"} and sub.origin not in {
            "researcher-supplied",
            "synthetic-fixture",
        }:
            raise ValueError("development fixtures cannot be relabeled as actual agent or human search")
        if sub.origin == "human-output" and sub.arm_id != "H" or sub.origin == "agent-output" and sub.arm_id == "H":
            raise ValueError("search output origin differs from its frozen arm")
        discovery._evidence([sub.original_output, *sub.attempt_evidence], cx)
        if sub.opportunity_id is not None:
            discovery._opportunity(sub.opportunity_id, sub.opportunity_spec_digest, cx)
            if not sub.source_ids:
                raise ValueError("candidate search must preserve its frozen source identities")
        if freeze.design == "prospective" and sub.origin in {"agent-output", "human-output"}:
            refs = [sub.original_output, *sub.attempt_evidence]
            if any(
                discovery.journal.latest(ref.journal_key, cx)["revision"] <= freeze_record["revision"] for ref in refs
            ):
                raise ValueError("prospective search outputs and attempts must follow the freeze")
            if sub.opportunity_id is not None:
                first = cx.execute(
                    "SELECT MIN(seq) FROM events WHERE mission=?", (key("opportunity", sub.opportunity_id),)
                ).fetchone()[0]
                if first <= freeze_record["revision"]:
                    raise ValueError("an opportunity known before the freeze is not a prospective discovery")
        for row in cx.execute(
            "SELECT DISTINCT mission FROM events WHERE mission GLOB ?", (PREFIX + "search-submission:*",)
        ):
            prior = SearchSubmission.model_validate(discovery.journal.latest(row[0], cx)["spec"])
            if prior.cost_mission_id == sub.cost_mission_id:
                raise Conflict("search arms and units require distinct original accounting missions")
        return discovery._new(
            "search-submission", slot(sub.search_id, sub.arm_id, sub.unit_id), command.expected_head, cx
        ), {
            "spec": sub.model_dump(),
            "freeze_record_digest": freeze_record["digest"],
            "cost_report_at_submission": discovery.costs.report(sub.cost_mission_id, cx),
            "resource_qualification": _search_accounting(discovery, sub, freeze, cx),
            "performance_claim": "recorded provenance only; no independently verified model performance",
        }
    if command.action == "search-review":
        review = SearchReview.model_validate(command.record)
        _, sub = _submission(discovery, review.submission, cx)
        if sub.status != "candidate":
            raise ValueError("failed or empty search is retained, not scored as a candidate")
        _freeze(discovery, sub.search_id, cx)
        discovery._evidence(review.evidence, cx)
        accepted_reviews = [
            row[0]
            for row in cx.execute(
                "SELECT DISTINCT mission FROM events WHERE mission GLOB ?", (PREFIX + "search-review:*",)
            )
            if SearchReview.model_validate(discovery.journal.latest(row[0], cx)["spec"]).submission == review.submission
        ]
        if len(accepted_reviews) >= MAX_REVIEWS:
            raise ValueError("review inventory reached the frozen representation limit; start a new review protocol")
        return discovery._new("search-review", review.review_id, command.expected_head, cx), {
            "spec": review.model_dump()
        }
    if command.action == "search-assess":
        terms = SearchAssessment.model_validate(command.record)
        _, sub = _submission(discovery, terms.submission, cx)
        _, freeze = _freeze(discovery, sub.search_id, cx)
        _review_inventory(discovery, terms, cx)
        reviews = []
        for ref in terms.reviews:
            record = _read_ref(discovery, ref, cx)
            review = SearchReview.model_validate(record["spec"])
            if ref.journal_key != key("search-review", review.review_id) or review.submission != terms.submission:
                raise ValueError("assessment requires exact reviews of this submission")
            discovery._evidence(review.evidence, cx)
            reviews.append(review)
        reasons = []
        for criterion in freeze.criteria:
            rows = [r for r in reviews if r.dimension == criterion.dimension]
            if not rows or any(r.score < criterion.minimum_score for r in rows):
                reasons.append("unqualified-" + criterion.dimension)
        novelty = [r for r in reviews if r.dimension == "novelty"]
        if not novelty or any(r.prior_art != "not-found-in-bounded-search" for r in novelty):
            reasons.append("prior-art-unresolved-or-established")
        if terms.leakage_audit:
            _read_ref(discovery, terms.leakage_audit, cx)
        if terms.leakage_disposition != "no-known-leakage":
            reasons.append("leakage-not-cleared")
        if sub.origin not in {"agent-output", "human-output"} or freeze.design != "prospective":
            reasons.append("nonprospective-or-supplied")
        construction, construction_reasons = _construction_state(discovery, terms.construction_observation, sub, cx)
        accounting = _search_accounting(discovery, sub, freeze, cx)
        reasons.extend(construction_reasons)
        reasons.extend(accounting["reasons"])
        if not any(r.review_relationship != "same-operator" for r in reviews):
            reasons.append("same-operator-review-only")
        return discovery._new("search-assessment", terms.assessment_id, command.expected_head, cx), {
            "spec": terms.model_dump(),
            "submission_spec": sub.model_dump(),
            "search_input_digest": input_digest(freeze),
            "disposition": "bounded-discovery-candidate" if not reasons else "exploratory",
            "limitations": sorted(set(reasons)),
            "construction": construction,
            "search_accounting": accounting,
            "beyond_human_foresight_established": False,
            "novelty_truth_established": False,
            "commercial_delivery_established": False,
            "operational_alpha": "requires separate execution-derived U/E evidence",
            "retained_alpha": "requires separate fresh E+/E evidence",
        }
    if command.action == "research-seed":
        seed = ResearchSeed.model_validate(command.record)
        assessment = _read_ref(discovery, seed.assessment, cx)
        terms = SearchAssessment.model_validate(assessment["spec"])
        if seed.assessment.journal_key != key("search-assessment", terms.assessment_id):
            raise ValueError("Nova-Seed requires a recorded discovery assessment")
        _inheritance_guard(discovery, assessment, cx)
        _, sub = _submission(discovery, terms.submission, cx)
        if sub.opportunity_id is None:
            raise ValueError("Nova-Seed requires a candidate hypothesis")
        opportunity = discovery._opportunity(sub.opportunity_id, sub.opportunity_spec_digest, cx)
        witness = discovery._witness(seed.witness_id, seed.witness_spec_digest, cx)
        if (
            witness.opportunity_id != sub.opportunity_id
            or witness.opportunity_spec_digest != sub.opportunity_spec_digest
        ):
            raise ValueError("Nova-Seed witness must preserve the assessed opportunity")
        discovery._evidence(seed.rights_evidence, cx)
        old = discovery._read("research-seed", seed.seed_id, cx)
        if command.expected_head != (old["digest"] if old else None) or seed.version != (
            old["spec"]["version"] + 1 if old else 1
        ):
            raise Conflict("Nova-Seed versions require the exact consecutive research head")
        if old and old["opportunity_id"] != sub.opportunity_id:
            raise ValueError("new opportunities require a new seed identity")
        return key("research-seed", seed.seed_id), {
            "spec": seed.model_dump(),
            "opportunity_id": opportunity.opportunity_id,
            "opportunity_spec_digest": sub.opportunity_spec_digest,
            "opportunity": opportunity.model_dump(),
            "assessment_digest": assessment["digest"],
            "claim_disposition": assessment["disposition"],
            "previous_digest": old["digest"] if old else None,
            "commitment": digest("insight-nova-seed-research/v1", seed),
            "commitment_scope": "integrity and recorded provenance, not truth, ownership or financial return",
            "token_created": False,
        }
    plan = ResearchPlan.model_validate(command.record)
    seed_record = _read_ref(discovery, plan.seed, cx)
    seed_spec = ResearchSeed.model_validate(seed_record["spec"])
    if plan.seed.journal_key != key("research-seed", seed_spec.seed_id):
        raise ValueError("FusionPlan requires the exact research Nova-Seed")
    assessment = _read_ref(discovery, seed_spec.assessment, cx)
    assessment_terms = SearchAssessment.model_validate(assessment["spec"])
    _submission(discovery, assessment_terms.submission, cx)
    _inheritance_guard(discovery, assessment, cx)
    discovery._evidence(seed_spec.rights_evidence, cx)
    opportunity = discovery._opportunity(seed_record["opportunity_id"], seed_record["opportunity_spec_digest"], cx)
    bundle_record = discovery._read("bundle", plan.bundle_id, cx)
    if bundle_record is None or digest("discovery-bundle", bundle_record["spec"]) != plan.bundle_spec_digest:
        raise Conflict("FusionPlan experiment bundle changed")
    bundle = ExplorationBundle.model_validate(bundle_record["spec"])
    if bundle.witness_id != seed_spec.witness_id or bundle.witness_spec_digest != seed_spec.witness_spec_digest:
        raise ValueError("FusionPlan must preserve the seed's exact transformation witness")
    discovery._witness(bundle.witness_id, bundle.witness_spec_digest, cx)
    if len(plan.draft_jobs) != len(bundle.steps) or any(
        job.goal != step.question or job.successMetric != step.decisive_check or job.duration != step.seconds_cap
        for job, step in zip(plan.draft_jobs, bundle.steps)
    ):
        raise ValueError("FusionPlan jobs must preserve every experiment question, acceptance and time bound")
    compiled = ascension.compile_plan([job.model_dump() for job in plan.draft_jobs])
    ascension.verify_plan(compiled)
    return discovery._new("research-plan", plan.plan_id, command.expected_head, cx), {
        "spec": plan.model_dump(),
        "fusion_plan": compiled,
        "milestones": [step.model_dump() for step in bundle.steps],
        "purpose": opportunity.purpose.model_dump(),
        "mark_inspection": "research-only; separate existing MARK eligibility and transaction authorization required",
        "draft_bounty_units": "AGIALPHA base units; no funds reserved, promised, minted or transferred",
        "execution_authority": False,
        "listed": False,
    }


def search_report(discovery: Any, identity: str) -> dict[str, Any]:
    """Keep missing, failed and unassessed fixed-denominator outcomes visible."""
    with discovery.journal.transaction() as cx:
        discovery.service._state(cx)
        record, freeze = _freeze(discovery, identity, cx)
        arms = []
        for arm in freeze.arms:
            counts = {"candidate": 0, "failed": 0, "no-candidate": 0, "missing": 0}
            rows = []
            for unit in freeze.search_units:
                row = discovery._read("search-submission", slot(identity, arm.arm_id, unit), cx)
                counts[row["spec"]["status"] if row else "missing"] += 1
                rows.append({"unit": unit, "record_digest": row["digest"] if row else None})
            arms.append({"arm": arm.arm_id, "denominator": len(freeze.search_units), "counts": counts, "slots": rows})
        return {
            "search_id": identity,
            "freeze_digest": record["digest"],
            "mode": freeze.mode,
            "design": freeze.design,
            "arms": arms,
            "human_search": "recorded arm" if any(a.arm_id == "H" for a in freeze.arms) else "unavailable",
            "human_limitation": freeze.human_search_limitation,
            "foresight_claim": "not established; absence from a finite control is not human impossibility",
            "authority_granted": False,
        }
