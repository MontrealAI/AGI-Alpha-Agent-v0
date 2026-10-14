# SPDX-License-Identifier: Apache-2.0
"""Publication must reject stale or incomplete wallet evidence."""
import copy
import unittest
from scripts.mark_wallet_evidence import CHECKS, hashes, verify_report


class EvidenceGate(unittest.TestCase):
    def test_exact_evidence_and_adversarial_mutations(self):
        report = {
            "schema": "agialpha.mark-wallet.acceptance.v1",
            "passed": True,
            "commit": "a" * 40,
            "version": "1.30.0",
            "origin": "https://example.test/",
            "assets": hashes(),
            "checks": CHECKS,
            "realMainnetTransactions": False,
            "physicalWalletValidated": False,
        }
        verify_report(report, "a" * 40, "1.30.0", "https://example.test/")
        for field, value in [
            ("commit", "b" * 40),
            ("version", "1.29.0"),
            ("checks", CHECKS[:-1]),
            ("assets", {}),
            ("passed", False),
            ("origin", "https://elsewhere.test/"),
            ("realMainnetTransactions", True),
        ]:
            with self.subTest(field=field):
                bad = copy.deepcopy(report)
                bad[field] = value
                with self.assertRaises(ValueError):
                    verify_report(bad, "a" * 40, "1.30.0", "https://example.test/")
