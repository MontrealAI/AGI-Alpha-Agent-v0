# SPDX-License-Identifier: Apache-2.0
"""Checks for native monetary boundaries and locally authenticated commands."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from repository_adapter import (
    MANIFEST,
    NativeResearchLedger,
    evidence_digest,
    replay_native_ledger,
    verify_native_sources,
)

CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]


def charge(activity: str, amount: int | None = 100, paid: int = 0, bucket: str = "A") -> dict:
    return {
        "activity_id": activity,
        "mission_id": "mission",
        "bucket": bucket,
        "category": "compute",
        "accrued_micro_usd": amount,
        "paid_micro_usd": paid,
        "basis": "unknown" if amount is None else "attested",
        "evidence_digest": evidence_digest("charge-fixture", {"activity": activity, "amount": amount}),
        "note": "Synthetic local accounting fixture",
    }


class RepositoryAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="frontier-adapter-test-")
        self.addCleanup(self.temporary.cleanup)
        self.bridge = NativeResearchLedger(Path(self.temporary.name) / "journal")

    def test_complete_disjoint_costs_and_cash_are_native(self) -> None:
        rows = []
        for bucket, amount, paid in [("A", 100, 50), ("B", 7, 7), ("C", 13, 13)]:
            for category in CATEGORIES:
                row = charge(f"{bucket}-{category}", amount if category == "compute" else 0,
                             paid if category == "compute" else 0, bucket)
                row["category"] = category
                rows.append(row)
        result = replay_native_ledger(
            rows, collections=[{"record_id": "sale", "mission_id": "mission", "amount_micro_usd": 200}],
            capital_micro_usd=1000, reserve_micro_usd=40,
        )
        report = result["report"]
        self.assertEqual(report["costs"], {"A": 100, "B": 7, "C": 13})
        self.assertEqual(report["collected_revenue"], 200)
        self.assertEqual(report["delivery_profit"], 100)
        self.assertEqual(report["complete_cost_profit"], 80)
        self.assertEqual(report["cash"], 1130)
        self.assertEqual(report["obligations"], 50)
        self.assertEqual(report["available_funds"], 1040)
        self.assertTrue(result["journal_verification"]["valid"])
        self.assertEqual(result["actual_customer_collections_micro_usd"], 0)

    def test_duplicate_activity_cannot_move_between_buckets(self) -> None:
        self.bridge.apply("charge", charge("same"))
        with self.assertRaisesRegex(ValueError, "activity already charged"):
            self.bridge.apply("charge", charge("same", bucket="C"))
        self.assertEqual(self.bridge.ledger.report()["costs"], {"A": 100, "B": 0, "C": 0})

    def test_unknown_cost_blocks_profit_and_available_funds(self) -> None:
        result = replay_native_ledger([charge("unmetered", amount=None)], capital_micro_usd=1000)
        self.assertIsNone(result["report"]["complete_cost_profit"])
        self.assertIsNone(result["report"]["obligations"])
        self.assertIsNone(result["report"]["available_funds"])

    def test_missing_categories_do_not_become_complete(self) -> None:
        result = replay_native_ledger([charge("only-compute")])
        self.assertFalse(result["report"]["complete"])
        self.assertIsNone(result["report"]["delivery_profit"])

    def test_duplicate_operation_is_idempotent_but_changed_terms_refuse(self) -> None:
        self.bridge.apply("charge", charge("once"), "same-operation")
        self.bridge.apply("charge", charge("once"), "same-operation")
        self.assertEqual(self.bridge.ledger.report()["costs"]["A"], 100)
        with self.assertRaisesRegex(ValueError, "different terms"):
            self.bridge.apply("charge", charge("once", amount=200), "same-operation")

    def test_revoked_local_accounting_signer_refuses(self) -> None:
        self.bridge.trust.revoke(self.bridge.principal)
        with self.assertRaisesRegex(ValueError, "not currently trusted"):
            self.bridge.apply("charge", charge("revoked"))
        self.assertEqual(self.bridge.ledger.report()["costs"]["A"], 0)

    def test_mutated_signed_amount_refuses(self) -> None:
        signed = self.bridge.signed("charge", charge("mutated"))
        signed.payload["record"]["accrued_micro_usd"] = 200
        with self.assertRaisesRegex(ValueError, "signature is invalid"):
            self.bridge.ledger.apply(signed)

    def test_invoice_is_not_collected_revenue(self) -> None:
        record = {"record_id": "invoice", "mission_id": "mission", "amount_micro_usd": 900,
                  "evidence_digest": evidence_digest("invoice", {"id": "unpaid"})}
        self.bridge.apply("invoice", record)
        self.assertEqual(self.bridge.ledger.report()["collected_revenue"], 0)
        self.assertEqual(self.bridge.ledger.report()["cash"], 0)

    def test_partial_payment_changes_cash_and_liability_once(self) -> None:
        self.bridge.apply("charge", charge("liability"))
        payment = {"payment_id": "p1", "activity_id": "liability", "amount_micro_usd": 40,
                   "evidence_digest": evidence_digest("payment", {"id": "p1"})}
        self.bridge.apply("payment", payment)
        report = self.bridge.ledger.report()
        self.assertEqual(report["cash"], -40)
        self.assertEqual(report["obligations"], 60)
        self.assertEqual(report["available_funds"], -100)
        with self.assertRaisesRegex(ValueError, "already reconciled"):
            self.bridge.apply("payment", payment)

    def test_native_source_manifest_rejects_drift(self) -> None:
        manifest = json.loads(MANIFEST.read_text())
        manifest["files"][0]["sha256"] = "0" * 64
        altered = Path(self.temporary.name) / "altered-manifest.json"
        altered.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "native source drift"):
            verify_native_sources(manifest_path=altered)


if __name__ == "__main__":
    unittest.main()
