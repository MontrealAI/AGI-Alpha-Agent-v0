# SPDX-License-Identifier: Apache-2.0
"""Adversarial review regressions; configured local roles are not organizational independence."""

from concurrent.futures import ThreadPoolExecutor
import threading

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.measurement import ConfirmationDesign
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import SignedEnvelope, sign_record
from test_measurement import observations, reserve, setup


def test_verified_approval_cannot_change_while_waiting_for_journal_lock(tmp_path, monkeypatch):
    ledger, keys, trust = setup(tmp_path)
    original = reserve(ledger, keys, n=20)
    approval = SignedEnvelope(**original["approval"])
    changed = ConfirmationDesign(**{**original["frozen"], "code_digest": "b" * 64})
    verified = threading.Event()
    verify = trust.verify

    def signal_verified(*args, **kwargs):
        result = verify(*args, **kwargs)
        verified.set()
        return result

    monkeypatch.setattr(trust, "verify", signal_verified)
    with ThreadPoolExecutor(max_workers=1) as pool:
        with ledger.journal.transaction():
            pending = pool.submit(ledger.reserve_confirmation, changed, 20, 1, approval, operation_id="unsigned-race")
            assert verified.wait(5), "signature verification did not reach the deterministic race boundary"
            approval.payload.update(freeze_digest=digest("confirmation-design", changed), operation_id="unsigned-race")
        with pytest.raises(ValueError, match="stale"):
            pending.result(timeout=10)
    with pytest.raises(ValueError, match="signature is invalid"):
        verify(approval, "measurement-confirmation", "verifier")
    assert len(ledger.snapshot()["attempts"]) == 1


@pytest.mark.parametrize("sample_size,claims", [(10000, 16), (5001, 1), (1000, 16)])
def test_unserializable_design_dimensions_fail_before_consuming_an_attempt(tmp_path, sample_size, claims):
    ledger, keys, _ = setup(tmp_path)
    with pytest.raises(ValueError, match="fixed bounded"):
        reserve(ledger, keys, n=sample_size, claims=claims)
    assert ledger.snapshot()["attempts"] == []


def test_largest_admitted_sample_product_can_actually_complete(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=5000, claims=2)
    result = ledger.conclude(attempt["attempt"], observations(ledger, keys, attempt, offset="boundary"))
    assert len(result["claims"]) == 2
    assert [claim["claim_id"] for claim in result["claims"]] == [
        claim["claim_id"] for claim in attempt["frozen"]["claims"]
    ]
    assert result["authorization_granted"] is False


def test_claim_definitions_are_frozen_and_duplicate_identities_rejected(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=20, claims=2)
    duplicate = {**attempt["frozen"], "claims": [attempt["frozen"]["claims"][0]] * 2}
    with pytest.raises(ValueError, match="unique"):
        ConfirmationDesign(**duplicate)
    changed_fields = {**attempt["frozen"], "claims": [dict(c) for c in attempt["frozen"]["claims"]]}
    changed_fields["claims"][0]["estimand"] = "post-hoc favorable subpopulation"
    changed = ConfirmationDesign(**changed_fields)
    with pytest.raises(ValueError, match="stale"):
        ledger.reserve_confirmation(changed, 20, 2, SignedEnvelope(**attempt["approval"]), operation_id="changed")
    assert len(ledger.snapshot()["attempts"]) == 1


def test_only_signed_custodian_can_abandon_and_failed_attempt_keeps_its_allocation(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=20)
    reason = "bounded exploration exhausted"
    payload = {
        "journal_identity": ledger.journal.identity,
        "attempt_digest": attempt["attempt_digest"],
        "reason": reason,
    }
    producer = sign_record(keys["local-producer"], "local-producer", "measurement-abandon", payload)
    with pytest.raises(ValueError, match="required role"):
        ledger.abandon(1, reason, producer)
    wrong_terms = sign_record(keys["local-verifier"], "local-verifier", "measurement-abandon", payload)
    with pytest.raises(ValueError, match="exact attempt"):
        ledger.abandon(1, "different reason", wrong_terms)
    assert ledger.snapshot()["attempts"][0]["state"] == "reserved"
    ledger.abandon(1, reason, wrong_terms)
    with pytest.raises(Conflict, match="terminal"):
        ledger.abandon(1, reason, wrong_terms)
    second = reserve(ledger, keys, n=20, operation="after-abandon")
    assert second["attempt"] == 2
    assert second["alpha_per_claim"] == "1/120"


def test_authenticated_partial_sample_is_terminal_and_disclosed_units_cannot_be_reused(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    first = reserve(ledger, keys, n=20)
    result = ledger.conclude(1, observations(ledger, keys, first, n=19, offset="disclosed"))
    assert result["decision"] == "invalid-sample"
    assert result["claims"] == []
    assert result["authorization_granted"] is False
    assert len(result["unit_ids"]) == 19
    with pytest.raises(Conflict, match="cannot be reused"):
        ledger.conclude(1, observations(ledger, keys, first, offset="replacement"))
    second = reserve(ledger, keys, n=19, operation="reuse-disclosed")
    reused = ledger.conclude(2, observations(ledger, keys, second, offset="disclosed"))
    assert reused["decision"] == "invalid-sample"
    assert reused["claims"] == []
    assert len(ledger.snapshot()["attempts"]) == 2


def test_unauthenticated_partial_submission_cannot_poison_another_attempt(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=20)
    forged = sign_record(
        keys["local-producer"],
        "local-producer",
        "measurement-observations",
        observations(ledger, keys, attempt, n=19).payload,
    )
    with pytest.raises(ValueError, match="required role"):
        ledger.conclude(1, forged)
    assert ledger.snapshot()["attempts"][0]["state"] == "reserved"
    result = ledger.conclude(1, observations(ledger, keys, attempt))
    assert len(result["claims"]) == 1
    assert result["authorization_granted"] is False
