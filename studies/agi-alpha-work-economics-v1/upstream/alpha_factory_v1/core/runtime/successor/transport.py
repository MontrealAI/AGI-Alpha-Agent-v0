# SPDX-License-Identifier: Apache-2.0
"""Request-bound evidence transport; integrity never creates verifier trust."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .protocol import RehearsalRequest, canonical, digest, safe_json_loads
from .signatures import verify_ed25519

MAX_RESULT_BYTES = 2_000_000
RESULT_SCOPE = "local-native-rehearsal"


def read_document(path: Path, *, max_bytes: int = MAX_RESULT_BYTES) -> dict[str, Any]:
    """Read one bounded regular JSON file without following a symbolic link."""
    import os
    import stat

    if path.is_symlink():
        raise ValueError("symbolic-link inputs are not permitted")
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > max_bytes:
            raise ValueError("input must be a bounded regular JSON file")
        raw = stream.read(max_bytes + 1)
    document = safe_json_loads(raw, max_bytes=max_bytes)
    if not isinstance(document, dict):
        raise ValueError("input must be a JSON object")  # noqa: TRY004
    return document


def request_from_file(path: Path) -> RehearsalRequest:
    """Validate the exact browser request before creating state or running work."""
    return RehearsalRequest.model_validate(read_document(path, max_bytes=16_384))


def result_envelope(request: RehearsalRequest, evidence: dict[str, Any], key: Ed25519PrivateKey) -> dict[str, Any]:
    """Bind the complete request and native scope inside the signed evidence."""
    request_hash = digest("request", request.model_dump())
    payload = {**evidence, "request": request.model_dump(), "request_hash": request_hash, "scope": RESULT_SCOPE}
    hashed = digest("evidence", payload)
    result = {
        "schema_version": 1,
        "kind": "successor-result",
        "request_hash": request_hash,
        "evidence": payload,
        "evidence_hash": hashed,
        "scope": RESULT_SCOPE,
        "signature": {
            "public_key": key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
            "signature": base64.b64encode(key.sign(bytes.fromhex(hashed))).decode("ascii"),
        },
    }
    if len(canonical(result)) > MAX_RESULT_BYTES:
        raise ValueError("result exceeds the bounded evidence transport limit")
    return result


def verify_result(document: dict[str, Any], request: RehearsalRequest, public_key: str | None = None) -> dict[str, Any]:
    """Verify a return; authenticate only against an independently supplied key."""
    fields = {"schema_version", "kind", "request_hash", "evidence", "evidence_hash", "scope", "signature"}
    # Exact builtin types reject bool/int substitution and arbitrary subclasses.
    if (
        set(document) != fields
        or (type(document["schema_version"]) is not int)  # noqa: E721
        or document["schema_version"] != 1
    ):
        raise ValueError("unsupported result envelope")
    if document["kind"] != "successor-result" or document["scope"] != RESULT_SCOPE:
        raise ValueError("result has the wrong native execution scope")
    hashed_request = digest("request", request.model_dump())
    if document["request_hash"] != hashed_request:
        raise ValueError("return belongs to a different request")
    evidence = document["evidence"]
    if not isinstance(evidence, dict):
        raise ValueError("evidence must be an object")  # noqa: TRY004
    if (
        evidence.get("request") != request.model_dump()
        or evidence.get("request_hash") != hashed_request
        or evidence.get("scope") != RESULT_SCOPE
    ):
        raise ValueError("signed evidence does not bind the complete request and scope")
    if digest("evidence", evidence) != document["evidence_hash"]:
        raise ValueError("evidence digest mismatch")
    signature = document["signature"]
    authenticated = False
    if signature is not None:
        if not isinstance(signature, dict) or set(signature) != {"public_key", "signature"}:
            raise ValueError("invalid result signature envelope")
        if not all(isinstance(value, str) for value in signature.values()):
            raise ValueError("invalid result signature encoding")
        try:
            verify_ed25519(
                bytes.fromhex(signature["public_key"]),
                base64.b64decode(signature["signature"], validate=True),
                bytes.fromhex(document["evidence_hash"]),
            )
        except (ValueError, InvalidSignature) as exc:
            raise ValueError("invalid result signature") from exc
        if public_key is not None:
            if signature["public_key"] != public_key:
                raise ValueError("result signer does not match the independently trusted key")
            authenticated = True
    elif public_key is not None:
        raise ValueError("trusted verification requires a signature")
    return {
        "request_hash": hashed_request,
        "evidence_hash": document["evidence_hash"],
        "integrity": "verified",
        "authentication": "trusted-local-signer" if authenticated else "untrusted-signer",
        "scope": RESULT_SCOPE,
        "performance_remeasured": False,
        "external_independence": False,
        "production_authority": False,
    }
