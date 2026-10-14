# SPDX-License-Identifier: Apache-2.0
"""Reject stale Studio artifacts and false lifecycle completion evidence."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from typing import Any

from scripts.nova_studio_evidence import BROWSER_CHECKS, REQUIRED_ACTIONS, STEPS, verify_browser, verify_lifecycle


class StudioEvidenceTests(unittest.TestCase):
    def test_browser_requires_exact_complete_zero_wallet_journey(self) -> None:
        assets = {"ascension/mainnet/index.html": "f" * 64}
        report: dict[str, Any] = {
            "schema": "agialpha.nova-studio.browser.v1",
            "passed": True,
            "commit": "a" * 40,
            "version": "1.30.0",
            "origin": "https://example.test/project/",
            "assets": assets,
            "checks": BROWSER_CHECKS,
            "pageErrors": [],
            "walletRequests": 0,
            "mainnetTransactions": 0,
            "physicalWalletValidated": False,
            "audits": [
                {"language": lang, "width": width, "step": step, "largeText": large, "violations": []}
                for lang in ("en", "fr")
                for width in (1440, 390, 320)
                for step in STEPS
                for large in (False, True)
            ],
        }
        with patch("scripts.nova_studio_evidence.hashes", return_value=assets):
            verify_browser(report, "a" * 40, "1.30.0", "https://example.test/project/")
            for key, value in [
                ("commit", "b" * 40),
                ("checks", BROWSER_CHECKS[:-1]),
                ("assets", {}),
                ("pageErrors", ["runtime failure"]),
                ("walletRequests", 1),
                ("mainnetTransactions", 1),
                ("physicalWalletValidated", True),
                ("origin", "https://other.test/"),
                ("passed", False),
                ("audits", []),
                ("audits", report["audits"][:-1]),
                ("audits", [report["audits"][0] | {"violations": [{"id": "color-contrast"}]}] + report["audits"][1:]),
            ]:
                with self.subTest(key=key), self.assertRaises(ValueError):
                    verify_browser(report | {key: value}, "a" * 40, "1.30.0", "https://example.test/project/")

    def test_lifecycle_binds_source_receipts_native_delivery_and_balance_deltas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            page = root / "docs/ascension/mainnet/index.html"
            page.parent.mkdir(parents=True)
            page.write_text("actual source")
            digest = hashlib.sha256(page.read_bytes()).hexdigest()
            folder = root / "evidence"
            folder.mkdir()
            names = sorted(REQUIRED_ACTIONS) + ["attest", "validate", "transferSeed"]
            actions: list[dict[str, Any]] = []
            for index, name in enumerate(names, 1):
                tx_hash = "0x" + f"{index:064x}"
                actions.append(
                    {
                        "action": name,
                        "hash": tx_hash,
                        "status": "finalized",
                        "receipt": {
                            "status": "0x1",
                            "transactionHash": tx_hash,
                            "blockHash": "0x" + "b" * 64,
                            "blockNumber": hex(index),
                            "from": "0x" + f"{index:040x}",
                        },
                    }
                )
            report: dict[str, Any] = {
                "schema": "agialpha.nova-studio.acceptance.v1",
                "passed": True,
                "mainnetTransactions": 0,
                "compilerSizes": [1, 2, 3, 7, 127, 128],
                "proofsVerified": 268,
                "actions": actions,
                "failureCases": {
                    "foreignMintEvent": "effect-unverified",
                    "restoredEffectBarrier": True,
                    "staleWalletPreview": True,
                    "removedReceipt": {"observationCleared": True, "resubmitted": False},
                },
                "nativeDelivery": {
                    "signatureVerified": True,
                    "executionReplayed": True,
                    "connected": False,
                    "resultHash": "0x" + "c" * 64,
                    "byteSHA256": hashlib.sha256(b"test native envelope").hexdigest(),
                    "artifact": "native-delivery.json",
                    "planRoot": "0x" + "e" * 64,
                    "signer": "f" * 64,
                },
                "settlement": {
                    "before": {"worker": "5"},
                    "after": {"worker": "8"},
                    "delta": {"worker": "3"},
                    "expected": {"worker": "3"},
                    "confirmed": True,
                },
            }
            report["browserNativeDelivery"] = copy.deepcopy(report["nativeDelivery"])
            report["browserSettlement"] = copy.deepcopy(report["settlement"])
            report["browserReceipts"] = [
                entry["receipt"] | {"transactionHash": "0x" + f"{i + 100:064x}"} for i, entry in enumerate(actions)
            ]
            browser = {
                "passed": True,
                "mainnetTransactions": 0,
                "pageErrors": [],
                "nativeDeliveryVerified": True,
                "unwrappedNativeFetch": True,
                "checks": ["actual browser"],
                "audits": [{"violations": []}],
            }
            for name, value in {
                "exact-source-report.json": report,
                "browser-report.json": browser,
                "local-recovery-example.json": {},
                "local-work-example.json": {},
            }.items():
                (folder / name).write_text(json.dumps(value))
            manifest: dict[str, Any] = {
                "schema": "agialpha.nova-studio.evidence-index.v1",
                "commit": "a" * 40,
                "mainnetTransactions": 0,
                "profile": {"chainId": 31337, "environment": "local-exact-source", "mainnetQualification": False},
                "sourceHashes": {"docs/ascension/mainnet/index.html": digest},
                "notPerformed": ["mainnet"],
            }
            (folder / "native-delivery.json").write_bytes(b"test native envelope")

            def save_index() -> None:
                manifest["artifacts"] = {
                    path.name: {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
                    for path in folder.iterdir()
                    if path.name != "evidence-index.json"
                }
                (folder / "evidence-index.json").write_text(json.dumps(manifest))

            with (
                patch("scripts.nova_studio_evidence.ROOT", root),
                patch("scripts.nova_studio_evidence.hashes", return_value={"ascension/mainnet/index.html": digest}),
            ):
                save_index()
                verify_lifecycle(folder, "a" * 40)
                with (
                    patch(
                        "scripts.nova_studio_evidence.hashes",
                        return_value={"ascension/mainnet/index.html": digest, "assets/successor/engine.mjs": "f" * 64},
                    ),
                    self.assertRaises(ValueError),
                ):
                    verify_lifecycle(folder, "a" * 40)
                with self.assertRaises(ValueError):
                    verify_lifecycle(folder, "b" * 40)
                page.write_text("different source")
                with self.assertRaises(ValueError):
                    verify_lifecycle(folder, "a" * 40)
                page.write_text("actual source")
                for mutation in (
                    "missing-receipt",
                    "duplicate-receipt",
                    "failed-receipt",
                    "native",
                    "balances",
                    "browser-receipts",
                    "browser-native",
                    "browser-balances",
                ):
                    bad = copy.deepcopy(report)
                    if mutation == "missing-receipt":
                        bad["actions"][0].pop("receipt")
                    elif mutation == "duplicate-receipt":
                        bad["actions"][-1] = copy.deepcopy(bad["actions"][0])
                    elif mutation == "failed-receipt":
                        bad["actions"][0]["receipt"]["status"] = "0x0"
                    elif mutation == "native":
                        bad["nativeDelivery"]["executionReplayed"] = False
                    elif mutation == "browser-receipts":
                        bad["browserReceipts"] = []
                    elif mutation == "browser-native":
                        bad["browserNativeDelivery"]["signatureVerified"] = False
                    elif mutation == "browser-balances":
                        bad["browserSettlement"]["after"]["worker"] = "9"
                    else:
                        bad["settlement"]["after"]["worker"] = "9"
                    (folder / "exact-source-report.json").write_text(json.dumps(bad))
                    save_index()
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        verify_lifecycle(folder, "a" * 40)
                (folder / "exact-source-report.json").write_text(json.dumps(report))
                save_index()
                (folder / "local-work-example.json").write_text("changed after indexing")
                with self.assertRaises(ValueError):
                    verify_lifecycle(folder, "a" * 40)


if __name__ == "__main__":
    unittest.main()
