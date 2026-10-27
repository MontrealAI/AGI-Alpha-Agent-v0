# SPDX-License-Identifier: Apache-2.0
"""Discovery custody using fictional authority and explicit internal needs."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import economy_regression_fixture
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import (
    ArrangementRequest,
    BundleCheckpoint,
    ComparisonArm,
    ComparisonPlan,
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
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import key as enterprise_key
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record
import test_flywheel_enterprise as e
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def evidence(state: dict[str, Any], journal_key: str = "@discovery-internal-need") -> Any:
    try:
        return e.evidence(state, journal_key)
    except KeyError:
        with state["journal"].transaction() as cx:
            state["service"]._state(cx)
            state["journal"].append(
                cx,
                journal_key,
                {
                    "kind": "synthetic-internal-need",
                    "purpose": "Finite resilient placement research",
                    "limits": "No independent buyer demand or live identity; researcher-supplied fixture",
                },
            )
            state["service"].checkpoint.advance(state["journal"], cx)
        return e.evidence(state, journal_key)


def command(
    state: dict[str, Any],
    action: str,
    record: Any,
    identity: str,
    expected: str | None = None,
    principal: str = "controller",
    expires_at: int | None = None,
) -> Any:
    raw = DiscoveryCommand(
        journal_identity=state["journal"].identity,
        operation_id=identity,
        expires_at=expires_at if expires_at is not None else int(time.time()) + 3600,
        action=action,
        expected_head=expected,
        record=record.model_dump() if hasattr(record, "model_dump") else record,
    )
    return sign_record(state["keys"][principal], principal, "flywheel-discovery-command", raw)


def opportunity(state: dict[str, Any], identity: str = "resilient-placement-discovery") -> Opportunity:
    offering = e.offering(state)
    ref = evidence(state)
    return Opportunity(
        opportunity_id=identity,
        version=1,
        purpose=Purpose(
            useful_purpose=offering.useful_outcome,
            deliverable=offering.deliverable,
            acceptance_criteria=offering.acceptance_criteria,
            scope=offering.scope,
            input_semantics="Finite host capacity, service demands and correlated failure domains",
            output_semantics="Placement with independent finite feasibility and optimality checks",
        ),
        needs=[
            Need(
                need_id="research-resilience",
                beneficiary=offering.beneficiary,
                independently_motivated_purpose="Verify resilience rather than producing a skill registry",
                outside_option="Use the ordinary exact placement solver",
                evidence=[ref],
                evidence_kind="internal-research",
                demand_uncertainty="No customer demand observed",
            )
        ],
        limiting_assumptions=["Treating failures as independent can hide correlated loss"],
        shared_structure_hypothesis="Both placement and resilience checks share finite domain assignments",
        formulations=[
            Formulation(
                formulation_id="exact",
                approach="Enumerate finite placements",
                material_difference="Strong ordinary exhaustive baseline",
                assumptions=["Finite instance"],
                dependencies=["ordinary-search"],
                uncertainty="Exponential scale",
            ),
            Formulation(
                formulation_id="prune",
                approach="Reuse a constrained search procedure",
                material_difference="Prune impossible shared domain assignments before expanding",
                assumptions=["Constraints preserve every feasible answer"],
                dependencies=["ordinary-search"],
                uncertainty="Strong conventional methods may tie",
            ),
        ],
        ingredients=[
            Ingredient(
                ingredient_id="ordinary-search",
                description="Established exact search",
                origin="established-method",
                evidence=[ref],
                limitations="Method and domain are supplied by the researcher",
            )
        ],
        unresolved_questions=["Can complete transfer benefits exceed additional costs?"],
        mode="hybrid",
    )


def register(state: dict[str, Any], spec: Opportunity | None = None) -> dict[str, Any]:
    spec = spec or opportunity(state)
    return Discovery(state["service"]).apply(command(state, "opportunity", spec, "opportunity-" + spec.opportunity_id))


def test_serious_candidate_keeps_prior_art_and_rechecks_its_evidence(setup: dict[str, Any]) -> None:
    state = setup
    ref = evidence(state, "@prior-art")
    case = OpportunityCase(
        existing_approaches=[
            PriorApproach(
                approach="Competent exact solver",
                already_delivers="Exact bounded solutions",
                availability_to_recipient="available",
                remaining_limitation="No observed gap at the tested scale",
                evidence=[ref],
            )
        ],
        unresolved_gap="An untested larger-scope recipient requirement",
        gap_evidence=[ref],
        why_now="New independently inspectable recipient evidence is needed",
        proposed_construction="A bounded reusable method",
        decisive_experiment="Compare the strong direct method",
        commercial_mechanism="Unaccepted value hypothesis",
        falsifying_observation="Conventional parity after costs",
        missing_evidence=["Actual recipient demand"],
        novelty_scope="recipient",
    )
    spec = opportunity(state).model_copy(update={"discovery_case": case})
    receipt = register(state, spec)
    assert receipt["spec"]["discovery_case"]["existing_approaches"][0]["availability_to_recipient"] == "available"
    with state["journal"].transaction() as cx:
        state["journal"].append(cx, "@prior-art", {"changed": True})
        state["service"].checkpoint.advance(state["journal"], cx)
    terms = witness(state, spec)
    with pytest.raises(Conflict, match="stale"):
        Discovery(state["service"]).apply(command(state, "witness", terms, "stale-case-witness"))


def test_selected_instrument_uses_the_same_journal_and_unknown_costs_pause(setup: dict[str, Any]) -> None:
    from scripts.record_discovery_flywheel import probe_lineage

    result = probe_lineage(setup)
    assert result["opportunity"]["spec"]["discovery_case"]["novelty_scope"] == "organization"
    assert result["bundle"]["status"] == "paused-uncertain"
    assert not result["bundle"]["observations"][0]["complete_selected_bucket"]
    assert result["decision"]["spec"]["disposition"] == "stop"
    assert not result["bundle"]["authority_granted"]
    assert result["report"]["recipient"]["verified"]
    protocol = setup["journal"].latest("@discovery-information-protocol:v1")
    artifact = setup["journal"].latest("@discovery-information-instrument:v1")
    assert protocol["revision"] < result["opportunity"]["revision"] < artifact["revision"]
    assert result["bundle"]["revision"] > artifact["revision"]
    setup["journal"].verify()


def witness(state: dict[str, Any], spec: Opportunity | None = None) -> TransformationWitness:
    spec = spec or opportunity(state)
    return TransformationWitness(
        witness_id="preserve-resilience",
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        purpose=spec.purpose,
        binding_restriction="Naive enumeration expands already impossible branches",
        removable_basis="Finite lower bounds can certify that partial assignments cannot succeed",
        change_kind="workflow",
        replacement="Prune certified impossible branches only",
        operation_in_original_setting="Emit the same placement schema and use the unchanged finite checker",
        falsifying_observation="Any missing feasible minimum or worse complete cost on fresh work",
        formulation_id="prune",
        evidence=[evidence(state)],
        limitations="Established search method; fixture does not establish autonomous invention",
    )


def register_witness(state: dict[str, Any]) -> dict[str, Any]:
    register(state)
    return Discovery(state["service"]).apply(command(state, "witness", witness(state), "first-witness"))


def bundle(
    state: dict[str, Any],
    identity: str = "complementary-package",
    mission: Any = None,
    bucket: str = "C",
    cap: int = 1000,
) -> ExplorationBundle:
    request_digest = digest("flywheel-execution-request", mission) if mission else None
    return ExplorationBundle(
        bundle_id=identity,
        witness_id=witness(state).witness_id,
        witness_spec_digest=digest("discovery-witness", witness(state)),
        steps=[
            ExperimentStep(
                step_id="construct",
                question="Can the same original outcome be verified?",
                proposed_artifact="Executable placement result",
                decisive_check="Original finite checker",
                falsifying_observation="Any invalid original result",
                cost_bucket=bucket,
                cost_cap_micro_usd=cap,
                seconds_cap=1800,
                execution_request_digest=request_digest,
            ),
            ExperimentStep(
                step_id="arrange",
                question="Can a complementary delivery arrangement pay?",
                dependencies=["construct"],
                proposed_artifact="Projected cash schedule",
                decisive_check="Complete conditional delivery and cash timing",
                falsifying_observation="Insufficient cash or nonparticipation",
                cost_bucket="C",
                cost_cap_micro_usd=1000,
                seconds_cap=1800,
            ),
        ],
        total_cost_cap_micro_usd=cap + 1000,
        total_seconds_cap=3600,
        checkpoint_after=["construct", "arrange"],
        stopping_conditions=["Stop if the original purpose changes"],
        joint_value_hypothesis="Construction and arrangement may be useful only together",
        uncertainty="Each intermediate may have negative value; demand is unobserved",
    )


def register_bundle(state: dict[str, Any], spec: ExplorationBundle | None = None) -> dict[str, Any]:
    spec = spec or bundle(state)
    return Discovery(state["service"]).apply(command(state, "bundle", spec, "bundle-" + spec.bundle_id))


def observation(state: dict[str, Any], spec: ExplorationBundle | None = None) -> ExperimentObservation:
    spec = spec or bundle(state)
    return ExperimentObservation(
        bundle_id=spec.bundle_id,
        step_id="construct",
        interpretation="inconclusive",
        observation="Inspect recorded prototype before deciding",
        evidence=[evidence(state)],
        artifact=evidence(state),
        cost_operation="construction-costs",
        elapsed_seconds=1,
        limitations="Internal evidence only; does not qualify a production artifact",
    )


def checkpoint(state: dict[str, Any], identity: str, disposition: str = "continue") -> dict[str, Any]:
    api = Discovery(state["service"])
    old = api.inspect("bundle", identity)
    terms = BundleCheckpoint(
        bundle_id=identity,
        disposition=disposition,
        evidence=[evidence(state)],
        rationale="Explicitly reassess the whole package",
        stopping_conditions_checked="Original purpose retained; no claimed commercial demand",
    )
    return api.apply(command(state, "checkpoint", terms, "checkpoint-" + str(old["revision"]), old["digest"]))


def comparison(state: dict[str, Any]) -> ComparisonPlan:
    spec = opportunity(state)
    arms = []
    for role in ("U", "E", "E+"):
        arms.append(
            ComparisonArm(
                role=role,
                model_profile_digest="a" * 64,
                access_and_tools_digest="b" * 64,
                resource_budget=ResourceBudget(tokens=1000, tool_actions=5, seconds=100, cost_cap_micro_usd=1000),
                workflow_digest=("c" if role == "U" else "d") * 64,
                retained_capability_digest="e" * 64 if role == "E+" else None,
                starting_capabilities=["Same ordinary exact solver access"],
                baseline_definition="Frozen explicit workflow",
            )
        )
    return ComparisonPlan(
        comparison_id="operational-alpha",
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        purpose=spec.purpose,
        human_reference=e.offering(state).human_reference,
        arms=arms,
        ordinary_use_basis="Representative ordinary tool use; no intentional weakening",
        fresh_instance_policy="Freeze before fresh seeds and protect the checker",
        complete_cost_policy="Include retries, failures, correction and user effort; unknown remains unknown",
        evidence=[evidence(state)],
    )


def test_discovery_records_survive_reconstruction_without_authority(setup: dict[str, Any]) -> None:
    state = setup
    original_costs = state["costs"].report()
    register_witness(state)
    register_bundle(state)
    plan = Discovery(state["service"]).apply(command(state, "comparison", comparison(state), "freeze-comparison"))
    assert plan["contrasts"] == {"Operational Alpha": "E versus U", "retained increment": "E+ versus E"}
    assert plan["results"] == "not measured" and plan["authority_granted"] is False
    assert Discovery(state["service"]).inspect("bundle", "complementary-package")["status"] == "planned"
    assert state["costs"].report() == original_costs
    state["journal"].verify()


@pytest.mark.parametrize(
    "attack", ["expired", "wrong-role", "wrong-journal", "replay", "signature", "stopped", "source"]
)
def test_signed_command_authority_boundaries(setup: dict[str, Any], attack: str) -> None:
    state = setup
    spec = opportunity(state)
    signed = command(
        state,
        "opportunity",
        spec,
        "register",
        principal="producer" if attack == "wrong-role" else "controller",
        expires_at=1 if attack == "expired" else None,
    )
    if attack in {"wrong-journal", "signature"}:
        raw = signed.model_dump()
        if attack == "wrong-journal":
            raw["payload"]["journal_identity"] = "urn:agialpha:ed25519:" + "a" * 64
            signed = sign_record(
                state["keys"]["controller"], "controller", "flywheel-discovery-command", raw["payload"]
            )
        else:
            raw["payload"]["record"]["purpose"]["useful_purpose"] = "Altered after signing"
            signed = signed.model_validate(raw)
    elif attack == "replay":
        Discovery(state["service"]).apply(signed)
    elif attack == "stopped":
        with state["journal"].transaction() as cx:
            control = state["journal"].document(state["journal"].latest("@control", cx))
            control["state"] = "paused"
            state["journal"].append(cx, "@control", control)
            state["service"].checkpoint.advance(state["journal"], cx)
    elif attack == "source":
        state["service"]._boot_execution_digest = "f" * 64
    with pytest.raises((ValueError, Conflict)):
        Discovery(state["service"]).apply(signed)


def test_original_meaning_cannot_be_relaxed_or_witness_rebound(setup: dict[str, Any]) -> None:
    state = setup
    record = register(state)
    changed = opportunity(state).model_dump()
    changed["version"] = 2
    changed["purpose"]["acceptance_criteria"] = ["Any plausible result"]
    with pytest.raises(ValueError, match="relaxed acceptance"):
        Discovery(state["service"]).apply(command(state, "opportunity", changed, "relax", record["digest"]))
    forged = witness(state).model_dump()
    forged["purpose"]["useful_purpose"] = "An easier purpose"
    with pytest.raises(ValueError, match="original purpose"):
        Discovery(state["service"]).apply(command(state, "witness", forged, "forged-witness"))
    changed["purpose"] = opportunity(state).purpose.model_dump()
    updated = Discovery(state["service"]).apply(command(state, "opportunity", changed, "revise", record["digest"]))
    assert updated["stage"] == "hypothesis" and updated["previous_digest"] == record["digest"]
    with pytest.raises(Conflict, match="opportunity changed"):
        Discovery(state["service"]).apply(command(state, "witness", witness(state), "stale-witness"))


@pytest.mark.parametrize("attack", ["cycle", "missing", "cost", "time", "checkpoint", "duplicate"])
def test_bundle_bounds_and_dependencies(attack: str, setup: dict[str, Any]) -> None:
    raw = bundle(setup).model_dump()
    if attack == "cycle":
        raw["steps"][0]["dependencies"] = ["arrange"]
    elif attack == "missing":
        raw["steps"][1]["dependencies"] = ["missing"]
    elif attack == "cost":
        raw["total_cost_cap_micro_usd"] = 1
    elif attack == "time":
        raw["total_seconds_cap"] = 1
    elif attack == "checkpoint":
        raw["checkpoint_after"] = ["missing"]
    else:
        raw["steps"][1]["step_id"] = "construct"
    with pytest.raises(ValueError):
        ExplorationBundle.model_validate(raw)


@pytest.mark.parametrize("attack", ["budget", "model", "tools", "retained", "workflow", "roles"])
def test_operational_alpha_plan_matches_resources_and_keeps_contrasts(setup: dict[str, Any], attack: str) -> None:
    raw = comparison(setup).model_dump()
    if attack == "budget":
        raw["arms"][0]["resource_budget"]["tokens"] = 1
    elif attack == "model":
        raw["arms"][0]["model_profile_digest"] = "1" * 64
    elif attack == "tools":
        raw["arms"][0]["access_and_tools_digest"] = "1" * 64
    elif attack == "retained":
        raw["arms"][1]["retained_capability_digest"] = "1" * 64
    elif attack == "workflow":
        raw["arms"][2]["workflow_digest"] = "1" * 64
    else:
        raw["arms"][2]["role"] = "E"
    with pytest.raises(ValueError):
        ComparisonPlan.model_validate(raw)


def test_unknown_costs_preserve_uncertainty_and_stop_next_steps(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    record = register_bundle(state)
    result = Discovery(state["service"]).apply(
        command(state, "observe", observation(state), "unknown-observation", record["digest"])
    )
    assert result["status"] == "paused-uncertain"
    assert result["observations"][0]["complete_selected_bucket"] is False
    with pytest.raises(Conflict):
        Discovery(state["service"]).apply(command(state, "observe", observation(state), "retry", result["digest"]))
    assert (
        Discovery(state["service"]).inspect("observation", "unknown-observation")["terms"]["acceptance"]
        == "not-claimed"
    )
    with pytest.raises(Conflict, match="unknown experiment liabilities"):
        checkpoint(state, "complementary-package")
    s.seal(state, "construction-costs", "C")
    recovered = checkpoint(state, "complementary-package")
    assert recovered["status"] == "observing"
    assert recovered["accounting_reconciliations"][0]["reports"][0]["cost_report"]["bucket_complete"]["C"] is True
    assert recovered["observations"][0]["complete_selected_bucket"] is False


def test_stop_checkpoint_does_not_require_fictional_profit(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    record = register_bundle(state)
    Discovery(state["service"]).apply(command(state, "observe", observation(state), "uncertain", record["digest"]))
    assert checkpoint(state, "complementary-package", "stop")["status"] == "stopped-controller"


def test_out_of_order_and_duplicate_observation_cas_refuse(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    record = register_bundle(state)
    raw = observation(state).model_dump()
    raw["step_id"] = "arrange"
    with pytest.raises(Conflict, match="prerequisite"):
        Discovery(state["service"]).apply(command(state, "observe", raw, "too-early", record["digest"]))
    s.seal(state, "construction-costs", "C")
    current = Discovery(state["service"]).apply(
        command(state, "observe", observation(state), "first", record["digest"])
    )
    with pytest.raises(Conflict, match="head changed"):
        Discovery(state["service"]).apply(command(state, "observe", observation(state), "stale-head", record["digest"]))
    checkpoint(state, "complementary-package")
    newer = Discovery(state["service"]).inspect("bundle", "complementary-package")
    with pytest.raises(Conflict, match="unrecorded"):
        Discovery(state["service"]).apply(
            command(state, "observe", observation(state), "duplicate-step", newer["digest"])
        )
    assert newer["digest"] != current["digest"]


def test_complementary_falsification_pauses_and_requires_signed_decision(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    record = register_bundle(state)
    s.seal(state, "construction-costs", "C")
    terms = observation(state).model_dump()
    terms["interpretation"] = "falsifies"
    result = Discovery(state["service"]).apply(command(state, "observe", terms, "negative-component", record["digest"]))
    assert result["status"] == "paused-checkpoint"
    terms["step_id"] = "arrange"
    terms["cost_operation"] = "arrangement-costs"
    with pytest.raises(Conflict):
        Discovery(state["service"]).apply(command(state, "observe", terms, "unreviewed-next", result["digest"]))
    continued = checkpoint(state, "complementary-package")
    assert continued["status"] == "observing"
    s.seal(state, "arrangement-costs", "C")
    complete = Discovery(state["service"]).apply(
        command(state, "observe", terms, "second-component", continued["digest"])
    )
    assert complete["status"] == "paused-checkpoint"
    assert checkpoint(state, "complementary-package")["status"] == "completed"
    assert state["costs"].report()["collected_revenue"] == 0


def test_same_costs_cannot_be_allocated_twice_across_bundles(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    first = register_bundle(state)
    s.seal(state, "construction-costs", "C")
    Discovery(state["service"]).apply(
        command(state, "observe", observation(state), "first-allocation", first["digest"])
    )
    other = bundle(state, "another-bundle")
    record = register_bundle(state, other)
    with pytest.raises(Conflict, match="another discovery observation"):
        Discovery(state["service"]).apply(
            command(state, "observe", observation(state, other), "second-allocation", record["digest"])
        )


def test_recorded_cost_overrun_remains_visible_and_terminal(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    spec = bundle(state, cap=0)
    record = register_bundle(state, spec)
    s.seal(state, "construction-costs", "C")
    raw = observation(state, spec).model_dump()
    raw["elapsed_seconds"] = 1801
    result = Discovery(state["service"]).apply(command(state, "observe", raw, "overrun", record["digest"]))
    assert result["status"] == "stopped-budget" and result["elapsed_seconds"] == 1801
    assert result["observations"][0]["within_declared_budget"] is False


def test_actual_execution_and_accepted_original_artifact_bind_observation(setup: dict[str, Any]) -> None:
    state = setup
    execution = e.launch(state)
    e.accept(state, execution)
    register_witness(state)
    mission = e.execution(state)[1]
    spec = bundle(state, mission=mission, bucket="A")
    record = register_bundle(state, spec)
    raw = observation(state, spec).model_dump()
    raw.update(
        artifact=evidence(state, operation_key("placement-origin")).model_dump(),
        cost_operation="placement-origin",
        execution_operation="placement-origin",
        acceptance="existing-placement-acceptance",
        elapsed_seconds=1800,
    )
    result = Discovery(state["service"]).apply(command(state, "observe", raw, "accepted-observation", record["digest"]))
    assert result["observations"][0]["execution_digest"] == execution["digest"]
    assert result["observations"][0]["complete_selected_bucket"] is True
    assert result["authority_granted"] is False


@pytest.mark.parametrize("seal_before_observation", [False, True])
def test_executed_observation_and_checkpoint_use_actual_mission_ledger(
    setup: dict[str, Any], seal_before_observation: bool
) -> None:
    state = setup
    s.funding(state)
    executor, mission, profile, permit = e.execution(state, mission_id="paid-delivery-mission")
    executor.run(mission, profile, permit)
    execution = state["journal"].latest(operation_key("placement-origin"))
    register_witness(state)
    spec = bundle(state, mission=mission, bucket="A")
    record = register_bundle(state, spec)
    raw = observation(state, spec).model_dump()
    raw.update(
        artifact=evidence(state, operation_key("placement-origin")).model_dump(),
        cost_operation="placement-origin",
        execution_operation="placement-origin",
        elapsed_seconds=1800,
    )
    # An unrelated sealed operation ID must never stand in for actual mission costs.
    s.seal(state, "placement-origin", "A")
    if seal_before_observation:
        s.seal(state, mission.mission_id, "A")
    api = Discovery(state["service"])
    result = api.apply(command(state, "observe", raw, "distinct-ledger-observation", record["digest"]))
    item = result["observations"][0]
    assert item["execution_digest"] == execution["digest"]
    assert item["ledger_mission_id"] == mission.mission_id
    assert item["cost_report"] == state["costs"].report(mission.mission_id)
    assert item["complete_selected_bucket"] is seal_before_observation
    assert (
        state["journal"].latest(key("cost-allocation", mission.mission_id + "/A"))["cost_operation"]
        == "placement-origin"
    )
    if not seal_before_observation:
        assert result["status"] == "paused-uncertain"
        with pytest.raises(Conflict, match="unknown experiment liabilities"):
            checkpoint(state, spec.bundle_id)
        s.seal(state, mission.mission_id, "A")
    result = checkpoint(state, spec.bundle_id)
    reconciled = result["accounting_reconciliations"][-1]["reports"][0]
    assert reconciled["ledger_mission_id"] == mission.mission_id
    assert reconciled["cost_report"] == state["costs"].report(mission.mission_id)
    assert result["known_cost_micro_usd"] == state["costs"].report(mission.mission_id)["costs"]["A"]
    assert result["status"] == "observing"


def test_distinct_execution_operations_cannot_allocate_the_same_mission_costs_twice(setup: dict[str, Any]) -> None:
    state = setup
    s.funding(state)
    executor, mission, profile, permit = e.execution(state, mission_id="shared-paid-mission")
    executor.run(mission, profile, permit)
    # Resolve the first attempt, leaving the scope open for the second actual local run.
    for row in state["costs"].snapshot()["charges"].values():
        if row["accrued_micro_usd"] is None:
            value = {
                k: row[k]
                for k in (
                    "activity_id",
                    "mission_id",
                    "bucket",
                    "category",
                    "accrued_micro_usd",
                    "paid_micro_usd",
                    "basis",
                    "evidence_digest",
                    "note",
                )
            }
            value.update(accrued_micro_usd=1, basis="attested", note="FICTIONAL test amount")
            f.account(state, "resolve", value, "resolve/" + row["activity_id"])
    second_executor, _, _, second_permit = e.execution(state, "second-attempt", mission_id=mission.mission_id)
    second_executor.run(mission, profile, second_permit)
    s.seal(state, mission.mission_id, "A")
    register_witness(state)
    api = Discovery(state["service"])
    for number, operation in enumerate(("placement-origin", "second-attempt")):
        spec = bundle(state, identity=f"attempt-bundle-{number}", mission=mission, bucket="A")
        record = register_bundle(state, spec)
        raw = observation(state, spec).model_dump()
        raw.update(
            artifact=evidence(state, operation_key(operation)).model_dump(),
            cost_operation=operation,
            execution_operation=operation,
            elapsed_seconds=1800,
        )
        signed = command(state, "observe", raw, f"allocate-attempt-{number}", record["digest"])
        if number == 0:
            api.apply(signed)
        else:
            with pytest.raises(Conflict, match="ledger mission and bucket"):
                api.apply(signed)


def test_checkpoint_refuses_changed_execution_receipt(setup: dict[str, Any]) -> None:
    state = setup
    e.launch(state)
    s.seal(state, "placement-origin", "A")
    register_witness(state)
    spec = bundle(state, mission=e.execution(state)[1], bucket="A")
    record = register_bundle(state, spec)
    raw = observation(state, spec).model_dump()
    raw.update(
        artifact=evidence(state, operation_key("placement-origin")).model_dump(),
        cost_operation="placement-origin",
        execution_operation="placement-origin",
        elapsed_seconds=1800,
    )
    Discovery(state["service"]).apply(command(state, "observe", raw, "original-receipt", record["digest"]))
    with state["journal"].transaction() as cx:
        prior = state["journal"].latest(operation_key("placement-origin"), cx)
        changed = state["journal"].document(prior)
        changed["result"] = {"different": True}
        state["journal"].append(cx, operation_key("placement-origin"), changed)
        state["service"].checkpoint.advance(state["journal"], cx)
    with pytest.raises(Conflict, match="original exact execution receipt"):
        checkpoint(state, spec.bundle_id)


def test_legacy_operation_allocation_reconciles_without_rewriting_history(
    setup: dict[str, Any], monkeypatch: Any
) -> None:
    state = setup
    s.funding(state)
    executor, mission, profile, permit = e.execution(state, mission_id="legacy-original-mission")
    executor.run(mission, profile, permit)
    register_witness(state)
    spec = bundle(state, mission=mission, bucket="A")
    record = register_bundle(state, spec)
    raw = observation(state, spec).model_dump()
    raw.update(
        artifact=evidence(state, operation_key("placement-origin")).model_dump(),
        cost_operation="placement-origin",
        execution_operation="placement-origin",
        elapsed_seconds=1800,
    )
    api = Discovery(state["service"])
    # Reproduce the previous operation-scoped lookup to create a legacy paused record.
    with monkeypatch.context() as context:
        context.setattr(api, "_ledger_mission", lambda terms, execution_digest, cx: terms.cost_operation)
        old = api.apply(command(state, "observe", raw, "legacy-scope-observation", record["digest"]))
    assert old["status"] == "paused-uncertain"
    assert not old["observations"][0]["cost_report"]["bucket_complete"]["A"]
    s.seal(state, mission.mission_id, "A")
    result = checkpoint(state, spec.bundle_id)
    assert result["status"] == "observing"
    assert result["observations"] == old["observations"]
    assert result["known_cost_micro_usd"] == state["costs"].report(mission.mission_id)["costs"]["A"]
    assert (
        state["journal"].latest(key("cost-allocation", mission.mission_id + "/A"))["ledger_mission_id"]
        == mission.mission_id
    )
    assert (
        state["journal"].latest(key("cost-allocation", "placement-origin/A"))["ledger_mission_id"] == "placement-origin"
    )


@pytest.mark.parametrize("attack", ["bucket", "artifact", "elapsed", "inputs", "acceptance", "mode"])
def test_execution_cannot_substitute_costs_artifact_inputs_or_acceptance(setup: dict[str, Any], attack: str) -> None:
    state = setup
    e.launch(state)
    register_witness(state)
    mission = e.execution(state)[1]
    spec = bundle(state, mission=mission, bucket="C" if attack == "bucket" else "A")
    if attack == "inputs":
        mission = mission.model_copy(update={"inputs": {"problem": s.problem(9999).model_dump()}})
        spec = bundle(state, mission=mission, bucket="A")
    elif attack == "mode":
        mission = mission.model_copy(update={"mode": "simulation"})
        spec = bundle(state, mission=mission, bucket="A")
    record = register_bundle(state, spec)
    raw = observation(state, spec).model_dump()
    raw.update(
        artifact=evidence(state, operation_key("placement-origin")).model_dump(),
        cost_operation="placement-origin",
        execution_operation="placement-origin",
        elapsed_seconds=1800,
    )
    if attack == "artifact":
        raw["artifact"] = evidence(state).model_dump()
    elif attack == "elapsed":
        raw["elapsed_seconds"] = 0
    elif attack == "acceptance":
        raw["acceptance"] = "existing-placement-acceptance"
    with pytest.raises((ValueError, KeyError)):
        Discovery(state["service"]).apply(command(state, "observe", raw, "attack", record["digest"]))


def test_stale_need_evidence_and_offer_recommendation_do_not_create_authority(setup: dict[str, Any]) -> None:
    state = setup
    register_witness(state)
    spec = opportunity(state)
    decision = DiscoveryDecision(
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        disposition="offer",
        rationale="Only recommend assessment",
        evidence=[evidence(state)],
        uncertainty="No external buyers",
        next_question="Would any buyer conditionally commit?",
    )
    record = Discovery(state["service"]).apply(command(state, "decision", decision, "suggest-offer"))
    assert record["stage"] == "recommendation-only" and record["authority_granted"] is False
    with state["journal"].transaction() as cx:
        state["journal"].append(cx, evidence(state).journal_key, {"withdrawn": True})
        state["service"].checkpoint.advance(state["journal"], cx)
    with pytest.raises(Conflict, match="stale"):
        Discovery(state["service"]).apply(command(state, "decision", decision, "stale-offer"))


def test_link_and_arrangement_project_without_advancing_offering_or_money(setup: dict[str, Any]) -> None:
    state = setup
    offering = e.register(state)
    register_witness(state)
    spec = opportunity(state)
    ref = evidence(state, enterprise_key("offering", "resilient-placement"))
    link = OfferingLink(
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        offering_id="resilient-placement",
        offering_record_digest=offering["digest"],
    )
    linked = Discovery(state["service"]).apply(command(state, "link-offering", link, "link"))
    assert linked["offering_authorization_inherited"] is False
    arrangement = economy_regression_fixture(ref).model_copy(update={"mode": "hybrid"})
    terms = ArrangementRequest(
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        arrangement=arrangement,
        initial_cash_micro_usd=900_000_000_000,
        financing_assumption_basis="Paper fixture; not actual account resources",
    )
    before = state["costs"].report()
    result = Discovery(state["service"]).apply(command(state, "arrangement", terms, "assessment"))
    assert result["stage"] == "projected-commercial-assessment"
    assert result["assessment"]["authority_granted"] is False
    assert result["assessment"]["actual_collections_micro_usd"] is None
    assert state["costs"].report() == before
    assert state["journal"].latest(enterprise_key("offering", "resilient-placement"))["stage"] == "hypothesis"


@pytest.mark.parametrize("attack", ["need", "offering", "commitment", "mode"])
def test_arrangement_rechecks_current_evidence_and_evidence_mode(setup: dict[str, Any], attack: str) -> None:
    state = setup
    e.register(state)
    register_witness(state)
    spec = opportunity(state)
    ref = evidence(state, enterprise_key("offering", "resilient-placement"))
    arrangement = economy_regression_fixture(ref).model_dump()
    arrangement["mode"] = "hybrid"
    if attack == "mode":
        arrangement["mode"] = "live"
    elif attack == "offering":
        arrangement["offering"]["record_digest"] = "f" * 64
    elif attack == "need":
        arrangement["participants"][0]["need"]["record_digest"] = "f" * 64
    else:
        arrangement["participants"][0]["commitment_evidence"] = [
            {"journal_key": ref.journal_key, "record_digest": "f" * 64}
        ]
    terms = ArrangementRequest(
        opportunity_id=spec.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", spec),
        arrangement=arrangement,
        initial_cash_micro_usd=900_000_000_000,
        financing_assumption_basis="Paper fixture",
    )
    with pytest.raises((Conflict, ValueError)):
        Discovery(state["service"]).apply(command(state, "arrangement", terms, "bad-assessment"))
