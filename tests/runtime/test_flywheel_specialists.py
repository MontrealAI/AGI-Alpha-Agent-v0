# SPDX-License-Identifier: Apache-2.0
"""Actual finite workflows with fictional frontier, ENS, billing and authority.

Positive protocol admissions below are adversarial conformance fixtures, never
claims of live peer execution or economic Alpha. The technical relay does not
admit a candidate without a competent frontier comparison.
"""

from __future__ import annotations

import copy
import random
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_capsules import (
    AlphaEvidence,
    CapsuleManifest,
    EvaluationPlan,
    input_digest,
)
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    operation_key,
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
)
from alpha_factory_v1.core.runtime.successor.flywheel_experiments import PlacementProblem, verify_placement
from alpha_factory_v1.core.runtime.successor.flywheel_gym import (
    GymCampaign,
    GymPlan,
    GymTask,
    PlacementEnvironment,
    evaluate_frozen,
)
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import (
    CapabilityDescription,
    PlacementInvocation,
    PlacementWorkflow,
    execute_workflow,
)
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record
from scripts.record_general_flywheel import ScriptedModel
import test_flywheel_protected as f


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def problem(seed: int, hosts: int = 4, services: int = 4, tight: bool = False) -> PlacementProblem:
    rng = random.Random(seed)
    return PlacementProblem(
        capacities=[rng.randint(3 if tight else 5, 7 if tight else 12) for _ in range(hosts)],
        failure_domains=["a", "b", "c", "a", "b"][:hosts],
        demands=[rng.randint(1, 4) for _ in range(services)],
        costs=[[rng.randint(1, 50) for _ in range(hosts)] for _ in range(services)],
    )


def funding(s: dict[str, Any]) -> None:
    f.account(
        s,
        "capital",
        {
            "record_id": "specialist-fictional-funding",
            "mission_id": "specialist-fixture",
            "amount_micro_usd": 10_000_000,
            "evidence_digest": f.ZERO,
        },
        "specialist-fictional-funding",
    )


def seal(s: dict[str, Any], mission: str, bucket: str) -> None:
    rows = [
        row
        for row in s["costs"].snapshot()["charges"].values()
        if row["mission_id"] == mission and row["bucket"] == bucket
    ]
    for row in rows:
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
            value.update(accrued_micro_usd=1, basis="attested", note="FICTIONAL conformance amount; not actual cost")
            f.account(s, "resolve", value, "resolve/" + row["activity_id"])
    for category in sorted(CATEGORIES - {row["category"] for row in rows}):
        value = {
            "activity_id": f"{mission}/{bucket}/{category}",
            "mission_id": mission,
            "bucket": bucket,
            "category": category,
            "accrued_micro_usd": 0,
            "paid_micro_usd": 0,
            "basis": "attested",
            "evidence_digest": f.ZERO,
            "note": "FICTIONAL explicit category; actual complete cost remains unknown",
        }
        f.account(s, "charge", value, "charge/" + value["activity_id"])
    action = {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket]
    f.account(
        s,
        action,
        {"mission_id": mission, "categories": sorted(CATEGORIES), "evidence_digest": f.ZERO},
        f"seal/{mission}/{bucket}",
    )


def execute(
    s: dict[str, Any], instance: PlacementProblem, workflow: PlacementWorkflow, mission_id: str
) -> dict[str, Any]:
    env = PlacementEnvironment(workflow)
    task = ExecutionMission(
        mission_id=mission_id,
        beneficiary="Synthetic systems engineering team",
        goal="Find minimum-cost capacity-respecting replicas surviving one failure domain loss",
        challenged_assumption="Cheapest replicas may share a failure domain",
        deliverable="Exact placement with an independent exhaustive check",
        acceptance_criteria=["Capacity and domain constraints", "Exact minimum or proven infeasibility"],
        inputs={"problem": instance.model_dump()},
        sharing_rights="Original Apache-2.0 synthetic work",
        stop_conditions=["Bounded local computation only"],
        mode="hybrid",
        components={
            "model": "simulated",
            "tools": "executed-local",
            "identity": "simulated",
            "acceptance": "executed-local",
            "market": "simulated",
        },
    )
    profile = ExecutionProfile(
        model_id="scripted-protocol-fixture/v1",
        reasoning_effort="high",
        supported_efforts=["high"],
        qualification_digest=f.ZERO,
        tools=[
            {
                "type": "function",
                "name": "placement_experiment",
                "description": "Bounded placement computation",
                "strict": True,
                "parameters": {
                    "type": "object",
                    "properties": {"problem": PlacementProblem.model_json_schema()},
                    "required": ["problem"],
                    "additionalProperties": False,
                },
            }
        ],
    )
    terms = ExecutionPermit(
        operation_id=mission_id,
        request_digest=digest("flywheel-execution-request", task),
        profile_digest=digest("flywheel-execution-profile", profile),
        environment_digest=digest("flywheel-execution-environment-contract", env.identity),
        config_digest=runtime_digest(s["journal"].config.model_dump()),
        quota_evidence_digest=f.ZERO,
        pricing_evidence_digest=f.ZERO,
        max_authorized_micro_usd=1000,
        expires_at=int(time.time()) + 3600,
        bucket="A",
    )
    signed = sign_record(
        s["keys"]["controller"],
        "controller",
        "flywheel-execution-permit",
        {"journal_identity": s["journal"].identity, "permit": terms.model_dump()},
    )
    result = MissionExecutor(s["journal"], s["trust"], s["costs"], ScriptedModel(instance), env).run(
        task, profile, signed
    )
    assert result["result"]["verification"]["accepted_finite_result"]
    return s["journal"].latest(operation_key(mission_id))


def origin(s: dict[str, Any]) -> dict[str, Any]:
    funding(s)
    record = execute(s, problem(2100), PlacementWorkflow(version=1), "placement-origin")
    seal(s, "placement-origin", "A")
    s["service"].accept_general_origin(
        f.signed(
            s,
            "general-acceptance",
            "acceptor",
            {
                "operation_id": "placement-origin",
                "execution_record_digest": record["digest"],
                "output_digest": digest("general-delivered-output", record["result"]),
                "rights_evidence": f.ZERO,
            },
            "accept-placement-origin",
        )
    )
    s["service"].configure(
        f.signed(
            s, "configure", "controller", {"beta_digest": f.BETA, "policy_digest": f.POLICY}, "configure-placement"
        )
    )
    return record


def retain(s: dict[str, Any], record: dict[str, Any], workflow: PlacementWorkflow, campaign: str | None = None) -> str:
    manifest = CapsuleManifest(
        skill_id="resilient-placement",
        version=1,
        origin_mission="placement-origin",
        origin_record_digest=record["digest"],
        origin_agent="one.agent.agi.eth",
        origin_wallet=s["origin_wallet"].address.lower(),
        content_digest=digest("flywheel-program", workflow),
        supported_scope="resilient-placement/v1",
        prerequisites=[],
        dependency_digests=[],
        limitations="Finite local protocol fixture; no qualified frontier advantage",
        rights="cleared-for-authenticated-network",
        rights_evidence=f.ZERO,
        gym_campaign_id=campaign,
        capability=CapabilityDescription(
            form="executable-skill",
            runtime="resilient-placement/v1",
            input_contract=f.ZERO,
            output_contract=f.ZERO,
            tests_digest=f.ZERO,
            provenance_digest=record["digest"],
            permissions=["bounded-local-compute"],
            dependencies=[],
            limitations="Synthetic conformance only",
        ),
    )
    ident = digest("flywheel-manifest", manifest)
    return s["service"].retain(
        manifest, workflow, f.signed(s, "candidate", "producer", {"manifest_digest": ident}, "retain-placement")
    )


def campaign(s: dict[str, Any], *, limit: int = 1_000_000) -> dict[str, Any]:
    plan = GymPlan(
        campaign_id="placement-gym",
        mission_id="placement-extra-rd",
        original=PlacementWorkflow(version=1),
        alternatives=[
            PlacementWorkflow(version=2, order="largest-demand", bound="residual", capacity_pruning=True),
            PlacementWorkflow(version=2, order="regret", bound="residual"),
        ],
        tasks=[
            GymTask(
                task_id=f"train-{seed}",
                partition="training",
                family="capacity-contention",
                problem=problem(seed, services=5, tight=True),
            )
            for seed in range(2101, 2105)
        ],
        max_logical_units=limit,
        max_seconds=60,
        max_authorized_micro_usd=10_000,
        environment_digest=s["service"].execution_digest,
        expires_at=int(time.time()) + 3600,
    )
    signed = sign_record(
        s["keys"]["controller"],
        "controller",
        "flywheel-gym-plan",
        {"journal_identity": s["journal"].identity, "plan": plan.model_dump()},
    )
    return GymCampaign(
        s["costs"],
        s["service"].checkpoint,
        s["service"].execution_digest,
        current_environment=s["service"]._execution_binding,
    ).run(signed)


def assess(s: dict[str, Any], ident: str, *, synthetic_saving: int = 0) -> str:
    inputs = [problem(2201), problem(2202, hosts=5)]
    plan = EvaluationPlan(
        candidate_digest=ident,
        beta_digest=f.BETA,
        execution_digest=s["service"].execution_digest,
        model_id="FICTIONAL-FRONTIER-CONFORMANCE",
        reasoning_mode="standard",
        reasoning_effort="max",
        policy_digest=f.POLICY,
        matched_tools_digest=f.ZERO,
        resource_rules_digest=f.ZERO,
        recipient_capabilities_digest=f.ZERO,
        retention_cost_record="placement-assessment",
        origin_input_digests=f.entry(s, ident)["origin_input_digests"],
        fresh_inputs=inputs,
        fresh_input_digests=[input_digest(p) for p in inputs],
        planned_reuses=100,
        remaining_retention_micro_usd=1,
        prospective_basis="FICTIONAL protocol horizon; no measured frontier or demand",
    )
    signed_plan = f.signed(s, "plan", "evaluator", plan.model_dump(), "placement-plan")
    s["service"].freeze(signed_plan)
    pairs: list[list[Any]] = [[], [], []]
    for index, stamp in enumerate(plan.fresh_input_digests):
        outputs = [digest("fixture-output", [index, arm]) for arm in range(2)]
        for arm in range(2):
            raw = {
                "candidate_digest": ident if arm == 0 else None,
                "input_digest": stamp,
                "output_digest": outputs[arm],
                "beta_digest": f.BETA,
                "model_id": plan.model_id,
                "reasoning_mode": "standard",
                "reasoning_effort": "max",
                "tools_digest": f.ZERO,
                "resource_rules_digest": f.ZERO,
                "recipient_capabilities_digest": f.ZERO,
                "provider_response_digest": f.ZERO,
                "billing_evidence_digest": f.ZERO,
                "actual_cost_micro_usd": 10 + (synthetic_saving if arm else 0),
                "usage": {"fictional_tokens": 1},
                "started_at": int(time.time()),
                "finished_at": int(time.time()),
                "evidence_basis": "configured-executor-attestation",
            }
            receipt = sign_record(s["keys"]["executor"], "executor", "flywheel-frontier-run", raw)
            pairs[arm].append(receipt)
            f.account(
                s,
                "charge",
                {
                    "activity_id": f"placement-eval/{index}/{arm}",
                    "mission_id": "placement-assessment",
                    "bucket": "B",
                    "category": "model",
                    "accrued_micro_usd": raw["actual_cost_micro_usd"],
                    "paid_micro_usd": 0,
                    "basis": "attested",
                    "evidence_digest": digest("flywheel-frontier-run-record", receipt),
                    "note": "FICTIONAL frontier receipt; no actual frontier call",
                },
                f"placement-charge/{index}/{arm}",
            )
        pairs[2].append(
            sign_record(
                s["keys"]["acceptor"],
                "acceptor",
                "flywheel-pair-acceptance",
                {
                    "plan_digest": digest("flywheel-plan", signed_plan),
                    "input_digest": stamp,
                    "candidate_output": outputs[0],
                    "beta_output": outputs[1],
                    "candidate_digest": ident,
                    "candidate_correct": True,
                    "beta_correct": True,
                    "evidence_digest": f.ZERO,
                },
            )
        )
    seal(s, "placement-assessment", "B")
    evidence = AlphaEvidence(
        plan_digest=digest("flywheel-plan", signed_plan),
        candidate_runs=pairs[0],
        beta_runs=pairs[1],
        acceptance=pairs[2],
        lower_net_saving_per_use_micro_usd=synthetic_saving,
        uncertainty_basis="FICTIONAL conformance bound",
        false_passes=0,
        false_rejections=0,
        abstentions=0,
        correlated_failure_analysis="No actual model comparison",
    )
    return s["service"].evaluate(f.signed(s, "evidence", "evaluator", evidence.model_dump(), "placement-evidence"))


@pytest.mark.parametrize("order", ["given", "largest-demand", "scarcity", "regret"])
@pytest.mark.parametrize("bound", ["static", "residual"])
def test_every_retained_procedure_matches_independent_oracle(order: str, bound: str) -> None:
    for seed in range(12):
        p = problem(seed, tight=bool(seed % 2))
        workflow = PlacementWorkflow(version=2, order=order, bound=bound, capacity_pruning=True)
        outcome = execute_workflow(p, workflow, lambda n: None)
        assert verify_placement(p, outcome)["accepted_finite_result"]
        assert outcome["logical_units"] > outcome["search_nodes"]


def test_environment_reset_transition_and_failed_budget_preserve_objective() -> None:
    env = PlacementEnvironment(PlacementWorkflow(version=1))
    task = GymTask(task_id="task", partition="training", family="test", problem=problem(4))
    first = env.reset(task)
    with pytest.raises(ValueError):
        env.step({"type": "deploy-infrastructure"}, lambda: True)
    env.step({"type": "run-workflow"}, lambda: True)
    assert env.outcome()["verification"]["accepted_finite_result"]
    with pytest.raises(Conflict):
        env.step({"type": "run-workflow"}, lambda: True)
    assert env.reset(task) == first
    env.reset(task.model_copy(update={"logical_limit": 1}))
    env.step({"type": "run-workflow"}, lambda: True)
    assert not env.outcome()["verification"]["accepted_finite_result"]


def test_retained_training_fresh_evaluation_and_no_automatic_admission(setup: dict[str, Any]) -> None:
    s = setup
    record = origin(s)
    frozen = campaign(s)
    assert frozen["status"] == "frozen-awaiting-protected-evaluation"
    candidate = PlacementWorkflow.model_validate(frozen["candidate"])
    assert candidate != PlacementWorkflow(version=1) and frozen["trials"]
    task = GymTask(
        task_id="fresh",
        partition="protected-evaluation",
        family="new-five-host-topology",
        problem=problem(2199, hosts=5),
    )
    result = evaluate_frozen(frozen, [task])
    assert result["technical_transfer_passed"] and result["admission"] == "do not admit"
    assert not result["live_qualified"] and not result["net_alpha_positive"]
    with pytest.raises(ValueError, match="exclude"):
        old = GymPlan.model_validate(frozen["plan"]["payload"]["plan"]).tasks[0]
        evaluate_frozen(frozen, [old.model_copy(update={"partition": "protected-evaluation"})])
    changed = copy.deepcopy(frozen)
    changed["candidate"]["bound"] = "static"
    with pytest.raises(ValueError, match="freeze"):
        evaluate_frozen(changed, [task])
    with pytest.raises(ValueError, match="Gym candidate"):
        retain(s, record, candidate, "placement-gym")
    seal(s, "placement-extra-rd", "C")
    ident = retain(s, record, candidate, "placement-gym")
    assert assess(s, ident) == "rejected"
    assert not s["library"].snapshot()[f.BRANCH]["active"]


def test_interrupted_gym_keeps_v1_unknown_cost_and_never_replays(setup: dict[str, Any]) -> None:
    s = setup
    origin(s)
    result = campaign(s, limit=1)
    assert result["candidate"] is None and result["status"] == "interrupted-or-budget-exhausted"
    assert result["original"] == PlacementWorkflow(version=1).model_dump()
    assert s["costs"].report()["unknown_costs"]
    with pytest.raises(Conflict, match="already attempted"):
        campaign(s, limit=1)


def test_synthetic_admission_actual_loading_authentication_and_revocation(setup: dict[str, Any]) -> None:
    s = setup
    record = origin(s)
    ident = retain(s, record, PlacementWorkflow(version=1))
    # This positive path uses intentionally fictional price/model attestations.
    assert assess(s, ident, synthetic_saving=20) == "assessed"
    f.control(s, ident, "validate")
    f.control(s, ident, "admit")
    resource = s["service"].catalog_resource()
    catalog = s["service"].catalog(
        f.proof(s, resource, "discover", digest("flywheel-catalog-request", {"resource": resource}))
    )
    assert catalog["manifests"][0]["candidate_digest"] == ident
    task = PlacementInvocation(
        mission_id="placement-peer",
        problem=problem(2300, hosts=5),
        beta_digest=f.BETA,
        policy_digest=f.POLICY,
        recipient_capabilities_digest=f.ZERO,
        prerequisite_digests=[],
        logical_limit=100_000,
        cost_cap_micro_usd=100,
    )
    proof = f.proof(s, ident, "invoke", digest("flywheel-invocation", task))
    receipt = s["service"].invoke(ident, task, proof)
    assert receipt["status"] == "executed-awaiting-acceptance-and-complete-cost"
    assert verify_placement(task.problem, receipt["result"])["accepted_finite_result"]
    assert receipt["peer_identity"] and not receipt["successful_peer_reuse"] and receipt["additional_value"] is None
    with pytest.raises((Conflict, ValueError)):
        s["service"].invoke(ident, task, proof)
    next_task = task.model_copy(update={"mission_id": "after-revoke"})
    stale = f.proof(s, ident, "invoke", digest("flywheel-invocation", next_task))
    f.control(s, ident, "revoke")
    with pytest.raises(Conflict):
        s["service"].invoke(ident, next_task, stale)


def test_reusable_production_adapter_changes_real_environment_and_checks_original_objective(tmp_path: Path) -> None:
    from alpha_factory_v1.core.runtime.successor.flywheel_gym import ToolEnvironmentTask, ToolMissionEnvironment

    target = tmp_path / "counter.txt"

    class Tool:
        component = "executed-local"
        identity = {"tool": "isolated-test-file-counter"}

        def perform(self, name: str, arguments: dict[str, Any], active: Any) -> dict[str, Any]:
            assert active() and name == "increment" and arguments == {"amount": 2}
            target.write_text(str(int(target.read_text()) + arguments["amount"]))
            return {"value": int(target.read_text())}

    env = ToolMissionEnvironment(
        Tool(),
        contract_digest=f.ZERO,
        reset=lambda value: target.write_text(str(value["value"])),
        observe=lambda: {"value": int(target.read_text())},
        check=lambda task, value: {"accepted": value["value"] == 2, "original_objective": task.objectives},
    )
    task = ToolEnvironmentTask(
        task_id="counter",
        partition="training",
        initial_state={"value": 0},
        objectives=["Produce value two"],
        constraints=["Only approved increment"],
        permitted_tools=["increment"],
        max_actions=1,
        max_seconds=10,
    )
    assert env.reset(task)["state"] == {"value": 0}
    with pytest.raises(ValueError):
        env.step({"tool": "host_shell", "arguments": {}}, lambda: True)
    assert env.perform("increment", {"amount": 2}, lambda: True) == {"value": 2}
    outcome = env.outcome()
    assert outcome["verification"]["accepted"] and outcome["evidence"][0]["before"]["state"]["value"] == 0
    assert outcome["evidence"][0]["after"]["state"]["value"] == 2
    assert not outcome["authority_granted"]
    assert env.reset(task)["state"] == {"value": 0}


@pytest.mark.parametrize("attack", ["shell", "weights", "unsupported-form", "partition", "permuted-input"])
def test_skill_and_training_contracts_refuse_unsupported_or_leaking_inputs(attack: str) -> None:
    from alpha_factory_v1.core.runtime.successor.flywheel_specialists import placement_fingerprint

    if attack == "shell":
        with pytest.raises(ValueError):
            PlacementWorkflow.model_validate({"version": 1, "shell": "malicious"})
    elif attack == "weights":
        with pytest.raises(ValueError):
            PlacementWorkflow(version=1, order="update-proprietary-weights")
    elif attack == "unsupported-form":
        capability = CapabilityDescription(
            form="trained-component",
            runtime="resilient-placement/v1",
            input_contract=f.ZERO,
            output_contract=f.ZERO,
            tests_digest=f.ZERO,
            provenance_digest=f.ZERO,
            permissions=["bounded-local-compute"],
            dependencies=[],
            limitations="Unsupported",
        )
        assert not capability.supported
    elif attack == "partition":
        with pytest.raises(ValueError, match="protected"):
            GymPlan(
                campaign_id="attack",
                mission_id="attack",
                original=PlacementWorkflow(version=1),
                alternatives=[PlacementWorkflow(version=2)],
                max_logical_units=100,
                max_authorized_micro_usd=1,
                environment_digest=f.ZERO,
                expires_at=int(time.time()) + 100,
                tasks=[
                    GymTask(task_id="secret", partition="protected-evaluation", family="secret", problem=problem(5))
                ],
            )
    else:
        p = problem(19)
        q = p.model_copy(update={"demands": p.demands[::-1], "costs": p.costs[::-1], "node_budget": 1})
        assert placement_fingerprint(p) == placement_fingerprint(q)


@pytest.mark.parametrize("attack", ["changed-owner", "corrupted-capsule", "mismatched-contract"])
def test_placement_resource_boundary_attacks_preserve_unknown_or_no_execution(
    setup: dict[str, Any], attack: str
) -> None:
    from alpha_factory_v1.core.runtime.successor.transformation_library import KEY
    from alpha_factory_v1.core.runtime.successor.flywheel_access import namehash
    from alpha_factory_v1.core.runtime.successor.flywheel_capsules import Invocation
    from alpha_factory_v1.core.runtime.successor.transformation import pilot_document, pilot_request

    s = setup
    ident = retain(s, origin(s), PlacementWorkflow(version=1))
    assert assess(s, ident, synthetic_saving=20) == "assessed"
    f.control(s, ident, "validate")
    f.control(s, ident, "admit")
    task: Any = PlacementInvocation(
        mission_id="boundary-attack",
        problem=problem(2900),
        beta_digest=f.BETA,
        policy_digest=f.POLICY,
        recipient_capabilities_digest=f.ZERO,
        prerequisite_digests=[],
        logical_limit=100000,
        cost_cap_micro_usd=100,
    )
    if attack == "mismatched-contract":
        task = Invocation(
            mission_id="boundary-attack",
            document=pilot_document(),
            charter=pilot_request().charter,
            beta_digest=f.BETA,
            policy_digest=f.POLICY,
            recipient_capabilities_digest=f.ZERO,
            prerequisite_digests=[],
            logical_limit=100000,
            cost_cap_micro_usd=100,
        )
    proof = f.proof(s, ident, "invoke", digest("flywheel-invocation", task))
    if attack == "changed-owner":
        for rpc in s["rpc"]:
            rpc.owners[namehash("two.agent.agi.eth").hex()] = "0x" + "12" * 20
        with pytest.raises(ValueError):
            s["service"].invoke(ident, task, proof)
    elif attack == "mismatched-contract":
        with pytest.raises(ValueError, match="contract"):
            s["service"].invoke(ident, task, proof)
    else:
        with s["journal"].transaction() as cx:
            state, network = s["service"]._state(cx)
            network["entries"][ident]["ciphertext"] = "corrupted-base64"
            s["service"]._commit(cx, state)
        receipt = s["service"].invoke(ident, task, proof)
        assert receipt["status"] == "failed" and receipt["result"] is None
        assert s["costs"].report()["unknown_costs"]


def test_signed_training_terms_are_snapshotted_before_environment_callbacks(setup: dict[str, Any]) -> None:
    s = setup
    origin(s)
    first = campaign(s)
    seal(s, "placement-extra-rd", "C")
    payload = copy.deepcopy(first["plan"]["payload"])
    payload["plan"]["campaign_id"] = "snapshot-campaign"
    payload["plan"]["mission_id"] = "snapshot-rd"
    signed = sign_record(s["keys"]["controller"], "controller", "flywheel-gym-plan", payload)
    original_limit = payload["plan"]["max_logical_units"]

    def current_environment() -> str:
        signed.payload["plan"]["max_logical_units"] = 1
        return s["service"]._execution_binding()

    result = GymCampaign(
        s["costs"], s["service"].checkpoint, s["service"].execution_digest, current_environment=current_environment
    ).run(signed)
    assert result["plan"]["payload"]["plan"]["max_logical_units"] == original_limit
    assert result["status"] == "frozen-awaiting-protected-evaluation"
    assert signed.payload["plan"]["max_logical_units"] == 1
