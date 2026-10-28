# SPDX-License-Identifier: Apache-2.0
"""Current prototype acceptance gates with entirely fictional production authority."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import Enterprise
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, sign_record
import test_flywheel_enterprise as e
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    state = f.setup.__wrapped__(tmp_path)
    for principal in ("prototype-controller", "commercial-controller"):
        key = Ed25519PrivateKey.generate()
        state["keys"][principal] = key
        state["trust"]._anchors[principal] = TrustAnchor(
            key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"controller"})
        )
    return state


def advance(state: dict[str, Any], stage: str) -> dict[str, Any]:
    enterprise = Enterprise(state["service"])
    old = enterprise.inspect("offering", "resilient-placement")
    raw = {
        "offering_id": "resilient-placement",
        "stage": stage,
        "execution_operation": None,
        "commercial": e.commercial(state, 100) if stage == "commercially-assessed" else None,
    }
    return enterprise.apply(
        e.command(state, "advance", raw, "advance-" + stage, old["digest"], principal="commercial-controller")
    )


def prepare(state: dict[str, Any], stage: str = "authorized") -> dict[str, Any]:
    """Use an actual accepted finite prototype with separate fixture signers."""
    s.funding(state)
    e.register(state)
    e.decision(state)
    executor, mission, profile, original = e.execution(state)
    permit = sign_record(
        state["keys"]["prototype-controller"],
        "prototype-controller",
        "flywheel-execution-permit",
        original.payload,
    )
    Enterprise(state["service"]).run("first-decision", executor, mission, profile, permit)
    record = state["journal"].latest(operation_key("placement-origin"))
    e.advance(state, "prototype")
    e.accept(state, record)
    technical = e.advance(state, "technically-qualified")
    assert record["permit"]["principal"] == "prototype-controller"
    assert state["journal"].latest(ACCEPTANCE_KEY + "placement-origin")["acceptance"]["principal"] == "acceptor"
    if stage == "technically-qualified":
        return technical
    assessed = advance(state, "commercially-assessed")
    if stage == "commercially-assessed":
        return assessed
    authorized = advance(state, "authorized")
    assert authorized["signed"]["principal"] == "commercial-controller"
    return authorized


def withdraw(state: dict[str, Any], support: str) -> None:
    if support in {"acceptor", "prototype-controller"}:
        state["trust"].revoke(support)
    else:
        with state["journal"].transaction() as cx:
            state["service"]._state(cx)
            record = state["journal"].document(state["journal"].latest(operation_key("placement-origin"), cx))
            record["result"]["limitations"].append("Changed after the original accepted prototype")
            state["journal"].append(cx, operation_key("placement-origin"), record)
            state["service"].checkpoint.advance(state["journal"], cx)
    # Current operator and commercial authority remain independently eligible.
    state["trust"].anchor("controller", "controller")
    state["trust"].anchor("commercial-controller", "controller")


@pytest.mark.parametrize("support", ["acceptor", "prototype-controller", "changed-origin"])
def test_production_decision_rechecks_its_original_accepted_prototype(setup: dict[str, Any], support: str) -> None:
    qualified = prepare(setup)
    original_costs = setup["costs"].snapshot()
    withdraw(setup, support)
    selected = e.decision(setup, "after-withdrawal", action="produce")
    assert selected["selected"] == "hold"
    assert not selected["alternatives"][0]["eligible"]
    assert "prototype acceptance is missing, changed or no longer eligible" in selected["alternatives"][0]["reasons"]
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement") == qualified
    assert setup["costs"].snapshot() == original_costs


@pytest.mark.parametrize("support", ["acceptor", "prototype-controller", "changed-origin"])
def test_production_dispatch_refuses_withdrawn_prototype_atomically(setup: dict[str, Any], support: str) -> None:
    qualified = prepare(setup)
    enterprise = Enterprise(setup["service"])
    decision = e.decision(setup, "before-withdrawal", action="produce")
    assert decision["selected"] == "deliver"
    withdraw(setup, support)
    executor, mission, profile, permit = e.execution(setup, "refused-production")
    before = setup["journal"].verify()
    costs = setup["costs"].snapshot()
    capacity = enterprise._read("active", "capacity", None)
    with setup["journal"].transaction() as cx:
        assert decision["context"] == enterprise._context(cx)
    with pytest.raises((ValueError, KeyError)):
        enterprise.run("before-withdrawal", executor, mission, profile, permit)
    assert setup["journal"].verify() == before
    assert setup["costs"].snapshot() == costs
    assert enterprise._read("active", "capacity", None) == capacity
    assert enterprise.inspect("decision", "before-withdrawal") == decision
    assert enterprise.inspect("offering", "resilient-placement") == qualified
    assert executor.transport.turn == 0
    with pytest.raises(KeyError):
        setup["journal"].latest(operation_key("refused-production"))
    with pytest.raises(KeyError):
        enterprise.inspect("launch", "refused-production")


@pytest.mark.parametrize("stage", ["commercially-assessed", "authorized"])
@pytest.mark.parametrize("support", ["acceptor", "prototype-controller", "changed-origin"])
def test_new_qualification_transition_requires_current_exact_prototype(
    setup: dict[str, Any], stage: str, support: str
) -> None:
    previous = "technically-qualified" if stage == "commercially-assessed" else "commercially-assessed"
    historical = prepare(setup, previous)
    withdraw(setup, support)
    before = setup["journal"].verify()
    costs = setup["costs"].snapshot()
    with pytest.raises((ValueError, KeyError)):
        advance(setup, stage)
    assert setup["journal"].verify() == before
    assert setup["costs"].snapshot() == costs
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement") == historical


@pytest.mark.parametrize("unrelated_revocation", [False, True])
def test_current_accepted_prototype_and_separate_operator_still_produce(
    setup: dict[str, Any], unrelated_revocation: bool
) -> None:
    qualified = prepare(setup)
    if unrelated_revocation:
        setup["trust"].revoke("executor")
    selected = e.decision(setup, "current-production", action="produce")
    assert selected["selected"] == "deliver"
    result = Enterprise(setup["service"]).run("current-production", *e.execution(setup, "current-delivery"))
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
    assert Enterprise(setup["service"]).inspect("offering", "resilient-placement") == qualified


@pytest.mark.parametrize("support", ["acceptor", "prototype-controller"])
def test_unqualified_old_acceptance_does_not_forbid_a_separately_permitted_new_prototype(
    setup: dict[str, Any], support: str
) -> None:
    prepare(setup)
    withdraw(setup, support)
    selected = e.decision(setup, "new-internal-prototype", action="prototype")
    assert selected["selected"] == "deliver"
    result = Enterprise(setup["service"]).run(
        "new-internal-prototype", *e.execution(setup, "independent-internal-prototype")
    )
    assert result["status"] == "delivered-awaiting-independent-acceptance-and-costs"
