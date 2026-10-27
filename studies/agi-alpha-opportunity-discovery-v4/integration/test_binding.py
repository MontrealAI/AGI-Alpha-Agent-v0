# SPDX-License-Identifier: Apache-2.0
"""Targeted integrity/authority tests; miniature code fixtures are not science outcomes."""

from __future__ import annotations

import copy
import importlib.metadata
import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path

from binding import (
    DOMAIN,
    MODE,
    bind_request,
    check_grant,
    dependency_inventory,
    digest,
    file_sha,
    grant_payload,
    inherited,
    native_trust,
    pack_bundle,
    safe_member,
    save,
    scan_payload,
    unpack_bundle,
    upstream_runner,
    verify_installed_bundle,
)
from recipient import consume_authority
from run_integration import authority_controls, complete_identity, native_scope_control


class IntegrityTests(unittest.TestCase):
    """Check meaningful failure boundaries without opening held-out scientific jobs."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.dependencies = {"packaging": importlib.metadata.version("packaging")}
        cls.inventory = dependency_inventory(cls.dependencies)

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="v4-binding-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.source = self.root / "source"
        (self.source / "instrument").mkdir(parents=True)
        (self.source / "instrument" / "cli.py").write_text("# CONFORMANCE-ONLY fixture; not a scientific instrument.\n")
        (self.source / "instrument" / "request.schema.json").write_text('{"type":"object"}\n')
        self.specification = {
            "schema": "inspection-evidence-closure/v1",
            "files": {
                str(path.relative_to(self.source)): file_sha(path) for path in (self.source / "instrument").iterdir()
            },
            "dependencies": self.dependencies,
            "schema_identity": "conformance-only-schema/v1",
            "policy_identity": "conformance-only-policy/v1",
            "entrypoint": "instrument/cli.py",
            "provenance": "Generated unit-test fixture; no scientific or commercial result.",
        }
        self.bundle = self.root / "bundle.zip"
        self.manifest = pack_bundle(self.source, self.specification, self.inventory["identity"], self.bundle)
        self.bundle_sha = file_sha(self.bundle)

    def test_existing_source_manifest_is_verified(self) -> None:
        self.assertGreater(len(inherited().upstream().verify_sources()["files"]), 1)

    def test_received_bytes_bind_complete_source_and_environment(self) -> None:
        destination = self.root / "receiver"
        manifest = unpack_bundle(self.bundle, destination, self.bundle_sha)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual(verify_installed_bundle(destination, manifest)["identity"], self.inventory["identity"])
        (destination / "instrument" / "cli.py").write_text("# changed after transfer\n")
        with self.assertRaisesRegex(ValueError, "recipient source changed"):
            verify_installed_bundle(destination, manifest)

    def test_source_drift_prevents_packing(self) -> None:
        (self.source / "instrument" / "cli.py").write_text("# source drift\n")
        with self.assertRaisesRegex(ValueError, "frozen runtime source changed"):
            pack_bundle(self.source, self.specification, self.inventory["identity"], self.root / "drift.zip")

    def test_altered_archive_refuses_old_identity(self) -> None:
        with self.bundle.open("ab") as stream:
            stream.write(b"altered")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            unpack_bundle(self.bundle, self.root / "receiver", self.bundle_sha)

    def test_undeclared_data_cannot_enter_payload(self) -> None:
        with zipfile.ZipFile(self.bundle, "a") as archive:
            archive.writestr("evaluation/protected/answers.json", "{}")
        with self.assertRaisesRegex(ValueError, "unsafe bundle member"):
            unpack_bundle(self.bundle, self.root / "receiver", file_sha(self.bundle))
        self.assertFalse(safe_member("instrument/../../protected/answers.json"))
        self.assertFalse(safe_member("instrument/test_answers.py"))
        self.assertTrue(safe_member("instrument/QIF_2_1_Units.xsd"))

    def test_credential_and_registered_protected_material_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "credential-pattern"):
            scan_payload(b"sk-" + b"X" * 30)
        with self.assertRaisesRegex(ValueError, "protected material"):
            scan_payload(b"unit-fixture-answer", (b"unit-fixture-answer",))
        bad = copy.deepcopy(self.specification)
        bad["provenance"] = "sk-" + "X" * 30
        with self.assertRaisesRegex(ValueError, "credential-pattern"):
            pack_bundle(self.source, bad, self.inventory["identity"], self.root / "secret.zip")

    def test_declared_dependency_version_mismatch_refused(self) -> None:
        with self.assertRaisesRegex(ValueError, "dependency version changed"):
            dependency_inventory({"packaging": "0.0.0-incompatible"})

    def test_request_semantics_and_source_bytes_are_both_bound(self) -> None:
        data = self.root / "public.xml"
        data.write_text("<public-fixture/>\n")
        request = {
            "mission": {"id": "fixture", "purpose": "evidence_audit", "statement": "First purpose"},
            "assets": {"source_qif": {"path": data.name, "sha256": file_sha(data)}},
        }
        path = self.root / "request.json"
        save(path, request)
        first = bind_request(path)
        request["mission"]["statement"] = "Different purpose"
        path.write_text(json.dumps(request))
        second = bind_request(path)
        self.assertNotEqual(first["request_sha256"], second["request_sha256"])
        self.assertEqual(first["assets"], second["assets"])
        data.write_text("<different-public-fixture/>\n")
        with self.assertRaisesRegex(ValueError, "mission source changed"):
            bind_request(path)

    def test_native_signature_time_revocation_and_scope_checks(self) -> None:
        native = native_trust()
        registry, keys = native.local_principals()
        context = {
            "mode": MODE,
            "recipient": "lyra.agent.agi.eth",
            "revoked": [],
            "public_controller_key": registry.anchor("local-controller", "controller").public_key,
        }
        identity = complete_identity(self.manifest, self.bundle_sha, {"fixture": "not-scientific"})
        binding = {
            "request_sha256": "1" * 64,
            "mission": {"statement": "fixture"},
            "assets": {"source": {"sha256": "2" * 64}},
        }
        checks = authority_controls(identity, binding, context, native, keys["local-controller"])
        self.assertEqual([row["name"] for row in checks if not row["passed"]], [])
        self.assertTrue(native_scope_control()["passed"])

    def test_existing_native_journal_prevents_grant_replay(self) -> None:
        native = native_trust()
        from alpha_factory_v1.core.runtime.store import Journal

        registry, keys = native.local_principals()
        context = {
            "mode": MODE,
            "recipient": "lyra.agent.agi.eth",
            "revoked": [],
            "public_controller_key": registry.anchor("local-controller", "controller").public_key,
        }
        identity = {"fixture": "authority-only"}
        binding = {"fixture": "current-mission"}
        now = int(time.time())
        payload = grant_payload(identity, binding, "one-use-fixture", now)
        envelope = native.sign_record(keys["local-controller"], "local-controller", DOMAIN, payload).model_dump()
        checked = check_grant(envelope, context, identity, binding, now)
        journal_path = self.root / "native-journal"
        journal = Journal.initialize(journal_path)
        consume_authority(journal_path, envelope, checked)
        events = journal.verify()["events"]
        with self.assertRaisesRegex(ValueError, "already consumed"):
            consume_authority(journal_path, envelope, checked)
        self.assertEqual(journal.verify()["events"], events)

    def test_generic_receipt_carries_neither_mission_acceptance_nor_authority(self) -> None:
        cache = inherited().QualificationCache()
        identity = complete_identity(self.manifest, self.bundle_sha, {"fixture": "not-scientific"})
        calls = []

        def qualify() -> dict[str, object]:
            calls.append(1)
            return {"accepted": True, "cases": 2, "scope": "unit fixture integrity only"}

        first = cache.qualify(identity, qualify)
        again = cache.qualify(identity, qualify)
        self.assertEqual(first["qualification_cases_executed"], 2)
        self.assertEqual(again["qualification_cases_executed"], 0)
        self.assertIsNone(again["authority"])
        self.assertIsNone(again["mission_acceptance"])
        changed = copy.deepcopy(identity)
        changed["evaluator"] = {"different": "evaluator"}
        cache.qualify(changed, qualify)
        self.assertEqual(len(calls), 2)

    def test_existing_A_B_C_ledger_counts_once_and_keeps_unknown_cost_unknown(self) -> None:
        runner = upstream_runner()
        result = inherited().upstream().replay_native(runner.conformance_commands(), controls=True)
        self.assertEqual(result["report"]["costs"], {"A": 900_000, "B": 180_000, "C": 270_000})
        self.assertEqual(result["report"]["complete_cost_profit"], 3_650_000)
        self.assertEqual([row["name"] for row in result["controls"] if not row["passed"]], [])
        self.assertEqual(result["actual_collections_micro_usd"], 0)
        self.assertTrue(result["journal"]["valid"])
        unknown = (
            inherited()
            .upstream()
            .replay_native(
                [
                    {
                        "action": "charge",
                        "record": {
                            "activity_id": "actual-unmetered",
                            "mission_id": "actual-research",
                            "bucket": "C",
                            "category": "model",
                            "accrued_micro_usd": None,
                            "paid_micro_usd": 0,
                            "basis": "unknown",
                            "evidence_digest": digest({"unmetered": True}),
                            "note": "Actual model expense unmetered; no zero-cost assertion.",
                        },
                    }
                ]
            )
        )
        self.assertIsNone(unknown["report"]["complete_cost_profit"])
        self.assertIsNone(unknown["report"]["available_funds"])
        self.assertEqual(unknown["report"]["collected_revenue"], 0)


if __name__ == "__main__":
    unittest.main()
