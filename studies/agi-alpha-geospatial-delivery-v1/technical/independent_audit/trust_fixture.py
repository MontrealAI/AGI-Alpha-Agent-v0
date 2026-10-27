# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT.parents[1]))
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record


def main() -> None:
    manifest_path = ROOT / "technical" / "capability_manifest.json"
    manifest_bytes = manifest_path.read_bytes()
    manifest_hash = hashlib.sha256(manifest_bytes).hexdigest()
    if manifest_hash != "4f46d46ee3b52ee95ca134cf5fbfa4021e689416d6f664c94c33e4b46718edb7":
        raise RuntimeError("Retained manifest differs from the reviewed freeze")
    manifest = json.loads(manifest_bytes)
    key = Ed25519PrivateKey.generate()
    stranger = Ed25519PrivateKey.generate()
    principal = "local-review-fixture.agent.agi.eth"
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
    registry = TrustRegistry({principal: TrustAnchor(public, frozenset({"verifier"}))})
    payload = {
        "scope": "synthetic local geospatial research fixture",
        "manifest_sha256": manifest_hash,
        "capability_id": manifest["capability_id"],
        "version": manifest["version"],
        "code": manifest["code"],
        "instrument_sha256": hashlib.sha256((ROOT / "src" / "geodelivery.py").read_bytes()).hexdigest(),
        "mission": "independent-audit-recipient-20261027",
        "execution_authorized": False,
        "live_ens": False,
    }
    envelope = sign_record(key, principal, "ti-library-review", payload)
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "manifest_code_hashes_match_retained_files",
            "passed": all(
                hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == h for p, h in manifest["code"].items()
            ),
        }
    )
    checks.append(
        {
            "name": "manifest_source_hashes_match_frozen_inputs",
            "passed": all(
                hashlib.sha256((ROOT / s["file"]).read_bytes()).hexdigest() == s["sha256"]
                for s in manifest["source_data"]
            ),
        }
    )
    checks.append(
        {
            "name": "manifest_evidence_references_resolve",
            "passed": all((ROOT / p).is_file() for p in manifest["evaluation"]),
        }
    )
    checks.append(
        {
            "name": "authorized_fixture_verifier_signature",
            "passed": registry.verify(envelope, "ti-library-review", "verifier") == payload,
        }
    )
    variants = [
        (
            "payload_tampering",
            registry,
            envelope.model_copy(update={"payload": {**payload, "mission": "changed"}}),
            "ti-library-review",
            "verifier",
        ),
        ("role_not_regranted", registry, envelope, "ti-library-review", "controller"),
        ("wrong_domain", registry, envelope, "ti-library-control", "verifier"),
        (
            "uninstalled_signer",
            registry,
            sign_record(stranger, "unknown.agent.agi.eth", "ti-library-review", payload),
            "ti-library-review",
            "verifier",
        ),
        ("fresh_recipient_no_trust", TrustRegistry({}), envelope, "ti-library-review", "verifier"),
    ]
    for name, trust, signed, domain, role in variants:
        try:
            trust.verify(signed, domain, role)
            checks.append({"name": name, "passed": False, "outcome": "unexpectedly accepted"})
        except ValueError as exc:
            checks.append({"name": name, "passed": True, "outcome": str(exc)})
    registry.revoke(principal)
    try:
        registry.verify(envelope, "ti-library-review", "verifier")
        checks.append({"name": "revocation", "passed": False})
    except ValueError as exc:
        checks.append({"name": "revocation", "passed": True, "outcome": str(exc)})
    result = {
        "scope": "Existing TrustRegistry and ti-library-review domain, local ephemeral fixture only",
        "principal": principal,
        "principal_is_live_ens": False,
        "independent_attestation": False,
        "execution_or_admission_granted": False,
        "private_key_persisted": False,
        "public_key": public,
        "envelope": envelope.model_dump(),
        "checks": checks,
        "passed": all(c["passed"] for c in checks),
        "limitations": "Signature validation authenticates local fixture bytes only. No geospatial capability admission, production policy change, live name resolution or deployment is implied. Different ephemeral keys produce different envelope bytes on replay; semantic test outcomes should match.",
    }
    path = Path(__file__).with_name("trust_fixture_results.json")
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"checks": len(checks), "passed": result["passed"], "output": str(path)}))


if __name__ == "__main__":
    main()
