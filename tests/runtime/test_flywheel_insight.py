# SPDX-License-Identifier: Apache-2.0
"""Adversarial discovery provenance and independent finite construction controls."""

from __future__ import annotations

import itertools
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_access_path import AccessProblem, check_access, construct_access
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import Discovery, ResourceBudget
from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import key
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY
from alpha_factory_v1.core.runtime.successor.flywheel_insight import (
    ResearchPlan,
    ResearchSeed,
    SearchArm,
    SearchAssessment,
    SearchCriterion,
    SearchFreeze,
    SearchReview,
    SearchSource,
    SearchSubmission,
    input_digest,
    search_report,
)
from alpha_factory_v1.core.runtime.successor.protocol import digest
from scripts.record_discovery_flywheel import append
from scripts.record_insight_frontier import problem, record
import test_flywheel_discovery as d
import test_flywheel_protected as f
import test_flywheel_enterprise as e
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def freeze(state: dict[str, Any], *, prospective: bool = False, identity: str = "test-search") -> SearchFreeze:
    source_ref = d.evidence(state)
    source = state["journal"].document(state["journal"].latest(source_ref.journal_key))
    return SearchFreeze(
        search_id=identity,
        open_brief="Find a consequential need not already specified as an application",
        information_cutoff=int(time.time()),
        sources=[
            SearchSource(
                source_id="public-source",
                url="https://example.org/source",
                title="Fictional source",
                available_at=1,
                captured_at=1,
                content_digest=digest("insight-source-snapshot/v1", source),
                rights="Fixture only",
                evidence=source_ref,
            )
        ],
        search_units=["one", "two"],
        arms=[
            SearchArm(
                arm_id=role,
                model_id="fixture-no-model-call",
                model_configuration_digest="a" * 64,
                access_and_tools_digest="b" * 64,
                protocol_digest=digest("test-protocol", role),
                budget=ResourceBudget(tokens=100, tool_actions=10, seconds=60, cost_cap_micro_usd=100),
                definition="Competent ordinary fixture" if role == "U" else "Expert fixture",
            )
            for role in ("U", "E")
        ],
        criteria=[
            SearchCriterion(dimension=name, rubric="Declared source-supported 0 to 4 rubric", minimum_score=3)
            for name in ("novelty", "usefulness", "feasibility", "commercial-plausibility")
        ],
        mode="live" if prospective else "synthetic",
        design="prospective" if prospective else "development",
        human_search_limitation="No human arm",
        leakage_controls="Test controls only, no independent semantic audit",
        ordinary_search_basis="No intentionally weakened comparator",
    )


def apply(state: dict[str, Any], action: str, terms: Any, identity: str, expected: str | None = None) -> dict[str, Any]:
    return Discovery(state["service"]).apply(d.command(state, action, terms, identity, expected))


def submission(state: dict[str, Any], protocol: SearchFreeze, *, origin: str = "synthetic-fixture") -> SearchSubmission:
    spec = d.opportunity(state, "test-candidate")
    d.register(state, spec)
    output = append(state, "@test-search-output", {"hypothesis": "Supplied test candidate", "fixture": True})
    return SearchSubmission(
        search_id=protocol.search_id,
        arm_id="E",
        unit_id="one",
        frozen_input_digest=input_digest(protocol),
        origin=origin,
        status="candidate",
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        source_ids=["public-source"],
        original_output=output,
        attempt_evidence=[output],
        usage=ResourceBudget(tokens=1, tool_actions=1, seconds=1, cost_cap_micro_usd=0),
        cost_mission_id="test-search-cost",
        limitations="No real model, frontier performance, money or identity",
    )


@pytest.mark.parametrize(
    "mutation", ["budget", "model", "tools", "units", "sources", "criteria", "cutoff", "prospective-fixture"]
)
def test_freeze_rejects_unmatched_or_leaked_protocol(setup: dict[str, Any], mutation: str) -> None:
    raw = freeze(setup).model_dump()
    if mutation == "budget":
        raw["arms"][0]["budget"]["tokens"] += 1
    elif mutation == "model":
        raw["arms"][0]["model_id"] = "different-model"
    elif mutation == "tools":
        raw["arms"][0]["access_and_tools_digest"] = "c" * 64
    elif mutation == "units":
        raw["search_units"][1] = "one"
    elif mutation == "sources":
        raw["sources"].append(raw["sources"][0])
    elif mutation == "criteria":
        raw["criteria"][0]["dimension"] = "usefulness"
    elif mutation == "cutoff":
        raw["sources"][0]["available_at"] = raw["information_cutoff"] + 1
    else:
        raw["design"] = "prospective"
    with pytest.raises(ValueError):
        SearchFreeze.model_validate(raw)


def test_exact_source_bytes_and_immutable_freeze(setup: dict[str, Any]) -> None:
    state = setup
    protocol = freeze(state)
    bad = protocol.model_dump()
    bad["sources"][0]["content_digest"] = "0" * 64
    with pytest.raises(ValueError, match="snapshot"):
        apply(state, "search-freeze", bad, "bad-source")
    apply(state, "search-freeze", protocol, "freeze")
    with pytest.raises(Conflict):
        apply(state, "search-freeze", protocol, "refreeze")
    changed = protocol.model_copy(update={"search_id": "future", "information_cutoff": int(time.time()) + 3600})
    with pytest.raises(ValueError, match="future"):
        apply(state, "search-freeze", changed, "future-freeze")


@pytest.mark.parametrize("mutation", ["input", "unit", "source", "usage", "origin", "no-source"])
def test_submission_preserves_frozen_provenance(setup: dict[str, Any], mutation: str) -> None:
    state = setup
    protocol = freeze(state)
    apply(state, "search-freeze", protocol, "freeze")
    raw = submission(state, protocol).model_dump()
    if mutation == "input":
        raw["frozen_input_digest"] = "0" * 64
    elif mutation == "unit":
        raw["unit_id"] = "new-denominator"
    elif mutation == "source":
        raw["source_ids"] = ["later-outcome"]
    elif mutation == "usage":
        raw["usage"]["tool_actions"] = 1000
    elif mutation == "origin":
        raw["origin"] = "agent-output"
    else:
        raw["source_ids"] = []
    before = state["journal"].verify()
    with pytest.raises(ValueError):
        apply(state, "search-submit", raw, "attempt")
    assert state["journal"].verify() == before


def test_fixed_denominator_missing_failure_and_cost_alias(setup: dict[str, Any]) -> None:
    state = setup
    protocol = freeze(state)
    apply(state, "search-freeze", protocol, "freeze")
    terms = submission(state, protocol)
    result = apply(state, "search-submit", terms, "submit")
    signed = d.command(state, "search-submit", terms, "submit")
    with pytest.raises(Conflict):
        Discovery(state["service"]).apply(signed)
    failed = terms.model_copy(
        update={"unit_id": "two", "status": "failed", "opportunity_id": None, "opportunity_spec_digest": None}
    )
    with pytest.raises(Conflict, match="accounting"):
        apply(state, "search-submit", failed, "aliased-cost")
    failed = failed.model_copy(update={"cost_mission_id": "other-attempt-cost"})
    apply(state, "search-submit", failed, "failed-attempt")
    report = search_report(Discovery(state["service"]), protocol.search_id)
    assert report["arms"][0]["denominator"] == 2 and report["arms"][0]["counts"]["missing"] == 2
    assert report["arms"][1]["counts"] == {"candidate": 1, "failed": 1, "no-candidate": 0, "missing": 0}
    assert report["human_search"] == "unavailable" and not report["authority_granted"]
    assert not result["cost_report_at_submission"]["bucket_complete"]["A"]


def test_old_output_or_known_opportunity_cannot_be_prospective(setup: dict[str, Any]) -> None:
    state = setup
    protocol = freeze(state, prospective=True)
    terms = submission(state, protocol, origin="agent-output")
    apply(state, "search-freeze", protocol, "freeze")
    with pytest.raises(ValueError, match="follow the freeze"):
        apply(state, "search-submit", terms, "old-output")
    output = append(state, "@fresh-output", {"fixture": True})
    terms = terms.model_copy(update={"original_output": output, "attempt_evidence": [output]})
    with pytest.raises(ValueError, match="known before"):
        apply(state, "search-submit", terms, "old-opportunity")


def test_stale_sources_and_roles_refuse(setup: dict[str, Any]) -> None:
    state = setup
    protocol = freeze(state)
    with pytest.raises(ValueError):
        Discovery(state["service"]).apply(
            d.command(state, "search-freeze", protocol, "wrong-role", principal="producer")
        )
    apply(state, "search-freeze", protocol, "freeze")
    terms = submission(state, protocol)
    append(state, protocol.sources[0].evidence.journal_key, {"changed": True})
    with pytest.raises(Conflict):
        apply(state, "search-submit", terms, "stale-source")


def test_high_subjective_scores_never_turn_fixtures_into_foresight(setup: dict[str, Any]) -> None:
    state = setup
    protocol = freeze(state)
    apply(state, "search-freeze", protocol, "freeze")
    result = apply(state, "search-submit", submission(state, protocol), "submit")
    ref = EvidenceRef(journal_key=result["id"], record_digest=result["digest"])
    source = protocol.sources[0].evidence
    reviews = []
    for dimension in ("novelty", "usefulness", "feasibility", "commercial-plausibility"):
        row = apply(
            state,
            "search-review",
            SearchReview(
                review_id=dimension,
                submission=ref,
                reviewer_id="same-reviewer",
                dimension=dimension,
                score=4,
                rationale="Correlated opinion is not independent proof",
                evidence=[source],
                review_relationship="same-operator",
                prior_art="not-found-in-bounded-search",
                limitations="Fixture only",
            ),
            "review-" + dimension,
        )
        reviews.append(EvidenceRef(journal_key=row["id"], record_digest=row["digest"]))
    assessed = apply(
        state,
        "search-assess",
        SearchAssessment(
            assessment_id="assess",
            submission=ref,
            reviews=reviews,
            construction_observation=None,
            leakage_audit=None,
            leakage_disposition="unassessed",
            limitations="No construction or prospective output",
        ),
        "assessment",
    )
    assert assessed["disposition"] == "exploratory"
    assert {
        "nonprospective-or-supplied",
        "no-linked-construction",
        "same-operator-review-only",
        "leakage-not-cleared",
    } <= set(assessed["limitations"])
    assert not assessed["beyond_human_foresight_established"] and not assessed["commercial_delivery_established"]


@pytest.mark.parametrize("family", ["facility", "data"])
def test_access_witness_matches_independent_permutation_control(family: str) -> None:
    spec = problem("fresh-" + family, family)
    result = construct_access(spec)
    choices = []
    for length in range(len(spec.steps) + 1):
        for candidate in itertools.permutations(spec.steps, length):
            facts, cost, seconds, pending = set(spec.starting_facts), 0, 0, 0
            for step in candidate:
                if (
                    step.permission == "denied"
                    or not set(step.requires) <= facts
                    or not set(spec.obligations) <= set(step.preserves)
                ):
                    break
                facts.update(step.produces)
                cost += step.estimated_cost_micro_usd
                seconds += step.duration_seconds
                pending += step.permission == "required"
            else:
                if (
                    set(spec.required_outputs) <= facts
                    and cost <= spec.cost_cap_micro_usd
                    and seconds <= spec.seconds_cap
                ):
                    choices.append((pending, cost, seconds, tuple(s.step_id for s in candidate)))
    expected = min(choices)
    assert (
        len(result["pending_permissions"]),
        result["estimated_cost_micro_usd"],
        result["duration_seconds"],
        tuple(s["step_id"] for s in result["steps"]),
    ) == expected
    assert result["status"] == "conditional-plan" and check_access(spec, result)
    assert "external-raw-transfer" not in [s["step_id"] for s in result["steps"]]


@pytest.mark.parametrize(
    "mutation", ["authority", "mode", "mission", "cost", "pending", "obligation", "acceptance", "steps"]
)
def test_forged_access_results_refuse(mutation: str) -> None:
    spec = problem()
    result = construct_access(spec)
    if mutation == "authority":
        result["authority_granted"] = True
    elif mutation == "mode":
        result["mode"] = "live"
    elif mutation == "mission":
        result["mission_id"] = "unrelated"
    elif mutation == "cost":
        result["estimated_cost_micro_usd"] = 0
    elif mutation == "pending":
        result["pending_permissions"] = []
    elif mutation == "obligation":
        result["preserved_obligations"] = []
    elif mutation == "acceptance":
        result["customer_acceptance"] = True
    else:
        result["steps"] = []
    assert not check_access(spec, result)


def test_denied_unknown_and_incomplete_access_never_become_authority() -> None:
    spec = problem()
    denied = spec.model_dump()
    denied["steps"][0]["permission"] = "denied"
    assert construct_access(AccessProblem.model_validate(denied))["status"] == "no-plan"
    result = construct_access(spec.model_copy(update={"search_node_cap": 1}))
    assert result["status"] == "incomplete" and not check_access(spec, result)
    assert not result["authority_granted"]


def test_connected_replay_preserves_seed_plan_costs_and_exploratory_claim() -> None:
    value = record()
    assert value["construction"]["checked"] and value["assessment"]["disposition"] == "exploratory"
    assert value["bundle"]["status"] == "paused-uncertain"
    assert value["seed"]["opportunity_id"] == value["opportunity"]["opportunity_id"]
    assert (
        not value["seed"]["token_created"] and not value["plan"]["listed"] and not value["plan"]["execution_authority"]
    )
    assert value["plan"]["fusion_plan"]["schema"] == "agialpha.ascension.fusion-plan.v1"
    assert (
        value["economics"]["actual_complete_cost_usd"] is None
        and value["economics"]["actual_customer_collections_usd"] == 0
    )
    assert value["economics"]["retention"]["decision"] == "no-retention"
    assert len(value["economics"]["policies"]) == 12
    assert all(row["ordinary_library_parity"] and row["recipient"]["checked"] for row in value["fresh_local_work"])


def seed_and_plan(state: dict[str, Any]) -> tuple[Any, Any, Any]:
    from alpha_factory_v1.core.runtime.ascension import JobSpec

    protocol = freeze(state)
    apply(state, "search-freeze", protocol, "freeze")
    sub = submission(state, protocol)
    submitted = apply(state, "search-submit", sub, "submit")
    sub_ref = EvidenceRef(journal_key=submitted["id"], record_digest=submitted["digest"])
    assessed = apply(
        state,
        "search-assess",
        SearchAssessment(
            assessment_id="assessment",
            submission=sub_ref,
            reviews=[],
            construction_observation=None,
            leakage_audit=None,
            leakage_disposition="unassessed",
            limitations="Exploratory fixture",
        ),
        "assess",
    )
    candidate = d.opportunity(state, "test-candidate")
    witness = d.witness(state, candidate)
    apply(state, "witness", witness, "witness")
    seed = ResearchSeed(
        seed_id="test-seed",
        version=1,
        assessment=EvidenceRef(journal_key=assessed["id"], record_digest=assessed["digest"]),
        witness_id=witness.witness_id,
        witness_spec_digest=digest("discovery-witness", witness),
        rights_evidence=[protocol.sources[0].evidence],
        rights_statement="Synthetic Apache-2.0 facts only",
        uncertainty="No verified discovery or market",
        next_experiment="Permission-cleared fresh briefs",
    )
    seeded = apply(state, "research-seed", seed, "seed")
    bundle = d.bundle(state).model_copy(update={"witness_spec_digest": digest("discovery-witness", witness)})
    apply(state, "bundle", bundle, "bundle")
    plan = ResearchPlan(
        plan_id="test-plan",
        seed=EvidenceRef(journal_key=seeded["id"], record_digest=seeded["digest"]),
        bundle_id=bundle.bundle_id,
        bundle_spec_digest=digest("discovery-bundle", bundle),
        draft_jobs=[
            JobSpec(
                goal=step.question,
                successMetric=step.decisive_check,
                duration=step.seconds_cap,
                bounty="100",
                priceWeight=0,
            )
            for step in bundle.steps
        ],
        required_permissions=["Separate live approval"],
        commercial_assumptions="No financial commitment",
    )
    return seed, seeded, plan


@pytest.mark.parametrize("field", ["goal", "successMetric", "duration"])
def test_fusion_plan_never_weakens_original_milestones(setup: dict[str, Any], field: str) -> None:
    _, _, plan = seed_and_plan(setup)
    raw = plan.model_dump()
    raw["draft_jobs"][0][field] = 1 if field == "duration" else "An easier substitute"
    with pytest.raises(ValueError, match="preserve every experiment"):
        apply(setup, "research-plan", raw, "altered-plan")
    result = apply(setup, "research-plan", plan, "correct-plan")
    assert not result["execution_authority"] and not result["listed"]


def test_seed_versions_and_late_adverse_review_invalidate_new_plans(setup: dict[str, Any]) -> None:
    state = setup
    seed, seeded, plan = seed_and_plan(state)
    with pytest.raises(Conflict):
        apply(state, "research-seed", seed, "duplicate-version")
    apply(state, "research-seed", seed.model_copy(update={"version": 2}), "seed-v2", seeded["digest"])
    with pytest.raises(Conflict):
        apply(state, "research-plan", plan, "stale-seed-plan")
    assessment = state["journal"].latest(seed.assessment.journal_key)
    terms = SearchAssessment.model_validate(assessment["spec"])
    added = apply(
        state,
        "search-review",
        SearchReview(
            review_id="late-adverse",
            submission=terms.submission,
            reviewer_id="later-reviewer",
            dimension="novelty",
            score=0,
            rationale="Established prior art",
            evidence=seed.rights_evidence,
            review_relationship="same-operator",
            prior_art="established-approach",
            limitations="Fixture",
        ),
        "late-adverse-review",
    )
    assert added["spec"]["score"] == 0
    current = Discovery(state["service"]).inspect("research-seed", seed.seed_id)
    with pytest.raises(Conflict, match="every recorded review"):
        apply(state, "research-seed", seed.model_copy(update={"version": 3}), "seed-after-review", current["digest"])
    with pytest.raises(Conflict, match="every recorded review"):
        apply(state, "search-assess", terms.model_copy(update={"assessment_id": "cherry-picked"}), "cherry-picked")


def cost(
    state: dict[str, Any], mission: str, amount: int | None, identity: str = "search-model", bucket: str = "A"
) -> None:
    f.account(
        state,
        "charge",
        Charge(
            activity_id=identity,
            mission_id=mission,
            bucket=bucket,
            category="model",
            accrued_micro_usd=amount,
            paid_micro_usd=0,
            basis="unknown" if amount is None else "attested",
            evidence_digest=f.ZERO,
            note="Fictional resource reconciliation control",
        ).model_dump(),
        "charge-" + identity,
    )


@pytest.mark.parametrize(
    "amount,declared,expected",
    [
        (150, 0, "search-ledger-budget-overrun"),
        (50, 0, "search-declared-cost-understates-ledger"),
        (None, 0, "search-costs-incomplete"),
        (50, 50, None),
    ],
)
def test_search_accounting_uses_actual_known_cost_and_preserves_unknowns(
    setup: dict[str, Any], amount: int | None, declared: int, expected: str | None
) -> None:
    state = setup
    protocol = freeze(state)
    apply(state, "search-freeze", protocol, "freeze")
    sub = submission(state, protocol)
    sub = sub.model_copy(update={"usage": sub.usage.model_copy(update={"cost_cap_micro_usd": declared})})
    cost(state, sub.cost_mission_id, amount)
    if amount is not None:
        s.seal(state, sub.cost_mission_id, "A")
    recorded = apply(state, "search-submit", sub, "submit")
    qualification = recorded["resource_qualification"]
    assert qualification["eligible"] is (expected is None)
    if expected is not None:
        assert expected in qualification["reasons"]
    terms = SearchAssessment(
        assessment_id="cost-assessment",
        submission=EvidenceRef(journal_key=recorded["id"], record_digest=recorded["digest"]),
        reviews=[],
        construction_observation=None,
        leakage_audit=None,
        leakage_disposition="unassessed",
        limitations="No performance claim",
    )
    assessed = apply(state, "search-assess", terms, "assess")
    if expected is not None:
        assert expected in assessed["limitations"]
    if amount is None:
        raw = next(row for row in state["costs"].snapshot()["charges"].values() if row["activity_id"] == "search-model")
        fields = {name: raw[name] for name in Charge.model_fields if name in raw}
        fields.update(accrued_micro_usd=150, basis="attested")
        f.account(state, "resolve", fields, "resolve-search")
        s.seal(state, sub.cost_mission_id, "A")
        updated = apply(state, "search-assess", terms.model_copy(update={"assessment_id": "reconciled"}), "reassess")
        assert "search-ledger-budget-overrun" in updated["limitations"]
        assert updated["search_accounting"]["report"]["complete"] is True


def constructed_assessment(state: dict[str, Any], last: str, search_cost: int = 50) -> tuple[Any, Any, Any, Any]:
    protocol = freeze(state, prospective=True)
    apply(state, "search-freeze", protocol, "freeze")
    sub = submission(state, protocol, origin="agent-output")
    sub = sub.model_copy(update={"usage": sub.usage.model_copy(update={"cost_cap_micro_usd": 50})})
    cost(state, sub.cost_mission_id, search_cost)
    s.seal(state, sub.cost_mission_id, "A")
    submitted = apply(state, "search-submit", sub, "submit")
    sub_ref = EvidenceRef(journal_key=submitted["id"], record_digest=submitted["digest"])
    execution = e.launch(state)
    e.accept(state, execution)
    candidate = d.opportunity(state, "test-candidate")
    witness = d.witness(state, candidate)
    apply(state, "witness", witness, "witness")
    bundle = d.bundle(state, mission=e.execution(state)[1], bucket="A").model_copy(
        update={"witness_spec_digest": digest("discovery-witness", witness)}
    )
    started = apply(state, "bundle", bundle, "bundle")
    first = d.executed_observation(state, bundle, "placement-origin")
    first.update(interpretation="supports", acceptance="existing-placement-acceptance")
    apply(state, "observe", first, "first-observation", started["digest"])
    continued = d.checkpoint(state, bundle.bundle_id)
    s.seal(state, "arrangement-costs", "C")
    second = d.observation(state, bundle).model_copy(
        update={"step_id": "arrange", "cost_operation": "arrangement-costs", "interpretation": last}
    )
    apply(state, "observe", second, "last-observation", continued["digest"])
    completed = d.checkpoint(state, bundle.bundle_id)
    assert completed["status"] == "completed"
    refs = []
    for dimension in ("novelty", "usefulness", "feasibility", "commercial-plausibility"):
        row = apply(
            state,
            "search-review",
            SearchReview(
                review_id=dimension,
                submission=sub_ref,
                reviewer_id="fixture-reviewer",
                dimension=dimension,
                score=4,
                rationale="Explicit conformance fixture, not a real independent model result",
                evidence=[protocol.sources[0].evidence],
                review_relationship="separate-model",
                prior_art="not-found-in-bounded-search",
                limitations="Fictional protocol inputs grant no live authority",
            ),
            "review-" + dimension,
        )
        refs.append(EvidenceRef(journal_key=row["id"], record_digest=row["digest"]))
    audit = append(state, "@fixture-leakage-audit", {"scope": "Synthetic controller attestation only"})
    observation = state["journal"].latest(key("observation", "first-observation"))
    assessed = apply(
        state,
        "search-assess",
        SearchAssessment(
            assessment_id="constructed-assessment",
            submission=sub_ref,
            reviews=refs,
            construction_observation=EvidenceRef(journal_key=observation["id"], record_digest=observation["digest"]),
            leakage_audit=audit,
            leakage_disposition="no-known-leakage",
            limitations="Protocol-only fixture; no real discovery or independent model performance",
        ),
        "assess",
    )
    return assessed, sub, witness, bundle


@pytest.mark.parametrize("interpretation", ["supports", "falsifies", "inconclusive"])
def test_selected_accepted_observation_cannot_hide_other_bundle_outcomes(
    setup: dict[str, Any], interpretation: str
) -> None:
    assessed, _, _, _ = constructed_assessment(setup, interpretation)
    if interpretation == "supports":
        assert assessed["disposition"] == "bounded-discovery-candidate"
    else:
        assert assessed["disposition"] == "exploratory"
        assert "construction-has-adverse-or-inconclusive-observations" in assessed["limitations"]
    assert len(assessed["construction"]["inventory"]) == 2
    assert not assessed["authority_granted"] and not assessed["beyond_human_foresight_established"]


def test_late_accounting_cannot_inherit_old_qualified_disposition(setup: dict[str, Any]) -> None:
    from alpha_factory_v1.core.runtime.ascension import JobSpec

    state = setup
    assessed, sub, witness, bundle = constructed_assessment(state, "supports")
    evidence = d.evidence(state)
    seed = ResearchSeed(
        seed_id="qualified-fixture-seed",
        version=1,
        assessment=EvidenceRef(journal_key=assessed["id"], record_digest=assessed["digest"]),
        witness_id=witness.witness_id,
        witness_spec_digest=digest("discovery-witness", witness),
        rights_evidence=[evidence],
        rights_statement="Fixture source only",
        uncertainty="No actual discovery or performance",
        next_experiment="Real independent trial",
    )
    seeded = apply(state, "research-seed", seed, "seed")
    cost(state, sub.cost_mission_id, 100, "late-search-cost", "B")
    s.seal(state, sub.cost_mission_id, "B")
    with pytest.raises(Conflict, match="dependencies changed"):
        apply(state, "research-seed", seed.model_copy(update={"version": 2}), "seed-v2", seeded["digest"])
    plan = ResearchPlan(
        plan_id="stale-qualified-plan",
        seed=EvidenceRef(journal_key=seeded["id"], record_digest=seeded["digest"]),
        bundle_id=bundle.bundle_id,
        bundle_spec_digest=digest("discovery-bundle", bundle),
        draft_jobs=[
            JobSpec(
                goal=step.question,
                successMetric=step.decisive_check,
                duration=step.seconds_cap,
                bounty="100",
                priceWeight=0,
            )
            for step in bundle.steps
        ],
        required_permissions=["Separate approval"],
        commercial_assumptions="No commitment",
    )
    with pytest.raises(Conflict, match="dependencies changed"):
        apply(state, "research-plan", plan, "plan")


@pytest.mark.parametrize("boundary", ["assessment", "seed", "plan"])
@pytest.mark.parametrize("revoked", [False, True])
def test_construction_authority_rechecked_at_qualification_boundary(
    setup: dict[str, Any], boundary: str, revoked: bool
) -> None:
    from alpha_factory_v1.core.runtime.ascension import JobSpec

    state = setup
    assessed, _, witness, bundle = constructed_assessment(state, "supports")
    assert assessed["disposition"] == "bounded-discovery-candidate"
    seed = ResearchSeed(
        seed_id="authority-bound-seed",
        version=1,
        assessment=EvidenceRef(journal_key=assessed["id"], record_digest=assessed["digest"]),
        witness_id=witness.witness_id,
        witness_spec_digest=digest("discovery-witness", witness),
        rights_evidence=[d.evidence(state)],
        rights_statement="Fictional source fixture only",
        uncertainty="No real discovery, model performance or current live identity established",
        next_experiment="Separate current authority and independently accepted fresh work",
    )
    terms: Any
    if boundary == "assessment":
        terms = SearchAssessment.model_validate(assessed["spec"]).model_copy(
            update={"assessment_id": "current-authority-assessment"}
        )
        action = "search-assess"
    elif boundary == "seed":
        terms, action = seed, "research-seed"
    else:
        seeded = apply(state, "research-seed", seed, "seed-before-revocation")
        terms = ResearchPlan(
            plan_id="authority-bound-plan",
            seed=EvidenceRef(journal_key=seeded["id"], record_digest=seeded["digest"]),
            bundle_id=bundle.bundle_id,
            bundle_spec_digest=digest("discovery-bundle", bundle),
            draft_jobs=[
                JobSpec(
                    goal=step.question,
                    successMetric=step.decisive_check,
                    duration=step.seconds_cap,
                    bounty="100",
                    priceWeight=0,
                )
                for step in bundle.steps
            ],
            required_permissions=["Separate current authorization; no authority from this fixture"],
            commercial_assumptions="No customer commitment or earned revenue",
        )
        action = "research-plan"
    historical_acceptance = state["journal"].latest(ACCEPTANCE_KEY + "placement-origin")
    before_costs = state["costs"].report()
    if revoked:
        state["trust"].revoke("acceptor")
    before = state["journal"].verify()
    if revoked and boundary != "assessment":
        with pytest.raises(Conflict, match="dependencies changed"):
            apply(state, action, terms, "current-authority-boundary")
        assert state["journal"].verify() == before
    else:
        result = apply(state, action, terms, "current-authority-boundary")
        if boundary == "assessment":
            assert result["disposition"] == ("exploratory" if revoked else "bounded-discovery-candidate")
            assert ("construction-acceptance-currently-ineligible" in result["limitations"]) == revoked
            assert result["construction"]["inventory"][0].get("acceptance_currently_eligible", True) is (not revoked)
        else:
            assert result["spec"] == terms.model_dump()
    assert state["journal"].latest(assessed["id"]) == assessed
    assert state["journal"].latest(historical_acceptance["id"]) == historical_acceptance
    assert state["costs"].report() == before_costs


def test_seventeenth_review_refuses_before_it_can_exceed_assessment_capacity(setup: dict[str, Any]) -> None:
    state = setup
    protocol = freeze(state)
    apply(state, "search-freeze", protocol, "freeze")
    submitted = apply(state, "search-submit", submission(state, protocol), "submit")
    sub_ref = EvidenceRef(journal_key=submitted["id"], record_digest=submitted["digest"])
    refs = []
    for index in range(16):
        terms = SearchReview(
            review_id=f"review-{index}",
            submission=sub_ref,
            reviewer_id=f"reviewer-{index}",
            dimension="novelty",
            score=1,
            rationale="Bounded inventory fixture",
            evidence=[protocol.sources[0].evidence],
            review_relationship="same-operator",
            limitations="No discovery claim",
        )
        row = apply(state, "search-review", terms, f"review-{index}")
        refs.append(EvidenceRef(journal_key=row["id"], record_digest=row["digest"]))
    before = state["journal"].verify()
    with pytest.raises(ValueError, match="inventory reached"):
        apply(state, "search-review", terms.model_copy(update={"review_id": "seventeenth"}), "seventeenth")
    assert state["journal"].verify() == before
    result = apply(
        state,
        "search-assess",
        SearchAssessment(
            assessment_id="all-sixteen",
            submission=sub_ref,
            reviews=refs,
            construction_observation=None,
            leakage_audit=None,
            leakage_disposition="unassessed",
            limitations="Every accepted review retained",
        ),
        "assess",
    )
    assert result["disposition"] == "exploratory"


@pytest.mark.parametrize("amount", [60, 150])
def test_complete_search_cost_contradiction_prevents_stronger_disposition(setup: dict[str, Any], amount: int) -> None:
    assessed, _, _, _ = constructed_assessment(setup, "supports", search_cost=amount)
    assert assessed["disposition"] == "exploratory"
    assert "search-declared-cost-understates-ledger" in assessed["limitations"]
    if amount > 100:
        assert "search-ledger-budget-overrun" in assessed["limitations"]
