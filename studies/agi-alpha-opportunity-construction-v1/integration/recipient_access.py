# SPDX-License-Identifier: Apache-2.0
"""Authenticate a public instrument receipt against a local agent-namespace fixture.

The namespace/key mapping is supplied out of band as a simulated local role.
No live ENS, network distribution, production admission, or validator change occurs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from query_authority import HERE, MODE, NATIVE_MANIFEST_SHA256, native_modules, read_json

RECIPIENT = "successor.agent.agi.eth"
DOMAIN = "reserve-instrument-receipt-v1"


def record_access(artifact: Path, descriptor: Path, output: Path) -> dict[str, Any]:
    """Verify exact public bytes and a recipient signature; export no private key."""
    for supplied in (artifact, descriptor):
        if not supplied.is_file() or supplied.is_symlink() or not supplied.resolve().is_relative_to(HERE.parent):
            raise ValueError("Instrument and descriptor must be ordinary public files within this study")
    artifact, descriptor = artifact.resolve(), descriptor.resolve()
    rights, descriptor_hash = read_json(descriptor)
    artifact_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if rights.get("schema") != "agialpha.research-capability.descriptor.v1":
        raise ValueError("Expected the study's explicit research capability descriptor")
    if rights.get("provenance", {}).get(artifact.relative_to(HERE.parent).as_posix()) != artifact_hash:
        raise ValueError("The rights descriptor does not bind these exact instrument bytes")
    if not rights.get("rights") or rights.get("authority") != [] or rights.get("live_ens_qualification") is not False:
        raise ValueError("The public research descriptor must retain its rights record and empty live authority")
    trust, _ = native_modules()
    key = Ed25519PrivateKey.generate()
    public_key = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    mapping = {"principal": RECIPIENT, "public_key": public_key, "roles": ["worker"], "provenance": "local-fixture"}
    registry = trust.TrustRegistry({RECIPIENT: trust.TrustAnchor(public_key, frozenset({"worker"}))})
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,62}\.agent\.agi\.eth", RECIPIENT):
        raise ValueError("Recipient is outside the bounded fixture agent namespace")
    payload = {
        "schema": "agialpha.reserve-instrument.receipt.v1",
        "recipient": RECIPIENT,
        "artifact_sha256": artifact_hash,
        "descriptor_sha256": descriptor_hash,
        "right": "receive-and-inspect-public-research-instrument-under-declared-rights",
        "mode": MODE,
        "mission_authority": "Not transferred; each query requires a separate current grant.",
    }
    signed = trust.sign_record(key, RECIPIENT, DOMAIN, payload)
    verified = registry.verify(signed, DOMAIN, "worker")
    if verified != payload:
        raise AssertionError("Recipient receipt changed during native verification")
    checks: list[dict[str, Any]] = []

    def refuse(name: str, operation: Callable[[], Any]) -> None:
        try:
            operation()
        except ValueError as error:
            checks.append({"name": name, "passed": True, "reason": str(error)})
        else:
            checks.append({"name": name, "passed": False, "reason": "Unexpected acceptance"})

    changed_name = signed.model_dump(mode="json")
    changed_name["principal"] = "untrusted.agent.agi.eth"
    refuse(
        "Another namespace label has no installed local trust anchor",
        lambda: registry.verify(trust.SignedEnvelope.model_validate(changed_name), DOMAIN, "worker"),
    )
    changed_artifact = signed.model_dump(mode="json")
    changed_artifact["payload"]["artifact_sha256"] = "0" * 64 if artifact_hash != "0" * 64 else "1" * 64
    refuse(
        "Changing the instrument invalidates the signed receipt",
        lambda: registry.verify(trust.SignedEnvelope.model_validate(changed_artifact), DOMAIN, "worker"),
    )
    other_key = Ed25519PrivateKey.generate()
    forged = trust.sign_record(other_key, RECIPIENT, DOMAIN, payload)
    refuse(
        "A self-supplied key cannot replace the configured recipient key",
        lambda: registry.verify(forged, DOMAIN, "worker"),
    )
    refuse(
        "Worker identity does not confer the existing validator role",
        lambda: registry.verify(signed, DOMAIN, "validator"),
    )
    registry.revoke(RECIPIENT)
    refuse("Revoked recipient is refused on the next check", lambda: registry.verify(signed, DOMAIN, "worker"))
    result = {
        "schema": "agialpha.reserve-instrument.local-access-evidence.v1",
        "status": "passed" if all(item["passed"] for item in checks) else "failed",
        "mode": MODE,
        "fixture_namespace_mapping": mapping,
        "native_source_manifest_sha256": NATIVE_MANIFEST_SHA256,
        "artifact": {"filename": artifact.name, "sha256": artifact_hash, "bytes": artifact.stat().st_size},
        "descriptor": {"filename": descriptor.name, "sha256": descriptor_hash, "schema": rights.get("schema")},
        "signed_recipient_receipt": signed.model_dump(mode="json"),
        "checks": checks,
        "live_ens_checks": 0,
        "network_publications": 0,
        "provider_calls": 0,
        "private_keys_exported": False,
        "mission_authority_transferred": False,
        "independent_execution_demonstrated_by_this_receipt": False,
        "qualification": "The public instrument is locally available by exact bytes and attributed rights. The simulated namespace/key mapping authenticates this local receipt, not ENS ownership or production admission.",
        "rights_boundary": "The descriptor supplies provenance, licenses, dependencies and permitted reuse. This signature authenticates its exact identity; it is not an independent legal rights review.",
        "execution_boundary": "Fresh work and ordinary-library parity are measured by the study driver. Merely receiving or acknowledging the same bytes is not additional retained Alpha.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if result["status"] != "passed":
        raise AssertionError("A local recipient-access control failed; its evidence was preserved")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("artifact", "descriptor", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    arguments = parser.parse_args()
    result = record_access(arguments.artifact, arguments.descriptor, arguments.output)
    print(
        json.dumps(
            {"status": result["status"], "recipient": RECIPIENT, "live_ens_checks": 0, "network_publications": 0}
        )
    )
