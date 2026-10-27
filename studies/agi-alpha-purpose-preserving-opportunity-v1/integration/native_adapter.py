# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from eth_account import Account
from eth_account.messages import encode_defunct
from pydantic import Field, ValidationError

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.flywheel_access import (
    AccessRequest,
    ENSAuthority,
    ResourceAccess,
    ServiceIdentity,
)
from alpha_factory_v1.core.runtime.successor.flywheel_capsules import CapsuleManifest
from alpha_factory_v1.core.runtime.successor.flywheel_costs import CATEGORIES, Charge, CostLedger
from alpha_factory_v1.core.runtime.successor.protocol import Digest, StrictModel, canonical, digest
from alpha_factory_v1.core.runtime.successor.trust import (
    JournalCheckpoint,
    SignedEnvelope,
    TrustAnchor,
    TrustRegistry,
    sign_record,
)

FIXTURE_SCOPE = "local-source-inspection/v1"
ACCEPTANCE_DOMAIN = "ecological-source-acceptance"
ACCOUNTING_PRINCIPAL = "fixture-accounting"
ACCEPTANCE_PRINCIPAL = "fixture-acceptance"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def must_reject(operation: Callable[[], Any], check_id: str) -> dict[str, Any]:
    try:
        operation()
    except (ValueError, Conflict, ValidationError) as error:
        return {"id": check_id, "passed": True, "result": "denied", "exception": type(error).__name__}
    raise AssertionError(f"Expected native denial: {check_id}")


class FixtureENSAuthority(ENSAuthority):
    def __init__(self, trust: TrustRegistry, wallets: dict[str, str]) -> None:
        self.trust = trust
        self.wallets = dict(wallets)

    def verify(self, name: str, wallet: str, *, now: int | None = None) -> dict[str, Any]:
        anchor = self.trust.anchor(name, "worker")
        if self.wallets.get(name) != wallet.lower():
            raise ValueError("local fixture name and wallet do not match")
        return {
            "evidence_basis": "local-fixture-association-not-ens",
            "live_ens_checked": False,
            "name": name,
            "wallet": wallet,
            "configured_local_principal_public_key": anchor.public_key,
            "authority_scope": FIXTURE_SCOPE,
        }


class SourceAcceptance(StrictModel):
    artifact_sha256: Digest
    mission_digest: Digest
    delivered_bytes_sha256: Digest
    scope: str = Field(max_length=80)
    check: str = Field(max_length=80)
    accepted: bool


def validate_acceptance(
    trust: TrustRegistry, signed: SignedEnvelope, artifact_digest: str, mission_digest: str
) -> dict[str, Any]:
    value = SourceAcceptance.model_validate(trust.verify(signed, ACCEPTANCE_DOMAIN, "acceptance"))
    if (
        value.artifact_sha256 != artifact_digest
        or value.delivered_bytes_sha256 != artifact_digest
        or value.mission_digest != mission_digest
        or value.scope != FIXTURE_SCOPE
        or value.check != "exact-byte-identity"
        or value.accepted is not True
    ):
        raise ValueError("fixture acceptance is not current for these exact source bytes and mission")
    return value.model_dump()


def source_inventory() -> list[dict[str, Any]]:
    paths = set()
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if name.startswith("alpha_factory_v1") and isinstance(filename, str):
            paths.add(Path(filename).resolve())
    return [
        {"path": path.relative_to(REPO).as_posix(), "bytes": path.stat().st_size, "sha256": sha256(path.read_bytes())}
        for path in sorted(paths)
        if path.is_relative_to(REPO) and path.suffix == ".py"
    ]


def public_journal(journal: Journal) -> list[dict[str, Any]]:
    with sqlite3.connect(journal.path) as connection:
        rows = connection.execute("SELECT body,hash,signature FROM events ORDER BY seq").fetchall()
    return [{"body": json.loads(body), "hash": hashed, "signature": signature} for body, hashed, signature in rows]


def make_principals() -> tuple[TrustRegistry, dict[str, Ed25519PrivateKey]]:
    roles = {
        "fixture-origin.agent.agi.eth": {"worker"},
        "fixture-successor.agent.agi.eth": {"worker"},
        ACCEPTANCE_PRINCIPAL: {"acceptance"},
        ACCOUNTING_PRINCIPAL: {"accounting"},
    }
    keys = {principal: Ed25519PrivateKey.generate() for principal in roles}
    anchors = {
        principal: TrustAnchor(
            key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset(roles[principal])
        )
        for principal, key in keys.items()
    }
    return TrustRegistry(anchors), keys


def apply_cost(
    ledger: CostLedger,
    keys: dict[str, Ed25519PrivateKey],
    operation_id: str,
    action: str,
    record: Any,
) -> dict[str, Any]:
    return ledger.apply(
        sign_record(
            keys[ACCOUNTING_PRINCIPAL],
            ACCOUNTING_PRINCIPAL,
            "flywheel-cost-command",
            {
                "journal_identity": ledger.journal.identity,
                "operation_id": operation_id,
                "action": action,
                "record": record,
            },
        )
    )


def accounting_fixtures(root: Path, trust: TrustRegistry, keys: dict[str, Ed25519PrivateKey]) -> dict[str, Any]:
    checks = []
    actual_journal = Journal.initialize(root / "actual-incomplete")
    actual = CostLedger(actual_journal, trust)
    for category in sorted(CATEGORIES):
        charge = Charge.model_validate(
            {
                "activity_id": f"actual-research-{category}",
                "mission_id": "actual-research-session",
                "bucket": "C",
                "category": category,
                "accrued_micro_usd": None,
                "paid_micro_usd": 0,
                "basis": "unknown",
                "evidence_digest": digest(
                    "actual-unknown-cost", {"category": category, "scope": "this-research-session"}
                ),
                "note": "Complete attributable session expense unavailable; no new cash purchase recorded by this adapter.",
            }
        )
        apply_cost(actual, keys, f"actual-charge-{category}", "charge", charge.model_dump())
    actual_report = actual.report()
    assert actual_report["collected_revenue"] == 0
    assert actual_report["complete_cost_profit"] is None
    assert actual_report["available_funds"] is None
    assert actual_report["obligations"] is None
    assert actual_report["unknown_costs"] is True
    checks.append({"id": "actual-unknown-cost-is-not-zero", "passed": True})
    checks.append({"id": "actual-collections-remain-zero", "passed": True})
    checks.append(
        must_reject(
            lambda: apply_cost(
                actual,
                keys,
                "deny-incomplete-seal",
                "seal-investment",
                {
                    "mission_id": "actual-research-session",
                    "evidence_digest": digest("unknown-seal", {}),
                    "categories": sorted(CATEGORIES),
                },
            ),
            "unknown-expense-cannot-be-completeness-sealed",
        )
    )
    modeled_journal = Journal.initialize(root / "assumed-ledger-fixture")
    modeled = CostLedger(modeled_journal, trust)
    categories = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]
    values = {
        "A": [800000, 200000, 100000, 50000, 50000, 25000000, 5000000, 4000000, 4800000],
        "B": [500000, 200000, 200000, 100000, 0, 2000000, 4000000, 0, 3000000],
        "C": [10000000, 2000000, 1000000, 1000000, 0, 60000000, 10000000, 6000000, 10000000],
    }
    apply_cost(
        modeled,
        keys,
        "assumed-capital-operation",
        "capital",
        {
            "record_id": "assumed-capital",
            "mission_id": "assumed-accounting-fixture",
            "amount_micro_usd": 200000000,
            "evidence_digest": digest("assumed-not-bank-evidence", {"capital": 200000000}),
        },
    )
    first_charge = None
    for bucket, amounts in values.items():
        for category, amount in zip(categories, amounts, strict=True):
            charge = Charge.model_validate(
                {
                    "activity_id": f"assumed-{bucket}-{category}",
                    "mission_id": "assumed-accounting-fixture",
                    "bucket": bucket,
                    "category": category,
                    "accrued_micro_usd": amount,
                    "paid_micro_usd": 30000000 if bucket == "C" and category == "human" else amount,
                    "basis": "attested",
                    "evidence_digest": digest(
                        "assumed-line-item", {"bucket": bucket, "category": category, "amount": amount}
                    ),
                    "note": "Fully assumed arithmetic fixture, not market calibration or an observed invoice/payment.",
                }
            )
            apply_cost(modeled, keys, f"assumed-charge-{bucket}-{category}", "charge", charge.model_dump())
            if first_charge is None:
                first_charge = charge.model_dump()
    checks.append(
        must_reject(
            lambda: apply_cost(modeled, keys, "duplicate-activity-new-operation", "charge", first_charge),
            "duplicate-activity-denied-before-seal",
        )
    )
    for bucket, action in (("A", "seal"), ("B", "seal-retention"), ("C", "seal-investment")):
        apply_cost(
            modeled,
            keys,
            f"assumed-seal-{bucket}",
            action,
            {
                "mission_id": "assumed-accounting-fixture",
                "evidence_digest": digest("assumed-fixture-seal", {"bucket": bucket}),
                "categories": sorted(CATEGORIES),
            },
        )
    apply_cost(modeled, keys, "assumed-reserve-operation", "reserve", 25000000)
    modeled_report = modeled.report()
    assert modeled_report["costs"] == {"A": 40000000, "B": 10000000, "C": 100000000}
    assert modeled_report["collected_revenue"] == 0
    assert modeled_report["cash"] == 80000000
    assert modeled_report["obligations"] == 30000000
    assert modeled_report["reserve"] == 25000000
    assert modeled_report["available_funds"] == 25000000
    assert modeled_report["complete_cost_profit"] == -150000000
    assert modeled_report["bucket_complete"] == {"A": True, "B": True, "C": True}
    checks.append({"id": "disjoint-assumed-abc-and-cash-liability-reserve-identity", "passed": True})
    return {
        "checks": checks,
        "actual": {
            "evidence_basis": "incomplete-session-accounting",
            "note": "Unknown accruals are retained; empty collection ledger means no customer receipt is claimed.",
            "report": actual_report,
            "journal_verification": actual_journal.verify(),
            "events": public_journal(actual_journal),
        },
        "assumed": {
            "evidence_basis": "fully-assumed-accounting-test-fixture",
            "not_root_commercial_study": True,
            "bank_evidence": None,
            "actual_receipts_or_payments": False,
            "report": modeled_report,
            "journal_verification": modeled_journal.verify(),
            "events": public_journal(modeled_journal),
        },
    }


def run_fixture(artifact_path: Path) -> dict[str, Any]:
    raw = artifact_path.read_bytes()
    artifact_digest = sha256(raw)
    checks: list[dict[str, Any]] = []
    trust, keys = make_principals()
    workers = {name: Account.create() for name in ("fixture-origin.agent.agi.eth", "fixture-successor.agent.agi.eth")}
    wallets = {name: worker.address.lower() for name, worker in workers.items()}
    with tempfile.TemporaryDirectory(prefix="ecological-native-fixture-") as temporary:
        root = Path(temporary)
        journal = Journal.initialize(root / "lifecycle")
        authority = FixtureENSAuthority(trust, wallets)
        access = ResourceAccess(journal, ServiceIdentity(origin="https://ecological-fixture.invalid"), authority)
        missions = [
            {
                "schema": "ecological-inspection-fixture/v1",
                "recipient": "fixture-origin",
                "useful_purpose": "Inspect retained instrument for initial biodiversity procurement inquiry",
                "fixture_obligation": "exact immutable source byte delivery only",
                "artifact_sha256": artifact_digest,
            },
            {
                "schema": "ecological-inspection-fixture/v1",
                "recipient": "fixture-successor",
                "useful_purpose": "Inspect same instrument for a different restoration inquiry",
                "fixture_obligation": "exact immutable source byte delivery only",
                "artifact_sha256": artifact_digest,
            },
        ]
        mission_digests = [digest("ecological-fixture-mission", mission) for mission in missions]
        assert mission_digests[0] != mission_digests[1]

        def acceptance(mission_digest: str) -> SignedEnvelope:
            return sign_record(
                keys[ACCEPTANCE_PRINCIPAL],
                ACCEPTANCE_PRINCIPAL,
                ACCEPTANCE_DOMAIN,
                SourceAcceptance(
                    artifact_sha256=artifact_digest,
                    mission_digest=mission_digest,
                    delivered_bytes_sha256=sha256(raw),
                    scope=FIXTURE_SCOPE,
                    check="exact-byte-identity",
                    accepted=True,
                ),
            )

        def proof(name: str, action: str, mission_digest: str) -> AccessRequest:
            challenge = access.challenge(name, wallets[name], artifact_digest, action, mission_digest)
            signature = Account.sign_message(
                encode_defunct(text=challenge["message"]), workers[name].key
            ).signature.hex()
            return AccessRequest(challenge_id=challenge["challenge_id"], signature=signature)

        first_acceptance = acceptance(mission_digests[0])
        assert validate_acceptance(trust, first_acceptance, artifact_digest, mission_digests[0])["accepted"]
        wrong_scope = sign_record(
            keys[ACCEPTANCE_PRINCIPAL],
            ACCEPTANCE_PRINCIPAL,
            ACCEPTANCE_DOMAIN,
            {**first_acceptance.payload, "scope": "ecological-production/v1"},
        )
        checks.append(
            must_reject(
                lambda: validate_acceptance(trust, wrong_scope, artifact_digest, mission_digests[0]),
                "signed-acceptance-cannot-expand-scope",
            )
        )
        wrong_role = sign_record(
            keys["fixture-origin.agent.agi.eth"],
            "fixture-origin.agent.agi.eth",
            ACCEPTANCE_DOMAIN,
            first_acceptance.payload,
        )
        checks.append(
            must_reject(
                lambda: validate_acceptance(trust, wrong_role, artifact_digest, mission_digests[0]),
                "worker-signature-cannot-claim-acceptance-role",
            )
        )
        read_proof = proof("fixture-origin.agent.agi.eth", "retrieve", mission_digests[0])
        checks.append(
            must_reject(
                lambda: access.prepare(read_proof, artifact_digest, "invoke", mission_digests[0]),
                "retrieve-proof-cannot-authorize-invoke",
            )
        )
        checks.append(
            must_reject(
                lambda: access.prepare(read_proof, artifact_digest, "retrieve", mission_digests[1]),
                "read-proof-cannot-cross-mission",
            )
        )
        checks.append(
            must_reject(
                lambda: access.prepare(read_proof, sha256(raw + b"changed"), "retrieve", mission_digests[0]),
                "proof-cannot-cross-artifact-bytes",
            )
        )
        prepared = access.prepare(read_proof, artifact_digest, "retrieve", mission_digests[0])
        with journal.transaction() as cx:
            received_authority = access.consume(prepared, cx)
            journal.append(
                cx,
                "@ecological-fixture:origin",
                {
                    "mission": missions[0],
                    "mission_digest": mission_digests[0],
                    "artifact_sha256": artifact_digest,
                    "delivered_bytes": len(raw),
                    "acceptance": first_acceptance.model_dump(),
                    "authority": received_authority,
                    "production_admitted": False,
                },
            )
        checks.append({"id": "native-signed-read-consumed-atomically", "passed": True})
        checks.append(
            must_reject(
                lambda: access.prepare(read_proof, artifact_digest, "retrieve", mission_digests[0]),
                "consumed-proof-replay-denied",
            )
        )
        checks.append(
            must_reject(
                lambda: validate_acceptance(trust, first_acceptance, artifact_digest, mission_digests[1]),
                "old-acceptance-does-not-transfer-to-successor",
            )
        )
        with journal.transaction() as cx:
            child = journal.append(
                cx,
                "@ecological-fixture:successor",
                {
                    "mission": missions[1],
                    "mission_digest": mission_digests[1],
                    "artifact_sha256": artifact_digest,
                    "inherited_structure": True,
                    "current_acceptance": None,
                    "current_authority": [],
                    "historical_acceptance": first_acceptance.model_dump(),
                    "production_admitted": False,
                },
            )
        assert child["current_acceptance"] is None and child["current_authority"] == []
        checks.append({"id": "successor-retains-bytes-with-empty-current-acceptance-and-authority", "passed": True})
        second_acceptance = acceptance(mission_digests[1])
        second_receipt = validate_acceptance(trust, second_acceptance, artifact_digest, mission_digests[1])
        invocation = proof("fixture-successor.agent.agi.eth", "invoke", mission_digests[1])
        prepared = access.prepare(invocation, artifact_digest, "invoke", mission_digests[1])
        with journal.transaction() as cx:
            current_authority = access.consume(prepared, cx)
            current = journal.latest("@ecological-fixture:successor", cx)
            journal.append(
                cx,
                "@ecological-fixture:successor",
                {
                    **journal.document(current),
                    "current_acceptance": second_acceptance.model_dump(),
                    "current_acceptance_verified": second_receipt["accepted"],
                    "current_authority": [current_authority],
                    "invocation": {"kind": "source-byte-inspection", "bytes": len(raw), "sha256": sha256(raw)},
                },
            )
        checks.append({"id": "successor-fresh-acceptance-and-native-invoke-authority", "passed": True})
        stale_proof = proof("fixture-origin.agent.agi.eth", "invoke", mission_digests[0])
        trust.revoke("fixture-origin.agent.agi.eth")
        checks.append(
            must_reject(
                lambda: access.prepare(stale_proof, artifact_digest, "invoke", mission_digests[0]),
                "revoked-local-principal-denied-fresh-access",
            )
        )
        malformed_scope = {
            "skill_id": "ecological-instrument",
            "version": 1,
            "origin_mission": "ecological-origin",
            "origin_record_digest": digest("fixture-origin", missions[0]),
            "origin_agent": "fixture-successor.agent.agi.eth",
            "origin_wallet": wallets["fixture-successor.agent.agi.eth"],
            "content_digest": artifact_digest,
            "supported_scope": "ecological-procurement-gap/v1",
            "prerequisites": [],
            "limitations": "Research artifact; ecological production scope unsupported by native capsule grammar.",
            "rights": "cleared-for-authenticated-network",
            "rights_evidence": digest("fixture-rights", {"basis": "hypothetical"}),
            "dependency_digests": [],
        }
        CapsuleManifest.model_validate({**malformed_scope, "supported_scope": "bounded-public-source-selection/v1"})
        checks.append(
            must_reject(
                lambda: CapsuleManifest.model_validate(malformed_scope),
                "native-capsule-rejects-unsupported-ecological-scope",
            )
        )
        checkpoint = JournalCheckpoint.capture(journal)
        checkpoint.verify(journal)
        checks.append({"id": "native-journal-signatures-chain-and-checkpoint-verify", "passed": True})
        accounting = accounting_fixtures(root, trust, keys)
        checks.extend(accounting.pop("checks"))
        lifecycle_events = public_journal(journal)
        lifecycle_verification = journal.verify()
    inventory = source_inventory()
    try:
        source_commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except (subprocess.SubprocessError, OSError):
        source_commit = None
    return {
        "schema": "ecological-native-integration-report/v1",
        "evidence_basis": "executed-local-native-API-fixture-with-simulated-identity-association",
        "artifact": {"filename": artifact_path.name, "bytes": len(raw), "sha256": artifact_digest},
        "research_source_commit": source_commit,
        "python_version": platform.python_version(),
        "fixture_public_signing_keys": {
            principal: key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
            for principal, key in keys.items()
        },
        "runtime_dependencies": {
            name: importlib.metadata.version(name) for name in ("pydantic", "cryptography", "eth-account")
        },
        "adapter_sha256": sha256(Path(__file__).read_bytes()),
        "runtime_sources": inventory,
        "runtime_inventory_sha256": sha256(canonical(inventory)),
        "checks": checks,
        "checks_passed": sum(check["passed"] is True for check in checks),
        "checks_total": len(checks),
        "missions": [{"document": mission, "digest": hashed} for mission, hashed in zip(missions, mission_digests)],
        "lifecycle": {"journal_verification": lifecycle_verification, "events": lifecycle_events},
        "accounting": accounting,
        "limits": {
            "live_ens_authentication": False,
            "live_model_provider_calls": 0,
            "live_customer_collections_usd": 0,
            "scientific_production_admission": "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE",
            "protected_capsule_admitted": False,
            "jobs_validator_or_settlement_changes": False,
            "complete_actual_cost_known": False,
            "ecological_semantics_checked_by_this_adapter": False,
            "identity_association": "Fictional names and temporary local wallet/Ed25519 keys; no RPC used.",
            "exported_keys": "Public fixture evidence only; report import does not confer authority or trust.",
            "invocation_scope": "Bounded immutable-source-byte inspection; core study evaluates ecological outcomes.",
            "reproducibility": "Check decisions and source commitments repeat; fresh random keys/timestamps change receipts.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    report = run_fixture(arguments.artifact.resolve())
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "checks_passed": report["checks_passed"],
                "checks_total": report["checks_total"],
                "output": str(arguments.output),
            }
        )
    )


if __name__ == "__main__":
    main()
