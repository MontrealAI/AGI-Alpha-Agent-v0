# SPDX-License-Identifier: Apache-2.0
"""Prospective cohort and real executor tests with explicitly fictional production."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import (
    ComparisonArm,
    ComparisonCase,
    ComparisonCost,
    ComparisonPlan,
    ComparisonTrial,
    Discovery,
    ResourceBudget,
)
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
    operation_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_experiments import PlacementProblem
from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, sign_record
from scripts.record_general_flywheel import ScriptedModel, SystemsTool
import test_flywheel_discovery as d
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def profile() -> ExecutionProfile:
    return ExecutionProfile(
        model_id="scripted-protocol-fixture/v1",
        reasoning_effort="high",
        supported_efforts=["high"],
        qualification_digest=f.ZERO,
        tools=[
            {
                "type": "function",
                "name": "placement_experiment",
                "description": "Actual bounded placement computation",
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


def plan(state: dict[str, Any], count: int = 2) -> ComparisonPlan:
    opportunity = d.opportunity(state)
    budget = ResourceBudget(tokens=1000, tool_actions=2, seconds=30, cost_cap_micro_usd=1000)
    workflows = {
        "U": "Use the provided exact solver and inspect its constraint checks.",
        "E": "Preserve original criteria, execute the provided exact solver, then independently check the output.",
    }
    workflows["E+"] = workflows["E"]
    arms = [
        ComparisonArm(
            role=role,
            model_profile_digest=digest("flywheel-execution-profile", profile()),
            access_and_tools_digest=digest("flywheel-execution-environment-contract", SystemsTool().identity),
            resource_budget=budget,
            workflow_digest=digest("comparison-workflow", workflows[role]),
            retained_capability_digest=digest("comparison-fixture-retained-input", {"supplied": True})
            if role == "E+"
            else None,
            starting_capabilities=["Same available exact solver and independent finite checker"],
            baseline_definition="Supplied protocol fixture, not a sampled ordinary frontier-model user",
        )
        for role in ("U", "E", "E+")
    ]
    cases = []
    for index in range(count):
        shared = {"problem": s.problem(7030 + index, services=3).model_dump()}
        trials = []
        for arm in arms:
            operation = f"comparison-{index}-{arm.role.replace('+', 'plus')}"
            trials.append(
                ComparisonTrial(
                    role=arm.role,
                    operation_id=operation,
                    mission=ExecutionMission(
                        mission_id=operation,
                        beneficiary="Internal protocol research team",
                        goal=opportunity.purpose.useful_purpose,
                        challenged_assumption="A comparison plan alone establishes no measured advantage",
                        deliverable=opportunity.purpose.deliverable,
                        acceptance_criteria=opportunity.purpose.acceptance_criteria,
                        inputs={
                            **shared,
                            "comparison_workflow": workflows[arm.role],
                            "comparison_retained": arm.retained_capability_digest,
                        },
                        sharing_rights="Original synthetic Apache-2.0 protocol fixtures",
                        stop_conditions=["Finite local compute and existing separately signed permissions"],
                        mode="hybrid",
                        components={
                            "model": "simulated",
                            "tools": "executed-local",
                            "identity": "simulated",
                            "acceptance": "executed-local",
                            "market": "simulated",
                        },
                        max_actions=budget.tool_actions,
                        max_seconds=budget.seconds,
                        max_turns=3,
                    ),
                )
            )
        cases.append(
            ComparisonCase(
                case_id=f"case-{index}",
                recipient_id="origin-fixture" if index == 0 else "recipient-fixture",
                phase="primary" if index == 0 else "fresh-recipient",
                shared_inputs_digest=digest("comparison-shared-inputs", shared),
                trials=trials,
            )
        )
    return ComparisonPlan(
        comparison_id="prospective-placement-protocol",
        opportunity_id=opportunity.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", opportunity),
        purpose=opportunity.purpose,
        human_reference=d.e.offering(state).human_reference,
        arms=arms,
        ordinary_use_basis="Equal methods and resources; scripted controls are not representative human users",
        fresh_instance_policy="Different frozen inputs and declared fixture recipient; training exposure unverified",
        complete_cost_policy="Trial A, present B/C and declared extra costs, once; fictional amounts are not bills",
        evidence=[d.evidence(state)],
        cases=cases,
    )


def freeze(state: dict[str, Any], spec: ComparisonPlan | None = None) -> ComparisonPlan:
    spec = spec or plan(state)
    d.register(state)
    Discovery(state["service"]).apply(d.command(state, "comparison", spec, "freeze-comparison"))
    s.funding(state)
    return spec


def run_trial(
    state: dict[str, Any],
    trial: ComparisonTrial,
    *,
    fail: bool = False,
    accept: bool = True,
    controller: str = "controller",
    transport: Any = None,
    execution_principal: str | None = None,
) -> dict[str, Any]:
    principal = controller if execution_principal is None else execution_principal
    environment = SystemsTool()
    instance = PlacementProblem.model_validate(trial.mission.inputs["problem"])
    transport = ScriptedModel(instance) if transport is None else transport
    if fail:

        def refuse(name: str, arguments: dict[str, Any], active: Any) -> dict[str, Any]:
            raise RuntimeError("Deliberate failed-tool conformance case, not an ordinary-user control")

        environment.perform = refuse  # type: ignore[method-assign]
    terms = ExecutionPermit(
        operation_id=trial.operation_id,
        request_digest=digest("flywheel-execution-request", trial.mission),
        profile_digest=digest("flywheel-execution-profile", profile()),
        environment_digest=digest("flywheel-execution-environment-contract", environment.identity),
        config_digest=runtime_digest(state["journal"].config.model_dump()),
        quota_evidence_digest=f.ZERO,
        pricing_evidence_digest=f.ZERO,
        max_authorized_micro_usd=1000,
        expires_at=int(time.time()) + 3600,
        bucket="A",
    )
    signed = sign_record(
        state["keys"][principal],
        principal,
        "flywheel-execution-permit",
        {"journal_identity": state["journal"].identity, "permit": terms.model_dump()},
    )
    MissionExecutor(state["journal"], state["trust"], state["costs"], transport, environment).run(
        trial.mission, profile(), signed
    )
    record = dict(state["journal"].latest(operation_key(trial.operation_id)))
    if accept and not fail:
        seal_and_accept(state, trial, record)
    return record


def seal_and_accept(state: dict[str, Any], trial: ComparisonTrial, record: dict[str, Any]) -> None:
    s.seal(state, trial.mission.mission_id, "A")
    state["service"].accept_general_origin(
        f.signed(
            state,
            "general-acceptance",
            "acceptor",
            {
                "operation_id": trial.operation_id,
                "execution_record_digest": record["digest"],
                "output_digest": digest("general-delivered-output", record["result"]),
                "rights_evidence": f.ZERO,
            },
            "accept/" + trial.operation_id,
        )
    )


def reconcile_trial_cost(state: dict[str, Any], trial: ComparisonTrial, amount: int) -> None:
    row = state["costs"].snapshot()["charges"]["execution/" + trial.operation_id]
    raw = {field: row[field] for field in Charge.model_fields}
    raw.update(accrued_micro_usd=amount, basis="attested", note="Fictional cost reconciliation, not a provider bill")
    f.account(state, "resolve", raw, "resolve/" + row["activity_id"])


def report(state: dict[str, Any], spec: ComparisonPlan) -> dict[str, Any]:
    return Discovery(state["service"]).inspect("comparison-result", spec.comparison_id)


def rewrite(state: dict[str, Any], journal_key: str, transform: Any) -> None:
    with state["journal"].transaction() as cx:
        state["service"]._state(cx)
        value = state["journal"].document(state["journal"].latest(journal_key, cx))
        transform(value)
        state["journal"].append(cx, journal_key, value)
        state["service"].checkpoint.advance(state["journal"], cx)


def test_complete_denominator_is_read_only_and_legacy_plans_stay_unmeasured(setup: dict[str, Any]) -> None:
    spec = freeze(setup)
    before = setup["costs"].snapshot()
    first = report(setup, spec)
    assert first == report(setup, spec)
    assert before == setup["costs"].snapshot()
    assert first["planned_cases"] == 2 and len(first["cells"]) == 6
    assert all(arm["planned"] == arm["unassessed"] == 2 for arm in first["arms"].values())
    assert first["contrasts"]["operational"]["possible_difference_bounds"] == [-2, 2]
    assert first["contrasts"]["retained"]["cost_saving_micro_usd"] is None
    legacy = d.comparison(setup).model_copy(update={"comparison_id": "legacy"})
    Discovery(setup["service"]).apply(d.command(setup, "comparison", legacy, "legacy-plan"))
    assert report(setup, legacy)["stage"] == "legacy-plan-without-frozen-cases"


def test_actual_equal_protocol_runs_preserve_zero_alpha_and_component_provenance(setup: dict[str, Any]) -> None:
    spec = freeze(setup)
    for case in spec.cases:
        for trial in case.trials:
            run_trial(setup, trial)
    value = report(setup, spec)
    assert all(arm["accepted"] == arm["planned"] == 2 and arm["cost_complete"] for arm in value["arms"].values())
    assert all(
        row["complete_matched_outcomes"] and row["accepted_difference"] == 0 for row in value["contrasts"].values()
    )
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] == "0"
    assert value["contrasts"]["retained"]["cost_saving_micro_usd"] is None
    assert value["model_evidence"] == "simulated-model-protocol-fixture"
    assert not any(
        value[name]
        for name in (
            "authority_granted",
            "customer_acceptance_established",
            "commercial_profit_established",
            "retained_invocation_established",
        )
    )
    assert value["human_reference_role"].startswith("commercial reference only")


def test_failures_and_unassessed_work_cannot_disappear_from_the_cohort(setup: dict[str, Any]) -> None:
    spec = freeze(setup)
    run_trial(setup, spec.cases[0].trials[0], fail=True)
    s.seal(setup, spec.cases[0].trials[0].mission.mission_id, "A")
    run_trial(setup, spec.cases[0].trials[1])
    run_trial(setup, spec.cases[0].trials[2], accept=False)
    value = report(setup, spec)
    assert value["arms"]["U"]["failed"] == 1 and value["arms"]["U"]["planned"] == 2
    assert value["arms"]["E+"]["unassessed"] == 2
    assert value["contrasts"]["operational"]["accepted_difference"] == 1
    assert value["contrasts"]["operational"]["possible_difference_bounds"] == [0, 2]
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["retained"]["cost_saving_micro_usd"] is None


@pytest.mark.parametrize(
    "attack",
    [
        "inputs",
        "criteria",
        "workflow",
        "retained",
        "purpose",
        "budget",
        "roles",
        "mission",
        "operation",
        "mode",
        "beneficiary",
    ],
)
def test_frozen_cases_reject_substitution_and_unmatched_controls(setup: dict[str, Any], attack: str) -> None:
    raw = plan(setup).model_dump()
    trials = raw["cases"][0]["trials"]
    mission = trials[0]["mission"]
    if attack == "inputs":
        mission["inputs"]["problem"]["demands"][0] += 1
    elif attack == "criteria":
        mission["acceptance_criteria"] = ["An easier task"]
    elif attack == "workflow":
        mission["inputs"]["comparison_workflow"] = "An unreported method"
    elif attack == "retained":
        mission["inputs"]["comparison_retained"] = "1" * 64
    elif attack == "purpose":
        mission["goal"] = "A different useful purpose"
    elif attack == "budget":
        mission["max_actions"] += 1
    elif attack == "roles":
        trials[0]["role"] = "E"
    elif attack == "mission":
        trials[0]["mission"]["mission_id"] = trials[1]["mission"]["mission_id"]
    elif attack == "operation":
        trials[0]["operation_id"] = trials[1]["operation_id"]
    elif attack == "mode":
        mission["mode"] = "simulation"
    else:
        mission["beneficiary"] = "Different quality obligations"
    with pytest.raises(ValueError):
        ComparisonPlan.model_validate(raw)


@pytest.mark.parametrize("attack", ["repeat-input", "same-recipient", "no-primary", "cross-mode", "duplicate-case"])
def test_fresh_work_declarations_have_prospective_distinct_inputs(setup: dict[str, Any], attack: str) -> None:
    raw = plan(setup).model_dump()
    if attack == "repeat-input":
        raw["cases"][1]["shared_inputs_digest"] = raw["cases"][0]["shared_inputs_digest"]
        for old, new in zip(raw["cases"][0]["trials"], raw["cases"][1]["trials"]):
            new["mission"]["inputs"] = copy.deepcopy(old["mission"]["inputs"])
    elif attack == "same-recipient":
        raw["cases"][1]["recipient_id"] = raw["cases"][0]["recipient_id"]
    elif attack == "no-primary":
        raw["cases"][0]["phase"] = "fresh-recipient"
    elif attack == "cross-mode":
        for case in raw["cases"]:
            for trial in case["trials"]:
                trial["mission"]["mode"] = "simulation"
    else:
        raw["cases"][1]["case_id"] = raw["cases"][0]["case_id"]
    with pytest.raises(ValueError):
        freeze(setup, ComparisonPlan.model_validate(raw))


def test_retrospective_freeze_and_duplicate_plan_claims_refuse_atomically(setup: dict[str, Any]) -> None:
    spec = freeze(setup)
    duplicate = spec.model_copy(update={"comparison_id": "another-comparison"})
    with pytest.raises(Conflict, match="already belongs"):
        Discovery(setup["service"]).apply(d.command(setup, "comparison", duplicate, "duplicate-plan"))
    assert Discovery(setup["service"])._read("comparison", duplicate.comparison_id, None) is None
    run_trial(setup, spec.cases[0].trials[0])
    with pytest.raises(Conflict, match="first execution"):
        Discovery(setup["service"]).apply(d.command(setup, "comparison", duplicate, "retrospective-plan"))


@pytest.mark.parametrize("attack", ["mission", "profile", "environment", "cap", "configuration", "bucket"])
def test_actual_receipt_must_match_the_frozen_condition(setup: dict[str, Any], attack: str) -> None:
    spec = freeze(setup, plan(setup, 1))
    trial = spec.cases[0].trials[0]
    run_trial(setup, trial)

    def change(value: dict[str, Any]) -> None:
        permit = value["permit"]["payload"]["permit"]
        if attack == "mission":
            value["mission"]["inputs"]["comparison_workflow"] = "Different context"
        elif attack == "profile":
            value["profile"]["model_id"] = "a-different-model"
        elif attack == "environment":
            permit["environment_digest"] = "1" * 64
        elif attack == "cap":
            permit["max_authorized_micro_usd"] += 1
        elif attack == "configuration":
            permit["config_digest"] = "1" * 64
        else:
            permit["bucket"] = "C"

    rewrite(setup, operation_key(trial.operation_id), change)
    value = report(setup, spec)
    assert value["cells"][0]["status"] == "binding-mismatch"
    assert value["arms"]["U"]["accepted"] == 0
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]


def test_original_mission_cost_identity_is_used_even_when_operation_text_differs(setup: dict[str, Any]) -> None:
    raw = plan(setup, 1).model_dump()
    raw["cases"][0]["trials"][0]["operation_id"] = "different-operation-namespace"
    spec = freeze(setup, ComparisonPlan.model_validate(raw))
    trial = spec.cases[0].trials[0]
    run_trial(setup, trial, accept=False)
    s.seal(setup, trial.mission.mission_id, "A")
    value = report(setup, spec)
    assert value["arms"]["U"]["known_costs_micro_usd"]["A"] == "1"
    assert value["cells"][0]["ledger_mission_id"] == trial.mission.mission_id
    assert value["cells"][0]["status"] == "acceptance-invalid-or-unsupported"


def test_additional_costs_count_once_and_unknowns_hold_the_cost_contrast(setup: dict[str, Any]) -> None:
    spec = plan(setup, 1)
    spec = spec.model_copy(
        update={"additional_costs": [ComparisonCost(role="E+", mission_id="additional-assessment", bucket="B")]}
    )
    spec = freeze(setup, spec)
    for trial in spec.cases[0].trials:
        run_trial(setup, trial)
    assert report(setup, spec)["contrasts"]["retained"]["cost_saving_micro_usd"] is None
    f.account(
        setup,
        "charge",
        {
            "activity_id": "extra-screen",
            "mission_id": "additional-assessment",
            "bucket": "B",
            "category": "human",
            "accrued_micro_usd": 77,
            "paid_micro_usd": 0,
            "basis": "attested",
            "evidence_digest": f.ZERO,
            "note": "Fictional conformance assessment amount, not real billing",
        },
        "extra-screen",
    )
    s.seal(setup, "additional-assessment", "B")
    before = setup["costs"].snapshot()
    value = report(setup, spec)
    assert value["contrasts"]["retained"]["cost_saving_micro_usd"] == "-77"
    assert value["arms"]["E+"]["known_costs_micro_usd"] == {"A": "1", "B": "77", "C": "0"}
    assert before == setup["costs"].snapshot()
    duplicate = spec.model_dump()
    duplicate["additional_costs"].append(duplicate["additional_costs"][0])
    with pytest.raises(ValueError, match="duplicate"):
        ComparisonPlan.model_validate(duplicate)


def test_stale_evidence_keeps_historical_cells_but_withholds_current_comparison(setup: dict[str, Any]) -> None:
    spec = freeze(setup, plan(setup, 1))
    for trial in spec.cases[0].trials:
        run_trial(setup, trial)
    rewrite(setup, spec.evidence[0].journal_key, lambda value: value.update(new_evidence="Requires reassessment"))
    value = report(setup, spec)
    assert not value["current_evidence_valid"]
    assert value["arms"]["E"]["accepted"] == 1
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None


@pytest.mark.parametrize("attack", ["missing-usage", "token-overrun", "stale-acceptance"])
def test_resource_and_acceptance_limits_do_not_turn_into_confirmed_alpha(setup: dict[str, Any], attack: str) -> None:
    spec = freeze(setup, plan(setup, 1))
    for trial in spec.cases[0].trials:
        run_trial(setup, trial)

    def change(value: dict[str, Any]) -> None:
        if attack == "missing-usage":
            value["usage_events"] = []
        elif attack == "token-overrun":
            value["usage_events"][0]["usage"]["total_tokens"] = 1001
        else:
            value["result"]["limitations"].append("Changed after original acceptance")

    rewrite(setup, operation_key(spec.cases[0].trials[0].operation_id), change)
    value = report(setup, spec)
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None


@pytest.mark.parametrize("change", ["source", "controller-revocation", "acceptor-revocation"])
def test_requalification_does_not_inherit_current_evidence_after_source_or_trust_changes(
    setup: dict[str, Any], change: str
) -> None:
    spec = freeze(setup, plan(setup, 1))
    for trial in spec.cases[0].trials:
        run_trial(setup, trial)
    if change == "source":
        from alpha_factory_v1.core.runtime.successor.flywheel_discovery import key

        rewrite(setup, key("comparison", spec.comparison_id), lambda value: value.update(source="1" * 64))
    else:
        setup["trust"].revoke("controller" if change == "controller-revocation" else "acceptor")
    value = report(setup, spec)
    if change != "source":
        assert all(arm["historical_acceptance_recorded"] == 1 for arm in value["arms"].values())
        assert all(cell["historical_acceptance_recorded"] for cell in value["cells"])
        assert all(arm["accepted"] == 0 for arm in value["arms"].values())
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None


def additional_principal(state: dict[str, Any], name: str, existing: str, role: str) -> None:
    """Install an explicit local fixture trust anchor, independently of incoming data."""
    state["keys"][name] = state["keys"][existing]
    original = state["trust"].anchor(existing, role)
    state["trust"]._anchors[name] = TrustAnchor(original.public_key, frozenset({role}))


@pytest.mark.parametrize("support", ["execution", "charge", "seal", "extra-retention-charge"])
def test_revoked_supporting_signer_withholds_current_qualification_without_erasing_history(
    setup: dict[str, Any], support: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    principal = "separate-executor" if support == "execution" else "separate-accounting"
    role = "controller" if support == "execution" else "accounting"
    additional_principal(setup, principal, "controller" if support == "execution" else "accountant", role)
    original_account = f.account

    def selective_account(state: dict[str, Any], action: str, record: Any, operation: str) -> None:
        selected = (
            support == "charge"
            and action == "charge"
            or support == "seal"
            and action in {"seal", "seal-retention", "seal-investment"}
            or support == "extra-retention-charge"
            and action == "charge"
            and record["bucket"] == "B"
        )
        if not selected:
            original_account(state, action, record, operation)
            return
        state["costs"].apply(
            sign_record(
                state["keys"][principal],
                principal,
                "flywheel-cost-command",
                {
                    "journal_identity": state["journal"].identity,
                    "operation_id": operation,
                    "action": action,
                    "record": record,
                },
            )
        )

    monkeypatch.setattr(f, "account", selective_account)
    spec = plan(setup, 1)
    if support == "extra-retention-charge":
        spec = spec.model_copy(update={"additional_costs": [ComparisonCost(role="E+", mission_id="extra", bucket="B")]})
    spec = freeze(setup, spec)
    for trial in spec.cases[0].trials:
        run_trial(setup, trial, execution_principal=principal if support == "execution" else "controller")
    if support == "extra-retention-charge":
        s.seal(setup, "extra", "B")
    before = report(setup, spec)
    assert before["current_evidence_valid"]
    assert before["contrasts"]["operational"]["complete_matched_outcomes"]
    assert before["contrasts"]["operational"]["cost_saving_micro_usd"] == "0"
    setup["trust"].revoke(principal)
    after = report(setup, spec)
    assert not after["current_evidence_valid"]
    assert all(arm["planned"] == 1 for arm in after["arms"].values())
    assert all(arm["accepted"] == (0 if support == "execution" else 1) for arm in after["arms"].values())
    assert [cell["execution_digest"] for cell in after["cells"]] == [
        cell["execution_digest"] for cell in before["cells"]
    ]
    assert [cell["acceptance_digest"] for cell in after["cells"]] == [
        cell["acceptance_digest"] for cell in before["cells"]
    ]
    assert all(arm["historical_acceptance_recorded"] == 1 for arm in after["arms"].values())
    assert all(cell["historical_acceptance_recorded"] for cell in after["cells"])
    assert all(not contrast["complete_matched_outcomes"] for contrast in after["contrasts"].values())
    assert all(contrast["cost_saving_micro_usd"] is None for contrast in after["contrasts"].values())


@pytest.mark.parametrize("attempt", ["not-attempted", "binding-mismatch", "bound-fixture"])
def test_model_evidence_comes_from_bound_receipts_instead_of_declared_live_cells(
    setup: dict[str, Any], attempt: str
) -> None:
    raw = plan(setup, 1).model_dump()
    for trial in raw["cases"][0]["trials"]:
        trial["mission"]["components"]["model"] = "live" if attempt == "not-attempted" else "simulated"
    spec = freeze(setup, ComparisonPlan.model_validate(raw))
    if attempt != "not-attempted":
        trial = spec.cases[0].trials[0]
        run_trial(setup, trial)
        if attempt == "binding-mismatch":
            rewrite(setup, operation_key(trial.operation_id), lambda value: value["profile"].update(model_id="wrong"))
    value = report(setup, spec)
    assert value["planned_cases"] == 1 and len(value["cells"]) == 3
    assert value["model_evidence"] == (
        "simulated-model-protocol-fixture" if attempt == "bound-fixture" else "no-executions"
    )
    assert not value["commercial_profit_established"]


@pytest.mark.parametrize(
    "role,amount,within",
    [("U", 1001, False), ("E", 1001, False), ("E+", 1001, False), ("E", 0, True), ("E", 999, True), ("E", 1000, True)],
)
def test_current_delivery_accrual_must_fit_the_original_frozen_trial_cap(
    setup: dict[str, Any], role: str, amount: int, within: bool
) -> None:
    spec = freeze(setup, plan(setup, 1))
    for trial in spec.cases[0].trials:
        record = run_trial(setup, trial, accept=False)
        reconcile_trial_cost(setup, trial, amount if trial.role == role else 1)
        seal_and_accept(setup, trial, record)
    value = report(setup, spec)
    target = next(cell for cell in value["cells"] if cell["role"] == role)
    assert target["accepted"] and target["outcome_known"]
    assert value["arms"][role]["known_costs_micro_usd"]["A"] == str(amount)
    assert len(value["cells"]) == 3 and value["planned_cases"] == 1
    assert value["current_evidence_valid"]
    assert target["within_observed_limits"] is within
    for name, roles in (("operational", {"U", "E"}), ("retained", {"E", "E+"})):
        assert value["contrasts"][name]["complete_matched_outcomes"] is (within or role not in roles)
        if not within and role in roles:
            assert value["contrasts"][name]["cost_saving_micro_usd"] is None


def test_fresh_recipient_late_reconciliation_cannot_requalify_an_overcap_trial(setup: dict[str, Any]) -> None:
    spec = freeze(setup)
    target = spec.cases[1].trials[1]
    for case in spec.cases:
        for trial in case.trials:
            if trial != target:
                run_trial(setup, trial)
    target_record = run_trial(setup, target, accept=False)
    for stage in ("unknown", "resolved-unsealed", "complete-overcap"):
        if stage == "resolved-unsealed":
            reconcile_trial_cost(setup, target, 1001)
        elif stage == "complete-overcap":
            seal_and_accept(setup, target, target_record)
        value = report(setup, spec)
        cell = next(row for row in value["cells"] if row["operation_id"] == target.operation_id)
        assert len(value["cells"]) == 6 and value["arms"]["E"]["planned"] == 2
        assert cell["phase"] == "fresh-recipient" and cell["execution_digest"] == target_record["digest"]
        assert not cell["within_observed_limits"], stage
        assert not value["contrasts"]["operational"]["complete_matched_outcomes"], stage
        assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None
    assert value["arms"]["E"]["accepted"] == 2
    assert value["arms"]["E"]["known_costs_micro_usd"]["A"] == "1002"


def test_known_under_cap_amount_without_completeness_is_not_a_budget_pass(setup: dict[str, Any]) -> None:
    spec = freeze(setup, plan(setup, 1))
    trial = spec.cases[0].trials[1]
    record = run_trial(setup, trial, accept=False)
    reconcile_trial_cost(setup, trial, 1000)
    before = report(setup, spec)
    assert before["arms"]["E"]["known_costs_micro_usd"]["A"] == "1000"
    assert not before["cells"][1]["within_observed_limits"]
    assert before["contrasts"]["operational"]["cost_saving_micro_usd"] is None
    seal_and_accept(setup, trial, record)
    after = report(setup, spec)
    assert after["cells"][1]["within_observed_limits"]
    assert after["cells"][1]["accepted"]


def test_customer_refund_and_refused_negative_expense_do_not_net_away_delivery_overrun(setup: dict[str, Any]) -> None:
    spec = freeze(setup, plan(setup, 1))
    target = spec.cases[0].trials[1]
    for trial in spec.cases[0].trials:
        record = run_trial(setup, trial, accept=False)
        reconcile_trial_cost(setup, trial, 1001 if trial == target else 1)
        seal_and_accept(setup, trial, record)
    f.account(
        setup,
        "customer-deposit",
        {
            "receipt_id": "comparison-fictional-deposit",
            "mission_id": target.mission.mission_id,
            "amount_micro_usd": 2000,
            "purpose": "service",
            "service_price_micro_usd": 2000,
            "mode": "synthetic",
            "evidence_digest": digest("comparison-fixture-deposit", {}),
            "note": "Fictional receipt only; no actual collection or execution funds",
        },
        "comparison-deposit",
    )
    f.account(
        setup,
        "customer-refund",
        {
            "event_id": "comparison-fictional-refund",
            "receipt_id": "comparison-fictional-deposit",
            "amount_micro_usd": 2000,
            "allocation": "unearned",
            "evidence_digest": digest("comparison-fixture-refund", {}),
            "reason": "Full fictional refund; incurred delivery cost remains incurred",
        },
        "comparison-refund",
    )
    before = setup["costs"].snapshot()
    with pytest.raises(ValueError):
        f.account(
            setup,
            "charge",
            {
                "activity_id": "refused-negative-expense",
                "mission_id": "negative-expense-fixture",
                "bucket": "A",
                "category": "correction",
                "accrued_micro_usd": -1001,
                "paid_micro_usd": 0,
                "basis": "attested",
                "evidence_digest": f.ZERO,
                "note": "Forbidden negative expense cannot cancel another mission's cost",
            },
            "comparison-negative-expense",
        )
    assert before == setup["costs"].snapshot()
    value = report(setup, spec)
    assert value["arms"]["E"]["accepted"] == 1
    assert value["arms"]["E"]["known_costs_micro_usd"]["A"] == "1001"
    assert not value["cells"][1]["within_observed_limits"]
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None


@pytest.mark.parametrize(
    "attack", ["operation", "execution", "output", "journal", "signature", "receipt", "role", "key"]
)
def test_historical_acceptance_requires_exact_bound_receipt_and_configured_signature(
    setup: dict[str, Any], attack: str
) -> None:
    from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY

    spec = freeze(setup, plan(setup, 1))
    trial = spec.cases[0].trials[0]
    run_trial(setup, trial)
    original = report(setup, spec)
    assert original["cells"][0]["historical_acceptance_recorded"]
    journal_key = ACCEPTANCE_KEY + trial.operation_id

    def change(value: dict[str, Any]) -> None:
        envelope = value["acceptance"]
        payload = envelope["payload"]
        if attack == "operation":
            payload["record"]["operation_id"] = "another-operation"
        elif attack == "execution":
            payload["record"]["execution_record_digest"] = "1" * 64
        elif attack == "output":
            payload["record"]["output_digest"] = "1" * 64
        elif attack == "journal":
            payload["journal_identity"] = "another-journal"
        elif attack == "receipt":
            value["record_digest"] = "1" * 64
        elif attack == "signature":
            envelope["signature"] = ("A" if envelope["signature"][0] != "A" else "B") + envelope["signature"][1:]
            return
        else:
            return
        value["acceptance"] = sign_record(
            setup["keys"]["acceptor"], "acceptor", envelope["domain"], payload
        ).model_dump()

    if attack == "role":
        anchor = setup["trust"]._anchors["acceptor"]
        setup["trust"]._anchors["acceptor"] = TrustAnchor(anchor.public_key, frozenset())
    elif attack == "key":
        del setup["trust"]._anchors["acceptor"]
    else:
        rewrite(setup, journal_key, change)
    value = report(setup, spec)
    cell = value["cells"][0]
    assert not cell["historical_acceptance_recorded"]
    assert value["arms"]["U"]["historical_acceptance_recorded"] == 0
    assert value["arms"]["U"]["planned"] == 1 and len(value["cells"]) == 3
    assert cell["historical_acceptance_evidence"] == {
        "schema_version": 1,
        "journal_key": journal_key,
        "record_digest": setup["journal"].latest(journal_key)["digest"],
    }
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None


def add_signer(state: dict[str, Any], principal: str, role: str) -> None:
    key = f.Ed25519PrivateKey.generate()
    state["keys"][principal] = key
    state["trust"]._anchors[principal] = TrustAnchor(
        key.public_key().public_bytes(f.Encoding.Raw, f.PublicFormat.Raw).hex(), frozenset({role})
    )


def account_as(state: dict[str, Any], action: str, record: Any, operation: str, principal: str) -> None:
    state["costs"].apply(
        sign_record(
            state["keys"][principal],
            principal,
            "flywheel-cost-command",
            {
                "journal_identity": state["journal"].identity,
                "operation_id": operation,
                "action": action,
                "record": record,
            },
        )
    )


def test_revoked_distinct_execution_controller_keeps_observations_without_current_contrasts(
    setup: dict[str, Any],
) -> None:
    spec = freeze(setup, plan(setup, 1))
    add_signer(setup, "delivery-controller", "controller")
    for trial in spec.cases[0].trials:
        run_trial(setup, trial, controller="delivery-controller")
    before = report(setup, spec)
    assert before["current_evidence_valid"]
    assert before["contrasts"]["operational"]["cost_saving_micro_usd"] == "0"
    setup["trust"].revoke("delivery-controller")
    after = report(setup, spec)
    assert not after["current_evidence_valid"]
    assert after["planned_cases"] == before["planned_cases"] == 1 and len(after["cells"]) == 3
    assert all(arm["accepted"] == 0 and arm["historical_acceptance_recorded"] == arm["planned"] == 1
               for arm in after["arms"].values())
    assert [cell["execution_digest"] for cell in after["cells"]] == [
        cell["execution_digest"] for cell in before["cells"]
    ]
    assert not any(cell["execution_authority_current"] for cell in after["cells"])
    assert not any(row["complete_matched_outcomes"] for row in after["contrasts"].values())
    assert all(row["cost_saving_micro_usd"] is None for row in after["contrasts"].values())


@pytest.mark.parametrize("support", ["charge", "original-charge", "seal-A", "seal-B", "seal-C"])
def test_revoked_supporting_accountant_invalidates_only_current_qualification(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch, support: str
) -> None:
    add_signer(setup, "retired-accountant", "accounting")
    bucket = "C" if support == "seal-C" else "B"
    spec = plan(setup, 1).model_copy(
        update={"additional_costs": [ComparisonCost(role="E+", mission_id="extra-assessment", bucket=bucket)]}
    )
    spec = freeze(setup, spec)
    ordinary_account = f.account

    def record_cost(state: dict[str, Any], action: str, record: Any, operation: str) -> None:
        custom_seal = (
            support == "seal-A"
            and action == "seal"
            and record["mission_id"] == spec.cases[0].trials[0].mission.mission_id
        )
        custom_seal = custom_seal or support == "seal-" + bucket and action in {"seal-retention", "seal-investment"}
        if custom_seal:
            account_as(state, action, record, operation, "retired-accountant")
        else:
            ordinary_account(state, action, record, operation)

    monkeypatch.setattr(f, "account", record_cost)
    for trial in spec.cases[0].trials:
        run_trial(setup, trial)
    extra = {
        "activity_id": "extra-screen",
        "mission_id": "extra-assessment",
        "bucket": bucket,
        "category": "human",
        "accrued_micro_usd": None if support == "original-charge" else 77,
        "paid_micro_usd": 0,
        "basis": "unknown" if support == "original-charge" else "attested",
        "evidence_digest": f.ZERO,
        "note": "Fictional separately signed additional assessment; no actual provider bill",
    }
    account_as(
        setup,
        "charge",
        extra,
        "additional-screen",
        "retired-accountant" if support in {"charge", "original-charge"} else "accountant",
    )
    s.seal(setup, "extra-assessment", bucket)
    before = report(setup, spec)
    assert before["current_evidence_valid"] and all(
        row["complete_matched_outcomes"] for row in before["contrasts"].values()
    )
    snapshot = setup["costs"].snapshot()
    setup["trust"].revoke("retired-accountant")
    after = report(setup, spec)
    assert not after["current_evidence_valid"]
    assert len(after["cells"]) == 3
    if support == "seal-A":
        # The frozen delivery facts survive; the owner's current monetary-cap
        # metadata must expose the revoked completeness signer separately.
        stable = {
            "status", "accepted", "outcome_known", "execution_digest", "acceptance_digest",
            "historical_acceptance_recorded", "historical_acceptance_evidence", "model_io",
        }
        assert {name: after["cells"][0][name] for name in stable} == {
            name: before["cells"][0][name] for name in stable
        }
        assert not after["cells"][0]["delivery_cost_complete"]
        assert after["cells"][0]["delivery_cost_status"] == "incomplete"
        assert not after["cells"][0]["within_observed_limits"]
        assert after["cells"][1:] == before["cells"][1:]
    else:
        assert after["cells"] == before["cells"]
    assert all(arm["accepted"] == arm["planned"] == 1 for arm in after["arms"].values())
    assert not any(row["complete_matched_outcomes"] for row in after["contrasts"].values())
    assert all(row["cost_saving_micro_usd"] is None for row in after["contrasts"].values())
    assert setup["costs"].snapshot() == snapshot


@pytest.mark.parametrize("attempted", [False, True])
def test_declared_live_model_with_no_bound_execution_has_no_actual_model_evidence(
    setup: dict[str, Any], attempted: bool
) -> None:
    spec = plan(setup, 1)
    for trial in spec.cases[0].trials:
        trial.mission.components["model"] = "live"
    spec = freeze(setup, ComparisonPlan.model_validate(spec.model_dump()))
    if attempted:
        with setup["journal"].transaction() as cx:
            setup["service"]._state(cx)
            for trial in spec.cases[0].trials:
                setup["journal"].append(cx, operation_key(trial.operation_id), {"profile": {}})
            setup["service"].checkpoint.advance(setup["journal"], cx)
    value = report(setup, spec)
    assert value["model_evidence"] == "no-executions"
    assert value["planned_cases"] == 1 and len(value["cells"]) == 3
    assert all(cell["execution_digest"] is None for cell in value["cells"])
    assert all(arm["execution_records"] == arm["accepted"] == 0 for arm in value["arms"].values())
    assert all(arm["unassessed"] == arm["planned"] == 1 for arm in value["arms"].values())


@pytest.mark.parametrize("attack", ["signature", "journal", "role"])
def test_execution_signature_substitution_never_qualifies_current_contrasts(setup: dict[str, Any], attack: str) -> None:
    spec = freeze(setup, plan(setup, 1))
    for trial in spec.cases[0].trials:
        run_trial(setup, trial)

    def change(value: dict[str, Any]) -> None:
        if attack == "signature":
            value["permit"]["signature"] = "AA=="
            return
        payload = copy.deepcopy(value["permit"]["payload"])
        principal = "controller" if attack == "journal" else "accountant"
        if attack == "journal":
            payload["journal_identity"] = "urn:agialpha:ed25519:" + "a" * 64
        value["permit"] = sign_record(
            setup["keys"][principal], principal, "flywheel-execution-permit", payload
        ).model_dump()

    rewrite(setup, operation_key(spec.cases[0].trials[0].operation_id), change)
    value = report(setup, spec)
    assert not value["current_evidence_valid"]
    assert len(value["cells"]) == 3 and value["cells"][0]["execution_digest"] is not None
    assert not value["cells"][0]["execution_authority_current"]
    assert not value["contrasts"]["operational"]["complete_matched_outcomes"]
    assert value["contrasts"]["operational"]["cost_saving_micro_usd"] is None


def configured_model_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from alpha_factory_v1.core.runtime.models import RuntimeConfig

    initialize = f.Journal.initialize

    def configured_initialize(root: Any, **kwargs: Any) -> Any:
        return initialize(root, RuntimeConfig(llm_url="http://127.0.0.1:9", llm_model=profile().model_id), **kwargs)

    with monkeypatch.context() as local:
        local.setattr(f.Journal, "initialize", staticmethod(configured_initialize))
        return f.setup.__wrapped__(tmp_path)


def declared_live_plan(state: dict[str, Any], context_cap: int = 750_000) -> tuple[ComparisonPlan, ExecutionProfile]:
    selected = profile().model_copy(update={"model_request_cap_micro_usd": 1, "max_context_bytes": context_cap})
    spec = plan(state, 1)
    spec = spec.model_copy(
        update={
            "arms": [
                arm.model_copy(update={"model_profile_digest": digest("flywheel-execution-profile", selected)})
                for arm in spec.arms
            ]
        }
    )
    for trial in spec.cases[0].trials:
        trial.mission.components["model"] = "live"
    return freeze(state, ComparisonPlan.model_validate(spec.model_dump())), selected


def run_declared_model_double(
    state: dict[str, Any], spec: ComparisonPlan, selected: ExecutionProfile, transport: Any
) -> Any:
    trial, environment = spec.cases[0].trials[0], SystemsTool()
    terms = ExecutionPermit(
        operation_id=trial.operation_id,
        request_digest=digest("flywheel-execution-request", trial.mission),
        profile_digest=digest("flywheel-execution-profile", selected),
        environment_digest=digest("flywheel-execution-environment-contract", environment.identity),
        config_digest=runtime_digest(state["journal"].config.model_dump()),
        quota_evidence_digest=f.ZERO,
        pricing_evidence_digest=f.ZERO,
        max_authorized_micro_usd=1000,
        expires_at=int(time.time()) + 3600,
        bucket="A",
    )
    signed = sign_record(
        state["keys"]["controller"],
        "controller",
        "flywheel-execution-permit",
        {"journal_identity": state["journal"].identity, "permit": terms.model_dump()},
    )
    return MissionExecutor(state["journal"], state["trust"], state["costs"], transport, environment).run(
        trial.mission, selected, signed
    )


@pytest.mark.parametrize("stop_before_request", [True, False])
def test_bound_execution_never_promotes_zero_or_uncertain_model_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stop_before_request: bool
) -> None:
    state = configured_model_state(tmp_path, monkeypatch)
    spec, selected = declared_live_plan(state, 1024 if stop_before_request else 750_000)
    snapshots = []

    class NoProviderDouble:
        component = "live"
        calls = 0

        def respond(self, *args: Any) -> Any:
            self.calls += 1
            snapshots.append(report(state, spec))
            raise TimeoutError("Offline uncertain-request fixture; no actual provider")

    transport = NoProviderDouble()
    result = run_declared_model_double(state, spec, selected, transport)
    value = report(state, spec)
    io = value["cells"][0]["model_io"]
    assert transport.calls == (0 if stop_before_request else 1)
    assert result["turn"] == 1 and result["status"] == "failed-or-uncertain"
    assert result["usage_events"] == [] and result["actions"] == 0
    assert io["recorded_response_count"] == 0 and io["provider_call_count"] is None
    assert not io["provider_provenance_verified"] and value["cells"][0]["execution_digest"] is not None
    assert len(value["cells"]) == 3 and value["arms"]["U"]["planned"] == 1
    if stop_before_request:
        assert result["reserved_request_caps_micro_usd"] == 0 and snapshots == []
        assert io["status"] == "no-request-boundary-recorded"
        assert value["model_evidence"] == "bound-executions-without-model-io-evidence"
    else:
        assert result["reserved_request_caps_micro_usd"] == 1
        assert io["status"] == "request-boundary-unresolved" and io["unresolved_request"] is True
        assert io["request_boundary_lower_bound"] == 1
        assert snapshots[0]["cells"][0]["model_io"]["status"] == "request-boundary-unresolved"
        assert value["model_evidence"] == "model-request-evidence-unresolved"
        rewrite(state, operation_key(spec.cases[0].trials[0].operation_id), lambda row: row.update(pending=None))
        missing = report(state, spec)["cells"][0]["model_io"]
        assert missing["unresolved_request"] is True and missing["provider_call_count"] is None


def test_recorded_scripted_responses_preserve_call_counts_without_provider_promotion(setup: dict[str, Any]) -> None:
    spec = freeze(setup, plan(setup, 1))
    trial = spec.cases[0].trials[0]
    transport = ScriptedModel(PlacementProblem.model_validate(trial.mission.inputs["problem"]))
    run_trial(setup, trial, transport=transport)
    value = report(setup, spec)
    io = value["cells"][0]["model_io"]
    assert transport.turn == io["recorded_response_count"] == io["processed_usage_count"] == 2
    assert io["request_boundary_lower_bound"] == 2 and io["status"] == "response-recorded"
    assert value["model_evidence"] == "simulated-model-protocol-fixture"
    assert io["provider_call_count"] is None and not io["provider_provenance_verified"]
    rewrite(setup, operation_key(trial.operation_id), lambda row: row.update(usage_events=[]))
    assert report(setup, spec)["cells"][0]["model_io"]["recorded_response_count"] == 2


def test_declared_live_double_responses_remain_provider_unverified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = configured_model_state(tmp_path, monkeypatch)
    spec, selected = declared_live_plan(state)

    class DeclaredLiveFixture(ScriptedModel):
        component = "live"

    transport = DeclaredLiveFixture(PlacementProblem.model_validate(spec.cases[0].trials[0].mission.inputs["problem"]))
    run_declared_model_double(state, spec, selected, transport)
    value = report(state, spec)
    io = value["cells"][0]["model_io"]
    assert transport.turn == io["recorded_response_count"] == 2
    assert io["declared_component"] == "live" and not io["provider_provenance_verified"]
    assert value["model_evidence"] == "recorded-model-responses-provider-unverified"
