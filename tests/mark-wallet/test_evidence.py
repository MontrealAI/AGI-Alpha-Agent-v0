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


class CacheBoundary(unittest.TestCase):
    def test_generated_wallet_profile_never_enters_the_offline_demo_cache(self):
        import tempfile
        from pathlib import Path
        from scripts.build_service_worker import build, gather_assets

        with tempfile.TemporaryDirectory() as temporary:
            docs = Path(temporary)
            (docs / "index.html").write_text("demo")
            original = build(docs)
            for name in [
                "assets/ascension-wallet/profile.json",
                "assets/ascension-wallet/app.mjs",
                "ascension-protocol/mainnet/index.html",
                "alpha_factory_v1/demos/ascension-protocol/mainnet/index.html",
                "assets/nova-studio/app.mjs",
                "ascension/mainnet/index.html",
                "alpha_factory_v1/demos/ascension/mainnet/index.html",
            ]:
                path = docs / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("network-only")
            self.assertEqual(gather_assets(docs), ["index.html"])
            self.assertEqual(build(docs), original)
            self.assertNotIn("ascension-wallet", (docs / "service-worker.js").read_text())
