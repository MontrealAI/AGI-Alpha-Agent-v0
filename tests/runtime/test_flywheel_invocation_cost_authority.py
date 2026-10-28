# SPDX-License-Identifier: Apache-2.0
"""Existing unsigned invocation reservations with fictional identity and funding."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.successor.flywheel_comparisons import _costs
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, KEY, Charge
from alpha_factory_v1.core.runtime.successor.protocol import digest
import test_flywheel_protected as f


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def invocation(state: dict[str, Any], *, fail: bool = False) -> tuple[str, Any, dict[str, Any]]:
    ident = f.admitted(state)
    request = f.invocation()
    if fail:
        request = request.model_copy(update={"logical_limit": 1})
    proof = f.proof(state, ident, "invoke", digest("flywheel-invocation", request))
    receipt = state["service"].invoke(ident, request, proof)
    assert receipt["status"] == ("failed" if fail else "executed-awaiting-acceptance-and-complete-cost")
    assert receipt["authorization"]["challenge_id"] == proof.challenge_id
    original = state["costs"].snapshot()["charges"]["reuse/" + request.mission_id]
    assert original["signed"] is None and original["accrued_micro_usd"] is None
    reconcile(state, request)
    return ident, request, receipt


def reconcile(state: dict[str, Any], request: Any) -> None:
    for category in sorted(CATEGORIES):
        row = Charge(
            activity_id="reuse/" + request.mission_id if category == "compute" else "invocation-cost/" + category,
            mission_id=request.mission_id,
            bucket="B",
            category=category,
            accrued_micro_usd=7 if category == "compute" else 1,
            paid_micro_usd=0,
            basis="attested",
            evidence_digest=f.ZERO,
            note="Fictional reconciliation, preserving all failed-attempt liability; no real provider billing",
        )
        f.account(state, "resolve" if category == "compute" else "charge", row.model_dump(), "reconcile/" + category)
    f.account(
        state,
        "seal-reuse",
        {"mission_id": request.mission_id, "evidence_digest": f.ZERO, "categories": sorted(CATEGORIES)},
        "invocation-cost-seal",
    )


def report(state: dict[str, Any], mission: str) -> dict[str, Any]:
    with state["journal"].transaction() as cx:
        return _costs(SimpleNamespace(costs=state["costs"]), mission, ["B"], cx)


def rewrite(state: dict[str, Any], journal_key: str, change: Any) -> None:
    with state["journal"].transaction() as cx:
        state["service"]._state(cx)
        value = state["journal"].document(state["journal"].latest(journal_key, cx))
        change(value)
        state["journal"].append(cx, journal_key, value)
        state["service"].checkpoint.advance(state["journal"], cx)


@pytest.mark.parametrize("fail,expired", [(False, False), (True, False), (False, True)])
def test_real_reconciled_invocation_costs_keep_current_support_without_reconsuming(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch, fail: bool, expired: bool
) -> None:
    _, request, receipt = invocation(setup, fail=fail)
    challenge_key = "@flywheel-challenge:" + receipt["authorization"]["challenge_id"]
    challenge = setup["journal"].latest(challenge_key)
    assert challenge["used"] is True
    if expired:
        monkeypatch.setattr(time, "time", lambda: challenge["payload"]["expires_at"] + 1)
    rpc_calls = [list(reader.calls) for reader in setup["rpc"]]

    def refuse_new_authority(*args: Any, **kwargs: Any) -> None:
        pytest.fail("cost inspection must not issue, prepare, consume, or renew resource authority")

    for name in ("challenge", "prepare", "consume"):
        monkeypatch.setattr(setup["access"], name, refuse_new_authority)
    monkeypatch.setattr(setup["access"].authority, "verify", refuse_new_authority)
    before = setup["journal"].verify()
    costs = copy.deepcopy(setup["costs"].snapshot())
    current = report(setup, request.mission_id)
    assert current["historical_complete"] and current["current_evidence_valid"] and current["complete"]
    assert current["known_micro_usd"] == {"B": "15"}
    assert setup["costs"].snapshot() == costs
    assert costs["charges"]["reuse/" + request.mission_id]["original"]["signed"] is None
    assert setup["journal"].verify() == before
    assert setup["journal"].latest(challenge_key) == challenge
    assert [reader.calls for reader in setup["rpc"]] == rpc_calls


@pytest.mark.parametrize(
    "principal", ["producer", "evaluator", "validator", "controller", "executor", "acceptor", "accountant"]
)
def test_revoked_invocation_support_stays_historical_without_current_qualification(
    setup: dict[str, Any], principal: str
) -> None:
    _, request, _ = invocation(setup)
    setup["trust"].revoke(principal)
    before = setup["journal"].verify()
    ledger = copy.deepcopy(setup["costs"].snapshot())
    current = report(setup, request.mission_id)
    assert current["historical_complete"] and not current["current_evidence_valid"] and not current["complete"]
    assert current["known_micro_usd"] == {"B": "15"}
    assert setup["costs"].snapshot() == ledger and setup["journal"].verify() == before


@pytest.mark.parametrize(
    "attack",
    [
        "orphan",
        "attempt",
        "request",
        "scope",
        "unsigned-resolved",
        "unconsumed",
        "wallet-signature",
        "wrong-purpose",
        "other-request-authorization",
    ],
)
def test_unsigned_reservation_requires_exact_durable_invocation_and_consumed_authority(
    setup: dict[str, Any], attack: str
) -> None:
    ident, request, receipt = invocation(setup)
    activity = "reuse/" + request.mission_id
    if attack in {"orphan", "attempt", "scope", "unsigned-resolved"}:

        def ledger_change(value: dict[str, Any]) -> None:
            current = value["charges"][activity]
            original = current["original"]
            if attack == "orphan":
                original["mission_id"] = "no-durable-invocation"
                original["activity_id"] = "reuse/no-durable-invocation"
            elif attack == "attempt":
                original["evidence_digest"] = f.ZERO
            elif attack == "scope":
                original["bucket"] = "A"
            else:
                current["signed"] = None

        rewrite(setup, KEY, ledger_change)
    elif attack == "request":
        rewrite(
            setup,
            "@flywheel-invocation:" + request.mission_id,
            lambda value: value["request"].update(recipient_capabilities_digest="1" * 64),
        )
    elif attack in {"wrong-purpose", "other-request-authorization"}:
        if attack == "wrong-purpose":
            purpose = digest("flywheel-discover", {"candidate_digest": ident})
            authority = setup["service"].manifest(ident, f.proof(setup, ident, "discover", purpose))["authorization"]
        else:
            other = request.model_copy(update={"mission_id": "another-actually-authorized-invocation"})
            other_proof = f.proof(setup, ident, "invoke", digest("flywheel-invocation", other))
            authority = setup["service"].invoke(ident, other, other_proof)["authorization"]
        rewrite(
            setup,
            "@flywheel-invocation:" + request.mission_id,
            lambda value: value["receipt"].update(authorization=authority),
        )
    else:
        challenge_key = "@flywheel-challenge:" + receipt["authorization"]["challenge_id"]

        def challenge_change(value: dict[str, Any]) -> None:
            if attack == "unconsumed":
                value["used"] = False
            elif attack == "wallet-signature":
                value["signature"] = "00" * 65

        rewrite(setup, challenge_key, challenge_change)
    before = setup["journal"].verify()
    current = report(setup, request.mission_id)
    assert current["historical_complete"] and not current["current_evidence_valid"] and not current["complete"]
    assert current["known_micro_usd"] == {"B": "15"}
    assert setup["journal"].verify() == before


def test_unsigned_invocation_reservation_requires_the_existing_service_validator(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    _, request, _ = invocation(setup)
    monkeypatch.setattr(setup["costs"], "invocation_reservation_check", None, raising=False)
    assert not report(setup, request.mission_id)["current_evidence_valid"]


def test_interrupted_invocation_keeps_unknown_liability_until_explicit_reconciliation(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    from alpha_factory_v1.core.runtime.successor import flywheel_capsules

    ident = f.admitted(setup)
    request = f.invocation()
    proof = f.proof(setup, ident, "invoke", digest("flywheel-invocation", request))

    def interrupted(*args: Any) -> None:
        raise SystemExit("offline fixture interruption after durable reservation")

    monkeypatch.setattr(flywheel_capsules, "execute_selection", interrupted)
    with pytest.raises(SystemExit, match="durable reservation"):
        setup["service"].invoke(ident, request, proof)
    stored = setup["service"].inspect_invocation(request.mission_id)
    assert stored["receipt"]["status"] == "executing-or-uncertain"
    unknown = report(setup, request.mission_id)
    assert unknown["current_evidence_valid"] and not unknown["historical_complete"] and not unknown["complete"]
    assert setup["costs"].snapshot()["charges"]["reuse/" + request.mission_id]["accrued_micro_usd"] is None
    reconcile(setup, request)
    current = report(setup, request.mission_id)
    assert current["current_evidence_valid"] and current["complete"]
    assert current["known_micro_usd"] == {"B": "15"}
    assert setup["service"].inspect_invocation(request.mission_id) == stored
    assert stored["receipt"]["successful_reuse"] is False


def test_placement_invocation_uses_the_same_bound_cost_authority(setup: dict[str, Any]) -> None:
    from alpha_factory_v1.core.runtime.successor.flywheel_specialists import PlacementInvocation, PlacementWorkflow
    import test_flywheel_specialists as specialists

    origin = specialists.origin(setup)
    ident = specialists.retain(setup, origin, PlacementWorkflow(version=1))
    assert specialists.assess(setup, ident, synthetic_saving=20) == "assessed"
    f.control(setup, ident, "validate")
    f.control(setup, ident, "admit")
    request = PlacementInvocation(
        mission_id="actual-placement-invocation-cost",
        problem=specialists.problem(2300, hosts=5),
        beta_digest=f.BETA,
        policy_digest=f.POLICY,
        recipient_capabilities_digest=f.ZERO,
        prerequisite_digests=[],
        logical_limit=100_000,
        cost_cap_micro_usd=100,
    )
    proof = f.proof(setup, ident, "invoke", digest("flywheel-invocation", request))
    receipt = setup["service"].invoke(ident, request, proof)
    assert receipt["status"] == "executed-awaiting-acceptance-and-complete-cost"
    reconcile(setup, request)
    current = report(setup, request.mission_id)
    assert current["current_evidence_valid"] and current["complete"]
    assert current["known_micro_usd"] == {"B": "15"}


def test_valid_consumed_authority_survives_a_pause_before_the_receipt_timestamp(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    ident = f.admitted(setup)
    request = f.invocation()
    proof = f.proof(setup, ident, "invoke", digest("flywheel-invocation", request))
    consume = setup["access"].consume

    def consume_then_pause(*args: Any) -> dict[str, Any]:
        authority = consume(*args)
        resumed_at = int(time.time()) + 121
        monkeypatch.setattr(time, "time", lambda: resumed_at)
        return authority

    monkeypatch.setattr(setup["access"], "consume", consume_then_pause)
    receipt = setup["service"].invoke(ident, request, proof)
    assert receipt["status"] == "executed-awaiting-acceptance-and-complete-cost"
    challenge = setup["journal"].latest("@flywheel-challenge:" + proof.challenge_id)
    assert challenge["used"] is True
    assert receipt["started_at"] > challenge["payload"]["expires_at"]
    reconcile(setup, request)
    assert report(setup, request.mission_id)["current_evidence_valid"]
