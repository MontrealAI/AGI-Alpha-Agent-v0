# SPDX-License-Identifier: Apache-2.0
"""Authenticate local assessment of public E1 v2 code with the native trust API.

This study adapter adds research-envelope checks, not a native permission or
admission API. It never executes the instrument, resolves ENS, contacts a network,
persists a private key, or installs trust in any running service. The ordinary
library control receives exactly the same public source bytes.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = ROOT.parents[1]
sys.path.insert(0, str(REPOSITORY))

from alpha_factory_v1.core.runtime.successor.protocol import canonical, safe_json_loads
from alpha_factory_v1.core.runtime.successor.trust import (
    SignedEnvelope,
    TrustRegistry,
    sign_record,
    validate_external_trust_bytes,
)

DOMAIN = "ti-library-review"
ISSUER = "e1-author-fixture.agent.agi.eth"
RECIPIENT = "e1-assessor-fixture.agent.agi.eth"
MISSION = "e1-v2-public-code-assessment-20261027"
CODE_FILES = {"src/e1_instrument_v2.py", "src/e1_verify_v2.py"}
NATIVE_FILES = {
    "alpha_factory_v1/core/runtime/successor/trust.py",
    "alpha_factory_v1/core/runtime/successor/protocol.py",
    "alpha_factory_v1/core/runtime/successor/signatures.py",
}
ACTION = "local-code-assessment"
GRANT_FIELDS = {
    "schema",
    "issuer",
    "recipient",
    "manifest_sha256",
    "code",
    "rights_sha256",
    "mission",
    "not_before_utc",
    "expires_at_utc",
    "action",
    "fixture_only",
    "execution_authorized",
    "network_admission",
    "live_ens",
}
REQUEST_FIELDS = {"schema", "recipient", "grant_sha256", "manifest_sha256", "mission", "action"}
Json = dict[str, Any]


def sha256(data: bytes) -> str:
    """Hash exactly the supplied bytes."""
    return hashlib.sha256(data).hexdigest()


def read_study_file(relative: str) -> bytes:
    """Read a regular study file without accepting escaping paths or symlinks."""
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(p in {".", ".."} for p in path.parts):
        raise ValueError("research file path escapes the study")
    target = ROOT.joinpath(*path.parts)
    if any(part.is_symlink() for part in [target, *target.parents] if part != ROOT.parent):
        raise ValueError("research files cannot use symlinks")
    if not target.resolve().is_relative_to(ROOT) or not target.is_file():
        raise ValueError("research file is missing or outside the study")
    return target.read_bytes()


def checked_code(manifest: Json) -> dict[str, bytes]:
    """Return only the two reviewed public v2 modules after hash verification."""
    if not isinstance(manifest.get("code"), dict) or set(manifest["code"]) != CODE_FILES:
        raise ValueError("manifest does not contain exactly the reviewed v2 public modules")
    result = {}
    for relative, expected in manifest["code"].items():
        data = read_study_file(relative)
        if sha256(data) != expected:
            raise ValueError("public code differs from its reviewed hash")
        if not data.startswith(b"# SPDX-License-Identifier: Apache-2.0\n"):
            raise ValueError("reviewed code license declaration is missing")
        result[relative] = data
    return result


def load_manifest(path: Path, expected_sha256: str) -> tuple[Json, str]:
    """Require an externally supplied exact manifest hash and its narrow scope."""
    if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256):
        raise ValueError("an exact reviewed manifest hash is required")
    data = read_study_file(path.absolute().relative_to(ROOT).as_posix())
    if sha256(data) != expected_sha256:
        raise ValueError("manifest differs from the separately supplied review pin")
    manifest = safe_json_loads(data)
    if not isinstance(manifest, dict) or manifest.get("schema") != "agi-alpha.research-instrument-manifest.v2":
        raise ValueError("unsupported research manifest")
    if manifest.get("version") != "2.0.0" or manifest.get("fixture_only") is not True:
        raise ValueError("only the local v2 research fixture is supported")
    if manifest.get("economic_admission") != "HOLD" or manifest.get("network_admission") is not False:
        raise ValueError("research assessment cannot admit a retained or network skill")
    rights = manifest.get("rights", {})
    required_rights = {
        "code_license": "Apache-2.0",
        "content_scope": "public-source-code-only",
        "included_data": "none",
        "customer_data_included": False,
        "secrets_included": False,
        "restricted_evaluation_answers_included": False,
        "allowed_fixture_action": ACTION,
    }
    if rights != required_rights:
        raise ValueError("manifest rights exceed the public-code assessment fixture")
    expected_native = {p: sha256((REPOSITORY / p).read_bytes()) for p in sorted(NATIVE_FILES)}
    if manifest.get("native_source_pins") != expected_native:
        raise ValueError("native trust source differs from its reviewed manifest pin")
    if manifest.get("license") != {
        "repository_path": "LICENSE",
        "sha256": sha256((REPOSITORY / "LICENSE").read_bytes()),
    }:
        raise ValueError("public source license differs from its reviewed manifest pin")
    checked_code(manifest)
    return manifest, expected_sha256


def utc(value: str) -> datetime:
    """Parse an explicitly UTC timestamp without local-time inference."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("research fixture timestamps must be UTC")
    return parsed


def authenticate_assessment(
    registry: TrustRegistry,
    grant: SignedEnvelope,
    request: SignedEnvelope,
    manifest_path: Path,
    manifest_hash: str,
    now: datetime,
) -> dict[str, bytes]:
    """Use native verifier signatures, then enforce the adapter's access bindings.

    TrustRegistry authenticates the signatures and exact verifier role. This
    adapter, not TrustRegistry, checks mission, recipient, expiry, rights and
    content scope. Returning public bytes confers no execution authority.
    """
    manifest, _ = load_manifest(manifest_path, manifest_hash)
    g = registry.verify(grant, DOMAIN, "verifier")
    r = registry.verify(request, DOMAIN, "verifier")
    if set(g) != GRANT_FIELDS or set(r) != REQUEST_FIELDS:
        raise ValueError("research envelope has missing or extra fields")
    if grant.principal != ISSUER or g["issuer"] != ISSUER:
        raise ValueError("research issuer is not the pinned fixture principal")
    if request.principal != RECIPIENT or g["recipient"] != RECIPIENT or r["recipient"] != RECIPIENT:
        raise ValueError("recipient proof does not match the pinned fixture assessor")
    if any(not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,62}\.agent\.agi\.eth", p) for p in [ISSUER, RECIPIENT]):
        raise ValueError("only explicit local agent.agi.eth fixture identities are supported")
    if g["schema"] != "agi-alpha.local-research-access.v1" or r["schema"] != "agi-alpha.local-research-request.v1":
        raise ValueError("unsupported research envelope schema")
    if g["mission"] != MISSION or r["mission"] != MISSION or g["action"] != ACTION or r["action"] != ACTION:
        raise ValueError("research mission or action binding mismatch")
    if g["manifest_sha256"] != manifest_hash or r["manifest_sha256"] != manifest_hash:
        raise ValueError("research manifest binding mismatch")
    if g["code"] != manifest["code"] or g["rights_sha256"] != sha256(canonical(manifest["rights"])):
        raise ValueError("research code or rights binding mismatch")
    if r["grant_sha256"] != sha256(canonical(grant.model_dump(mode="json"))):
        raise ValueError("recipient request names a different signed grant")
    if g["fixture_only"] is not True or any(
        g[field] is not False for field in ["execution_authorized", "network_admission", "live_ens"]
    ):
        raise ValueError("research access cannot confer execution, admission or live identity")
    start, end = utc(g["not_before_utc"]), utc(g["expires_at_utc"])
    if now.tzinfo is None or now.utcoffset() != timedelta(0) or not start <= now < end:
        raise ValueError("research grant is expired or not yet valid")
    if end - start > timedelta(hours=1):
        raise ValueError("fixture lifetime exceeds one hour")
    return checked_code(manifest)


def write_json(path: Path, value: Json) -> None:
    """Write a new public fixture result; no private signing material is accepted."""
    with path.open("x", encoding="utf-8") as output:
        output.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def run(manifest_path: Path, manifest_pin: str, output: Path) -> Json:
    """Run the local authenticated handoff and targeted refusal fixtures."""
    manifest, manifest_hash = load_manifest(manifest_path, manifest_pin)
    output = output.absolute()
    if (
        not output.resolve().is_relative_to(ROOT)
        or output.exists()
        or any(p.is_symlink() for p in [output, *output.parents])
    ):
        raise ValueError("fixture output must be a new directory inside the study")
    keys = {principal: Ed25519PrivateKey.generate() for principal in [ISSUER, RECIPIENT]}
    public_trust = {
        "schema_version": 1,
        "principals": {
            principal: {
                "public_key": key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(),
                "roles": ["verifier"],
                "provenance": "local",
                "independence_attestation": "",
            }
            for principal, key in keys.items()
        },
    }

    def fresh_registry() -> TrustRegistry:
        return validate_external_trust_bytes(canonical(public_trust))

    registry = fresh_registry()
    now = datetime.now(timezone.utc)
    payload = {
        "schema": "agi-alpha.local-research-access.v1",
        "issuer": ISSUER,
        "recipient": RECIPIENT,
        "manifest_sha256": manifest_hash,
        "code": manifest["code"],
        "rights_sha256": sha256(canonical(manifest["rights"])),
        "mission": MISSION,
        "not_before_utc": (now - timedelta(minutes=1)).isoformat(),
        "expires_at_utc": (now + timedelta(minutes=15)).isoformat(),
        "action": ACTION,
        "fixture_only": True,
        "execution_authorized": False,
        "network_admission": False,
        "live_ens": False,
    }

    def pair(changes: Json | None = None) -> tuple[SignedEnvelope, SignedEnvelope]:
        grant = sign_record(keys[ISSUER], ISSUER, DOMAIN, {**payload, **(changes or {})})
        request = sign_record(
            keys[RECIPIENT],
            RECIPIENT,
            DOMAIN,
            {
                "schema": "agi-alpha.local-research-request.v1",
                "recipient": RECIPIENT,
                "grant_sha256": sha256(canonical(grant.model_dump(mode="json"))),
                "manifest_sha256": manifest_hash,
                "mission": MISSION,
                "action": ACTION,
            },
        )
        return grant, request

    grant, request = pair()

    def assess(g: SignedEnvelope = grant, r: SignedEnvelope = request, trust: TrustRegistry = registry) -> Any:
        return authenticate_assessment(trust, g, r, manifest_path, manifest_hash, now)

    authenticated_bytes = assess()
    checks: list[Json] = [{"name": "native_verifier_signatures_and_all_research_bindings", "passed": True}]

    def refuses(name: str, action: Callable[[], Any]) -> None:
        try:
            action()
        except ValueError as exc:
            checks.append({"name": name, "passed": True, "outcome": str(exc)})
        else:
            checks.append({"name": name, "passed": False, "outcome": "unexpectedly accepted"})

    refuses(
        "payload_tampering", lambda: assess(grant.model_copy(update={"payload": {**payload, "mission": "changed"}}))
    )
    for name, changes in [
        ("signed_wrong_mission", {"mission": "other-research-mission"}),
        ("signed_wrong_rights", {"rights_sha256": "0" * 64}),
        ("signed_wrong_manifest", {"manifest_sha256": "0" * 64}),
        ("signed_wrong_code", {"code": {p: "0" * 64 for p in CODE_FILES}}),
        ("signed_wrong_recipient", {"recipient": "other.agent.agi.eth"}),
        ("signed_expired_grant", {"expires_at_utc": now.isoformat()}),
        ("signed_future_grant", {"not_before_utc": (now + timedelta(minutes=1)).isoformat()}),
        ("signed_excessive_lifetime", {"expires_at_utc": (now + timedelta(days=1)).isoformat()}),
        ("execution_request", {"execution_authorized": True}),
        ("network_admission_request", {"network_admission": True}),
        ("live_ens_claim", {"live_ens": True}),
        ("role_expansion_in_payload", {"roles": ["controller"]}),
    ]:
        changed_grant, changed_request = pair(changes)
        refuses(name, lambda g=changed_grant, r=changed_request: assess(g, r))
    refuses("controller_role_not_regranted", lambda: registry.verify(grant, DOMAIN, "controller"))
    refuses("wrong_signature_domain", lambda: registry.verify(grant, "ti-library-control", "verifier"))
    refuses("fresh_recipient_has_no_trust", lambda: assess(trust=TrustRegistry({})))
    stranger = Ed25519PrivateKey.generate()
    unknown = sign_record(stranger, "unknown-fixture.agent.agi.eth", DOMAIN, request.payload)
    refuses("uninstalled_recipient_signer", lambda: assess(r=unknown))
    wrong_key = sign_record(stranger, RECIPIENT, DOMAIN, request.payload)
    refuses("wrong_key_for_installed_name", lambda: assess(r=wrong_key))
    other_request = sign_record(keys[RECIPIENT], RECIPIENT, DOMAIN, {**request.payload, "grant_sha256": "0" * 64})
    refuses("request_replayed_against_other_grant", lambda: assess(r=other_request))
    bad_trust = copy.deepcopy(public_trust)
    bad_trust["principals"][RECIPIENT]["roles"] = ["research-reader"]
    refuses("unsupported_native_role_refused", lambda: validate_external_trust_bytes(canonical(bad_trust)))
    for principal in [ISSUER, RECIPIENT]:
        revoked = fresh_registry()
        revoked.revoke(principal)
        refuses("revocation_" + principal, lambda trust=revoked: assess(trust=trust))
    refuses("changed_manifest_review_pin", lambda: load_manifest(manifest_path, "0" * 64))
    bad_code = {**manifest, "code": {p: "0" * 64 for p in CODE_FILES}}
    refuses("code_hash_mismatch", lambda: checked_code(bad_code))
    bad_path = {**manifest, "code": {"../../private": "0" * 64}}
    refuses("unreviewed_code_path", lambda: checked_code(bad_path))

    if not all(check["passed"] for check in checks):
        raise RuntimeError("research access fixture failed; no artifact handoff was written")
    output.mkdir(parents=True, exist_ok=False)
    comparisons = []
    for relative, authenticated in authenticated_bytes.items():
        ordinary = read_study_file(relative)
        if ordinary != authenticated:
            raise ValueError("ordinary-library code changed after authenticated assessment")
        for recipient_dir, data in [("authenticated_recipient", authenticated), ("ordinary_library", ordinary)]:
            target = output / recipient_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        comparisons.append(
            {
                "path": relative,
                "authenticated_sha256": sha256(authenticated),
                "ordinary_library_sha256": sha256(ordinary),
                "byte_identical": authenticated == ordinary,
            }
        )
    for recipient_dir in ["authenticated_recipient", "ordinary_library"]:
        (output / recipient_dir / "LICENSE").write_bytes((REPOSITORY / "LICENSE").read_bytes())
    checks.append(
        {"name": "ordinary_library_identical_public_code", "passed": all(x["byte_identical"] for x in comparisons)}
    )
    result = {
        "schema": "agi-alpha.local-research-access-results.v2",
        "created_at_utc": now.isoformat(),
        "manifest_path": manifest_path.resolve().relative_to(ROOT).as_posix(),
        "manifest_sha256": manifest_hash,
        "adapter_sha256": sha256(Path(__file__).read_bytes()),
        "native_api": ["validate_external_trust_bytes", "TrustRegistry.verify", "TrustRegistry.revoke", "sign_record"],
        "native_domain": DOMAIN,
        "native_role": "verifier",
        "native_source_pins": manifest["native_source_pins"],
        "local_public_trust_fixture": public_trust,
        "grant": grant.model_dump(mode="json"),
        "recipient_request": request.model_dump(mode="json"),
        "code_control": comparisons,
        "checks": checks,
        "passed": all(check["passed"] for check in checks),
        "boundary": {
            "ephemeral_private_keys_persisted": False,
            "independent_external_attestation": False,
            "live_ens_resolved": False,
            "network_used": False,
            "instrument_executed_by_fixture": False,
            "canonical_roles_or_code_changed": False,
            "trust_installed_in_running_service": False,
            "network_skill_admitted": False,
            "economic_retention": "HOLD",
            "actual_customer_data_shared": False,
            "actual_funds_or_receipts": False,
        },
        "limitations": [
            "Keys and agent.agi.eth names are generated local fixtures, not verified live ENS identities.",
            "The native registry verifies signatures and roles; this study adapter supplies mission, rights, hash and expiry checks.",
            "Authentication proves fixture provenance of public bytes, not source truth, code safety, delivery validity or value.",
            "Public Apache-2.0 code remains available to the ordinary library control; no exclusive-rights claim is made.",
            "No execution permission, production admission, validator role expansion, operational gain or profitable retention follows.",
            "Fresh runs generate new ephemeral keys and signatures. Semantic outcomes should match; signature bytes will differ.",
        ],
    }
    write_json(output / "RESULTS.json", result)
    return {"passed": result["passed"], "checks": len(checks), "output": str(output / "RESULTS.json")}


def main() -> None:
    """Accept an explicit review pin and write a new bounded fixture directory."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.manifest, args.manifest_sha256, args.output), sort_keys=True))


if __name__ == "__main__":
    main()
