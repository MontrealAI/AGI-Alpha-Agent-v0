# SPDX-License-Identifier: Apache-2.0
"""Strict Ed25519 import admission across native SUCCESSOR boundaries."""

from __future__ import annotations

import base64
import hashlib
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.store import canonical as historical_canonical
from alpha_factory_v1.core.runtime.successor.ascension import _verified, validate_historical_settlement
from alpha_factory_v1.core.runtime.successor.protocol import Institution, MissionConstitution, RehearsalRequest, digest
from alpha_factory_v1.core.runtime.successor.signatures import validate_ed25519_point, verify_ed25519
from alpha_factory_v1.core.runtime.successor.state import SuccessorStore
from alpha_factory_v1.core.runtime.successor.transport import result_envelope, verify_result
from alpha_factory_v1.core.runtime.successor.trust import JournalCheckpoint, TrustAnchor, local_principals, sign_record

# RFC 8032 section 7.1, TEST 1 (empty message).
PUBLIC = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
SIGNATURE = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb"
    "8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
)
FIELD = 2**255 - 19
ORDER = 2**252 + 27742317777372353535851937790883648493
TORSION_Y = (
    0,
    1,
    FIELD - 1,
    int.from_bytes(bytes.fromhex("26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05"), "little"),
    int.from_bytes(bytes.fromhex("c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a"), "little"),
)


def test_rfc8032_signature_and_changed_message() -> None:
    verify_ed25519(PUBLIC, SIGNATURE, b"")
    with pytest.raises(InvalidSignature):
        verify_ed25519(PUBLIC, SIGNATURE, b"changed")


@pytest.mark.parametrize("y", TORSION_Y + (FIELD, FIELD + 1, 2**255 - 1))
@pytest.mark.parametrize("sign", (0, 1))
def test_small_order_and_noncanonical_points_rejected_at_key_and_signature_r(y: int, sign: int) -> None:
    encoded = (y | (sign << 255)).to_bytes(32, "little")
    with pytest.raises(ValueError, match="noncanonical or has small order"):
        TrustAnchor(encoded.hex(), frozenset({"verifier"}))
    with pytest.raises(ValueError, match="noncanonical or has small order"):
        verify_ed25519(encoded, SIGNATURE, b"")
    with pytest.raises(ValueError, match="noncanonical or has small order"):
        verify_ed25519(PUBLIC, encoded + SIGNATURE[32:], b"")


@pytest.mark.parametrize("scalar", (ORDER, ORDER + 1, 2**256 - 1))
def test_noncanonical_signature_scalar_rejected(scalar: int) -> None:
    with pytest.raises(ValueError, match="scalar is noncanonical"):
        verify_ed25519(PUBLIC, SIGNATURE[:32] + scalar.to_bytes(32, "little"), b"")


def test_encoding_lengths_are_checked_before_library_verification() -> None:
    for size in (0, 31, 33):
        with pytest.raises(ValueError, match="exactly 32"):
            validate_ed25519_point(bytes(size))
    for size in (0, 63, 65):
        with pytest.raises(ValueError, match="exactly 64"):
            verify_ed25519(PUBLIC, bytes(size), b"")


def test_zero_key_forged_results_rejected_for_every_message() -> None:
    key = Ed25519PrivateKey.generate()
    request = RehearsalRequest(request_id="00000000-0000-4000-8000-000000000001")
    # Certain OpenSSL versions accept this forged pair for some messages. Do not
    # depend on any backend doing so: the boundary must reject every message.
    for index in range(32):
        forged = result_envelope(request, {"counter": index}, key)
        forged["signature"] = {"public_key": bytes(32).hex(), "signature": base64.b64encode(bytes(64)).decode()}
        with pytest.raises(ValueError, match="invalid result signature"):
            verify_result(forged, request)
        with pytest.raises(ValueError, match="invalid result signature"):
            verify_result(forged, request, bytes(32).hex())


def test_genuine_result_and_registry_signature_positive_controls() -> None:
    trust, keys = local_principals()
    request = RehearsalRequest(request_id="00000000-0000-4000-8000-000000000001")
    key = keys["local-verifier"]
    result = result_envelope(request, {"verdict": "HOLD"}, key)
    public = trust.anchor("local-verifier", "verifier").public_key
    assert verify_result(result, request, public)["authentication"] == "trusted-local-signer"
    record = sign_record(key, "local-verifier", "proof", {"verdict": "HOLD"})
    assert trust.verify(record, "proof", "verifier") == record.payload
    forged = record.model_copy(update={"signature": base64.b64encode(bytes(64)).decode()})
    with pytest.raises(ValueError, match="record signature is invalid"):
        trust.verify(forged, "proof", "verifier")
    altered = bytearray(base64.b64decode(result["signature"]["signature"]))
    altered[40] ^= 1
    result["signature"]["signature"] = base64.b64encode(altered).decode()
    with pytest.raises(ValueError, match="invalid result signature"):
        verify_result(result, request, public)


def test_zero_key_cannot_authenticate_adapter_binding() -> None:
    body = {"schema_version": 1, "counter": 1}
    public = bytes(32).hex()
    envelope = {
        "domain": "ascension-execution-binding",
        "body": body,
        "digest": digest("ascension-execution-binding", body),
        "public_key": public,
        "signature": base64.b64encode(bytes(64)).decode(),
    }
    with pytest.raises(ValueError, match="Adapter signature is invalid"):
        _verified(envelope, "ascension-execution-binding", public)


def test_zero_key_cannot_authenticate_historical_settlement() -> None:
    public = bytes(32).hex()
    chain = {"chain": 31337, "market": "0x" + "11" * 20, "job": 1}
    settlement = {"schema_version": 1, "chain": chain}
    body = {
        "schema": 1,
        "sequence": 1,
        "previous": "0" * 64,
        "identity": "urn:agialpha:ed25519:" + public,
        "mission": "@successor:ascension:settlement:" + digest("settlement-job", chain),
        "time_ns": 2**54,
        "document": {"state": "imported", "settlement": settlement},
    }
    raw = historical_canonical(body)
    record = {
        "schema": "agialpha.ascension.journal-settlement.v1",
        "public_key": public,
        "canonical_body": raw.decode(),
        "hash": hashlib.sha256(raw).hexdigest(),
        "signature": base64.b64encode(bytes(64)).decode(),
        "settlement": settlement,
    }
    with pytest.raises(ValueError, match="Historical settlement signature is invalid"):
        validate_historical_settlement(record)


def test_zero_key_portable_forgery_does_not_create_state(tmp_path: Path) -> None:
    trust, _ = local_principals()
    source = SuccessorStore(Journal.initialize(tmp_path / "source"), trust)
    source.create_institution(
        Institution(
            id="institution",
            controller="local-controller",
            constitution=MissionConstitution(mission_id="mission", owner="local-controller", objective="check imports"),
        ),
        {},
    )
    package = source.export_portable("institution")
    public = bytes(32).hex()
    identity = "urn:agialpha:ed25519:" + public
    package["payload"]["source_identity"] = identity
    package["payload"]["checkpoint"]["identity"] = identity
    package["digest"] = digest("portable", package["payload"])
    package["signature"] = base64.b64encode(bytes(64)).decode()
    checkpoint = JournalCheckpoint(**package["payload"]["checkpoint"])
    destination = SuccessorStore(Journal.initialize(tmp_path / "destination"), trust)
    before = destination.journal.verify()
    with pytest.raises(ValueError, match="portable source signature is invalid"):
        destination.restore_portable(package, {}, source_public_key=public, checkpoint=checkpoint)
    assert destination.journal.verify() == before
