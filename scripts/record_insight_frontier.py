# SPDX-License-Identifier: Apache-2.0
"""Replay the research-access candidate through existing signed discovery custody."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.ascension import JobSpec
from alpha_factory_v1.core.runtime.successor.flywheel_access_path import (
    AccessProblem,
    AccessStep,
    check_access,
    construct_access,
)
from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import (
    Arrangement,
    ArrangementScenario,
    Participant,
    ProjectedCost,
    ProjectedReceipt,
    ProjectedRefund,
    assess_arrangement,
)
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import (
    Discovery,
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
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import (
    Enterprise,
    EnterpriseCommand,
    EvidenceRef,
    HumanReference,
    Offering,
    key as enterprise_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge
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
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest, safe_json_loads
from alpha_factory_v1.core.runtime.successor.trust import sign_record
from scripts.record_discovery_flywheel import append, apply, ref

ROOT = Path(__file__).resolve().parents[1]
M = 1_000_000
SOURCES = [
    {
        "id": "ready-pv",
        "url": "https://www.readypv.eu/procedure/",
        "title": "Ready-PV access procedure",
        "summary": "Access involves eligibility, an experimental proposal, technical feasibility and approval. This is an existing access pathway, not evidence that providers lack all coordination.",
    },
    {
        "id": "nist-scope",
        "url": "https://www.nist.gov/nvlap/accreditation-vs-certification",
        "title": "NIST accreditation scope",
        "summary": "Accreditation covers particular methods and parameters. A laboratory's general accreditation cannot substitute for verifying the required measurement scope.",
    },
    {
        "id": "odrl",
        "url": "https://www.w3.org/TR/odrl-model/",
        "title": "W3C ODRL Information Model 2.2",
        "summary": "Permissions, prohibitions, constraints and duties already have a standardized policy representation. Combining declared conditions is established prior art.",
    },
]


def conventional_challenge(root: Path = ROOT) -> dict[str, Any]:
    """Bind the completed conventional challenge without promoting it to discovery evidence."""
    directory = root / "evidence/decisive-frontier-20261027/conventional"
    freeze_raw = (directory / "FREEZE_typecorrected.json").read_bytes()
    freeze = json.loads(freeze_raw)
    result_raw = (directory / "RESULT_typecorrected.json").read_bytes()
    result = json.loads(result_raw)
    source_paths = {
        "source_sha256": "scripts/insight_conventional_challenge.py",
        "candidate_source_sha256": "alpha_factory_v1/core/runtime/successor/flywheel_access_path.py",
    }
    if result["freeze_sha256"] != hashlib.sha256(freeze_raw).hexdigest():
        raise ValueError("conventional result differs from its frozen inputs")
    for field, name in source_paths.items():
        if freeze[field] != hashlib.sha256((root / name).read_bytes()).hexdigest():
            raise ValueError("conventional challenge requires its exact recorded source")
    if result["source_sha256"] != freeze["source_sha256"]:
        raise ValueError("conventional result differs from its recorded comparator")
    summary = {
        name: format(value, ".17g") if isinstance(value, float) else value for name, value in result["summary"].items()
    }
    return {
        "summary": summary,
        "timing_encoding": "Measured process CPU and wall seconds are decimal strings; original JSON bytes remain bound",
        "mode": result["mode"],
        "verdict": result["verdict"],
        "money": result["money"],
        "customer_acceptance": result["customer_acceptance"],
        "authority_granted": result["authority_granted"],
        "freeze_sha256": result["freeze_sha256"],
        "result_sha256": hashlib.sha256(result_raw).hexdigest(),
        "source_sha256": freeze["source_sha256"],
        "scope": "Execution challenge after disclosure; type-corrected same-input confirmation, not a discovery trial",
        "technical_breakthrough_claim": "stopped",
        "discovery_advantage": "untested",
    }


def problem(identity: str = "research-access-origin", family: str = "facility") -> AccessProblem:
    obligations = ["preserve-original-acceptance", "keep-protected-data-local", "verify-method-scope"]
    facts = ["eligible-team", "sample-ready"] if family == "facility" else ["eligible-team", "data-ready"]
    ready = facts[1]
    raw = [
        ("institution-clearance", ["eligible-team"], ["institution-approved"], "required", 0, 600),
        ("access-award", ["eligible-team"], ["resource-allocated"], "documented", 5, 300),
        ("scope-check", ["resource-allocated"], ["method-in-scope"], "documented", 10, 300),
        ("local-adapter", [ready, "institution-approved"], ["safe-input-ready"], "required", 25, 900),
        ("bounded-run", ["method-in-scope", "safe-input-ready"], ["reviewable-outcome"], "required", 40, 900),
        ("external-raw-transfer", [ready], ["reviewable-outcome"], "documented", 1, 60),
        ("ordinary-full-service", [ready], ["reviewable-outcome"], "documented", 900, 1800),
    ]
    return AccessProblem(
        mission_id=identity,
        useful_purpose="Produce a checkable access-plan feasibility packet while preserving original scientific and data obligations",
        starting_facts=facts,
        required_outputs=["reviewable-outcome"],
        obligations=obligations,
        steps=[
            AccessStep(
                step_id=name,
                purpose=name.replace("-", " "),
                requires=requires,
                produces=produces,
                preserves=obligations if name != "external-raw-transfer" else obligations[:1],
                permission=permission,
                permission_basis="Synthetic declarations; no institution or provider approved this example",
                estimated_cost_micro_usd=cost * M,
                duration_seconds=seconds,
            )
            for name, requires, produces, permission, cost, seconds in raw
        ],
        cost_cap_micro_usd=200 * M,
        seconds_cap=6000,
        mode="synthetic",
        limitations="Authored monotone predicates over synthetic facility/data examples; real capacity, rights, wait times and policy interpretation unverified",
    )


def dossier() -> list[dict[str, Any]]:
    return [
        {
            "id": "calibration-cohort",
            "en": "Shared calibration cohorts",
            "fr": "Cohortes d’étalonnage partagées",
            "need": "Small laboratories face lumpy validation expenses",
            "decision": "rejected for this increment",
            "reason": "Proficiency testing and shared laboratory access are established; material-quality and liability evidence is unavailable",
        },
        {
            "id": "heat-access",
            "en": "Reachable cooling refuges",
            "fr": "Refuges frais accessibles",
            "need": "Nominal cooling capacity may be inaccessible to some residents",
            "decision": "rejected for this increment",
            "reason": "A useful deployment needs local health, accessibility, transport and facility evidence beyond this bounded engineering run",
        },
        {
            "id": "usable-research-access",
            "en": "From awarded access to usable research",
            "fr": "De l’accès attribué à une recherche réalisable",
            "need": "Small teams need an executable route across resource, institutional, data and method constraints",
            "decision": "selected for exploratory construction",
            "reason": "Existing access procedures and policy languages are explicit prior art; a finite in-repository composition gap is testable, but novelty and buyer demand remain unestablished",
        },
    ]


def economics(source: EvidenceRef) -> dict[str, Any]:
    values = [1800, 1100, 850, 450]
    costs = {
        "low": {
            "model": 8,
            "tools": 2,
            "execution": 2,
            "verification": 3,
            "retry-correction": 5,
            "packaging": 5,
            "residual-coordination": 25,
            "support": 10,
            "overhead": 20,
        },
        "base": {
            "model": 25,
            "tools": 10,
            "execution": 5,
            "verification": 10,
            "retry-correction": 30,
            "packaging": 20,
            "residual-coordination": 100,
            "support": 25,
            "overhead": 35,
        },
        "high": {
            "model": 80,
            "tools": 25,
            "execution": 15,
            "verification": 35,
            "retry-correction": 120,
            "packaging": 50,
            "residual-coordination": 300,
            "support": 75,
            "overhead": 100,
        },
    }
    policies = []
    for level, components in costs.items():
        for price in (400, 800, 1000, 1200):
            buyers = [i for i, value in enumerate(values) if value >= price]
            participants = [
                Participant(
                    participant_id=f"assumed-buyer-{i}",
                    need=source,
                    outside_option="Human-led development or no purchase; values are unvalidated assumptions",
                    useful_outcome="Checked access-plan feasibility packet, not physical facility access",
                    responsibilities=["Supply permission-cleared facts and accept the scoped packet before payment"],
                    price_cap_micro_usd=values[i] * M,
                    value_hypothesis_micro_usd=values[i] * M,
                    commitment="proposed",
                    commitment_conditions=["No customer or contract observed"],
                    rights_and_failure_terms="Unaccepted draft; failed packets are not invoiced and rescinded acceptance is fully refunded",
                )
                for i in range(4)
            ]
            scenarios = []
            for outcome, weight in (
                ("paid", 600_000),
                ("technical-failure", 200_000),
                ("default", 150_000),
                ("refund", 50_000),
            ):
                receipts = (
                    []
                    if outcome == "technical-failure"
                    else [
                        ProjectedReceipt(
                            projection_id=f"sale-{i}",
                            participant_id=f"assumed-buyer-{i}",
                            amount_micro_usd=price * M,
                            earned_at=2,
                            collected_at=None if outcome == "default" else 3,
                            acceptance_hypothesis="Synthetic acceptance of this exact feasibility offering; never an observed sale",
                        )
                        for i in buyers
                    ]
                )
                refunds = (
                    [
                        ProjectedRefund(
                            refund_id=f"refund-{i}",
                            projection_id=f"sale-{i}",
                            amount_micro_usd=price * M,
                            at=4,
                            reason="Synthetic rescission/full-refund stress",
                        )
                        for i in buyers
                    ]
                    if outcome == "refund"
                    else []
                )
                scenarios.append(
                    ArrangementScenario(
                        scenario_id=outcome,
                        probability_ppm=weight,
                        qualified=outcome != "technical-failure",
                        risk_states={},
                        costs=[
                            ProjectedCost(
                                activity_id="retention-screen",
                                bucket="B",
                                category="assessment",
                                cash_micro_usd=5 * M,
                                opportunity_micro_usd=0,
                                incurred_at=0,
                                paid_at=0,
                                basis="Modeled additional screen rejecting retention; never included in A",
                            )
                        ]
                        + [
                            ProjectedCost(
                                activity_id=f"{i}-{name}",
                                bucket="A",
                                category="delivery",
                                cash_micro_usd=value * M,
                                opportunity_micro_usd=0,
                                incurred_at=0,
                                paid_at=1,
                                basis="Unmeasured production forecast; necessary construction/learning included once; no reusable research premium",
                            )
                            for i in buyers
                            for name, value in components.items()
                        ],
                        receipts=receipts,
                        refunds=refunds,
                        failure_handling="All attempted delivery costs persist; failure earns nothing; defaults provide no working cash; refunds are paid",
                    )
                )
            arrangement = Arrangement(
                arrangement_id=f"access-packet-{level}-{price}",
                version=1,
                offering=source,
                participants=participants,
                scenarios=scenarios,
                state_space_basis="Four common outcomes, not independent customer diversification; conversion falls with assumed value caps",
                financing_basis="Fictional prefunding only, not earned revenue",
                rights_cleared=False,
                rights_basis="Service, supplier, institutional and data permissions require actual verification",
                mode="simulation",
                authority_required="Separate consent, approved resources and commercial terms",
                limitations=[
                    "All demand, costs, acceptance/default/refund rates and willingness to pay are unmeasured",
                    "This is a tested finite price family, not a globally optimal price",
                ],
            )
            assessment = assess_arrangement(arrangement, 10_000 * M, 500 * M)
            assessment["branches"] = [
                {key: value for key, value in branch.items() if key != "timeline"} for branch in assessment["branches"]
            ]
            assessment["timeline_reproduction"] = (
                "Recompute exact time-ordered states from the retained original scenario events with unchanged assess_arrangement"
            )
            policies.append(
                {
                    "cost_case": level,
                    "price_usd": price,
                    "assumed_participants": len(buyers),
                    "components_usd_per_attempt": components,
                    "arrangement": arrangement.model_dump(),
                    "assessment": assessment,
                }
            )
    return {
        "offering": "Checked access-plan feasibility packet",
        "human_development_reference": {
            "basis": "justified scenario estimates, not published service quotes",
            "low": {"hours": 8, "loaded_hourly_usd": 100},
            "base": {"hours": 16, "loaded_hourly_usd": 125},
            "high": {"hours": 32, "loaded_hourly_usd": 150},
            "scope": "Interpret source/permission facts, implement finite composition, adversarial checks and package; infrastructure charges additional and never pass-through revenue",
        },
        "buyer_value_usd": values,
        "buyer_value_evidence": "unvalidated hypothetical avoided development/delay value, separate from human pathway cost",
        "residual_effort_basis": "0.25 / 1 / 3 hours of unresolved customer/supplier fact coordination at an assumed loaded USD100/hour; automated witness checks have no extra manual-review fee",
        "business_cost_scope": {
            "support": "Residual customer corrections and warranty handling; not the automated witness check",
            "overhead": "Allocated acquisition, administration, hosting and required maintenance; no demonstrated unit-cost quote",
            "reserve": "USD500 fictional cash buffer held separately; a reserve is not an expense or revenue",
            "measurement": "All monetary costs here are assumptions; authoring and shared tool bills remain unknown",
        },
        "arrangement_comparison": [
            {
                "id": "existing",
                "name_en": "Human-led existing arrangement",
                "name_fr": "Organisation actuelle dirigée par des humains",
                "cost_range_usd": [800, 2000, 4800],
                "basis": "The scoped development hours/rates above; not a service selling-price quote",
                "accepted_outcome": "Unverified; requires the same source, rights and acceptance checks",
            },
            {
                "id": "technical-only",
                "name_en": "Technical change alone",
                "name_fr": "Changement technique seul",
                "cost_range_usd": None,
                "basis": "Finite planning works, but trustworthy real declarations, supplier coordination and recipient acceptance are not supplied by the checker",
                "accepted_outcome": "Not established; a component's running cost cannot price the complete outcome",
            },
            {
                "id": "coordination-only",
                "name_en": "Commercial coordination alone",
                "name_fr": "Coordination commerciale seule",
                "cost_range_usd": [800, 2000, 4800],
                "basis": "Competent provider-assisted human development, with no assumed automation saving",
                "accepted_outcome": "Unverified; no signed buyer/provider terms",
            },
            {
                "id": "joint",
                "name_en": "Joint arrangement with checked construction",
                "name_fr": "Organisation conjointe avec construction vérifiée",
                "cost_range_usd": [sum(costs[level].values()) for level in ("low", "base", "high")],
                "basis": "The same complete A scenarios, not measured savings; B/C and cash obligations remain separate",
                "accepted_outcome": "Conditional model only; every priced arrangement remains HOLD",
            },
            {
                "id": "conventional-shared",
                "name_en": "Equally capable conventional shared arrangement",
                "name_fr": "Organisation conventionnelle partagée aussi compétente",
                "cost_range_usd": [sum(costs[level].values()) for level in ("low", "base", "high")],
                "basis": "Identical information and cost assumptions; independent finite execution control ties, so no premium or measured cost benefit is attributed to the new checker",
                "accepted_outcome": "Same conditional feasibility and HOLD; real utility and demand untested",
            },
        ],
        "policies": policies,
        "retention": {
            "decision": "no-retention",
            "assessment_B_usd": 5,
            "prospective_retention_B_usd": 150,
            "assumed_saving_per_use_usd": 0,
            "additional_invocation_usd": 5,
            "break_even_uses": None,
            "reason": "No fresh benefit measured. Equal-content ordinary library can tie; invocation would add cost.",
        },
        "optional_C_research_usd": {"low": 0, "base": 100, "high": 500},
        "actual_customer_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "actual_profit_usd": None,
        "profit_claim": "none; scenario contribution is conditional and complete actual research cost is unknown",
    }


def record() -> dict[str, Any]:
    sys.path.insert(0, str(ROOT / "tests/runtime"))
    import test_flywheel_protected as f

    with tempfile.TemporaryDirectory(prefix="insight-frontier-fixture-") as temporary:
        state = f.setup.__wrapped__(Path(temporary))
        now = int(time.time())
        sources = []
        for source in SOURCES:
            body = {
                "url": source["url"],
                "title": source["title"],
                "paraphrase": source["summary"],
                "captured_on": "2026-10-27",
                "scope": "Source-guided session research; publication dates not independently established",
            }
            evidence = append(state, "@insight-source/" + source["id"], body)
            sources.append(
                SearchSource(
                    source_id=source["id"],
                    url=source["url"],
                    title=source["title"],
                    available_at=now,
                    captured_at=now,
                    content_digest=digest("insight-source-snapshot/v1", body),
                    rights="Short paraphrases and links; no customer data",
                    evidence=evidence,
                )
            )
        budget = ResourceBudget(tokens=40_000, tool_actions=30, seconds=3600, cost_cap_micro_usd=50 * M)
        freeze = SearchFreeze(
            search_id="usable-access-search-v1",
            open_brief="Find an unmet need where small organizations possess resources or nominal access but cannot yet realize a valuable outcome. Preserve scientific purpose, data obligations and approval boundaries.",
            information_cutoff=now,
            sources=sources,
            search_units=["candidate-1", "candidate-2", "candidate-3"],
            arms=[
                SearchArm(
                    arm_id=role,
                    model_id="gpt-6-astra",
                    model_configuration_digest=digest(
                        "insight-proposed-model",
                        {"model": "gpt-6-astra", "reasoning": "max", "api": "responses", "not_invoked": True},
                    ),
                    access_and_tools_digest=digest(
                        "insight-proposed-tools", {"sources": [s.source_id for s in sources], "local-checker": True}
                    ),
                    protocol_digest=digest("insight-protocol", {"arm": role, "scope": "planned, no model calls"}),
                    budget=budget,
                    definition="Representative ordinary use must be sampled before a real trial"
                    if role == "U"
                    else "Expert source-grounded alternative formulation; this replay supplies the outputs",
                )
                for role in ("U", "E")
            ],
            criteria=[
                SearchCriterion(
                    dimension=dimension,
                    rubric="0 unsupported, 1 weak, 2 plausible, 3 construction/source-supported, 4 separately confirmed; score does not establish truth",
                    minimum_score=3,
                )
                for dimension in ("novelty", "usefulness", "feasibility", "commercial-plausibility")
            ],
            mode="synthetic",
            design="development",
            human_search_limitation="No human-expert search; no timed human trial",
            leakage_controls="Development replay only: candidates selected during the session before this freeze. Do not call this a protected prospective comparison.",
            ordinary_search_basis="Planned competent ordinary access; U remains missing because no actual ordinary-model search was run",
        )
        frozen = apply(state, "search-freeze", "freeze-access-search", freeze)
        base_problem = problem()
        purpose = Purpose(
            useful_purpose=base_problem.useful_purpose,
            deliverable="Source-bound feasibility packet with conditional milestones and unresolved permission requirements",
            acceptance_criteria=[
                "Preserve every original obligation",
                "Check all returned access-path predicates and budget bounds",
                "Report pending permissions and grant no execution authority",
            ],
            input_semantics="Declared finite predicates with source identities; no inference of institutional approval from an award",
            output_semantics="Conditional research proposal or no-plan result; no actual facility access",
            scope="synthetic-conditional-access/v1",
        )
        case = OpportunityCase(
            existing_approaches=[
                PriorApproach(
                    approach="Ready-PV access procedures; ODRL policies; competent manual constraint planning",
                    already_delivers="Eligibility, proposals and approval procedures; structured permissions and duties",
                    availability_to_recipient="available",
                    remaining_limitation="No measured recipient gap yet; this repository lacked a finite composition witness across these declarations",
                    evidence=[s.evidence for s in sources],
                )
            ],
            unresolved_gap="Nominal access alone does not establish an authorized, scoped and usable end-to-end experiment",
            gap_evidence=[s.evidence for s in sources],
            why_now="Current reasoning/tool APIs and existing digital access procedures make a bounded, inspectable construction inexpensive to attempt; cost advantage remains unmeasured",
            proposed_construction="A finite obligation-preserving access-path checker and separately approved experiment milestones",
            decisive_experiment="Construct paths and refusals, compare an independent permutation control, then test permission-cleared real briefs",
            commercial_mechanism="Sell a scoped feasibility packet when avoided development/delay value covers complete delivery cost",
            falsifying_observation="The best existing provider/process already solves the same problem at no higher total effort, or the packet cannot preserve a material obligation",
            missing_evidence=[
                "Actual recipient need and source policies",
                "External permission correctness",
                "Metered production costs and buyer willingness to pay",
            ],
            novelty_scope="organization",
        )
        opportunity = Opportunity(
            opportunity_id="usable-research-access",
            version=1,
            purpose=purpose,
            needs=[
                Need(
                    need_id="usable-not-nominal-access",
                    beneficiary="Small research teams crossing institutional and provider boundaries",
                    independently_motivated_purpose=purpose.useful_purpose,
                    outside_option="Use provider access personnel and existing proposal processes",
                    evidence=[s.evidence for s in sources],
                    evidence_kind="published",
                    demand_uncertainty="No buyer observation",
                )
            ],
            limiting_assumptions=[
                "A resource allocation is sufficient for an executable, permission-complete experiment"
            ],
            shared_structure_hypothesis="Resource conditions and institutional/data obligations may be composed into a single checkable conditional route",
            formulations=[
                Formulation(
                    formulation_id=identity,
                    approach=approach,
                    material_difference=difference,
                    assumptions=["Identical scientific acceptance and declared facts"],
                    uncertainty="Unmeasured real-world advantage",
                )
                for identity, approach, difference in [
                    ("manual", "Provider-assisted manual planning", "Competent conventional reference"),
                    ("finite", "Construct an obligation-preserving finite path", "Executable checkable artifact"),
                    ("decline", "Use an existing full-service route or decline", "Retain the outside option"),
                ]
            ],
            ingredients=[
                Ingredient(
                    ingredient_id="policy-planning",
                    description="Existing policy representation and finite planning",
                    origin="established-method",
                    evidence=[s.evidence for s in sources],
                    limitations="No new algorithm is claimed",
                )
            ],
            unresolved_questions=case.missing_evidence,
            discovery_case=case,
            mode="simulation",
        )
        apply(state, "opportunity", "register-usable-access", opportunity)
        witness = TransformationWitness(
            witness_id="compose-access-not-waive-obligations",
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            purpose=purpose,
            binding_restriction="An award and an independently suitable tool do not by themselves supply every prerequisite",
            removable_basis="Expose and compose the missing institutional, data and method steps; request approval separately",
            change_kind="coordination",
            replacement="A conditional access path with an explicit unresolved permission set",
            operation_in_original_setting="Preserve the same deliverable and every obligation; no authority is inherited",
            falsifying_observation=case.falsifying_observation,
            formulation_id="finite",
            evidence=[s.evidence for s in sources],
            limitations="Synthetic finite conditions; existing manual planning can tie",
        )
        apply(state, "witness", "record-access-witness", witness)
        bundle = ExplorationBundle(
            bundle_id="access-path-construction",
            witness_id=witness.witness_id,
            witness_spec_digest=digest("discovery-witness", witness),
            steps=[
                ExperimentStep(
                    step_id="construct",
                    question="Construct a finite access path or preserve a justified refusal",
                    proposed_artifact=purpose.deliverable,
                    decisive_check="Every original obligation and declared prerequisite remains satisfied; no authority granted",
                    falsifying_observation=case.falsifying_observation,
                    cost_bucket="A",
                    cost_cap_micro_usd=100 * M,
                    seconds_cap=600,
                )
            ],
            total_cost_cap_micro_usd=100 * M,
            total_seconds_cap=600,
            checkpoint_after=["construct"],
            stopping_conditions=["Unknown costs pause", "Any relaxed obligation falsifies acceptance"],
            joint_value_hypothesis="A useful feasibility packet might connect otherwise unusable resources",
            uncertainty="Need, novelty and commercial success unestablished",
        )
        apply(state, "bundle", "plan-access-construction", bundle)
        result = construct_access(base_problem)
        assert check_access(base_problem, result)
        artifact = append(
            state,
            "@insight-access-artifact",
            {
                "problem": base_problem.model_dump(),
                "result": result,
                "witness_check": True,
                "components": {"computation": "executed-local", "inputs": "synthetic", "permission": "ungranted"},
            },
        )
        f.account(
            state,
            "charge",
            Charge(
                activity_id="access-construction-actual-cost-unknown",
                mission_id="access-construction-actual",
                bucket="A",
                category="model",
                accrued_micro_usd=None,
                paid_micro_usd=0,
                basis="unknown",
                evidence_digest=artifact.record_digest,
                note="Authoring, source work, runtime and complete inference billing were not metered; never substitute modeled cost",
            ).model_dump(),
            "record-access-unknown-cost",
        )
        apply(
            state,
            "observe",
            "access-construction-observation",
            ExperimentObservation(
                bundle_id=bundle.bundle_id,
                step_id="construct",
                interpretation="supports",
                observation="Actual local checker constructs a conditional path, rejects the cheap obligation-violating route and preserves all pending permissions",
                evidence=[artifact],
                artifact=artifact,
                cost_operation="access-construction-actual",
                elapsed_seconds=1,
                limitations="Finite witness only; original monetary costs unknown; no accepted external delivery",
            ),
            Discovery(state["service"]).inspect("bundle", bundle.bundle_id)["digest"],
        )
        output = append(
            state,
            "@insight-session-output",
            {
                "candidate_dossier": dossier(),
                "origin": "source-guided session selection before the development freeze; supplied for replay",
                "not_frontier_trial": True,
            },
        )
        submission = SearchSubmission(
            search_id=freeze.search_id,
            arm_id="E",
            unit_id="candidate-3",
            frozen_input_digest=input_digest(freeze),
            origin="researcher-supplied",
            status="candidate",
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            source_ids=[s.source_id for s in sources],
            original_output=output,
            attempt_evidence=[output],
            usage=ResourceBudget(tokens=1, tool_actions=1, seconds=1, cost_cap_micro_usd=0),
            cost_mission_id="search-replay-E-candidate-3",
            limitations="Usage is a protocol placeholder, not actual model telemetry; monetary cost is unknown",
        )
        produced = apply(state, "search-submit", "submit-access-candidate", submission)
        submission_ref = EvidenceRef(journal_key=produced["id"], record_digest=produced["digest"])
        for index in (1, 2):
            rejected = submission.model_copy(
                update={
                    "unit_id": f"candidate-{index}",
                    "status": "no-candidate",
                    "opportunity_id": None,
                    "opportunity_spec_digest": None,
                    "cost_mission_id": f"search-replay-E-candidate-{index}",
                    "limitations": dossier()[index - 1]["reason"],
                }
            )
            apply(state, "search-submit", f"reject-candidate-{index}", rejected)
        review_refs = []
        for dimension, score in (("novelty", 1), ("usefulness", 2), ("feasibility", 3), ("commercial-plausibility", 1)):
            reviewed = apply(
                state,
                "search-review",
                "review-access-" + dimension,
                SearchReview(
                    review_id="access-" + dimension,
                    submission=submission_ref,
                    reviewer_id="same-session-operator",
                    dimension=dimension,
                    score=score,
                    rationale="Local construction is checkable; prior art is substantial and recipient/commercial evidence is missing",
                    evidence=[artifact, *[s.evidence for s in sources]],
                    review_relationship="same-operator",
                    prior_art="established-approach" if dimension == "novelty" else "unresolved",
                    limitations="Same-operator assessment, not independent truth or customer review",
                ),
            )
            review_refs.append(EvidenceRef(journal_key=reviewed["id"], record_digest=reviewed["digest"]))
        assessed = apply(
            state,
            "search-assess",
            "assess-access-candidate",
            SearchAssessment(
                assessment_id="access-candidate-assessment",
                submission=submission_ref,
                reviews=review_refs,
                construction_observation=ref(state, key("observation", "access-construction-observation")),
                leakage_audit=None,
                leakage_disposition="unassessed",
                limitations="Exploratory development candidate. No measured U/E search, no prospective foresight result, no market validation",
            ),
        )
        seed = ResearchSeed(
            seed_id="usable-access-research-seed",
            version=1,
            assessment=EvidenceRef(journal_key=assessed["id"], record_digest=assessed["digest"]),
            witness_id=witness.witness_id,
            witness_spec_digest=digest("discovery-witness", witness),
            rights_evidence=[artifact],
            rights_statement="Original Apache-2.0 source and synthetic facts; real institutional/data rights unresolved",
            uncertainty="No new discovery or profitable delivery qualified",
            next_experiment="Two permission-cleared real briefs and a credible provider-assisted baseline with complete effort/cost receipts",
        )
        seeded = apply(state, "research-seed", "record-access-seed", seed)
        plan = ResearchPlan(
            plan_id="usable-access-fusion-plan",
            seed=EvidenceRef(journal_key=seeded["id"], record_digest=seeded["digest"]),
            bundle_id=bundle.bundle_id,
            bundle_spec_digest=digest("discovery-bundle", bundle),
            draft_jobs=[
                JobSpec(
                    goal=s.question, successMetric=s.decisive_check, bounty="100", duration=s.seconds_cap, priceWeight=0
                )
                for s in bundle.steps
            ],
            required_permissions=[
                "Separate controller permit",
                "Real institutional and data-owner clearance",
                "Qualified provider access",
            ],
            commercial_assumptions="No buyer, payment or token commitment; 100 AGIALPHA base units per job are inert draft compiler inputs",
        )
        planned = apply(state, "research-plan", "compile-access-fusion-plan", plan)
        offering = Offering(
            offering_id="access-plan-feasibility-packet",
            version=1,
            beneficiary=opportunity.needs[0].beneficiary,
            useful_outcome=purpose.useful_purpose,
            deliverable=purpose.deliverable,
            scope=purpose.scope,
            acceptance_criteria=purpose.acceptance_criteria,
            need_evidence=[s.evidence for s in sources],
            demand_uncertainty="No demand or willingness to pay observed",
            human_reference=HumanReference(
                service="Comparable human-led finite feasibility instrument development",
                source="Unmeasured 16-hour scenario at loaded USD125/hour; no service quote",
                basis="estimated-team-hours",
                team_hours=16,
                hourly_rate_micro_usd=125 * M,
                total_micro_usd=2000 * M,
            ),
            permitted_tools=["local-finite-checker"],
            price_policy="Test USD400/800/1000/1200 against declining hypothetical participation; 1000 is half the illustrative human-led development cost, not an observed service price",
            price_candidates_micro_usd=[400 * M, 800 * M, 1000 * M, 1200 * M],
            capacity=4,
            turnaround_seconds=6000,
            complete_cost_cap_micro_usd=1000 * M,
            risks=["Source/permission interpretation", "No buyer acceptance"],
            operating_limits=["Research only", "No access, authority or settlement"],
            mode="simulation",
        )
        command = EnterpriseCommand(
            journal_identity=state["journal"].identity,
            operation_id="record-access-offering",
            expires_at=int(time.time()) + 3600,
            action="offering",
            expected_head=None,
            record=offering.model_dump(),
        )
        Enterprise(state["service"]).apply(
            sign_record(state["keys"]["controller"], "controller", "flywheel-enterprise-command", command)
        )
        offering_ref = ref(state, enterprise_key("offering", offering.offering_id))
        apply(
            state,
            "link-offering",
            "link-access-offering",
            OfferingLink(
                opportunity_id=opportunity.opportunity_id,
                opportunity_spec_digest=digest("discovery-opportunity", opportunity),
                offering_id=offering.offering_id,
                offering_record_digest=offering_ref.record_digest,
            ),
        )
        fresh = []
        for family in ("facility", "data"):
            fresh_problem = problem("fresh-" + family, family)
            outcome = subprocess.run(
                [sys.executable, "-m", "scripts.record_insight_frontier", "--recipient"],
                cwd=ROOT,
                input=canonical(fresh_problem),
                capture_output=True,
                check=True,
                timeout=30,
            )
            value = safe_json_loads(outcome.stdout)
            assert value["checked"]
            fresh.append(
                {
                    "family": family,
                    "problem": fresh_problem.model_dump(),
                    "recipient": value,
                    "ordinary_library_parity": value["result"] == construct_access(fresh_problem),
                    "scope": "Fresh local process, authored synthetic mission; not authenticated cross-agent skill adoption",
                }
            )
        construction_cases = []
        for case_id in ("origin", "denied", "incomplete"):
            current = base_problem.model_dump()
            if case_id == "denied":
                current["steps"][0]["permission"] = "denied"
            if case_id == "incomplete":
                current["search_node_cap"] = 1
            current = AccessProblem.model_validate(current)
            outcome = construct_access(current)
            construction_cases.append(
                {
                    "case_id": case_id,
                    "problem": current.model_dump(),
                    "result": outcome,
                    "witness_checked": check_access(current, outcome),
                }
            )
        return {
            "schema": "insight-frontier-evidence/v1",
            "construction_cases": construction_cases,
            "candidate_dossier": dossier(),
            "sources": SOURCES,
            "freeze": state["journal"].document(frozen),
            "search_report": search_report(Discovery(state["service"]), freeze.search_id),
            "opportunity": opportunity.model_dump(),
            "witness": witness.model_dump(),
            "bundle": Discovery(state["service"]).inspect("bundle", bundle.bundle_id),
            "construction": {"problem": base_problem.model_dump(), "result": result, "checked": True},
            "assessment": state["journal"].document(assessed),
            "seed": state["journal"].document(seeded),
            "plan": state["journal"].document(planned),
            "economics": economics(offering_ref),
            "offering_id": offering.offering_id,
            "cost_report": state["costs"].report("access-construction-actual"),
            "fresh_local_work": fresh,
            "conventional_challenge": conventional_challenge(),
            "model_calls": 0,
            "model_call_scope": "Controlled experiment API calls only; session authorship and tool use are unmetered and not a frontier-model trial",
            "actual_customer_collections_usd": 0,
            "live_authentication": "not run",
            "next_experiment": seed.next_experiment,
            "source_sha256": {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in (
                    "alpha_factory_v1/core/runtime/successor/flywheel_insight.py",
                    "alpha_factory_v1/core/runtime/successor/flywheel_access_path.py",
                    "scripts/record_insight_frontier.py",
                )
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--recipient", action="store_true")
    args = parser.parse_args()
    if args.recipient:
        spec = AccessProblem.model_validate(safe_json_loads(sys.stdin.buffer.read(120_001)))
        result = construct_access(spec)
        sys.stdout.buffer.write(
            canonical({"result": result, "checked": check_access(spec, result), "authority_granted": False})
        )
        return
    if args.output is None:
        parser.error("choose --output or --recipient")
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError("preserve earlier evidence; choose a new output")
    result = record()
    payload = canonical(result) + b"\n"
    with args.output.open("xb") as stream:
        stream.write(payload)


if __name__ == "__main__":
    main()
