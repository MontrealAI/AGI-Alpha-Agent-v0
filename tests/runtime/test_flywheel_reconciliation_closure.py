# SPDX-License-Identifier: Apache-2.0
"""Cancel unused permits with actual local execution and fictional authority/bills."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise, key
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.flywheel_learning import check_general_output
import test_flywheel_enterprise as e
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def caught(state: dict[str, Any], cause: str = "qualification", legacy: bool = False) -> tuple[Any, ...]:
    s.funding(state)
    e.register(state)
    e.decision(state)
    executor, mission, profile, permit = e.execution(state)

    def unavailable() -> None:
        raise Conflict("fictional temporary qualification unavailable")

    if cause == "qualification":
        executor.qualification_check = unavailable
    else:
        executor.transport.component = "unqualified"
    with pytest.raises((Conflict, ValueError)):
        Enterprise(state["service"]).run("first-decision", executor, mission, profile, permit)
    executor.qualification_check = lambda: None
    executor.transport.component = "simulated"
    with pytest.raises(KeyError):
        state["journal"].latest(operation_key(mission.mission_id))
    assert not state["costs"].snapshot()["charges"]
    if legacy:
        with state["journal"].transaction() as cx:
            value = state["journal"].document(state["journal"].latest(key("launch", mission.mission_id), cx))
            del value["ledger_mission_id"]
            state["journal"].append(cx, key("launch", mission.mission_id), value)
            state["service"].checkpoint.advance(state["journal"], cx)
    return executor, mission, profile, permit


def pause(state: dict[str, Any], paused: bool = True) -> None:
    state["journal"].control(paused)
    with state["journal"].transaction() as cx:
        state["service"].checkpoint.advance(state["journal"], cx)


def reconciliation(
    state: dict[str, Any], mission: Any = None, principal: str = "controller", stale: bool = False
) -> Any:
    launch = Enterprise(state["service"]).inspect("launch", "placement-origin")
    raw = {"execution_operation": "placement-origin", "evidence": [e.evidence(state).model_dump()]}
    if mission is not None:
        raw["original_mission"] = mission.model_dump()
    return e.command(state, "reconcile", raw, "close-unused", f.ZERO if stale else launch["digest"], principal)


@pytest.mark.parametrize("cause", ["qualification", "component"])
@pytest.mark.parametrize("legacy", [False, True])
def test_cancelled_preflight_permit_never_becomes_usable_after_conditions_recover(
    setup: dict[str, Any], cause: str, legacy: bool
) -> None:
    executor, mission, profile, permit = caught(setup, cause, legacy)
    s.seal(setup, mission.mission_id, "A")
    pause(setup)
    before = setup["costs"].snapshot()
    enterprise = Enterprise(setup["service"])
    result = enterprise.apply(reconciliation(setup, mission if legacy else None))
    assert result["status"] == "reconciled-failure" and result["authority_restored"] is False
    assert result["execution_digest"] is None
    assert not setup["journal"].latest(key("active", "capacity"))["reservations"]
    pause(setup, False)
    with pytest.raises(Conflict, match="already attempted"):
        executor.run(mission, profile, permit)
    assert setup["costs"].snapshot() == before
    closure = setup["journal"].latest(operation_key("placement-origin"))
    assert closure["schema_name"] == "flywheel-execution-closure/v1"
    assert closure["status"] == "cancelled-before-execution" and closure["execution_started"] is False
    assert result["closure_digest"] == closure["digest"]
    with setup["journal"].transaction() as cx:
        with pytest.raises(ValueError, match="actually delivered"):
            check_general_output(setup["service"], "placement-origin", cx)
    assert enterprise.inspect("decision", "first-decision")["consumed"]
    with pytest.raises(Conflict, match="consumed"):
        enterprise.run("first-decision", *e.execution(setup))
    with pytest.raises(Conflict, match="already attempted"):
        e.execution(setup)[0].run(*e.execution(setup)[1:])
    assert e.decision(setup, "fresh-authority")["selected"] == "deliver"
    fresh = enterprise.run("fresh-authority", *e.execution(setup, "fresh-operation"))
    assert fresh["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert setup["costs"].report()["collected_revenue"] == 0
    setup["journal"].verify()


@pytest.mark.parametrize("fault", ["launch-write", "checkpoint"])
def test_closure_and_capacity_release_roll_back_together(
    setup: dict[str, Any], fault: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, mission, _, _ = caught(setup)
    s.seal(setup, mission.mission_id, "A")
    pause(setup)
    signed = reconciliation(setup)
    original = setup["journal"].verify()
    append = setup["journal"].append

    def fail(*args: Any) -> None:
        raise RuntimeError("injected durable-finalization failure")

    def fail_launch(cx: Any, identity: str, value: dict[str, Any]) -> dict[str, Any]:
        if identity == key("launch", "placement-origin"):
            fail()
        return append(cx, identity, value)

    with monkeypatch.context() as context:
        if fault == "launch-write":
            context.setattr(setup["journal"], "append", fail_launch)
        else:
            context.setattr(setup["service"].checkpoint, "advance", fail)
        with pytest.raises(RuntimeError, match="durable-finalization"):
            Enterprise(setup["service"]).apply(signed)
    assert setup["journal"].verify() == original
    assert setup["journal"].latest(key("active", "capacity"))["reservations"]
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("placement-origin"))
    result = Enterprise(setup["service"]).apply(signed)
    assert result["closure_digest"] == setup["journal"].latest(operation_key("placement-origin"))["digest"]


@pytest.mark.parametrize("boundary", ["unknown", "unpaused", "stale", "wrong-role", "attempting", "execution-charge"])
def test_unstarted_closure_preserves_reconciliation_boundaries(setup: dict[str, Any], boundary: str) -> None:
    _, mission, _, _ = caught(setup)
    if boundary == "attempting":
        with setup["journal"].transaction() as cx:
            value = setup["journal"].document(setup["journal"].latest(key("launch", "placement-origin"), cx))
            value["status"] = "attempting-or-uncertain"
            setup["journal"].append(cx, key("launch", "placement-origin"), value)
            setup["service"].checkpoint.advance(setup["journal"], cx)
    if boundary == "execution-charge":
        f.account(
            setup,
            "charge",
            {
                "activity_id": "execution/placement-origin",
                "mission_id": mission.mission_id,
                "bucket": "A",
                "category": "model",
                "accrued_micro_usd": 1,
                "paid_micro_usd": 0,
                "basis": "attested",
                "evidence_digest": f.ZERO,
                "note": "FICTIONAL inconsistent reservation/receipt; requires investigation",
            },
            "inconsistent-reservation",
        )
    if boundary != "unknown":
        s.seal(setup, mission.mission_id, "A")
    if boundary != "unpaused":
        pause(setup)
    signed = reconciliation(
        setup, principal="producer" if boundary == "wrong-role" else "controller", stale=boundary == "stale"
    )
    before = setup["journal"].verify()
    with pytest.raises((Conflict, ValueError)):
        Enterprise(setup["service"]).apply(signed)
    assert setup["journal"].verify() == before
    assert setup["journal"].latest(key("active", "capacity"))["reservations"]
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("placement-origin"))


def test_terminal_failed_execution_retains_its_actual_receipt(setup: dict[str, Any]) -> None:
    s.funding(setup)
    e.register(setup)
    e.decision(setup)
    executor, mission, profile, permit = e.execution(setup)

    def unavailable(*args: Any) -> Any:
        raise TimeoutError("fixture model interruption")

    executor.transport.respond = unavailable
    Enterprise(setup["service"]).run("first-decision", executor, mission, profile, permit)
    receipt = setup["journal"].latest(operation_key("placement-origin"))
    s.seal(setup, mission.mission_id, "A")
    pause(setup)
    result = Enterprise(setup["service"]).apply(reconciliation(setup))
    assert result["execution_digest"] == receipt["digest"]
    assert result["failure_kind"] == "terminal-execution-failure"
    assert result.get("closure_digest") is None
    assert setup["journal"].latest(operation_key("placement-origin")) == receipt
