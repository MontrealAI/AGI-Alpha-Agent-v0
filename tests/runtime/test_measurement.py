# SPDX-License-Identifier: Apache-2.0
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from fractions import Fraction

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.measurement import (
    ConfirmationDesign,
    EvaluationInstrument,
    MeasurementLedger,
)
from alpha_factory_v1.core.runtime.successor.protocol import digest
from alpha_factory_v1.core.runtime.successor.trust import local_principals, sign_record


def setup(tmp_path, epsilon=None):
    journal = Journal.initialize(tmp_path / "agent")
    trust, keys = local_principals()
    ledger = MeasurementLedger(journal, trust)
    instrument = EvaluationInstrument(
        instrument_id="outcome",
        version=1,
        domain="public-documents",
        method="separately adjudicated coverage",
        implementation_digest="1" * 64,
        calibration_error_ppm=epsilon,
        calibration_evidence=[] if epsilon is None else ["a" * 64],
        calibration_scope="constructed arithmetic; not empirical calibration",
    )
    approve_instrument(ledger, keys, instrument, None, "initial")
    return ledger, keys, trust


def approve_instrument(ledger, keys, instrument, previous, operation):
    validation = sign_record(
        keys["local-verifier"],
        "local-verifier",
        "measurement-validation",
        {
            "journal_identity": ledger.journal.identity,
            "previous_instrument": previous,
            "instrument_digest": digest("measurement-instrument", instrument),
            "diagnosis": "proxy missed a material qualification",
            "scope": "local rehearsal only",
            "cases": [
                {
                    "id": "case-one",
                    "evidence_digest": "2" * 64,
                    "old_score_ppm": 0,
                    "new_score_ppm": 1000000,
                    "outcome_ppm": 1000000,
                }
            ],
        },
    )
    approval = sign_record(
        keys["local-controller"],
        "local-controller",
        "measurement-approval",
        {
            "journal_identity": ledger.journal.identity,
            "previous_instrument": previous,
            "instrument_digest": digest("measurement-instrument", instrument),
            "validation_digest": digest("measurement-validation", validation.model_dump()),
        },
    )
    return ledger.revise_instrument(instrument, validation, approval, operation_id=operation)


def reserve(ledger, keys, operation="attempt-one", n=2000, claims=1, campaign="campaign-one", **changes):
    fields = dict(
        campaign_id=campaign,
        producer="local-producer",
        charter_digest="1" * 64,
        candidate_digest="2" * 64,
        comparator_digest="3" * 64,
        code_digest="4" * 64,
        model_digest="5" * 64,
        configuration_digest="6" * 64,
        bridge_digest="7" * 64,
        resource_rules_digest="8" * 64,
        initial_agents_digest="9" * 64,
        archive_access_digest="a" * 64,
        sampling_unit="independent-campaign",
        population="fresh complete campaigns",
        independence_protocol="custodian draws fresh initial agents and untouched terminal cases",
        claims=[
            {
                "claim_id": f"claim-{i}",
                "estimand": "mean paired terminal outcome gain",
                "score_definition": "frozen evaluator integer ppm under common instrument",
            }
            for i in range(claims)
        ],
        margin_ppm=20000,
    )
    fields.update(changes)
    frozen = ConfirmationDesign(**fields)
    epoch = ledger.snapshot()["epochs"][-1]
    approval = sign_record(
        keys["local-verifier"],
        "local-verifier",
        "measurement-confirmation",
        {
            "journal_identity": ledger.journal.identity,
            "freeze_digest": digest("confirmation-design", frozen),
            "sample_size": n,
            "claim_count": claims,
            "instrument_digest": epoch["instrument_digest"],
            "epoch": epoch["epoch"],
            "operation_id": operation,
        },
    )
    return ledger.reserve_confirmation(frozen, n, claims, approval, operation_id=operation)


def observations(ledger, keys, attempt, n=None, offset="one", gain=100000):
    n = attempt["sample_size"] if n is None else n
    return sign_record(
        keys["local-verifier"],
        "local-verifier",
        "measurement-observations",
        {
            "journal_identity": ledger.journal.identity,
            "attempt_digest": attempt["attempt_digest"],
            "unit_ids": [f"{offset}-{i}" for i in range(n)],
            "scores": [[[500000 + gain, 500000] for _ in range(n)] for _ in range(attempt["claim_count"])],
            "freshness_attestation": "constructed after reservation; simulated process evidence only",
            "independence_attestation": "test-only independent campaign labels; not empirical research",
        },
    )


def test_width_two_calibration_and_no_automatic_authority(tmp_path):
    ledger, keys, _ = setup(tmp_path, epsilon=10000)
    attempt = reserve(ledger, keys)
    result = ledger.conclude(1, observations(ledger, keys, attempt))
    claim = result["claims"][0]
    assert abs(Decimal(claim["score_lower_bound"]) - Decimal("0.0392638538")) < Decimal("0.00000001")
    assert claim["score_margin_pass"] is True
    assert claim["outcome_margin_pass"] is False
    assert result["authorization_granted"] is False
    assert result["alpha_per_claim"] == "1/40"


def test_missing_calibration_remains_explicit(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys)
    result = ledger.conclude(1, observations(ledger, keys, attempt))
    assert result["claims"][0]["outcome_lower_bound"] is None
    assert result["claims"][0]["outcome_margin_pass"] is None


def test_global_failed_parallel_attempts_and_renaming(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    with ThreadPoolExecutor(max_workers=4) as pool:
        attempts = list(
            pool.map(lambda i: reserve(ledger, keys, operation=f"op-{i}", campaign=f"renamed-{i}", claims=2), range(4))
        )
    assert {a["attempt"] for a in attempts} == {1, 2, 3, 4}
    for attempt in attempts:
        assert Fraction(attempt["alpha_per_claim"]) == Fraction(1, 40 * attempt["attempt"] * (attempt["attempt"] + 1))
        reason = "budget exhausted; no evidence"
        approval = sign_record(
            keys["local-verifier"],
            "local-verifier",
            "measurement-abandon",
            {
                "journal_identity": ledger.journal.identity,
                "attempt_digest": attempt["attempt_digest"],
                "reason": reason,
            },
        )
        ledger.abandon(attempt["attempt"], reason, approval)
    reopened = MeasurementLedger(Journal(ledger.journal.root), ledger.trust)
    fifth = reserve(reopened, keys, operation="op-5", campaign="another-name")
    assert fifth["attempt"] == 5
    assert fifth["alpha_per_claim"] == "1/600"
    assert all(a["state"] == "abandoned" for a in reopened.snapshot()["attempts"][:4])


def test_fixed_sample_no_peeking_replay_or_changed_final_result(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=20)
    rejected = ledger.conclude(1, observations(ledger, keys, attempt, n=19, offset="partial"))
    assert rejected["decision"] == "invalid-sample"
    with pytest.raises(Conflict, match="failed or cancelled"):
        ledger.conclude(1, observations(ledger, keys, attempt))
    attempt = reserve(ledger, keys, operation="full", n=20)
    signed = observations(ledger, keys, attempt)
    result = ledger.conclude(2, signed)
    assert ledger.conclude(2, signed) == result
    with pytest.raises(Conflict, match="already completed"):
        ledger.conclude(2, observations(ledger, keys, attempt, gain=200000))
    second = reserve(ledger, keys, operation="second", n=20)
    assert ledger.conclude(3, observations(ledger, keys, second))["decision"] == "invalid-sample"
    third = reserve(ledger, keys, operation="third", n=19)
    assert ledger.conclude(4, observations(ledger, keys, third, offset="partial"))["decision"] == "invalid-sample"


def test_revision_creates_new_epoch_preserves_old_scores_and_binding(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    first = reserve(ledger, keys, n=20)
    old_result = ledger.conclude(1, observations(ledger, keys, first))
    previous = ledger.snapshot()["epochs"][-1]
    replacement = EvaluationInstrument(**{**previous["instrument"], "version": 2, "method": "validated replacement"})
    second_epoch = approve_instrument(ledger, keys, replacement, previous["instrument_digest"], "revision")
    assert second_epoch["epoch"] == 2
    second = reserve(ledger, keys, operation="second", n=20)
    assert second["epoch"] == 2
    assert ledger.snapshot()["attempts"][0]["result"] == old_result
    assert ledger.snapshot()["epochs"][0] == previous


def test_forged_roles_and_stale_changed_freeze_cannot_authorize(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=20)
    frozen = ConfirmationDesign(**{**attempt["frozen"], "code_digest": "b" * 64})
    approval = __import__("alpha_factory_v1.core.runtime.successor.trust", fromlist=["SignedEnvelope"]).SignedEnvelope(
        **attempt["approval"]
    )
    with pytest.raises(ValueError, match="stale"):
        ledger.reserve_confirmation(frozen, 20, 1, approval, operation_id="changed")
    forged = sign_record(
        keys["local-producer"],
        "local-producer",
        "measurement-observations",
        observations(ledger, keys, attempt).payload,
    )
    with pytest.raises(ValueError, match="required role"):
        ledger.conclude(1, forged)
    with pytest.raises(ValueError, match="different terms"):
        reserve(ledger, keys, n=21)


def test_producer_name_cannot_be_relabelled_to_evade_separation(tmp_path):
    ledger, keys, _ = setup(tmp_path)
    with pytest.raises(ValueError, match="configured runtime producer"):
        reserve(ledger, keys, producer="pretend-producer")


def test_alias_principals_sharing_a_producer_key_cannot_validate_instruments(tmp_path):
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry

    ledger, keys, trust = setup(tmp_path)
    aliased = TrustRegistry(
        {
            "local-producer": trust.anchor("local-producer", "producer"),
            "local-controller": trust.anchor("local-controller", "controller"),
            "local-verifier": TrustAnchor(
                trust.anchor("local-producer", "producer").public_key, frozenset({"verifier"})
            ),
        }
    )
    same_key = {**keys, "local-verifier": keys["local-producer"]}
    reopened = MeasurementLedger(ledger.journal, aliased)
    previous = reopened.snapshot()["epochs"][-1]
    replacement = EvaluationInstrument(**{**previous["instrument"], "version": 2})
    with pytest.raises(ValueError, match="distinct configured"):
        approve_instrument(reopened, same_key, replacement, previous["instrument_digest"], "alias-review")


@pytest.mark.parametrize("bad", [True, -1, 1000001, 1.5])
def test_scores_reject_bool_out_of_bounds_and_float(tmp_path, bad):
    ledger, keys, _ = setup(tmp_path)
    attempt = reserve(ledger, keys, n=1)
    payload = observations(ledger, keys, attempt).payload
    payload["scores"][0][0][0] = bad
    if isinstance(bad, float):
        with pytest.raises(ValueError):
            sign_record(keys["local-verifier"], "local-verifier", "measurement-observations", payload)
    else:
        assert (
            ledger.conclude(
                1, sign_record(keys["local-verifier"], "local-verifier", "measurement-observations", payload)
            )["decision"]
            == "invalid-sample"
        )
