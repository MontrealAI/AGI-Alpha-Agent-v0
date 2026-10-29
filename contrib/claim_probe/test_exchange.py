# SPDX-License-Identifier: Apache-2.0
"""End-to-end gated delivery with the actual claim checker and durable storage."""

import concurrent.futures
import tempfile
from pathlib import Path
import unittest

from alpha_factory_v1.core.runtime.claim_probe import checker, contracts, instrument, operator
from alpha_factory_v1.core.runtime.meta_discovery.exchange import Exchange


def exchange(path):
    return Exchange(path, contract_id="claim-probe/v1", task_validator=contracts.validate, result_checker=checker.check)


class ProbeExchangeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "orders.sqlite"
        self.db = exchange(self.path)
        self.task = operator.example()
        self.db.provision_simulated_buyer("buyer", "manager-usdc", 10_000_000)
        self.db.offer("o", "campaign", "buyer", "manager-usdc", "USDC", 6, 1_000_000, self.task, 10)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def funded(self):
        self.db.event("o", "consent", "consent", {"buyer": "buyer", "termsHash": self.db.terms_hash("o")}, 0)
        self.db.event("o", "fund", "fund", {"buyer": "buyer"}, 1)

    def verified(self):
        self.funded()
        self.db.event("o", "deliver", "deliver", {"artifact": instrument.probe(self.task)}, 2)
        self.db.event("o", "verify", "verify", {}, 3)

    def test_unfunded_output_refused(self):
        with self.assertRaises(PermissionError):
            self.db.download("o", "buyer")
        with self.assertRaises(ValueError):
            self.db.event("o", "deliver", "deliver", {"artifact": instrument.probe(self.task)}, 0)

    def test_escrow_restricted_then_earned(self):
        self.funded()
        a = self.db.accounting("manager-usdc")
        self.assertEqual(a["revenue"], 0)
        self.assertEqual(a["restricted"], 1_000_000)
        self.db.event("o", "deliver", "deliver", {"artifact": instrument.probe(self.task)}, 2)
        self.db.event("o", "verify", "verify", {}, 3)
        with self.assertRaises(PermissionError):
            self.db.download("o", "buyer")
        self.db.event("o", "settle", "settle", {}, 4)
        self.assertTrue(self.db.download("o", "buyer"))
        self.assertEqual(self.db.accounting("manager-usdc")["cash"], 1_000_000)

    def test_invalid_output_and_refund(self):
        self.funded()
        wrong = instrument.probe(self.task)
        wrong["witness"]["value"] = "-999"
        self.db.event("o", "deliver", "deliver", {"artifact": wrong}, 2)
        with self.assertRaises(ValueError):
            self.db.event("o", "verify", "verify", {}, 3)
        self.db.event("o", "refund", "timeout", {}, 11)
        self.assertEqual(self.db.accounting("manager-usdc")["cash"], 0)
        self.assertEqual(self.db.accounting("manager-usdc")["restricted"], 0)

    def test_unknown_not_accepted_as_completed_audit(self):
        self.funded()
        result = instrument.probe(self.task)
        result.update(status="UNKNOWN", witness=None, cover=[])
        self.db.event("o", "deliver", "deliver", {"artifact": result}, 2)
        with self.assertRaises(ValueError):
            self.db.event("o", "verify", "verify", {}, 3)

    def test_contract_change_on_reopen_refused(self):
        with self.assertRaises(ValueError):
            Exchange(self.path)

    def test_interruption_before_commit_and_retry(self):
        self.verified()
        with self.assertRaises(InterruptedError):
            self.db.event("o", "settle", "settle", {}, 4, crash=True)
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 0)
        self.db.close()
        self.db = exchange(self.path)
        self.db.event("o", "settle", "settle", {}, 4)
        self.db.event("o", "settle", "settle", {}, 4)
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 1_000_000)

    def test_concurrent_duplicate_settlement(self):
        self.verified()

        def settle(_):
            with_db = exchange(self.path)
            try:
                return with_db.event("o", "same-settle", "settle", {}, 4)
            finally:
                with_db.close()

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(settle, range(4))), ["settled"] * 4)
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 1_000_000)

    def test_chargeback_preserves_loss_and_revokes_access(self):
        self.verified()
        self.db.event("o", "settle", "settle", {}, 4)
        self.assertTrue(self.db.download("o", "buyer"))
        self.db.event("o", "reverse", "chargeback", {}, 5)
        self.assertEqual(self.db.accounting("manager-usdc")["revenue"], 0)
        self.assertEqual(self.db.accounting("manager-usdc")["cash"], 0)
        with self.assertRaises(PermissionError):
            self.db.download("o", "buyer")

    def test_reordered_and_rebound_event_refused(self):
        self.funded()
        with self.assertRaises(ValueError):
            self.db.event("o", "fund", "fund", {"buyer": "buyer"}, 2)
        with self.assertRaises(ValueError):
            self.db.event("o", "old", "consent", {"buyer": "buyer", "termsHash": self.db.terms_hash("o")}, 0)

    def test_currency_and_credit_boundaries(self):
        with self.assertRaises(ValueError):
            self.db.offer("wrong", "campaign", "buyer", "jobs-agialpha", "USDC", 6, 1, self.task, 10)
        with self.assertRaises(ValueError):
            self.db.event("o", "credit", "credit", {}, 0)


if __name__ == "__main__":
    unittest.main()
