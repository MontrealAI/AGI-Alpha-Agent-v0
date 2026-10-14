# SPDX-License-Identifier: Apache-2.0
"""A release cannot substitute stale or fabricated Nova browser evidence."""
import copy
import unittest
from unittest.mock import patch

from scripts.nova_studio_evidence import CHECKS, EVM_CHECKS, verify_evm_report, verify_report


class EvidenceGate(unittest.TestCase):
    def test_public_report_requires_exact_source_and_complete_checks(self):
        report = {
            "schema": "agialpha.nova-studio.acceptance.v1",
            "passed": True,
            "commit": "a" * 40,
            "version": "1.31.0",
            "origin": "https://example.test/",
            "assets": {"app.mjs": "b" * 64},
            "checks": CHECKS,
            "realMainnetTransactions": False,
            "physicalWalletValidated": False,
        }
        with patch("scripts.nova_studio_evidence.hashes", return_value=report["assets"]):
            verify_report(report, "a" * 40, "1.31.0", "https://example.test/")
            for key, value in [
                ("commit", "c" * 40),
                ("version", "1.30.0"),
                ("assets", {}),
                ("checks", CHECKS[:-1]),
                ("passed", False),
                ("realMainnetTransactions", True),
                ("physicalWalletValidated", True),
                ("origin", "https://another.test/"),
            ]:
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_report(report | {key: value}, "a" * 40, "1.31.0", "https://example.test/")

    def test_evm_gate_rejects_incomplete_duplicate_or_failed_transactions(self):
        actions = [
            "seal",
            "openReview",
            "attest",
            "attest",
            "open",
            "approve",
            "approve",
            "buy",
            "bloom",
            "route",
            "approve",
            "approve",
            "agentDeposit",
            "bid",
            "award",
            "submit",
            "validate",
            "validate",
        ]
        receipts = []
        for index, action in enumerate(actions):
            tx_hash = "0x" + format(index + 1, "064x")
            receipts.append(
                {"action": action, "hash": tx_hash, "receipt": {"transactionHash": tx_hash, "status": "0x1"}}
            )
        report = {
            "schema": "agialpha.nova-studio.evm-browser.v1",
            "passed": True,
            "commit": "a" * 40,
            "version": "1.31.0",
            "sourceAssets": {"app.mjs": "b" * 64},
            "checks": EVM_CHECKS,
            "exactSource": True,
            "chainId": 31337,
            "profileHash": "c" * 64,
            "realMainnetTransactions": False,
            "physicalWalletValidated": False,
            "realStorageProviderValidated": False,
            "receipts": receipts,
            "nativeDelivery": {
                "uiHashAutofilled": True,
                "uiSubmission": True,
                "runtimeConnected": False,
                "verification": {"valid": True, "resultHash": "0x" + "d" * 64},
            },
            "settlement": {
                "state": "paid",
                "job": {"state": "4", "refund": "20000000000000000000", "resultHash": "0x" + "d" * 64},
                "accounting": {
                    "verified": True,
                    "before": {
                        "agent": "0",
                        "validator1": "0",
                        "validator2": "0",
                        "funder": "0",
                        "totalSupply": "800000000000000000",
                    },
                    "after": {
                        "agent": "75240000000000000000",
                        "validator1": "1980000000000000000",
                        "validator2": "1980000000000000000",
                        "funder": "0",
                        "totalSupply": "0",
                    },
                    "deltas": {
                        "agent": "75240000000000000000",
                        "validator1": "1980000000000000000",
                        "validator2": "1980000000000000000",
                        "funder": "0",
                        "totalSupply": "-800000000000000000",
                    },
                },
            },
        }
        with patch("scripts.nova_studio_evidence.hashes", return_value=report["sourceAssets"]):
            verify_evm_report(report, "a" * 40, "1.31.0")
            for key, value in [
                ("chainId", 1),
                ("sourceAssets", {}),
                ("exactSource", False),
                ("checks", EVM_CHECKS[:-1]),
                ("receipts", []),
                ("receipts", receipts[:-1]),
                ("receipts", receipts[:-1] + receipts[:1]),
                ("profileHash", "unknown"),
                ("realStorageProviderValidated", True),
                ("settlement", {}),
                ("nativeDelivery", {}),
            ]:
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_evm_report(report | {key: value}, "a" * 40, "1.31.0")
            for field, value in [("status", "0x0"), ("transactionHash", "0x" + "e" * 64)]:
                bad = copy.deepcopy(report)
                bad["receipts"][0]["receipt"][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_evm_report(bad, "a" * 40, "1.31.0")


if __name__ == "__main__":
    unittest.main()
