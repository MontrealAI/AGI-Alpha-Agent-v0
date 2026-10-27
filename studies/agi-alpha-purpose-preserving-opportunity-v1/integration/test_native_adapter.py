# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
import base64
import tempfile
import unittest
from pathlib import Path
from typing import Any, ClassVar

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from native_adapter import ACCEPTANCE_DOMAIN, run_fixture

from alpha_factory_v1.core.runtime.successor.protocol import digest


class NativeFixtureTests(unittest.TestCase):
    raw: ClassVar[bytes]
    report: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "test-artifact.json"
            cls.raw = b'{"scope":"integration-test-only","version":1}\n'
            artifact.write_bytes(cls.raw)
            cls.report = run_fixture(artifact)

    def test_source_binding_and_material_mission_change(self) -> None:
        self.assertEqual(self.report["artifact"]["sha256"], hashlib.sha256(self.raw).hexdigest())
        self.assertNotEqual(self.report["missions"][0]["digest"], self.report["missions"][1]["digest"])
        self.assertGreater(len(self.report["runtime_sources"]), 5)

    def test_local_native_boundaries_all_pass(self) -> None:
        self.assertEqual(self.report["checks_passed"], self.report["checks_total"])
        self.assertGreaterEqual(self.report["checks_total"], 15)
        ids = {row["id"] for row in self.report["checks"]}
        self.assertIn("old-acceptance-does-not-transfer-to-successor", ids)
        self.assertIn("native-capsule-rejects-unsupported-ecological-scope", ids)
        self.assertIn("revoked-local-principal-denied-fresh-access", ids)

    def test_unknown_actual_cost_and_zero_collections(self) -> None:
        actual = self.report["accounting"]["actual"]["report"]
        self.assertTrue(actual["unknown_costs"])
        self.assertFalse(actual["complete"])
        self.assertIsNone(actual["complete_cost_profit"])
        self.assertIsNone(actual["available_funds"])
        self.assertEqual(actual["collected_revenue"], 0)

    def test_assumed_accounting_kept_separate(self) -> None:
        assumed = self.report["accounting"]["assumed"]
        self.assertFalse(assumed["actual_receipts_or_payments"])
        self.assertIsNone(assumed["bank_evidence"])
        self.assertTrue(assumed["not_root_commercial_study"])
        report = assumed["report"]
        self.assertEqual(report["costs"], {"A": 40000000, "B": 10000000, "C": 100000000})
        self.assertEqual(report["cash"] - report["obligations"] - report["reserve"], report["available_funds"])
        self.assertEqual(report["collected_revenue"], 0)

    def test_no_live_or_ecological_acceptance_claim(self) -> None:
        limits = self.report["limits"]
        self.assertFalse(limits["live_ens_authentication"])
        self.assertFalse(limits["protected_capsule_admitted"])
        self.assertFalse(limits["ecological_semantics_checked_by_this_adapter"])
        self.assertEqual(limits["scientific_production_admission"], "NOT_QUALIFIED_UNSUPPORTED_SCIENTIFIC_SCOPE")

    def test_public_report_excludes_private_credentials(self) -> None:
        encoded = json.dumps(self.report)
        for token in ("BEGIN PRIVATE KEY", "identity.key", "api.token", "private_key"):
            self.assertNotIn(token, encoded)
        self.assertTrue(self.report["lifecycle"]["journal_verification"]["valid"])

    def test_exported_acceptance_signature_is_verifiable(self) -> None:
        body = next(
            event["body"]["document"]
            for event in reversed(self.report["lifecycle"]["events"])
            if event["body"]["mission"] == "@ecological-fixture:successor"
        )
        self.assertTrue(body["current_acceptance_verified"])
        receipt = body["current_acceptance"]
        self.assertEqual(receipt["domain"], ACCEPTANCE_DOMAIN)
        public = self.report["fixture_public_signing_keys"][receipt["principal"]]
        commitment = digest(ACCEPTANCE_DOMAIN, {"principal": receipt["principal"], "payload": receipt["payload"]})
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)).verify(
            base64.b64decode(receipt["signature"]), bytes.fromhex(commitment)
        )


if __name__ == "__main__":
    unittest.main()
