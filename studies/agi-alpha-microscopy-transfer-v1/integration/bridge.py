# SPDX-License-Identifier: Apache-2.0
"""Reuse the pinned research lifecycle and native accounting without production admission.

Adapted from capability-opportunity-v1 at research commit 231834269599d85e49cfe1ca9917a1a874522d44.
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parent


def verify_sources() -> dict[str, Any]:
    """Fail closed before importing a changed upstream implementation."""
    manifest = json.loads((ROOT / "source_manifest.json").read_text())
    for row in manifest["files"]:
        path = ROOT / row["local_path"]
        if path.is_symlink() or not path.is_file():
            raise ValueError("upstream source must be an ordinary file: " + row["local_path"])
        data = path.read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError("upstream source drift: " + row["local_path"])
    return cast(dict[str, Any], manifest)


def run_lifecycle(
    candidates: list[dict[str, Any]],
    operations: list[dict[str, Any]] | None = None,
    protected_material: list[Any] | None = None,
    beta_version: str = "microscopy-competent-expert-v1",
    execution_authorized: bool = False,
) -> dict[str, Any]:
    """Move actual artifact bytes through the existing fixture-only lifecycle."""
    verify_sources()
    rows = []
    for candidate in candidates:
        row = dict(candidate)
        path = Path(row.pop("artifact_path"))
        if path.is_symlink() or not path.is_file():
            raise ValueError("artifact must be an ordinary file")
        content = path.read_bytes()
        if len(content) > 2_000_000:
            raise ValueError("artifact exceeds two-megabyte research bridge bound")
        actual = hashlib.sha256(content).hexdigest()
        expected = row.pop("expected_artifact_sha256", None)
        if expected is not None and actual != expected:
            raise ValueError("frozen artifact digest mismatch")
        row["artifact_sha256"] = actual
        row["artifact_content"] = base64.b64encode(content).decode("ascii")
        row["content_encoding"] = "base64"
        rows.append(row)
    request = {
        "module_root": str(ROOT / "vendor" / "beyond_beta"),
        "candidates": rows,
        "operations": operations or [],
        "protected_material": protected_material or [],
        "beta_version": beta_version,
        "execution_authorized": execution_authorized,
    }
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js required for the pinned research lifecycle")
    result = subprocess.run(
        [node, str(ROOT / "replay.mjs")],
        input=json.dumps(request, allow_nan=False),
        text=True,
        capture_output=True,
        check=True,
        timeout=60,
    )
    return cast(dict[str, Any], json.loads(result.stdout))


def replay_native(commands: list[dict[str, Any]], controls: bool = False) -> dict[str, Any]:
    """Execute signed accounting commands and optional negative conformance checks."""
    verify_sources()
    sys.path.insert(0, str(ROOT / "vendor" / "runtime"))
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
    from pydantic import ValidationError
    from alpha_factory_v1.core.runtime.store import Journal
    from alpha_factory_v1.core.runtime.successor.flywheel_capsules import CapsuleManifest
    from alpha_factory_v1.core.runtime.successor.flywheel_costs import CostLedger
    from alpha_factory_v1.core.runtime.successor.protocol import digest
    from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

    native_root = (ROOT / "vendor" / "runtime").resolve()
    loaded = []
    for name, module in sorted(sys.modules.items()):
        if not name.startswith("alpha_factory_v1"):
            continue
        path = getattr(module, "__file__", None)
        if path and not Path(path).resolve().is_relative_to(native_root):
            raise ValueError("native import came from outside the pinned closure: " + name)
        if path:
            data = Path(path).read_bytes()
            loaded.append({"module": name, "sha256": hashlib.sha256(data).hexdigest()})

    with tempfile.TemporaryDirectory(prefix="microscopy-native-ledger-") as temporary:
        journal = Journal.initialize(Path(temporary) / "native")
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        trust = TrustRegistry({"study-accounting": TrustAnchor(public, frozenset({"accounting"}))})
        ledger = CostLedger(journal, trust)
        submitted: list[dict[str, Any]] = []
        reports: list[dict[str, Any]] = []
        checks: list[dict[str, Any]] = []

        def apply(command: dict[str, Any], identity: str | None = None) -> Any:
            payload = {
                "journal_identity": journal.identity,
                "operation_id": identity or f"study-command-{len(submitted)}",
                "action": command["action"],
                "record": command["record"],
            }
            signed = sign_record(key, "study-accounting", "flywheel-cost-command", payload)
            return ledger.apply(signed)

        for command in commands:
            apply(command)
            submitted.append(command)
            reports.append(ledger.report())
        if controls:
            if commands:
                before = journal.verify()["events"]
                apply(commands[0], "study-command-0")
                checks.append(
                    {"name": "identical-command-is-idempotent", "passed": journal.verify()["events"] == before}
                )
            charge = next((x for x in commands if x["action"] == "charge"), None)
            if charge is not None:
                altered = {"action": "charge", "record": {**charge["record"], "bucket": "C"}}
                try:
                    apply(altered, "duplicate-activity-control")
                    passed = False
                    reason = "accepted"
                except ValueError as exc:
                    passed, reason = True, str(exc)
                checks.append({"name": "duplicate-activity-across-buckets-refused", "passed": passed, "reason": reason})
            manifest = {
                "skill_id": "microscopy-measurement-instrument",
                "version": 1,
                "origin_mission": "originating-scientific-work",
                "origin_record_digest": digest("fixture-origin", {"synthetic": True}),
                "origin_agent": "atlas.agent.agi.eth",
                "origin_wallet": "0x" + "11" * 20,
                "content_digest": digest("fixture-artifact", {"synthetic": True}),
                "supported_scope": "bounded-public-source-selection/v1",
                "prerequisites": [],
                "limitations": "Conformance control only. No model, ENS, customer or production claim.",
                "rights": "cleared-for-authenticated-network",
                "rights_evidence": digest("fixture-rights", {"synthetic": True}),
                "dependency_digests": [],
            }
            CapsuleManifest.model_validate(manifest)
            try:
                CapsuleManifest.model_validate({**manifest, "supported_scope": "microscopy-moments/v1"})
                passed, reason = False, "accepted"
            except ValidationError as exc:
                passed = any(e["loc"] == ("supported_scope",) and e["type"] == "literal_error" for e in exc.errors())
                reason = "supported_scope literal rejects scientific component"
            checks.append({"name": "native-microscopy-capsule-refused", "passed": passed, "reason": reason})
            payload = {
                "journal_identity": journal.identity,
                "operation_id": "tampered-signature-control",
                "action": "reserve",
                "record": 0,
            }
            tampered = sign_record(key, "study-accounting", "flywheel-cost-command", payload)
            tampered.payload["record"] = 1
            event_count = journal.verify()["events"]
            try:
                ledger.apply(tampered)
                passed, reason = False, "accepted"
            except ValueError as exc:
                passed, reason = True, str(exc)
            checks.append(
                {
                    "name": "tampered-native-signed-record-refused",
                    "passed": passed and journal.verify()["events"] == event_count,
                    "reason": reason,
                }
            )
            wrong_journal = sign_record(
                key, "study-accounting", "flywheel-cost-command", {**payload, "journal_identity": "another-journal"}
            )
            try:
                ledger.apply(wrong_journal)
                passed, reason = False, "accepted"
            except ValueError as exc:
                passed, reason = True, str(exc)
            checks.append(
                {
                    "name": "signed-record-for-another-journal-refused",
                    "passed": passed and journal.verify()["events"] == event_count,
                    "reason": reason,
                }
            )
            trust.revoke("study-accounting")
            try:
                apply({"action": "reserve", "record": 0}, "revoked-accountant")
                passed, reason = False, "accepted"
            except ValueError as exc:
                passed, reason = True, str(exc)
            checks.append({"name": "revoked-accounting-authority-refused", "passed": passed, "reason": reason})
        verification = journal.verify()
        return {
            "schema": "capability-opportunity-native-replay/v1",
            "commands": submitted,
            "reports_after_each_command": reports,
            "report": ledger.report(),
            "controls": checks,
            "journal": {"valid": verification["valid"], "events": verification["events"]},
            "imported_modules": loaded,
            "actual_collections_micro_usd": 0,
            "production_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
            "authority": "REAL_LOCAL_ED25519_CHECKS_WITH_EPHEMERAL_FIXTURE_PRINCIPALS",
            "money_basis": "Caller-declared research assumptions; no bank or provider verification.",
            "jobs_validator_governance_settlement_changes": False,
        }
