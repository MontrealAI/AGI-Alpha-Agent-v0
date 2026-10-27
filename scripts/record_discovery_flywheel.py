# SPDX-License-Identifier: Apache-2.0
"""Record discovery on existing enterprise seams with explicit fictional resources."""

from __future__ import annotations

import argparse
import hashlib
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import (
    Arrangement,
    ArrangementScenario,
    Participant,
    ProjectedCost,
    ProjectedReceipt,
    assess_arrangement,
    economy_regression_fixture,
)
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import (
    ComparisonArm,
    ComparisonPlan,
    BundleCheckpoint,
    ArrangementRequest,
    Discovery,
    DiscoveryCommand,
    DiscoveryDecision,
    ExperimentObservation,
    ExperimentStep,
    ExplorationBundle,
    Formulation,
    Ingredient,
    Need,
    OfferingLink,
    Opportunity,
    OpportunityCase,
    PriorApproach,
    Purpose,
    ResourceBudget,
    TransformationWitness,
    key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise, EvidenceRef, key as offering_key
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.flywheel_gym import GymTask, evaluate_frozen
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record

ROOT = Path(__file__).resolve().parents[1]
FOUNDATIONS = (
    "docs/Transformational_Intelligence.tex",
    "docs/Invent_the_Economy.tex",
    "docs/papers/transformational-autonomous-enterprises-v1.tex",
)


def ref(state: dict[str, Any], journal_key: str) -> EvidenceRef:
    return EvidenceRef(journal_key=journal_key, record_digest=state["journal"].latest(journal_key)["digest"])


def append(state: dict[str, Any], journal_key: str, value: dict[str, Any]) -> EvidenceRef:
    with state["journal"].transaction() as cx:
        state["service"]._state(cx)
        state["journal"].append(cx, journal_key, value)
        state["service"].checkpoint.advance(state["journal"], cx)
    return ref(state, journal_key)


def apply(state: dict[str, Any], action: str, identity: str, spec: Any, expected: str | None = None) -> dict[str, Any]:
    command = DiscoveryCommand(
        journal_identity=state["journal"].identity,
        operation_id=identity,
        expires_at=int(time.time()) + 3600,
        action=action,
        expected_head=expected,
        record=spec.model_dump() if hasattr(spec, "model_dump") else spec,
    )
    return Discovery(state["service"]).apply(
        sign_record(state["keys"]["controller"], "controller", "flywheel-discovery-command", command.model_dump())
    )


def probe_lineage(state: dict[str, Any]) -> dict[str, Any]:
    from scripts.record_opportunity_probe import candidate_dossier, record as probe_record

    dossier = candidate_dossier()
    artifact = append(
        state,
        "@discovery-information-protocol:v1",
        {
            "candidate_dossier": dossier,
            "source_digests": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in (
                    "alpha_factory_v1/core/runtime/successor/flywheel_probe.py",
                    "alpha_factory_v1/core/runtime/successor/flywheel_execution.py",
                    "tests/runtime/test_flywheel_execution.py",
                    "scripts/record_opportunity_probe.py",
                )
            },
            "freeze_scope": "Source-pinned reproducibility protocol before this replay; released synthetic conformance cases",
            "novelty": "Researcher-selected internal application; no autonomous discovery or protected holdout claim",
        },
    )
    chosen = dossier[0]
    purpose = Purpose(
        useful_purpose=chosen["useful_outcome"],
        deliverable="A scoped information request, finite effect classification or justified refusal",
        acceptance_criteria=[
            "Every remaining declared world supports the reported effect",
            "Missing observations and outside-model evidence never become a resolved effect",
            "No output grants retry, live acceptance or execution authority",
        ],
        input_semantics="Immutable synthetic hypotheses, bounded read contracts and scoped observations",
        output_semantics="Conditional finite-model computation, never an operational effect receipt",
        scope="finite-information-probe/v1",
    )
    case = OpportunityCase(
        existing_approaches=[
            PriorApproach(
                approach=chosen["existing_approaches"],
                already_delivers="Durable execution, idempotent operations and direct audit where provided",
                availability_to_recipient="unknown",
                remaining_limitation=chosen["remaining_gap"],
                evidence=[artifact],
            )
        ],
        unresolved_gap=chosen["remaining_gap"],
        gap_evidence=[artifact],
        why_now=chosen["why_now"],
        proposed_construction=chosen["construction"],
        decisive_experiment=chosen["decisive_experiment"],
        commercial_mechanism=chosen["commercial_mechanism"],
        falsifying_observation=chosen["falsifier"],
        missing_evidence=["Real audit coverage", "External recipient demand", "Complete monetary costs"],
        novelty_scope="organization",
    )
    opportunity = Opportunity(
        opportunity_id=chosen["id"],
        version=1,
        purpose=purpose,
        needs=[
            Need(
                need_id="uncertain-original-effect",
                beneficiary=chosen["beneficiary"],
                independently_motivated_purpose=chosen["useful_outcome"],
                outside_option=chosen["existing_approaches"],
                evidence=[artifact],
                evidence_kind="internal-research",
                demand_uncertainty="No actual buyer or payment observed",
            )
        ],
        limiting_assumptions=["A client acknowledgment log is sufficient to determine a remote effect"],
        shared_structure_hypothesis="Different interrupted operations can share ambiguity-partition machinery",
        formulations=[
            Formulation(
                formulation_id="log-only",
                approach="Inspect the retained client log",
                material_difference="No additional effect observation",
                assumptions=["Same missing acknowledgment"],
                uncertainty="Cannot distinguish the three supplied effect states",
            ),
            Formulation(
                formulation_id="direct-audit",
                approach="Read and interpret an available scoped audit",
                material_difference="Strong conventional reference with identical read access",
                assumptions=["Audit covers the original operation"],
                uncertainty="Real-service coverage unknown",
            ),
            Formulation(
                formulation_id="constructed-probe",
                approach=chosen["construction"],
                material_difference="Construct a distinguishing information request or refuse",
                assumptions=["Finite model and immutable observation contracts"],
                uncertainty="Same-content/direct-audit controls can match; no measured Alpha",
            ),
        ],
        ingredients=[
            Ingredient(
                ingredient_id="finite-model",
                description="Read contracts and effect hypotheses",
                origin="supplied",
                evidence=[artifact],
                limitations="Finite worlds and selection supplied by the researcher",
            )
        ],
        unresolved_questions=case.missing_evidence,
        mode="hybrid",
        discovery_case=case,
    )
    registered = apply(state, "opportunity", "probe-opportunity", opportunity)
    witness = TransformationWitness(
        witness_id="request-missing-information",
        opportunity_id=opportunity.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", opportunity),
        purpose=purpose,
        binding_restriction="All three effects have the same client-visible acknowledgment log",
        removable_basis="An operation-bound audit, if available, separates the supplied effect states",
        change_kind="information",
        replacement=chosen["construction"],
        operation_in_original_setting="Request only a separately permitted read; preserve original effect identity",
        falsifying_observation=chosen["falsifier"],
        formulation_id="constructed-probe",
        evidence=[artifact],
        limitations="Conditional on finite coverage; direct audit matches; not a new recovery algorithm",
    )
    witnessed = apply(state, "witness", "probe-witness", witness)
    bundle = ExplorationBundle(
        bundle_id="finite-probe-construction",
        witness_id=witness.witness_id,
        witness_spec_digest=digest("discovery-witness", witness),
        steps=[
            ExperimentStep(
                step_id="construct-and-check",
                question=chosen["decisive_experiment"],
                proposed_artifact=purpose.deliverable,
                decisive_check=purpose.acceptance_criteria[0],
                falsifying_observation=chosen["falsifier"],
                cost_bucket="C",
                cost_cap_micro_usd=1_000_000,
                seconds_cap=60,
            )
        ],
        total_cost_cap_micro_usd=1_000_000,
        total_seconds_cap=60,
        checkpoint_after=["construct-and-check"],
        stopping_conditions=["Unknown monetary costs", "Unqualified observation coverage", "Missing demand"],
        joint_value_hypothesis="A useful diagnosis service may combine a shared instrument with scoped adapters",
        uncertainty="No monetary bill or outside commercial evidence; no authorization to spend the cap",
    )
    planned = apply(state, "bundle", "probe-bundle", bundle)
    started = time.monotonic()
    report = probe_record()
    elapsed = int(time.monotonic() - started) + 1
    executed_artifact = append(state, "@discovery-information-instrument:v1", report)
    observed = apply(
        state,
        "observe",
        "probe-observation",
        ExperimentObservation(
            bundle_id=bundle.bundle_id,
            step_id="construct-and-check",
            interpretation="inconclusive",
            observation="Local finite classification and refusal checks pass; direct audit matches",
            evidence=[artifact, executed_artifact],
            artifact=executed_artifact,
            cost_operation="probe-unmeasured-rd",
            elapsed_seconds=elapsed,
            limitations="Actual local computation; no frontier call, live effect acceptance or monetary cost seal",
        ),
        planned["digest"],
    )
    stop = apply(
        state,
        "decision",
        "probe-stop",
        DiscoveryDecision(
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            disposition="stop",
            rationale=chosen["decision"],
            evidence=[artifact, executed_artifact],
            uncertainty="Natural coverage, complete costs and external demand remain unestablished",
            next_question="Does a real authorized audit expose adequate operation-specific evidence at useful cost?",
        ),
    )
    return {
        "opportunity": registered,
        "witness": witnessed,
        "bundle": observed,
        "protocol": artifact.model_dump(),
        "artifact": executed_artifact.model_dump(),
        "decision": stop,
        "report": report,
    }


def record() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "tests/runtime"))
    import test_flywheel_enterprise as e
    import test_flywheel_protected as f
    import test_flywheel_specialists as s
    from scripts.record_enterprise_flywheel import record as enterprise_record

    with tempfile.TemporaryDirectory(prefix="discovery-fictional-conformance-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        service = state["service"]
        source = append(
            state,
            "@discovery-foundation-fixture:v1",
            {
                "papers": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in FOUNDATIONS},
                "supplied": "Purpose, finite domain, alternatives, demand and market numbers are researcher supplied",
                "evidence_type": "internal-research-source-register",
            },
        )
        spec = e.offering(state)
        purpose = Purpose(
            useful_purpose=spec.useful_outcome,
            deliverable=spec.deliverable,
            acceptance_criteria=spec.acceptance_criteria,
            input_semantics="Finite hosts, service demands, capacities and correlated failure-domain assignments",
            output_semantics="Minimum feasible replicated placement or independently checked infeasibility",
            scope=spec.scope,
        )
        opportunity = Opportunity(
            opportunity_id="resilience-construction",
            version=1,
            purpose=purpose,
            needs=[
                Need(
                    need_id="internal-placement",
                    beneficiary=spec.beneficiary,
                    independently_motivated_purpose="Avoid capacity violations and same-domain replicas",
                    outside_option="Existing direct exhaustive solver with the identical acceptance checker",
                    evidence=spec.need_evidence,
                    evidence_kind="internal-research",
                    demand_uncertainty="No outside customer, price acceptance or paid job observed",
                )
            ],
            limiting_assumptions=[
                "Cheap replicas can share a failure domain",
                "Every search order has the same work cost",
            ],
            shared_structure_hypothesis="Capacity and correlated-domain restrictions recur across fresh placement needs",
            formulations=[
                Formulation(
                    formulation_id="direct",
                    approach="Direct exhaustive enumeration",
                    material_difference="No retained ordering or pruning",
                    assumptions=["Bounded finite search"],
                    dependencies=["finite-oracle"],
                    uncertainty="May remain the best complete-cost option",
                ),
                Formulation(
                    formulation_id="ordered-pruned",
                    approach="Compose demand ordering and capacity-aware pruning",
                    material_difference="Explore shared search structure while preserving the exact feasible set",
                    assumptions=["Independent exhaustive verification remains unchanged"],
                    dependencies=["finite-oracle"],
                    uncertainty="Established conventional method may tie; overhead can erase savings",
                ),
            ],
            ingredients=[
                Ingredient(
                    ingredient_id="finite-oracle",
                    description="Existing placement checker, task grammar and candidate menu",
                    origin="supplied",
                    evidence=[source],
                    limitations="Provided by researchers; not autonomous discovery",
                )
            ],
            unresolved_questions=[
                "Does complete fresh-work benefit exceed development and transfer costs?",
                "Would an independently motivated buyer pay?",
            ],
            mode="hybrid",
        )
        opportunity_receipt = apply(state, "opportunity", "register-opportunity", opportunity)
        witness = TransformationWitness(
            witness_id="purpose-preserving-search",
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            purpose=purpose,
            binding_restriction="Naive enumeration spends work on capacity-infeasible partial assignments",
            removable_basis="Sound pruning and ordering can alter search work without changing valid outcomes",
            change_kind="workflow",
            replacement="Construct a reusable ordering plus residual-capacity procedure",
            operation_in_original_setting="Run the original inputs and recheck every output with the independent exhaustive oracle",
            falsifying_observation="Any invalid accepted output, or no complete-cost advantage against competent conventional reuse",
            formulation_id="ordered-pruned",
            evidence=[source],
            limitations="Mechanism hypothesis using established methods; not an invention or net Alpha claim",
        )
        witness_receipt = apply(state, "witness", "freeze-witness", witness)
        _, frozen_mission, _, _ = e.execution(state)
        bundle = ExplorationBundle(
            bundle_id="delivery-and-optional-development",
            witness_id=witness.witness_id,
            witness_spec_digest=digest("discovery-witness", witness),
            steps=[
                ExperimentStep(
                    step_id="useful-delivery",
                    question="Does the original exact outcome pass?",
                    proposed_artifact=spec.deliverable,
                    decisive_check="Existing independently signed original-purpose acceptance",
                    falsifying_observation="Original constraints fail",
                    cost_bucket="A",
                    cost_cap_micro_usd=1000,
                    seconds_cap=1800,
                    execution_request_digest=digest("flywheel-execution-request", frozen_mission),
                ),
                ExperimentStep(
                    step_id="optional-gym",
                    question="Can a frozen combination reduce search work on fresh cases?",
                    dependencies=["useful-delivery"],
                    proposed_artifact="Versioned placement workflow and all trial histories",
                    decisive_check="Original independent checker, competent conventional and identical-content controls",
                    falsifying_observation="No full-cost reusable advantage or unsupported fresh semantics",
                    cost_bucket="C",
                    cost_cap_micro_usd=10_000,
                    seconds_cap=60,
                ),
            ],
            total_cost_cap_micro_usd=11_000,
            total_seconds_cap=1860,
            checkpoint_after=["useful-delivery", "optional-gym"],
            stopping_conditions=[
                "Unknown costs pause the package",
                "Budget overrun stops further package work",
                "Failed reusable advantage stops admission",
            ],
            joint_value_hypothesis="Ordering and pruning may help jointly; useful delivery does not require later learning",
            uncertainty="Monetary costs are fictional attestations; actual complete cost remains unknown",
        )
        bundle_receipt = apply(state, "bundle", "freeze-bundle", bundle)
        origin = e.launch(state)
        e.advance(state, "prototype")
        e.accept(state, origin)
        technical = e.advance(state, "technically-qualified")
        offering_link = apply(
            state,
            "link-offering",
            "link-offering",
            OfferingLink(
                opportunity_id=opportunity.opportunity_id,
                opportunity_spec_digest=digest("discovery-opportunity", opportunity),
                offering_id=spec.offering_id,
                offering_record_digest=technical["digest"],
            ),
        )
        first = apply(
            state,
            "observe",
            "observe-delivery",
            ExperimentObservation(
                bundle_id=bundle.bundle_id,
                step_id="useful-delivery",
                interpretation="supports",
                observation="Original finite useful delivery independently accepted; no market acceptance claimed",
                evidence=[ref(state, offering_key("offering", spec.offering_id))],
                artifact=ref(state, operation_key("placement-origin")),
                cost_operation="placement-origin",
                elapsed_seconds=(origin["elapsed_ms"] + 999) // 1000,
                execution_operation="placement-origin",
                acceptance="existing-placement-acceptance",
                limitations="Scripted model; actual local tool result, fictional costs and identities",
            ),
            bundle_receipt["digest"],
        )
        continuing = apply(
            state,
            "checkpoint",
            "continue-after-delivery",
            BundleCheckpoint(
                bundle_id=bundle.bundle_id,
                disposition="continue",
                evidence=[ref(state, key("bundle", bundle.bundle_id))],
                rationale="Original finite result passed; bounded optional research remains worthwhile to inspect",
                stopping_conditions_checked="Fictional cost seal complete and within A budget; no paid job or net Alpha claim",
            ),
            first["digest"],
        )
        service.configure(
            f.signed(
                state,
                "configure",
                "controller",
                {"beta_digest": f.BETA, "policy_digest": f.POLICY},
                "configure-placement",
            )
        )
        frozen = s.campaign(state)
        if frozen["candidate"] is None:
            raise RuntimeError("No candidate; preserve original failed campaign")
        workflow = PlacementWorkflow.model_validate(frozen["candidate"])
        s.seal(state, "placement-extra-rd", "C")
        fresh = evaluate_frozen(
            frozen,
            [
                GymTask(
                    task_id=f"discovery-fresh-{seed}",
                    partition="protected-evaluation",
                    family="changed-topology",
                    problem=s.problem(seed, hosts=5, services=5, tight=True),
                )
                for seed in range(3100, 3112)
            ],
        )
        artifact_ref = append(
            state,
            "@discovery-built-workflow:v1",
            {
                "workflow": workflow.model_dump(),
                "gym": frozen,
                "fresh": fresh,
                "scope": "Actual local workflow search; supplied candidate menu; no model-weight update",
            },
        )
        completed = apply(
            state,
            "observe",
            "observe-development",
            ExperimentObservation(
                bundle_id=bundle.bundle_id,
                step_id="optional-gym",
                interpretation="inconclusive",
                observation="Frozen procedure executes fresh finite tasks; complete frontier-model advantage remains unmeasured",
                evidence=[artifact_ref],
                artifact=artifact_ref,
                cost_operation="placement-extra-rd",
                elapsed_seconds=1,
                limitations="C accounting uses fictional complete conformance attestations, not actual monetary cost",
            ),
            continuing["digest"],
        )
        completed = apply(
            state,
            "checkpoint",
            "close-after-development",
            BundleCheckpoint(
                bundle_id=bundle.bundle_id,
                disposition="continue",
                evidence=[artifact_ref],
                rationale="Both bounded steps recorded; close experiment without granting any further authority",
                stopping_conditions_checked="No complete-cost or market superiority established; further production is withheld",
            ),
            completed["digest"],
        )
        candidate_id = s.retain(state, origin, workflow, "placement-gym")
        admission = s.assess(state, candidate_id)
        assert admission == "rejected"
        _, _, profile, _ = e.execution(state)
        expert_workflow = digest(
            "discovery-expert-workflow", {"procedure": "formulate, execute, independently check, correct"}
        )
        budget = ResourceBudget(tokens=4000, tool_actions=8, seconds=1800, cost_cap_micro_usd=1000)
        comparison = ComparisonPlan(
            comparison_id="operational-alpha-not-run",
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            purpose=purpose,
            human_reference=spec.human_reference,
            arms=[
                ComparisonArm(
                    role=role,
                    model_profile_digest=digest("flywheel-execution-profile", profile),
                    access_and_tools_digest=digest("discovery-tools", profile.tools),
                    resource_budget=budget,
                    workflow_digest=(
                        digest("discovery-ordinary-workflow", {"procedure": "reasonable direct tool use"})
                        if role == "U"
                        else expert_workflow
                    ),
                    retained_capability_digest=candidate_id if role == "E+" else None,
                    starting_capabilities=["Same approved fixture tools and checker; no frontier trial"],
                    baseline_definition="Prospective illustrative configuration, not evidence of representative ordinary frontier use",
                )
                for role in ("U", "E", "E+")
            ],
            ordinary_use_basis="Ordinary-use sampling must be independently justified before live testing",
            fresh_instance_policy="Freeze profiles before protected fresh tasks; include failure, retries and correction",
            complete_cost_policy="Compare E-U and E+-E separately; charge every A/B/C activity once, include user effort",
            evidence=[source],
        )
        comparison_receipt = apply(state, "comparison", "freeze-operational-comparison", comparison)
        arrangement = Arrangement(
            arrangement_id="resilience-uncommitted-assessment",
            version=1,
            offering=ref(state, offering_key("offering", spec.offering_id)),
            capability_digests=[candidate_id],
            dependency_evidence=[artifact_ref],
            participants=[
                Participant(
                    participant_id="unconfirmed-prospective-beneficiary",
                    need=spec.need_evidence[0],
                    outside_option="Use the established conventional solver or decline the offering",
                    useful_outcome=spec.useful_outcome,
                    responsibilities=[
                        "Agree on original requirements, permitted data and payment terms before any offer"
                    ],
                    price_cap_micro_usd=spec.price_candidates_micro_usd[0],
                    value_hypothesis_micro_usd=None,
                    commitment="proposed",
                    commitment_conditions=["No buyer commitment has been obtained"],
                    rights_and_failure_terms="Rights, refunds, support and failure allocation remain unresolved",
                )
            ],
            scenarios=[
                ArrangementScenario(
                    scenario_id="illustrative-delivery",
                    probability_ppm=1_000_000,
                    qualified=True,
                    risk_states={},
                    costs=[
                        ProjectedCost(
                            activity_id="hypothetical-complete-delivery",
                            bucket="A",
                            category="delivery",
                            cash_micro_usd=spec.complete_cost_cap_micro_usd,
                            opportunity_micro_usd=0,
                            incurred_at=0,
                            paid_at=0,
                            basis="Fictional bounded conformance cost, not a complete actual cost forecast",
                        )
                    ],
                    receipts=[
                        ProjectedReceipt(
                            projection_id="unaccepted-price-hypothesis",
                            participant_id="unconfirmed-prospective-beneficiary",
                            amount_micro_usd=spec.price_candidates_micro_usd[0],
                            earned_at=1,
                            collected_at=1,
                            acceptance_hypothesis="Unaccepted illustrative price; not actual acceptance, demand or revenue",
                        )
                    ],
                    failure_handling="Single supplied branch is an incomplete commercial hypothesis; do not offer",
                )
            ],
            state_space_basis="Intentionally incomplete first assessment to expose missing commitments and rights",
            financing_basis="Fictional conformance cash; not earned operating funds",
            rights_cleared=False,
            rights_basis="Commercial and customer-data rights unresolved",
            mode="hybrid",
            authority_required="Separate current production permit, rights, demand, complete costs and resource provisioning",
            limitations=[
                "This arrangement is not a calibrated market forecast",
                "Successful technical qualification does not establish an authorized offering",
            ],
        )
        arrangement_receipt = apply(
            state,
            "arrangement",
            "assess-uncommitted-arrangement",
            ArrangementRequest(
                opportunity_id=opportunity.opportunity_id,
                opportunity_spec_digest=digest("discovery-opportunity", opportunity),
                arrangement=arrangement,
                initial_cash_micro_usd=10_000_000,
                financing_assumption_basis="Fictional seed capital from the synthetic protocol; no bank or customer receipt",
            ),
        )
        stop = apply(
            state,
            "decision",
            "stop-unqualified-claim",
            DiscoveryDecision(
                opportunity_id=opportunity.opportunity_id,
                opportunity_spec_digest=digest("discovery-opportunity", opportunity),
                disposition="stop",
                rationale="Reusable net advantage and market evidence are insufficient; original useful internal delivery remains accepted",
                evidence=[
                    ref(state, key("bundle", bundle.bundle_id)),
                    artifact_ref,
                    ref(state, key("arrangement", arrangement.arrangement_id)),
                ],
                uncertainty="Actual frontier comparisons, complete monetary costs and outside demand remain unmeasured",
                next_question="Acquire approved actual model, budget and rights-cleared demand evidence before a new bounded study",
            ),
        )
        fixture = economy_regression_fixture(source)
        economics = assess_arrangement(fixture, 900_000_000_000)
        insufficient = assess_arrangement(fixture, 600_000_000_000)
        selected_probe_lineage = probe_lineage(state)
        state["journal"].verify()
        connected = {
            "opportunity": opportunity_receipt,
            "witness": witness_receipt,
            "bundle": completed,
            "offering_link": offering_link,
            "original_execution": origin,
            "technical_qualification": technical,
            "constructed_workflow": workflow.model_dump(),
            "fresh_evaluation": fresh,
            "candidate_digest": candidate_id,
            "admission": admission,
            "comparison_plan": comparison_receipt,
            "arrangement": arrangement_receipt,
            "next_decision": stop,
            "accounting_fictional": state["costs"].report(),
        }

    inherited = enterprise_record()
    paths = sorted((ROOT / "alpha_factory_v1/core/runtime").rglob("*.py")) + [
        Path(__file__).resolve(),
        *[ROOT / name for name in FOUNDATIONS],
        ROOT / "scripts/record_enterprise_flywheel.py",
        ROOT / "scripts/record_opportunity_probe.py",
        ROOT / "docs/agent/DISCOVERY_FRONTIER_VERIFICATION.json",
        ROOT / "scripts/record_general_flywheel.py",
        ROOT / "scripts/record_specialist_relay.py",
        ROOT / "tests/test_flywheel_arrangements.py",
        ROOT / "tests/test_flywheel_discovery_ui.py",
        ROOT / "tests/browser/test_flywheel_discovery_browser.py",
        *sorted((ROOT / "tests/runtime").glob("test_flywheel_*.py")),
    ]
    return {
        "schema_name": "discovery-flywheel-evidence/v1",
        "author": {"name": "Vincent Boucher", "title": "President of MONTREAL.AI"},
        "sources": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "summary": {
            "mode": "hybrid",
            "local_components": "executed",
            "discovery": "researcher-supplied finite fixture; no autonomous invention",
            "actual_frontier_calls": 0,
            "actual_customer_collections_micro_usd": 0,
            "complete_actual_cost": "unknown",
            "actual_profit": "not established",
            "operational_alpha_comparison": "frozen example plan; not run",
            "admission": "rejected",
            "next_action": "stop",
            "live_qualified": False,
            "authority_inherited": False,
        },
        "lineage": [
            {
                "stage": "Opportunity",
                "status": "signed hypothesis",
                "evidence": "Original purpose and supplied ingredients recorded",
                "limitation": "Internal synthetic needs; no external demand",
            },
            {
                "stage": "Transformation",
                "status": "purpose preserved",
                "evidence": "Exact original requirements plus removable restriction and falsifier",
                "limitation": "Established ordering/pruning; no invention claim",
            },
            {
                "stage": "Construction and delivery",
                "status": "executed locally",
                "evidence": "Existing executor, independent finite acceptance and optional Gym",
                "limitation": "Scripted model; fictional identity and monetary attestations",
            },
            {
                "stage": "Commercial arrangement",
                "status": "separate modeled regression",
                "evidence": "Paper fixture: 300000 success, 120000 expected, 900000 prefunding",
                "limitation": "Supplied hypothetical coalition; no customer or revenue",
            },
            {
                "stage": "Retention and successor",
                "status": "rejected; stop",
                "evidence": "Actual candidate assessed; no net Alpha established",
                "limitation": "Separate positive relay is fictional conformance only",
            },
        ],
        "connected": connected,
        "discovery_selected_prototype": selected_probe_lineage,
        "economy_regression": {
            "arrangement": fixture.model_dump(),
            "adequate_cash": economics,
            "insufficient_cash": insufficient,
            "separate_from_placement_lineage": True,
        },
        "protected_peer_conformance": inherited["positive_protocol_only"],
        "preserved_fair_alternatives": inherited["technical_path"]["composition"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("preserve prior evidence; choose a new output")
    value = record()
    with args.output.open("xb") as stream:
        stream.write(canonical(value) + b"\n")
