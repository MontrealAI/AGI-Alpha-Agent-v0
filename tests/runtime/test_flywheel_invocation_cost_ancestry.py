# SPDX-License-Identifier: Apache-2.0
"""Historical protected invocations remain costable without granting fresh access."""

from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import ComparisonCost
from alpha_factory_v1.core.runtime.successor.protocol import digest
import test_flywheel_comparisons as comparison
import test_flywheel_protected as protected


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return protected.setup.__wrapped__(tmp_path)


def invoke(state: dict[str, Any], *, logical_limit: int = 10_000) -> tuple[str, Any, Any]:
    ident = protected.admitted(state)
    request = protected.invocation().model_copy(update={"logical_limit": logical_limit})
    proof = protected.proof(state, ident, "invoke", digest("flywheel-invocation", request))
    receipt = state["service"].invoke(ident, request, proof)
    return ident, request, receipt


def current_costs(state: dict[str, Any], mission: str) -> None:
    with state["journal"].transaction() as cx:
        state["costs"].require_current_evidence(mission, ["B"], cx)


@pytest.mark.parametrize("logical_limit", [1, 10_000])
def test_reconciled_success_and_failure_keep_legitimate_invocation_costs(
    setup: dict[str, Any], logical_limit: int
) -> None:
    _, request, receipt = invoke(setup, logical_limit=logical_limit)
    assert (receipt["result"] is not None) == (logical_limit > 1)
    protected.close_zero_cost_attempt(setup, request.mission_id)
    before = setup["costs"].snapshot()
    current_costs(setup, request.mission_id)
    assert setup["costs"].snapshot() == before
    assert setup["costs"].report(request.mission_id)["bucket_complete"]["B"]
    assert before["charges"]["reuse/" + request.mission_id]["original"]["signed"] is None


def test_complete_comparison_accepts_actual_protected_invocation_ancestry(setup: dict[str, Any]) -> None:
    spec = comparison.plan(setup, count=1).model_copy(
        update={"additional_costs": [ComparisonCost(role="E+", mission_id="fresh-peer", bucket="B")]}
    )
    comparison.d.register(setup)
    comparison.Discovery(setup["service"]).apply(comparison.d.command(setup, "comparison", spec, "freeze-comparison"))
    _, request, _ = invoke(setup)
    protected.close_zero_cost_attempt(setup, request.mission_id)
    for trial in spec.cases[0].trials:
        comparison.run_trial(setup, trial)
    value = comparison.report(setup, spec)
    assert value["current_evidence_valid"]
    assert value["contrasts"]["retained"]["complete_matched_outcomes"]
    assert value["contrasts"]["retained"]["cost_saving_micro_usd"] == "0"
    assert value["retained_invocation_established"] is False


@pytest.mark.parametrize("change", ["expiry", "capsule-revocation", "ens-owner"])
def test_historical_costs_survive_without_reviving_fresh_authority(
    setup: dict[str, Any], change: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)
    ident, request, _ = invoke(setup)
    protected.close_zero_cost_attempt(setup, request.mission_id)
    if change == "expiry":
        monkeypatch.setattr(time, "time", lambda: now + 3600)
    elif change == "capsule-revocation":
        protected.control(setup, ident, "revoke")
    else:
        for rpc in setup["rpc"]:
            rpc.owners[protected.namehash("two.agent.agi.eth").hex()] = "0x" + "12" * 20
    before = setup["costs"].snapshot()
    calls = [len(rpc.calls) for rpc in setup["rpc"]]
    current_costs(setup, request.mission_id)
    assert [len(rpc.calls) for rpc in setup["rpc"]] == calls
    assert setup["costs"].snapshot() == before
    fresh = request.model_copy(update={"mission_id": "not-authorized-again"})
    token = protected.proof(setup, ident, "invoke", digest("flywheel-invocation", fresh))
    with pytest.raises((ValueError, Conflict)):
        setup["service"].invoke(ident, fresh, token)
    with pytest.raises(KeyError):
        setup["journal"].latest("@flywheel-invocation:" + fresh.mission_id)


@pytest.mark.parametrize(
    "attack",
    [
        "missing-invocation",
        "request",
        "attempt",
        "activity",
        "category",
        "amount",
        "candidate",
        "authorization",
        "unconsumed",
        "signature",
        "journal",
        "purpose",
        "time",
        "accountant",
        "missing-signature-field",
        "legacy-unqualified",
        "nested-original",
    ],
)
def test_null_signature_needs_exact_historical_invocation_and_consumed_proof(
    setup: dict[str, Any], attack: str
) -> None:
    _, request, receipt = invoke(setup)
    protected.close_zero_cost_attempt(setup, request.mission_id)
    ledger = setup["costs"].snapshot()
    row = copy.deepcopy(ledger["charges"]["reuse/" + request.mission_id])
    invocation_key = "@flywheel-invocation:" + request.mission_id
    challenge_key = "@flywheel-challenge:" + receipt["authorization"]["challenge_id"]
    if attack in {"activity", "category", "amount", "attempt", "missing-invocation"}:
        field, value = {
            "activity": ("activity_id", "unrelated"),
            "category": ("category", "model"),
            "amount": ("accrued_micro_usd", 1),
            "attempt": ("evidence_digest", protected.ZERO),
            "missing-invocation": ("mission_id", "never-invoked"),
        }[attack]
        row["original"][field] = value
    elif attack == "missing-signature-field":
        del row["original"]["signed"]
    elif attack == "nested-original":
        row["original"]["original"] = copy.deepcopy(row["original"])
    elif attack == "accountant":
        setup["trust"].revoke("accountant")
    else:
        key = (
            invocation_key
            if attack in {"request", "candidate", "authorization", "time", "legacy-unqualified"}
            else challenge_key
        )

        def change(value: dict[str, Any]) -> None:
            if attack == "request":
                value["request"]["logical_limit"] += 1
            elif attack == "candidate":
                value["receipt"]["candidate_digest"] = protected.ZERO
            elif attack == "authorization":
                value["receipt"]["authorization"]["wallet"] = "0x" + "12" * 20
            elif attack == "time":
                value["receipt"]["started_at"] = 0
            elif attack == "legacy-unqualified":
                value["request"] = None
            elif attack == "unconsumed":
                value["used"] = False
            elif attack == "signature":
                value["signature"] = "00" * 65
            elif attack == "journal":
                value["payload"]["journal_identity"] = protected.ZERO
            elif attack == "purpose":
                value["payload"]["action"] = "discover"

        comparison.rewrite(setup, key, change)
    with setup["journal"].transaction() as cx:
        with pytest.raises((ValueError, KeyError, TypeError, Conflict)):
            setup["costs"]._current_charge(row, cx)


def test_resolved_row_cannot_substitute_a_different_valid_reservation(setup: dict[str, Any]) -> None:
    ident, request, _ = invoke(setup)
    protected.close_zero_cost_attempt(setup, request.mission_id)
    second = request.model_copy(update={"mission_id": "another-valid-invocation"})
    setup["service"].invoke(
        ident, second, protected.proof(setup, ident, "invoke", digest("flywheel-invocation", second))
    )
    protected.close_zero_cost_attempt(setup, second.mission_id)
    row = setup["costs"].snapshot()["charges"]["reuse/" + request.mission_id]
    parent = copy.deepcopy(row)
    parent["original"] = setup["costs"].snapshot()["charges"]["reuse/" + second.mission_id]["original"]
    with setup["journal"].transaction() as cx:
        setup["costs"]._current_charge(parent["original"], cx)
        with pytest.raises(ValueError, match="differs from its original reservation"):
            setup["costs"]._current_charge(parent, cx)


def test_consumed_proof_can_cross_expiry_before_receipt_timestamp(
    setup: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    now = int(time.time())
    monkeypatch.setattr(time, "time", lambda: now)
    ident = protected.admitted(setup)
    request = protected.invocation()
    proof = protected.proof(setup, ident, "invoke", digest("flywheel-invocation", request))
    expiry = setup["journal"].latest("@flywheel-challenge:" + proof.challenge_id)["payload"]["expires_at"]
    for rpc in setup["rpc"]:
        rpc.block["timestamp"] = hex(expiry - 1)
    now = expiry - 1
    original_consume = setup["access"].consume

    def consume(prepared: Any, cx: Any) -> dict[str, Any]:
        nonlocal now
        authority = original_consume(prepared, cx)
        now = expiry
        return dict(authority)

    monkeypatch.setattr(setup["access"], "consume", consume)
    receipt = setup["service"].invoke(ident, request, proof)
    assert receipt["started_at"] == expiry and receipt["authorization"]["checked_at"] == expiry - 1
    protected.close_zero_cost_attempt(setup, request.mission_id)
    current_costs(setup, request.mission_id)
