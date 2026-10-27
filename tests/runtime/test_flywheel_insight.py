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
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import EvidenceRef
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
