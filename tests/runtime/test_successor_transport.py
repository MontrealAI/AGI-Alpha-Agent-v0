# SPDX-License-Identifier: Apache-2.0
"""A browser return cannot authenticate itself or substitute another request."""

from copy import deepcopy
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from alpha_factory_v1.core.runtime.successor.protocol import RehearsalRequest, canonical
from alpha_factory_v1.core.runtime.successor.transport import read_document, result_envelope, verify_result


def request(seed: int = 42) -> RehearsalRequest:
    return RehearsalRequest(request_id="12345678-1234-4234-8234-123456789012", seed=seed)


def test_round_trip_authenticates_only_separately_supplied_key() -> None:
    output = result_envelope(request(), {"verdict": "HOLD"}, Ed25519PrivateKey.generate())
    assert verify_result(output, request())["authentication"] == "untrusted-signer"
    checked = verify_result(output, request(), output["signature"]["public_key"])
    assert checked["authentication"] == "trusted-local-signer"
    assert checked["external_independence"] is False
    assert checked["production_authority"] is False
    assert checked["performance_remeasured"] is False


def test_an_attacker_signed_return_cannot_appoint_its_own_key() -> None:
    legitimate = result_envelope(request(), {}, Ed25519PrivateKey.generate())
    forgery = result_envelope(request(), {}, Ed25519PrivateKey.generate())
    with pytest.raises(ValueError, match="independently trusted"):
        verify_result(forgery, request(), legitimate["signature"]["public_key"])


@pytest.mark.parametrize("location", ["outer_request", "inner_request", "inner_scope", "evidence", "signature"])
def test_rejects_mutation_of_every_binding(location: str) -> None:
    output = result_envelope(request(), {"verdict": "HOLD"}, Ed25519PrivateKey.generate())
    changed = deepcopy(output)
    if location == "outer_request":
        changed["request_hash"] = "0" * 64
    elif location == "inner_request":
        changed["evidence"]["request"]["seed"] = 43
    elif location == "inner_scope":
        changed["evidence"]["scope"] = "independent-production"
    elif location == "evidence":
        changed["evidence"]["verdict"] = "PASS"
    else:
        changed["signature"]["signature"] = "A" * 88
    with pytest.raises(ValueError):
        verify_result(changed, request())
    with pytest.raises(ValueError, match="different request"):
        verify_result(output, request(43))


def test_rejects_duplicates_oversize_links_and_boolean_version(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"a":1,"a":2}')
    with pytest.raises(ValueError, match="duplicate"):
        read_document(path)
    path.write_text('{"a":"' + "a" * 100 + '"}')
    with pytest.raises(ValueError, match="bounded"):
        read_document(path, max_bytes=20)
    link = tmp_path / "link.json"
    link.symlink_to(path)
    with pytest.raises(ValueError, match="symbolic"):
        read_document(link)
    result = result_envelope(request(), {}, Ed25519PrivateKey.generate())
    result["schema_version"] = True
    with pytest.raises(ValueError, match="unsupported"):
        verify_result(result, request())


def test_result_is_portable_json(tmp_path: Path) -> None:
    result = result_envelope(request(), {"measurements": {"time_ns": 17}}, Ed25519PrivateKey.generate())
    path = tmp_path / "result.json"
    path.write_bytes(canonical(result))
    assert read_document(path) == result
