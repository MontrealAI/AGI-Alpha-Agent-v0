# SPDX-License-Identifier: Apache-2.0
"""Current prototype authority on fictional, locally executed enterprise work."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise, key
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY
import test_flywheel_enterprise as e


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return e.setup.__wrapped__(tmp_path)


def qualified(state: dict[str, Any], stage: str = "authorized") -> dict[str, Any]:
    record = e.launch(state)
    e.advance(state, "prototype")
    e.accept(state, record)
    result = e.advance(state, "technically-qualified")
    if stage == "technically-qualified":
        return result
    result = e.advance(state, "commercially-assessed", e.commercial(state, 100))
    if stage == "commercially-assessed":
        return result
    return e.advance(state, "authorized")


def historical(state: dict[str, Any]) -> dict[str, Any]:
    return {
        name: copy.deepcopy(state["journal"].latest(name))
        for name in (operation_key("placement-origin"), ACCEPTANCE_KEY + "placement-origin")
    }


def unchanged(state: dict[str, Any], original: dict[str, Any]) -> None:
    assert {name: state["journal"].latest(name) for name in original} == original
    assert state["costs"].report()["collected_revenue"] == 0
    state["journal"].verify()


@pytest.mark.parametrize("stage", ["technically-qualified", "commercially-assessed"])
def test_revoked_prototype_acceptance_blocks_further_authorization(setup: dict[str, Any], stage: str) -> None:
    old = qualified(setup, stage)
    original = historical(setup)
    setup["trust"].revoke("acceptor")
    next_stage = "commercially-assessed" if stage == "technically-qualified" else "authorized"
    with pytest.raises(ValueError, match="trusted|prototype"):
        e.advance(setup, next_stage, e.commercial(setup, 100) if next_stage == "commercially-assessed" else None)
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement") == old
    unchanged(setup, original)


@pytest.mark.parametrize("principal", ["acceptor", "accountant"])
def test_revoked_prototype_support_makes_production_ineligible(setup: dict[str, Any], principal: str) -> None:
    old = qualified(setup)
    original = historical(setup)
    setup["trust"].revoke(principal)
    held = e.decision(setup, "after-prototype-revocation", action="produce")
    assert held["selected"] == "hold"
    assert not held["alternatives"][0]["eligible"]
    assert "prototype acceptance or supporting evidence is not currently eligible" in held["alternatives"][0]["reasons"]
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement") == old
    with pytest.raises(ValueError, match="no execution"):
        Enterprise(setup["service"]).run("after-prototype-revocation", *e.execution(setup, "held-production"))
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("held-production"))
    unchanged(setup, original)


@pytest.mark.parametrize("principal", ["acceptor", "accountant"])
def test_production_dispatch_rechecks_prototype_before_consumption(setup: dict[str, Any], principal: str) -> None:
    qualified(setup)
    frozen = e.decision(setup, "before-prototype-revocation", action="produce")
    original = historical(setup)
    ledger = copy.deepcopy(setup["costs"].snapshot())
    setup["trust"].revoke(principal)
    enterprise = Enterprise(setup["service"])
    with pytest.raises(ValueError, match="trusted|prototype"):
        enterprise.run("before-prototype-revocation", *e.execution(setup, "revoked-production"))
    assert enterprise.inspect("decision", "before-prototype-revocation") == frozen
    assert setup["costs"].snapshot() == ledger
    with pytest.raises(KeyError):
        enterprise.inspect("launch", "revoked-production")
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("revoked-production"))
    unchanged(setup, original)


@pytest.mark.parametrize("when", ["preflight", "model-response", "tool-response"])
def test_in_memory_prototype_revocation_stops_subsequent_production_actions(setup: dict[str, Any], when: str) -> None:
    qualified(setup)
    e.decision(setup, "active-production", action="produce")
    original = historical(setup)
    executor, mission, profile, permit = e.execution(setup, "interrupted-production")
    prior_checks: list[str] = []

    def prior() -> None:
        prior_checks.append("checked")
        if when == "preflight":
            setup["trust"].revoke("acceptor")

    executor.qualification_check = prior
    respond = executor.transport.respond
    perform = executor.environment.perform
    model_calls: list[str] = []
    tool_calls: list[str] = []

    def model(*args: Any) -> dict[str, Any]:
        model_calls.append("scripted-offline-response")
        result = respond(*args)
        if when == "model-response":
            setup["trust"].revoke("acceptor")
        return result

    def tool(*args: Any) -> dict[str, Any]:
        tool_calls.append("local-placement-tool")
        result = perform(*args)
        if when == "tool-response":
            setup["trust"].revoke("acceptor")
        return result

    executor.transport.respond = model
    executor.environment.perform = tool
    enterprise = Enterprise(setup["service"])
    if when == "preflight":
        with pytest.raises(ValueError, match="trusted|prototype"):
            enterprise.run("active-production", executor, mission, profile, permit)
        with pytest.raises(KeyError):
            setup["journal"].latest(operation_key("interrupted-production"))
        assert not model_calls and not tool_calls
        assert "execution/interrupted-production" not in setup["costs"].snapshot()["charges"]
    else:
        result = enterprise.run("active-production", executor, mission, profile, permit)
        assert result["status"] == "failed-or-uncertain"
        assert result["error_type"] == "ValueError"
        assert result["actions"] == (1 if when == "tool-response" else 0)
        assert len(model_calls) == 1
        assert len(tool_calls) == (1 if when == "tool-response" else 0)
        assert result["pending"].startswith("tool/" if when == "tool-response" else "model/")
        charge = setup["costs"].snapshot()["charges"]["execution/interrupted-production"]
        assert charge["accrued_micro_usd"] is None
    assert prior_checks
    assert executor.qualification_check is prior
    assert enterprise.inspect("decision", "active-production")["consumed"]
    assert enterprise.inspect("launch", "interrupted-production")["status"] == "failed-or-uncertain"
    assert "interrupted-production" in setup["journal"].latest(key("active", "capacity"))["reservations"]
    unchanged(setup, original)


@pytest.mark.parametrize("control", ["unrelated-revocation", "expired-prototype-permit"])
def test_current_prototype_controls_do_not_invalidate_historical_expiry(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch, control: str
) -> None:
    qualified(setup)
    original = historical(setup)
    if control == "unrelated-revocation":
        setup["trust"].revoke("evaluator")
    else:
        expiry = original[operation_key("placement-origin")]["permit"]["payload"]["permit"]["expires_at"]
        monkeypatch.setattr(time, "time", lambda: expiry + 1)
    selected = e.decision(setup, "current-production-control", action="produce")
    assert selected["selected"] == "deliver"
    result = Enterprise(setup["service"]).run(
        "current-production-control", *e.execution(setup, "current-production-control-run")
    )
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert result["actions"] == 1
    unchanged(setup, original)


def test_reentrant_shared_executor_keeps_support_checks_local_to_each_run(setup: dict[str, Any]) -> None:
    qualified(setup)
    e.decision(setup, "reentrant-production", action="produce")
    executor, mission, profile, permit = e.execution(setup, "reentrant-production-run")
    _, inner_mission, inner_profile, inner_permit = e.execution(setup, "reentrant-refused-run")
    original_qualification = executor.qualification_check
    respond = executor.transport.respond
    inner_checks: list[str] = []
    outer_calls: list[str] = []

    def refuse_inner() -> None:
        inner_checks.append("inner-support-only")
        raise ValueError("independently refused inner support")

    def model(*args: Any) -> dict[str, Any]:
        assert executor.qualification_check is original_qualification
        if not outer_calls:
            with pytest.raises(ValueError, match="independently refused inner support"):
                executor.run(inner_mission, inner_profile, inner_permit, support_check=refuse_inner)
            assert inner_checks == ["inner-support-only"]
            with pytest.raises(KeyError):
                setup["journal"].latest(operation_key(inner_mission.mission_id))
        outer_calls.append("outer-scripted-response")
        return respond(*args)

    executor.transport.respond = model
    result = Enterprise(setup["service"]).run("reentrant-production", executor, mission, profile, permit)
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert len(outer_calls) == 2
    assert inner_checks == ["inner-support-only"]
    assert executor.qualification_check is original_qualification
    assert "execution/reentrant-refused-run" not in setup["costs"].snapshot()["charges"]
