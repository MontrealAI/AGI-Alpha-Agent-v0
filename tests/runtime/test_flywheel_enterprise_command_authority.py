# SPDX-License-Identifier: Apache-2.0
"""Current enterprise commands govern later actions, with fictional authority only."""

from __future__ import annotations

import copy
from pathlib import Path
import time
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise, key
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, sign_record
import test_flywheel_enterprise as e
import test_flywheel_enterprise_technical_authority as t
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    state = t.setup.__wrapped__(tmp_path)
    private = Ed25519PrivateKey.generate()
    state["keys"]["decision-controller"] = private
    state["trust"]._anchors["decision-controller"] = TrustAnchor(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"controller"})
    )
    return state


def prepare(state: dict[str, Any], action: str) -> dict[str, Any]:
    if action == "produce":
        return t.prepare(state)
    s.funding(state)
    return e.register(state)


def decision(state: dict[str, Any], action: str, *, short_expiry: bool = False) -> dict[str, Any]:
    template = e.decision(state, "request-template", action=action)
    request = copy.deepcopy(template["request"])
    request["decision_id"] = "independent-decision"
    signed = e.command(state, "decide", request, "independent-decision", principal="decision-controller")
    if short_expiry:
        payload = copy.deepcopy(signed.payload)
        payload["expires_at"] = int(time.time()) + 10
        signed = sign_record(
            state["keys"]["decision-controller"],
            "decision-controller",
            "flywheel-enterprise-command",
            payload,
        )
    return Enterprise(state["service"]).apply(signed)


def withdraw(state: dict[str, Any], principal: str, kind: str) -> None:
    if kind == "revoke":
        state["trust"].revoke(principal)
    else:
        private = Ed25519PrivateKey.generate()
        state["trust"]._anchors[principal] = TrustAnchor(
            private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"controller"})
        )


@pytest.mark.parametrize("when", ["decision", "dispatch"])
def test_revoked_commercial_authorizer_cannot_start_production(setup: dict[str, Any], when: str) -> None:
    original = prepare(setup, "produce")
    enterprise = Enterprise(setup["service"])
    costs = setup["costs"].snapshot()
    if when == "decision":
        setup["trust"].revoke("commercial-controller")
        held = e.decision(setup, "after-commercial-withdrawal", action="produce")
        assert held["selected"] == "hold"
        assert not held["alternatives"][0]["eligible"]
        assert "commercial authorization is no longer eligible" in held["alternatives"][0]["reasons"]
    else:
        chosen = decision(setup, "produce")
        setup["trust"].revoke("commercial-controller")
        executor, mission, profile, permit = e.execution(setup, "commercial-refusal")
        calls: list[str] = []
        respond = executor.transport.respond

        def model(*args: Any) -> dict[str, Any]:
            calls.append("simulated-response")
            return respond(*args)

        executor.transport.respond = model
        with pytest.raises(ValueError, match="trusted|authorization"):
            enterprise.run("independent-decision", executor, mission, profile, permit)
        assert not calls
        assert enterprise.inspect("decision", "independent-decision") == chosen
        with pytest.raises(KeyError):
            enterprise.inspect("launch", "commercial-refusal")
        with pytest.raises(KeyError):
            setup["journal"].latest(operation_key("commercial-refusal"))
    assert enterprise.inspect("offering", "resilient-placement") == original
    assert setup["costs"].snapshot() == costs


ACTIVE_CASES = [
    (action, principal, kind)
    for action in ("produce", "prototype")
    for principal, kinds in (
        ("decision-controller", ("revoke", "rotate", "expire")),
        ("commercial-controller", ("revoke", "rotate") if action == "produce" else ()),
    )
    for kind in kinds
]


@pytest.mark.parametrize("action,principal,kind", ACTIVE_CASES)
@pytest.mark.parametrize("when", ["model-response", "tool-response"])
def test_active_enterprise_authority_stops_later_actions_and_preserves_liabilities(
    setup: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    action: str,
    principal: str,
    kind: str,
    when: str,
) -> None:
    original = prepare(setup, action)
    chosen = decision(setup, action, short_expiry=kind == "expire")
    deadline = chosen["signed"]["payload"]["expires_at"]
    executor, mission, profile, permit = e.execution(setup, "active-enterprise")
    model_calls: list[str] = []
    tool_calls: list[str] = []
    prior_calls: list[str] = []
    respond, perform = executor.transport.respond, executor.environment.perform

    def prior() -> None:
        prior_calls.append("existing-qualification")

    def changed() -> None:
        if kind == "expire":
            monkeypatch.setattr(time, "time", lambda: deadline + 1)
        else:
            withdraw(setup, principal, kind)

    def model(*args: Any) -> dict[str, Any]:
        model_calls.append("simulated-model")
        result = respond(*args)
        if when == "model-response":
            changed()
        return result

    def tool(*args: Any) -> dict[str, Any]:
        tool_calls.append("bounded-local-placement")
        result = perform(*args)
        if when == "tool-response":
            changed()
        return result

    executor.qualification_check = prior
    executor.transport.respond, executor.environment.perform = model, tool
    enterprise = Enterprise(setup["service"])
    result = enterprise.run("independent-decision", executor, mission, profile, permit)
    assert result["status"] == "failed-or-uncertain"
    assert result["actions"] == (1 if when == "tool-response" else 0)
    assert len(model_calls) == 1 and len(tool_calls) == (1 if when == "tool-response" else 0)
    assert result["pending"].startswith("tool/" if when == "tool-response" else "model/")
    assert prior_calls and executor.qualification_check is prior
    assert enterprise.inspect("decision", "independent-decision")["consumed"]
    assert enterprise.inspect("launch", "active-enterprise")["status"] == "failed-or-uncertain"
    assert "active-enterprise" in setup["journal"].latest(key("active", "capacity"))["reservations"]
    charge = setup["costs"].snapshot()["charges"]["execution/active-enterprise"]
    assert charge["accrued_micro_usd"] is None
    assert enterprise.inspect("offering", "resilient-placement") == original
    assert enterprise.inspect("decision", "independent-decision")["signed"] == chosen["signed"]


@pytest.mark.parametrize("action", ["produce", "prototype"])
def test_current_independent_controllers_allow_the_original_delivery(setup: dict[str, Any], action: str) -> None:
    prepare(setup, action)
    decision(setup, action)
    result = Enterprise(setup["service"]).run("independent-decision", *e.execution(setup, "current-production"))
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert result["actions"] == 1


def test_consumed_commercial_command_deadline_is_not_a_new_offering_lease(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    original = prepare(setup, "produce")
    deadline = original["signed"]["payload"]["expires_at"]
    monkeypatch.setattr(time, "time", lambda: deadline + 1)
    decision(setup, "produce")
    result = Enterprise(setup["service"]).run("independent-decision", *e.execution(setup, "historical-command"))
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement") == original


def test_unrelated_revocation_does_not_stop_independently_authorized_production(setup: dict[str, Any]) -> None:
    prepare(setup, "produce")
    decision(setup, "produce")
    setup["trust"].revoke("unrelated-principal")
    result = Enterprise(setup["service"]).run("independent-decision", *e.execution(setup, "unrelated-controller"))
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
