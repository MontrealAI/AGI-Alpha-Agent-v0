# SPDX-License-Identifier: Apache-2.0
"""Record one source-backed opportunity and a bounded local construction assay."""

from __future__ import annotations

import hashlib
import math
import time
from pathlib import Path
from typing import Any, Literal

from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge
from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import Arrangement, ArrangementScenario, Participant
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import (
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
    Opportunity,
    OfferingLink,
    Purpose,
    TransformationWitness,
    key as discovery_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import (
    BuyerValueHypothesis,
    Enterprise,
    EnterpriseCommand,
    EvidenceRef,
    OfferingV2,
    key as offering_key,
)
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record
from scripts import experiment_workflow_requalification as workflow

SOURCES = [
    {
        "id": "mcp-tools",
        "url": "https://modelcontextprotocol.io/specification/2026-07-28/server/tools",
        "finding": "Available tools may change and vary with request authorization; input and output schemas describe structure.",
        "boundary": "Protocol documentation is evidence of an integration problem, not observed buyer demand.",
    },
    {
        "id": "pact-consumer",
        "url": "https://docs.pact.io/consumer",
        "finding": "Consumer contract tests should exercise actual consumer expectations; provider functional correctness is separate.",
        "boundary": "Consumer-driven testing is established practice, not a new invention claimed here.",
    },
    {
        "id": "hypothesis",
        "url": "https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html",
        "finding": "Generated inputs can test supplied properties; the chosen property and input domain still bound the result.",
        "boundary": "Finite probes and property tests do not prove arbitrary semantic equivalence.",
    },
    {
        "id": "pandas-migration",
        "url": "https://pandas.pydata.org/docs/whatsnew/v3.0.0.html",
        "finding": "Documented dependency behavior changes motivate checking consumers during migration.",
        "boundary": "This is another candidate need, not an incident or customer project observed in this run.",
    },
]


def _append(state: dict[str, Any], identity: str, value: dict[str, Any]) -> EvidenceRef:
    with state["journal"].transaction() as cx:
        state["service"]._state(cx)
        record = state["journal"].append(cx, identity, value)
        state["service"].checkpoint.advance(state["journal"], cx)
    return EvidenceRef(journal_key=identity, record_digest=record["digest"])


def _apply(
    state: dict[str, Any],
    action: Literal["opportunity", "witness", "bundle", "observe", "decision", "link-offering", "arrangement"],
    identity: str,
    spec: Any,
    expected: str | None = None,
) -> dict[str, Any]:
    terms = DiscoveryCommand(
        journal_identity=state["journal"].identity,
        operation_id=identity,
        expires_at=int(time.time()) + 3600,
        action=action,
        expected_head=expected,
        record=spec.model_dump(),
    )
    signed = sign_record(state["keys"]["controller"], "controller", "flywheel-discovery-command", terms.model_dump())
    return Discovery(state["service"]).apply(signed)


def record_candidate(state: dict[str, Any], source: EvidenceRef) -> dict[str, Any]:
    """Execute internal research; supplied custody roles remain fictional fixtures."""
    from test_flywheel_protected import account

    register = _append(
        state,
        "@workflow-discovery-sources:v1",
        {
            "sources": SOURCES,
            "retrieved_on": "2026-10-27",
            "source_kind": "official-primary-documentation",
            "retrieval": "Pages were opened and read during engineering; this recorder does not fetch or attest remote bytes",
            "foundation": source.model_dump(),
            "actual_external_customer_requests": 0,
        },
    )
    selection = _append(
        state,
        "@workflow-discovery-selection:v1",
        {
            "open_need": "Keep useful inherited workflows dependable when tools, dependencies and mission meaning change",
            "candidates": [
                {
                    "id": "A",
                    "need": "Comparable evaluator requirements across inherited work",
                    "evidence": source.model_dump(),
                    "assessment": "Consequential; broader evaluator-policy work already has an owner",
                },
                {
                    "id": "B",
                    "need": "Dependency migration consumer repair",
                    "source": SOURCES[3]["url"],
                    "assessment": "Consequential; version installation and representative consumer data add scope",
                },
                {
                    "id": "C",
                    "need": "Fresh consumer checks before reusing a tool workflow",
                    "source": SOURCES[0]["url"],
                    "assessment": "Direct fit to current executor and useful inheritance; affordable local falsifier exists",
                },
            ],
            "selected": "C",
            "decision_basis": "Direct recipient fit and additive ownership, not a guaranteed Alpha forecast",
            "supplied": "Researcher chose needs, candidate menu, scoped workflow, checks and drift cases; no autonomous discovery claim",
            "available_alternatives": "Full fresh consumer-contract checks, ordinary same-content library, or stop",
        },
    )
    purpose = Purpose(
        useful_purpose=workflow.PURPOSE,
        deliverable="Actual JSON ticket-duration report and original-purpose checks",
        acceptance_criteria=[
            "Every requested ticket ID is unchanged",
            "Each duration is exact integer milliseconds",
            "Total equals the sum of original durations",
            "Reuse never inherits mission authority",
        ],
        input_semantics="Requested ticket identifiers and original integer durations in milliseconds",
        output_semantics="Per-ticket original durations and exact total; tool prose confers no authority",
        scope="Finite local consumer-contract assay; not a generic semantic detector or an MCP conformance suite",
    )
    need = Need(
        need_id="tool-consumer-freshness",
        beneficiary="Existing workflow recipient and runtime operator",
        independently_motivated_purpose="Preserve correct consumer results after tool changes, independently of selling Alpha",
        outside_option="Run competent full fresh consumer-contract checks and the exact delivered-output checker",
        evidence=[register, selection],
        evidence_kind="published",
        demand_uncertainty="Documentation motivates an internal engineering need; no buyer, price or commitment observed",
    )
    opportunity = Opportunity(
        opportunity_id="workflow-inheritance-after-tool-changes",
        version=1,
        purpose=purpose,
        needs=[need],
        limiting_assumptions=[
            "Schema compatibility alone preserves a consumer's useful purpose",
            "Cached generic qualification can automatically supply fresh permission",
        ],
        shared_structure_hypothesis="Identity, consumer meaning and per-mission authority must remain distinct across tool consumers",
        formulations=[
            Formulation(
                formulation_id=name,
                approach=approach,
                material_difference=difference,
                assumptions=["Original-purpose emitted-output checks remain unchanged"],
                dependencies=["consumer-contract-practice"],
                uncertainty=uncertainty,
            )
            for name, approach, difference, uncertainty in [
                (
                    "schema-only",
                    "Check declared schema and exact final output",
                    "No cached generic qualification",
                    "May be sufficient and cheaper for this complete local-output contract",
                ),
                (
                    "full-contract",
                    "Rerun full consumer checks on each mission",
                    "No generic qualification inheritance",
                    "Strong established alternative may dominate total cost",
                ),
                (
                    "scoped-reuse",
                    "Bind cached qualification, recheck fresh consumer outputs, regrant authority",
                    "Reuse only evaluator-bound identity and scope; same-content ordinary library receives identical treatment",
                    "Two sentinel probes cannot certify arbitrary changes; complete output checks are still required",
                ),
            ]
        ],
        ingredients=[
            Ingredient(
                ingredient_id="consumer-contract-practice",
                description="Pact-style consumer testing and explicit properties",
                origin="established-method",
                evidence=[register],
                limitations="No claim of a new testing method; Pact and Hypothesis are references, not invoked packages",
            ),
            Ingredient(
                ingredient_id="local-workflow",
                description="Researcher-written finite ticket workflow and drift scenarios",
                origin="supplied",
                evidence=[selection, source],
                limitations="Fixtures instantiate the selected need; they do not establish general tool-semantic detection",
            ),
        ],
        unresolved_questions=[
            "Does reuse help after whole workflow and qualification construction costs?",
            "Would any independent recipient pay?",
            "What shifts evade the finite checks?",
        ],
        mode="hybrid",
    )
    opportunity_record = _apply(state, "opportunity", "workflow-opportunity", opportunity)
    witness = TransformationWitness(
        witness_id="workflow-reuse-recheck-regrant",
        opportunity_id=opportunity.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", opportunity),
        purpose=purpose,
        binding_restriction="A retained tool workflow's earlier qualification does not establish current consumer compatibility",
        removable_basis="Stable generic checks can be reused only under exact evaluator-bound identity, while fresh results are checked",
        change_kind="workflow",
        replacement="Separate reusable qualification, exact fresh consumer checks and per-mission grants",
        operation_in_original_setting="Write the original duration report through ToolMissionEnvironment and inspect emitted bytes",
        falsifying_observation="Any accepted incorrect duration, inherited authority, or claimed net advantage erased by complete costs",
        formulation_id="scoped-reuse",
        evidence=[register, selection],
        limitations="Established consumer testing; finite supplied cases, fictional permissions and no proprietary model learning",
    )
    witness_record = _apply(state, "witness", "workflow-witness", witness)
    experiment_source = Path(workflow.__file__).resolve()
    freeze = _append(
        state,
        "@workflow-discovery-prospective-freeze:v1",
        {
            "source_sha256": hashlib.sha256(experiment_source.read_bytes()).hexdigest(),
            "probe_suite_digest": digest("probe-suite", [list(v) for v in workflow.GENERIC]),
            "fresh_inputs": [list(v) for v in workflow.FRESH],
            "arms": list(workflow.ARMS),
            "checker_digest": workflow.checker_digest(),
            "policy": "Freeze precedes execution; strong full fresh and identical-content alternatives are retained",
        },
    )
    bundle = ExplorationBundle(
        bundle_id="workflow-local-requalification",
        witness_id=witness.witness_id,
        witness_spec_digest=digest("discovery-witness", witness),
        steps=[
            ExperimentStep(
                step_id="construct-and-test",
                question="Can this scoped consumer safely reuse qualification?",
                proposed_artifact="Actual local reports, drift refusals, original-output checks and all comparison histories",
                decisive_check="Unchanged exact ticket outputs, separate fixture grants and strong conventional controls",
                falsifying_observation=witness.falsifying_observation,
                cost_bucket="C",
                cost_cap_micro_usd=1_000_000,
                seconds_cap=120,
            )
        ],
        total_cost_cap_micro_usd=1_000_000,
        total_seconds_cap=120,
        checkpoint_after=["construct-and-test"],
        stopping_conditions=[
            "Unknown full research cost pauses admission",
            "No demand or live resources means no commercial offering",
        ],
        joint_value_hypothesis="Stable reuse plus fresh consumer checks and separately granted authority may jointly preserve usefulness",
        uncertainty="A USD1 planning ceiling is not a spending permit; no costs are inferred from logical check counts",
    )
    planned = _apply(state, "bundle", "workflow-bundle", bundle)
    started = time.monotonic()
    result = workflow.experiment()
    elapsed = math.ceil(time.monotonic() - started)
    if result["source_sha256"] != state["journal"].latest(freeze.journal_key)["source_sha256"]:
        raise ValueError("experiment source changed after the prospective freeze")
    artifact = _append(
        state,
        "@workflow-discovery-experiment:v1",
        {
            "freeze": freeze.model_dump(),
            "result": result,
            "elapsed_seconds": elapsed,
            "execution_type": "actual local ToolMissionEnvironment actions; no MissionExecutor model receipt",
        },
    )
    costs = Charge(
        activity_id="workflow-requalification/research",
        mission_id="workflow-requalification-research",
        bucket="C",
        category="overhead",
        accrued_micro_usd=None,
        paid_micro_usd=0,
        basis="unknown",
        evidence_digest=artifact.record_digest,
        note="Complete actual research monetary cost is unknown; fictional accounting signer, no monetary transaction",
    )
    account(state, "charge", costs.model_dump(), "workflow-research-cost-unknown")
    observation = ExperimentObservation(
        bundle_id=bundle.bundle_id,
        step_id="construct-and-test",
        interpretation="inconclusive",
        observation="Actual local workflow and original-output checks execute; method superiority and full cost are unresolved",
        evidence=[register, selection, freeze, artifact],
        artifact=artifact,
        cost_operation=costs.mission_id,
        elapsed_seconds=elapsed,
        acceptance="not-claimed",
        limitations="Local artifact checks do not mint existing placement acceptance, live identity, demand or commercial revenue",
    )
    observed = _apply(state, "observe", "workflow-local-observation", observation, planned["digest"])
    decision = DiscoveryDecision(
        opportunity_id=opportunity.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", opportunity),
        disposition="stop",
        rationale="Preserve the prototype; stop admission and commercial offering until complete costs and recipient value are supported",
        evidence=[artifact, register, selection],
        uncertainty="Finite support only; actual monetary cost and independent willingness to pay unknown",
        next_question="Assess a real recipient's full consumer contract and complete costs before any separately authorized deployment",
    )
    offering = OfferingV2(
        offering_id="consumer-workflow-requalification",
        version=1,
        beneficiary=need.beneficiary,
        useful_outcome=purpose.useful_purpose,
        deliverable=purpose.deliverable,
        scope=purpose.scope,
        acceptance_criteria=purpose.acceptance_criteria,
        need_evidence=[register, selection],
        demand_uncertainty="Independent buyer demand and a scope-equivalent human service are unestablished",
        buyer_value_hypothesis=BuyerValueHypothesis(
            beneficiary=need.beneficiary,
            outside_option=need.outside_option,
            basis="Correct consumer results may avoid rework; this documented problem and finite prototype do not establish a price",
            source_evidence=[register, selection, artifact],
            uncertainty="Buyer value and willingness-to-pay ranges remain unknown; no quote or commitment is observed",
        ),
        permitted_tools=["render_report"],
        price_policy="No quote until buyer value, complete costs and rights are assessed",
        price_candidates_micro_usd=[],
        capacity=1,
        turnaround_seconds=120,
        complete_cost_cap_micro_usd=1_000_000,
        risks=["Finite checks may miss unmodeled changes", "Actual complete cost and demand are unknown"],
        operating_limits=[
            "Internal prototype only; no commercial execution authority",
            "Retain human-service pricing where a credible equivalent exists",
        ],
        mode="hybrid",
    )
    offer_command = EnterpriseCommand(
        journal_identity=state["journal"].identity,
        operation_id="workflow-offering-hypothesis",
        expires_at=int(time.time()) + 3600,
        action="offering",
        expected_head=None,
        record=offering.model_dump(),
    )
    offer_record = Enterprise(state["service"]).apply(
        sign_record(
            state["keys"]["controller"],
            "controller",
            "flywheel-enterprise-command",
            offer_command.model_dump(),
        )
    )
    offer_ref = EvidenceRef(
        journal_key=offering_key("offering", offering.offering_id), record_digest=offer_record["digest"]
    )
    linked = _apply(
        state,
        "link-offering",
        "workflow-link-offering",
        OfferingLink(
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            offering_id=offering.offering_id,
            offering_record_digest=offer_record["digest"],
        ),
    )
    arrangement = Arrangement(
        arrangement_id="workflow-uncommitted-arrangement",
        version=1,
        offering=offer_ref,
        dependency_evidence=[register, freeze, artifact],
        participants=[
            Participant(
                participant_id="prospective-workflow-recipient",
                need=selection,
                outside_option=need.outside_option,
                useful_outcome=purpose.useful_purpose,
                responsibilities=[
                    "Supply a meaningful consumer contract and obtain separately scoped execution authority"
                ],
                price_cap_micro_usd=0,
                commitment="proposed",
                commitment_conditions=["No quote, financing or commercial obligation is presently authorized"],
                rights_and_failure_terms="Customer-specific rights, support and refund terms remain unnegotiated",
            )
        ],
        scenarios=[
            ArrangementScenario(
                scenario_id="current-unassessed-dossier",
                probability_ppm=1_000_000,
                qualified=False,
                risk_states={},
                failure_handling="Withhold offering and collections; obtain costs, rights and independent buyer evidence first",
            )
        ],
        state_space_basis="One current unassessed state, not a success-probability or market forecast",
        financing_basis="No commercial prefunding or payment commitment is established; unknown research cost remains in the actual ledger",
        rights_cleared=False,
        rights_basis="No customer-specific rights assessment or external agreement",
        mode="hybrid",
        authority_required="Existing separate technical, commercial and exact execution gates remain required",
        limitations=[
            "No modeled sales or price; zero projected movements are not a complete-cost estimate",
            "Internal research cost remains unknown; this proposal cannot authorize revenue or production",
        ],
    )
    arranged = _apply(
        state,
        "arrangement",
        "workflow-assess-uncommitted-arrangement",
        ArrangementRequest(
            opportunity_id=opportunity.opportunity_id,
            opportunity_spec_digest=digest("discovery-opportunity", opportunity),
            arrangement=arrangement,
            initial_cash_micro_usd=0,
            financing_assumption_basis="No financing proposed or verified; zero is the withheld proposal envelope, not an account balance",
        ),
    )
    decision = decision.model_copy(
        update={
            "evidence": [
                artifact,
                register,
                selection,
                offer_ref,
                EvidenceRef(
                    journal_key=discovery_key("arrangement", arrangement.arrangement_id),
                    record_digest=arranged["digest"],
                ),
            ]
        }
    )
    decided = _apply(state, "decision", "workflow-justified-stop", decision)
    return {
        "sources": dict(state["journal"].latest(register.journal_key)),
        "source_ref": register.model_dump(),
        "selection": dict(state["journal"].latest(selection.journal_key)),
        "selection_ref": selection.model_dump(),
        "opportunity": opportunity_record,
        "witness": witness_record,
        "freeze": dict(state["journal"].latest(freeze.journal_key)),
        "freeze_ref": freeze.model_dump(),
        "bundle": observed,
        "artifact": artifact.model_dump(),
        "experiment": result,
        "decision": decided,
        "offering": offer_record,
        "offering_link": linked,
        "arrangement": arranged,
        "costs": state["costs"].report(costs.mission_id),
        "authority_granted": False,
        "actual_customer_collections": 0,
        "live_qualified": False,
    }
