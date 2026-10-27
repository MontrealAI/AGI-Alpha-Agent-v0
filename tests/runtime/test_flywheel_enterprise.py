# SPDX-License-Identifier: Apache-2.0
"""Enterprise execution with fictional account, market and ENS resources."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, digest as runtime_digest
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import (
    Alternative,
    DecisionRequest,
    Enterprise,
    EnterpriseCommand,
    EvidenceRef,
    HumanReference,
    Offering,
    key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_execution import (
    ExecutionMission,
    ExecutionPermit,
    ExecutionProfile,
    MissionExecutor,
    operation_key,
)
from alpha_factory_v1.core.runtime.successor.flywheel_gym import PlacementEnvironment
from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementWorkflow
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import sign_record
from scripts.record_general_flywheel import ScriptedModel
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def evidence(state: dict[str, Any], journal_key: str = "@control") -> EvidenceRef:
    return EvidenceRef(journal_key=journal_key, record_digest=state["journal"].latest(journal_key)["digest"])


def offering(state: dict[str, Any], identity: str = "resilient-placement") -> Offering:
    need_key = "@enterprise-internal-research-need:v1"
    try:
        need = evidence(state, need_key)
    except KeyError:
        with state["journal"].transaction() as cx:
            state["service"]._state(cx)
            state["journal"].append(
                cx,
                need_key,
                {
                    "beneficiary": "Internal systems engineering research team",
                    "requirement": (
                        "Check replicated-service placement under correlated rack failure and finite capacity"
                    ),
                    "scope": "Internal synthetic engineering problem; no external market or customer demand observed",
                    "problem": s.problem(2100).model_dump(),
                },
            )
            state["service"].checkpoint.advance(state["journal"], cx)
        need = evidence(state, need_key)
    return Offering(
        offering_id=identity,
        version=1,
        beneficiary="Internal systems engineering research team",
        useful_outcome="A checkable service placement surviving one failure-domain loss",
        deliverable="Executable placement result and independent exhaustive acceptance",
        scope="Finite replicated-service placement prototype; no infrastructure deployment",
        acceptance_criteria=["Capacity and domain constraints", "Exact minimum or proven infeasibility"],
        need_evidence=[need],
        demand_uncertainty="Internal need only; no observed buyer demand",
        human_reference=HumanReference(
            service="Equivalent solver prototype and independent verification",
            source="Illustrative engineering estimate, not a market observation",
            basis="estimated-team-hours",
            team_hours=40,
            hourly_rate_micro_usd=100_000_000,
            total_micro_usd=4_000_000_000,
        ),
        permitted_tools=["placement_experiment"],
        price_policy="Compare explicit value-based price hypotheses",
        price_candidates_micro_usd=[1_000_000_000, 2_000_000_000, 3_000_000_000],
        capacity=1,
        turnaround_seconds=1800,
        complete_cost_cap_micro_usd=1000,
        risks=["Exponential worst-case search", "Complete actual cost unknown"],
        operating_limits=["Internal research-funded hybrid execution only", "No sales or production deployment"],
        mode="hybrid",
    )


def command(
    state: dict[str, Any],
    action: str,
    record: dict[str, Any],
    identity: str,
    expected: str | None = None,
    principal: str = "controller",
) -> Any:
    raw = EnterpriseCommand(
        journal_identity=state["journal"].identity,
        operation_id=identity,
        expires_at=int(time.time()) + 3600,
        action=action,
        expected_head=expected,
        record=record,
    )
    return sign_record(state["keys"][principal], principal, "flywheel-enterprise-command", raw.model_dump())


def register(state: dict[str, Any], spec: Offering | None = None) -> dict[str, Any]:
    spec = spec or offering(state)
    return Enterprise(state["service"]).apply(
        command(state, "offering", spec.model_dump(), "register-" + spec.offering_id)
    )


def decision(
    state: dict[str, Any],
    identity: str = "first-decision",
    action: str = "prototype",
    benefit: int = 2000,
    cost: int = 1000,
) -> dict[str, Any]:
    ref = evidence(state, key("offering", "resilient-placement"))
    base = dict(
        lower_benefit_micro_usd=benefit,
        upper_benefit_micro_usd=benefit + 1000,
        cash_cost_cap_micro_usd=cost,
        opportunity_cost_micro_usd=0,
        slots=1,
        seconds=1800,
        evidence=[ref],
        uncertainty="FICTIONAL research value forecast; no revenue",
    )
    request = DecisionRequest(
        decision_id=identity,
        available_slots=1,
        horizon_seconds=1800,
        extra_reserve_micro_usd=0,
        max_cash_micro_usd=1000,
        alternatives=[
            Alternative(alternative_id="deliver", action=action, offering_id="resilient-placement", **base),
            Alternative(
                alternative_id="hold",
                action="hold",
                lower_benefit_micro_usd=0,
                upper_benefit_micro_usd=0,
                cash_cost_cap_micro_usd=0,
                opportunity_cost_micro_usd=0,
                slots=0,
                seconds=0,
                evidence=[ref],
                uncertainty="Hold preserves available funds",
            ),
        ],
    )
    return Enterprise(state["service"]).apply(command(state, "decide", request.model_dump(), identity))


def execution(state: dict[str, Any], operation: str = "placement-origin") -> tuple[Any, Any, Any, Any]:
    spec = offering(state)
    instance = s.problem(2100)
    env = PlacementEnvironment(PlacementWorkflow(version=1))
    mission = ExecutionMission(
        mission_id=operation,
        beneficiary=spec.beneficiary,
        goal=spec.useful_outcome,
        challenged_assumption="Cheap replicas can share a failure domain",
        deliverable=spec.deliverable,
        acceptance_criteria=spec.acceptance_criteria,
        inputs={"problem": instance.model_dump()},
        sharing_rights="Apache-2.0 synthetic work",
        stop_conditions=["Refuse unapproved actions"],
        mode="hybrid",
        max_seconds=1800,
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
                "description": "Bounded placement tool",
                "strict": True,
                "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
            }
        ],
    )
    terms = ExecutionPermit(
        operation_id=operation,
        request_digest=digest("flywheel-execution-request", mission),
        profile_digest=digest("flywheel-execution-profile", profile),
        environment_digest=digest("flywheel-execution-environment-contract", env.identity),
        config_digest=runtime_digest(state["journal"].config.model_dump()),
        quota_evidence_digest=f.ZERO,
        pricing_evidence_digest=f.ZERO,
        max_authorized_micro_usd=1000,
        expires_at=int(time.time()) + 3600,
        bucket="A",
    )
    permit = sign_record(
        state["keys"]["controller"],
        "controller",
        "flywheel-execution-permit",
        {"journal_identity": state["journal"].identity, "permit": terms.model_dump()},
    )
    executor = MissionExecutor(state["journal"], state["trust"], state["costs"], ScriptedModel(instance), env)
    return executor, mission, profile, permit


def launch(state: dict[str, Any]) -> dict[str, Any]:
    s.funding(state)
    register(state)
    decision(state)
    Enterprise(state["service"]).run("first-decision", *execution(state))
    return state["journal"].latest(operation_key("placement-origin"))


def advance(state: dict[str, Any], stage: str, commercial: dict[str, Any] | None = None) -> dict[str, Any]:
    enterprise = Enterprise(state["service"])
    old = enterprise.inspect("offering", "resilient-placement")
    raw = {
        "offering_id": "resilient-placement",
        "stage": stage,
        "execution_operation": "placement-origin" if stage in {"prototype", "technically-qualified"} else None,
        "commercial": commercial,
    }
    return enterprise.apply(command(state, "advance", raw, "advance-" + stage, old["digest"]))


def accept(state: dict[str, Any], record: dict[str, Any]) -> None:
    s.seal(state, "placement-origin", "A")
    state["service"].accept_general_origin(
        f.signed(
            state,
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


def commercial(state: dict[str, Any], lower: int = -100) -> dict[str, Any]:
    return {
        "evidence": [evidence(state).model_dump()],
        "price_micro_usd": 2_000_000_000,
        "demand_basis": "No observed buyers; test forecast only",
        "lower_net_value_micro_usd": lower,
        "upper_net_value_micro_usd": 1000,
        "additional_cost_cap_micro_usd": 500,
        "limitations": "FICTIONAL commercial assessment, not validated demand or revenue",
    }


def test_connected_delivery_qualification_and_negative_commercial_decision(setup: dict[str, Any]) -> None:
    record = launch(setup)
    assert record["actions"] == 1
    assert Enterprise(setup["service"]).inspect("launch", "placement-origin")["status"] == "completed"
    advance(setup, "prototype")
    with pytest.raises((KeyError, ValueError)):
        advance(setup, "technically-qualified")
    accept(setup, record)
    advance(setup, "technically-qualified")
    assessment = advance(setup, "commercially-assessed", commercial(setup))
    assert assessment["stage"] == "commercially-assessed"
    with pytest.raises(ValueError, match="positive conservative"):
        advance(setup, "authorized")
    held = decision(setup, "hold-unprofitable", benefit=0)
    assert held["selected"] == "hold"
    assert setup["costs"].report()["collected_revenue"] == 0
    setup["journal"].verify()


def test_positive_fictional_qualification_can_produce_without_learning(setup: dict[str, Any]) -> None:
    record = launch(setup)
    advance(setup, "prototype")
    accept(setup, record)
    advance(setup, "technically-qualified")
    advance(setup, "commercially-assessed", commercial(setup, 100))
    advance(setup, "authorized")
    selected = decision(setup, "beta-production", action="produce")
    assert selected["selected"] == "deliver"
    Enterprise(setup["service"]).run("beta-production", *execution(setup, "second-production"))
    assert not setup["service"].library.snapshot()["protected_network_v1"]["active"]


@pytest.mark.parametrize("attack", ["tool", "beneficiary", "criteria", "mode", "budget", "expiry"])
def test_execution_cannot_widen_offering(setup: dict[str, Any], attack: str) -> None:
    s.funding(setup)
    register(setup)
    decision(setup)
    executor, mission, profile, permit = execution(setup)
    if attack == "tool":
        profile.tools[0]["name"] = "shell"
    elif attack == "beneficiary":
        mission = mission.model_copy(update={"beneficiary": "external client"})
    elif attack == "criteria":
        mission = mission.model_copy(update={"acceptance_criteria": ["accept any result"]})
    elif attack == "mode":
        mission = mission.model_copy(update={"mode": "simulation"})
    else:
        payload = copy.deepcopy(permit.payload)
        payload["permit"]["max_authorized_micro_usd" if attack == "budget" else "expires_at"] = (
            1001 if attack == "budget" else 1
        )
        permit = sign_record(setup["keys"]["controller"], "controller", permit.domain, payload)
    with pytest.raises(ValueError):
        Enterprise(setup["service"]).run("first-decision", executor, mission, profile, permit)
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("placement-origin"))


@pytest.mark.parametrize("attack", ["stale-evidence", "cross-journal", "expired", "wrong-role", "replay", "skip-stage"])
def test_commands_reject_authority_and_history_attacks(setup: dict[str, Any], attack: str) -> None:
    enterprise = Enterprise(setup["service"])
    spec = offering(setup)
    signed = command(setup, "offering", spec.model_dump(), "first")
    if attack == "stale-evidence":
        changed = spec.model_dump()
        changed["need_evidence"][0]["record_digest"] = f.ZERO
        signed = command(setup, "offering", changed, "first")
    elif attack in {"cross-journal", "expired"}:
        payload = copy.deepcopy(signed.payload)
        payload["journal_identity" if attack == "cross-journal" else "expires_at"] = (
            f.ZERO if attack == "cross-journal" else 1
        )
        signed = sign_record(setup["keys"]["controller"], "controller", signed.domain, payload)
    elif attack == "wrong-role":
        signed = command(setup, "offering", spec.model_dump(), "first", principal="producer")
    elif attack == "replay":
        enterprise.apply(signed)
    elif attack == "skip-stage":
        register(setup)
        with pytest.raises(ValueError, match="cannot be skipped"):
            advance(setup, "authorized")
        return
    with pytest.raises((ValueError, Conflict)):
        enterprise.apply(signed)


def test_revision_resets_qualification_and_stale_decision_refuses(setup: dict[str, Any]) -> None:
    s.funding(setup)
    old = register(setup)
    decision(setup)
    updated = offering(setup).model_copy(update={"version": 2})
    new = Enterprise(setup["service"]).apply(command(setup, "offering", updated.model_dump(), "revise", old["digest"]))
    assert new["stage"] == "hypothesis"
    with pytest.raises(Conflict, match="evidence is stale|offering changed"):
        Enterprise(setup["service"]).run("first-decision", *execution(setup))


def test_unknown_costs_hold_and_replay_never_reexecutes(setup: dict[str, Any]) -> None:
    launch(setup)
    selected = decision(setup, "after-unknown")
    assert selected["selected"] == "hold"
    assert any("cash unknown" in r for r in selected["alternatives"][0]["reasons"])
    with pytest.raises(Conflict):
        Enterprise(setup["service"]).run("first-decision", *execution(setup))


def test_interrupted_attempt_keeps_capacity_and_unknown_liability(setup: dict[str, Any]) -> None:
    s.funding(setup)
    register(setup)
    decision(setup)
    executor, mission, profile, permit = execution(setup)
    executor.transport.respond = lambda *args: (_ for _ in ()).throw(TimeoutError("injected transport interruption"))
    result = Enterprise(setup["service"]).run("first-decision", executor, mission, profile, permit)
    assert result["status"] == "failed-or-uncertain"
    assert Enterprise(setup["service"]).inspect("launch", "placement-origin")["status"] == "failed-or-uncertain"
    active = setup["journal"].latest(key("active", "capacity"))
    assert active["reservations"]["placement-origin"]["slots"] == 1
    assert setup["costs"].report()["unknown_costs"]
    old = Enterprise(setup["service"]).inspect("launch", "placement-origin")
    raw = {"execution_operation": "placement-origin", "evidence": [evidence(setup).model_dump()]}
    with pytest.raises(Conflict):
        Enterprise(setup["service"]).apply(command(setup, "reconcile", raw, "reconcile-early", old["digest"]))
    s.seal(setup, "placement-origin", "A")
    setup["journal"].control(True)
    with setup["journal"].transaction() as cx:
        setup["service"].checkpoint.advance(setup["journal"], cx)
    raw["evidence"] = [evidence(setup).model_dump()]
    fixed = Enterprise(setup["service"]).apply(command(setup, "reconcile", raw, "reconcile", old["digest"]))
    assert fixed["status"] == "reconciled-failure"
    assert not setup["journal"].latest(key("active", "capacity"))["reservations"]
    assert Enterprise(setup["service"]).inspect("decision", "first-decision")["consumed"]


def test_changed_forecast_evidence_refuses_before_consuming_or_io(setup: dict[str, Any]) -> None:
    s.funding(setup)
    register(setup)
    original = decision(setup)
    forecast_key = "@enterprise-forecast-fixture"
    with setup["journal"].transaction() as cx:
        setup["journal"].append(cx, forecast_key, {"scope": "fictional", "lower_benefit": 2000})
        setup["service"].checkpoint.advance(setup["journal"], cx)
    request = copy.deepcopy(original["request"])
    request["decision_id"] = "forecast-decision"
    for alternative in request["alternatives"]:
        alternative["evidence"] = [evidence(setup, forecast_key).model_dump()]
    enterprise = Enterprise(setup["service"])
    enterprise.apply(command(setup, "decide", request, "forecast-decision"))
    with setup["journal"].transaction() as cx:
        setup["journal"].append(cx, forecast_key, {"scope": "fictional", "lower_benefit": 0})
        setup["service"].checkpoint.advance(setup["journal"], cx)
    with pytest.raises(Conflict, match="evidence is stale"):
        enterprise.run("forecast-decision", *execution(setup))
    assert not enterprise.inspect("decision", "forecast-decision")["consumed"]
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("placement-origin"))


def test_terminal_executor_failure_recovers_after_lost_finalization(setup: dict[str, Any], monkeypatch: Any) -> None:
    s.funding(setup)
    register(setup)
    decision(setup)
    enterprise = Enterprise(setup["service"])
    executor, mission, profile, permit = execution(setup)
    executor.transport.respond = lambda *args: (_ for _ in ()).throw(TimeoutError("fixture failure"))
    with monkeypatch.context() as context:

        def crash(*args: Any) -> None:
            raise SystemExit("process ended after terminal executor receipt")

        context.setattr(enterprise, "_finish", crash)
        with pytest.raises(SystemExit):
            enterprise.run("first-decision", executor, mission, profile, permit)
    old = enterprise.inspect("launch", "placement-origin")
    assert old["status"] == "attempting-or-uncertain"
    assert setup["journal"].latest(operation_key("placement-origin"))["status"] == "failed-or-uncertain"
    s.seal(setup, "placement-origin", "A")
    setup["journal"].control(True)
    with setup["journal"].transaction() as cx:
        setup["service"].checkpoint.advance(setup["journal"], cx)
    raw = {"execution_operation": "placement-origin", "evidence": [evidence(setup).model_dump()]}
    result = enterprise.apply(command(setup, "reconcile", raw, "recover-terminal", old["digest"]))
    assert result["status"] == "reconciled-failure"
    assert not setup["journal"].latest(key("active", "capacity"))["reservations"]
    assert enterprise.inspect("decision", "first-decision")["consumed"]


def test_changed_commercial_assessment_evidence_cannot_authorize(setup: dict[str, Any]) -> None:
    record = launch(setup)
    advance(setup, "prototype")
    accept(setup, record)
    advance(setup, "technically-qualified")
    forecast = "@commercial-forecast-fixture"
    with setup["journal"].transaction() as cx:
        setup["journal"].append(cx, forecast, {"demand": "fictional-positive"})
        setup["service"].checkpoint.advance(setup["journal"], cx)
    terms = commercial(setup, 100)
    terms["evidence"] = [evidence(setup, forecast).model_dump()]
    advance(setup, "commercially-assessed", terms)
    with setup["journal"].transaction() as cx:
        setup["journal"].append(cx, forecast, {"demand": "withdrawn"})
        setup["service"].checkpoint.advance(setup["journal"], cx)
    with pytest.raises(Conflict, match="evidence is stale"):
        advance(setup, "authorized")
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement")["stage"] == "commercially-assessed"


def test_withdrawn_authorized_commercial_evidence_blocks_decision_and_dispatch(setup: dict[str, Any]) -> None:
    record = launch(setup)
    advance(setup, "prototype")
    accept(setup, record)
    advance(setup, "technically-qualified")
    forecast = "@authorized-commercial-forecast"
    with setup["journal"].transaction() as cx:
        setup["journal"].append(cx, forecast, {"demand": "fictional-positive"})
        setup["service"].checkpoint.advance(setup["journal"], cx)
    terms = commercial(setup, 100)
    terms["evidence"] = [evidence(setup, forecast).model_dump()]
    advance(setup, "commercially-assessed", terms)
    advance(setup, "authorized")
    assert decision(setup, "before-withdrawal", action="produce")["selected"] == "deliver"
    with setup["journal"].transaction() as cx:
        setup["journal"].append(cx, forecast, {"demand": "withdrawn"})
        setup["service"].checkpoint.advance(setup["journal"], cx)
    held = decision(setup, "after-withdrawal", action="produce")
    assert held["selected"] == "hold"
    assert "commercial assessment evidence is missing or stale" in held["alternatives"][0]["reasons"]
    enterprise = Enterprise(setup["service"])
    with pytest.raises(Conflict, match="evidence is stale"):
        enterprise.run("before-withdrawal", *execution(setup, "withdrawn-production"))
    assert not enterprise.inspect("decision", "before-withdrawal")["consumed"]
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("withdrawn-production"))
    request = copy.deepcopy(held["request"])
    request["decision_id"] = "research-without-sales"
    prototype = copy.deepcopy(request["alternatives"][0])
    prototype.update(alternative_id="internal-prototype", action="prototype")
    request["alternatives"].append(prototype)
    selected = enterprise.apply(command(setup, "decide", request, "research-without-sales"))
    assert selected["selected"] == "internal-prototype"
    result = enterprise.run("research-without-sales", *execution(setup, "internal-after-withdrawal"))
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"


def test_two_offerings_share_global_capacity_without_occupying_each_others_slots(setup: dict[str, Any]) -> None:
    s.funding(setup)
    register(setup)
    first = decision(setup)
    executor, mission, profile, permit = execution(setup)
    executor.transport.respond = lambda *args: (_ for _ in ()).throw(TimeoutError("fixture failure"))
    enterprise = Enterprise(setup["service"])
    enterprise.run("first-decision", executor, mission, profile, permit)
    s.seal(setup, "placement-origin", "A")
    other = register(setup, offering(setup, "second-offering"))
    request = copy.deepcopy(first["request"])
    request["decision_id"] = "global-full"
    for alternative in request["alternatives"]:
        alternative["evidence"] = [evidence(setup, other["id"]).model_dump()]
        if alternative["offering_id"] is not None:
            alternative["offering_id"] = "second-offering"
    full = enterprise.apply(command(setup, "decide", request, "global-full"))
    assert full["selected"] == "hold"
    assert "capacity or time budget" in full["alternatives"][0]["reasons"]
    assert "offering occupied capacity" not in full["alternatives"][0]["reasons"]
    request.update(decision_id="second-slot", available_slots=2)
    available = enterprise.apply(command(setup, "decide", request, "second-slot"))
    assert available["selected"] == "deliver"
    result = enterprise.run("second-slot", *execution(setup, "second-offering-mission"))
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    reservations = setup["journal"].latest(key("active", "capacity"))["reservations"]
    assert set(reservations) == {"placement-origin"}
    assert reservations["placement-origin"]["offering_id"] == "resilient-placement"
