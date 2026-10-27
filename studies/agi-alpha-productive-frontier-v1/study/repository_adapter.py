# SPDX-License-Identifier: Apache-2.0
"""Replay research attestations through unchanged native accounting and trust."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

STUDY_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = Path(__file__).resolve().parents[3]
MANIFEST = STUDY_ROOT / "evidence" / "native_source_manifest.json"
SOURCE_COMMIT = "80b345828f34fd8a6e592977dd17ef37141305f4"


def verify_native_sources(repository: Path = REPOSITORY, manifest_path: Path = MANIFEST) -> dict[str, Any]:
    """Refuse missing or changed runtime bytes before importing the reused code."""
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["repository_commit"] != SOURCE_COMMIT:
        raise ValueError("native source commit differs from the study freeze")
    for row in manifest["files"]:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("invalid native source path")
        path = repository / relative
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"native source is not a regular file: {relative}")
        data = path.read_bytes()
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise ValueError(f"native source drift: {relative}")
    return manifest


class NativeResearchLedger:
    """Use a temporary local accounting signer, never an ENS or customer identity."""

    def __init__(self, directory: Path) -> None:
        self.manifest = verify_native_sources()
        if str(REPOSITORY) not in sys.path:
            sys.path.insert(0, str(REPOSITORY))
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

        from alpha_factory_v1.core.runtime.store import Journal
        from alpha_factory_v1.core.runtime.successor.flywheel_costs import CostLedger
        from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry

        self.journal = Journal.initialize(directory)
        self.key = Ed25519PrivateKey.generate()
        public = self.key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        self.principal = "productive-frontier-local-accounting"
        self.trust = TrustRegistry({self.principal: TrustAnchor(public, frozenset({"accounting"}))})
        self.ledger = CostLedger(self.journal, self.trust)
        self.commands: list[dict[str, Any]] = []

    def signed(self, action: str, record: Any, operation_id: str | None = None) -> Any:
        """Bind the exact action and record to this local Journal."""
        from alpha_factory_v1.core.runtime.successor.trust import sign_record

        return sign_record(
            self.key,
            self.principal,
            "flywheel-cost-command",
            {
                "journal_identity": self.journal.identity,
                "operation_id": operation_id or f"research-command-{len(self.commands)}",
                "action": action,
                "record": record,
            },
        )

    def apply(self, action: str, record: Any, operation_id: str | None = None) -> dict[str, Any]:
        """Apply the native command with no custom balance or authority logic."""
        signed = self.signed(action, record, operation_id)
        result: dict[str, Any] = self.ledger.apply(signed)
        self.commands.append({"operation_id": signed.payload["operation_id"], "action": action, "record": record})
        return result

    def report(self) -> dict[str, Any]:
        """Export only public research evidence and the native calculated report."""
        verification = self.journal.verify()
        return {
            "schema": "productive-frontier-native-accounting/v1",
            "repository_commit": SOURCE_COMMIT,
            "report": self.ledger.report(),
            "journal_verification": {"valid": verification["valid"], "events": verification["events"]},
            "commands": self.commands,
            "authority": "LOCAL_EPHEMERAL_TEST_SIGNER; NOT_ENS_AUTHENTICATION",
            "amount_basis": "SUPPLIED_RESEARCH_ATTESTATIONS; NOT_PROVIDER_OR_BANK_VERIFICATION",
            "actual_customer_collections_micro_usd": 0,
            "production_capability_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
            "reused_source_files": self.manifest["files"],
        }


def evidence_digest(domain: str, value: Any) -> str:
    """Use the native domain-separated research commitment implementation."""
    verify_native_sources()
    if str(REPOSITORY) not in sys.path:
        sys.path.insert(0, str(REPOSITORY))
    from alpha_factory_v1.core.runtime.successor.protocol import digest

    result: str = digest(domain, value)
    return result


def replay_native_ledger(
    charges: Iterable[dict[str, Any]],
    *,
    collections: Iterable[dict[str, Any]] = (),
    capital_micro_usd: int = 0,
    reserve_micro_usd: int = 0,
    seal: bool = True,
    extra_commands: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Replay explicit A/B/C costs without filling missing categories or expenses."""
    with tempfile.TemporaryDirectory(prefix="productive-frontier-ledger-") as temporary:
        bridge = NativeResearchLedger(Path(temporary) / "journal")
        from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES

        if capital_micro_usd:
            bridge.apply(
                "capital",
                {
                    "record_id": "research-capital",
                    "mission_id": "enterprise",
                    "amount_micro_usd": capital_micro_usd,
                    "evidence_digest": evidence_digest("research-capital", {"amount": capital_micro_usd}),
                },
            )
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for value in charges:
            row = dict(value)
            row.setdefault("basis", "unknown" if row.get("accrued_micro_usd") is None else "attested")
            row.setdefault("note", "SIMULATED accounting amount; no customer or provider payment established")
            row.setdefault("evidence_digest", evidence_digest("research-charge", row))
            bridge.apply("charge", row)
            groups.setdefault((row["mission_id"], row["bucket"]), []).append(row)
        for value in collections:
            row = dict(value)
            row.setdefault("evidence_digest", evidence_digest("research-collection", row))
            bridge.apply("collection", row)
        for command in extra_commands:
            bridge.apply(command["action"], command["record"], command.get("operation_id"))
        if seal:
            for (mission, bucket), rows in groups.items():
                if {row["category"] for row in rows} != CATEGORIES:
                    continue
                if any(row["accrued_micro_usd"] is None for row in rows):
                    continue
                bridge.apply(
                    {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket],
                    {
                        "mission_id": mission,
                        "categories": sorted(CATEGORIES),
                        "evidence_digest": evidence_digest("research-seal", rows),
                    },
                )
        bridge.apply("reserve", reserve_micro_usd)
        return bridge.report()
