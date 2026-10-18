# SPDX-License-Identifier: Apache-2.0
"""Validate the sanitized current deployment without network or private reports."""
from __future__ import annotations

import json
import re
import unittest
import tempfile
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "deployments/ethereum-mainnet/2026-10-18/manifest.json"
EXPECTED = {
    "AscensionAccess": (
        "0x9eE41dF6d076Fa4F89b102b76DEf1c503a1e7C3A",
        "0xbd76213da1ebba1a6844db3049d301adb728d1d5bb0817040105034f2ba83db0",
    ),
    "NovaSeed": (
        "0x31BD0736DcD55DA2f9a2BB586C8a98695F86f19E",
        "0x8d0cfaf628c5308164b3f6fc78782b6371269ea20a676cdd56d3cefa04ec0513",
    ),
    "AscensionRiskOracle": (
        "0x198FC6EBee21c6A0B34E4d055AFD6D811AA6dE58",
        "0x28854aa99af51722ecadb843f28cfb502e2fb5b69e4c1c328df053a143679a01",
    ),
    "AscensionJobMarket": (
        "0xc1d3d7fb064C23c46C4EB20d24ab6EA650FF0ceE",
        "0xc74b0146846ad71ad4840de1e2944e59f9c03d41157edce525b73c02bf567be0",
    ),
    "AscensionMark": (
        "0x6D5323b2609E36fDc4dB3B2501B7BcF0E131033c",
        "0xa85b88ff97fc3f5312bbfc9e33dccae1653aacb85461c943db115ad222ad480d",
    ),
}


class CurrentMainnetRecordTests(unittest.TestCase):
    """Pin the published facts and fail closed on contradictory readiness claims."""

    def setUp(self) -> None:
        self.record = json.loads(RECORD.read_text())

    def test_generated_directory_is_exact_and_has_no_wallet_or_provider_script(self) -> None:
        from scripts.generate_mainnet_directory import build

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record = root / RECORD.relative_to(ROOT)
            record.parent.mkdir(parents=True)
            record.write_bytes(RECORD.read_bytes())
            build(root)
            generated = root / "docs/deployments/2026-10-18"
            self.assertEqual(
                {path.name for path in generated.iterdir()}, {"index.html", "manifest.json", "directory.css"}
            )
            for path in generated.iterdir():
                self.assertEqual(path.read_bytes(), (ROOT / path.relative_to(root)).read_bytes(), path.name)
            page = (generated / "index.html").read_text()
            self.assertIn("docs/DISCLAIMER_SNIPPET.md", page)
            self.assertIn("default-src 'none'", page)
            self.assertNotRegex(page.lower(), r"<script\b|\bon[a-z]+\s*=|javascript:")
            for forbidden in (
                "window.ethereum",
                "eth_requestAccounts",
                "eth_sendTransaction",
                "wallet_connect",
                "https://mainnet.infura.io",
            ):
                self.assertNotIn(forbidden, page)

    def test_schema_and_exact_source(self) -> None:
        r = self.record
        self.assertEqual(r["schema"], "agialpha.ethereum-mainnet.public-deployment.v1")
        self.assertEqual(r["chainId"], 1)
        self.assertEqual(r["network"], "ethereum-mainnet")
        self.assertEqual(r["recordDate"], "2026-10-18")
        self.assertEqual(r["source"]["commit"], "c0fc5217e364a39a4cd123d17a8317c06b80f820")
        self.assertEqual(r["source"]["tree"], "6c0ed7b1a5d40662bcd3e124a6d2aedd6447fcf2")
        self.assertEqual(r["planSha256"], "b4227447a26bbd13bbd6069de5aa704e78ef3d1d6c7e48ba71784064aff25f77")
        self.assertEqual(r["authorityBlock"]["number"], 26220072)
        self.assertEqual(
            r["authorityBlock"]["hash"], "0x8a3357d17a61a8f37c99dc836ac1176c6ee44b6261a81c41893527046c88a088"
        )

    def test_exact_five_contracts_and_explorer_results(self) -> None:
        contracts = self.record["contracts"]
        self.assertEqual(len(contracts), 5)
        self.assertEqual({c["name"]: (c["address"], c["creation"]["transactionHash"]) for c in contracts}, EXPECTED)
        for index, contract in enumerate(contracts):
            self.assertEqual(contract["creation"]["index"], index)
            self.assertRegex(contract["codeHash"], r"^0x[0-9a-f]{64}$")
            self.assertEqual(contract["explorer"]["status"], "EXACT_MATCH")
            self.assertIs(contract["explorer"]["explorerAccepted"], True)
            for key in ("publishedStandardInputSha256", "publishedAbiSha256"):
                self.assertRegex(contract["explorer"][key], r"^[0-9a-f]{64}$")
            self.assertEqual(contract["addressUrl"], f"https://etherscan.io/address/{contract['address']}#code")
            self.assertEqual(
                contract["creationUrl"], f"https://etherscan.io/tx/{contract['creation']['transactionHash']}"
            )

    def test_exact_two_bindings_and_graph(self) -> None:
        r = self.record
        bindings = r["bindings"]
        self.assertEqual(len(bindings), 2)
        expected = [
            (
                "bindMarketplace",
                "AscensionRiskOracle",
                "AscensionJobMarket",
                813,
                26219975,
                "0xbe9501a1da1d28c0705e43390a61232f3574f8eadd7583398f9cbb7fc388432b",
            ),
            (
                "bindMark",
                "AscensionJobMarket",
                "AscensionMark",
                814,
                26220058,
                "0xaa1339ae0fe993445464e617d6bbbe1e193db2164075d5dc0b7958e311750c88",
            ),
        ]
        for binding, (method, source, target, nonce, block, tx) in zip(bindings, expected):
            self.assertEqual(binding["method"], method)
            self.assertEqual(binding["to"], EXPECTED[source][0])
            self.assertEqual(binding["argument"], EXPECTED[target][0])
            self.assertEqual(binding["nonce"], nonce)
            self.assertEqual(binding["block"]["number"], block)
            self.assertEqual(binding["transactionHash"], tx)
            self.assertEqual(binding["transactionUrl"], f"https://etherscan.io/tx/{tx}")
            self.assertEqual(binding["receiptStatus"], 1)
            self.assertIs(binding["exactObservedEnvelopeValidated"], True)
            self.assertEqual(binding["finalizedAcceptanceBlock"], r["authorityBlock"])
        self.assertIs(r["authority"]["graphAuthorityVerified"], True)
        owners = [c for c in r["contracts"] if "owner" in c["values"]]
        self.assertEqual(len(owners), 3)
        for contract in owners:
            self.assertEqual(contract["values"]["owner"], r["governor"])
            self.assertEqual(contract["values"]["pendingOwner"], "0x" + "0" * 40)
        by_name = {c["name"]: c for c in r["contracts"]}
        self.assertEqual(by_name["AscensionRiskOracle"]["values"]["marketplace"], EXPECTED["AscensionJobMarket"][0])
        self.assertEqual(by_name["AscensionJobMarket"]["values"]["mark"], EXPECTED["AscensionMark"][0])

    def test_limits_and_fee_deviation_remain_explicit(self) -> None:
        r = self.record
        self.assertEqual(
            r["status"],
            {
                "activationAllowed": False,
                "readyForPublicFunding": False,
                "fullyProductionReady": False,
                "globalPauseAvailable": False,
                "externalCloseoutPending": False,
                "externalAuthorityCloseoutComplete": True,
            },
        )
        rec = r["reconciliation"]
        self.assertEqual(rec["originalSessionSequence"], 20)
        for key in (
            "originalSessionComplete",
            "actorLocksRetained",
            "secondPreTransactionIntentRecorded",
            "originalFirstIntentMatched",
            "originalFirstFeeApprovalMatched",
        ):
            self.assertIs(rec[key], False)
        for key in (
            "originalJournalUnchanged",
            "bothOriginalActorLeasesReleased",
            "observationIsNotRetroactiveApproval",
            "combinedActualExceedsOriginalApprovedMaximum",
        ):
            self.assertIs(rec[key], True)
        self.assertEqual(rec["combinedActualGasCostWei"], "221497159466359")
        self.assertEqual(rec["originalCombinedApprovedMaximumWei"], "150000000000000")
        self.assertEqual(sum(int(b["actualGasCostWei"]) for b in r["bindings"]), int(rec["combinedActualGasCostWei"]))
        self.assertEqual(Decimal(rec["combinedActualGasCostETH"]) * 10**18, Decimal(rec["combinedActualGasCostWei"]))
        self.assertEqual(rec["externalCloseoutCompletedAt"], "2026-10-18T15:24:15.848Z")
        self.assertEqual(rec["closeoutTransactionsBroadcast"], 0)
        self.assertIs(rec["closeoutSigningPerformed"], False)
        self.assertEqual(
            r["provenance"]["externalAuthorityCloseout"]["payloadSha256"],
            "f31b65ccb3ad0b76e5f60aeaff9c58a90723dd62ce6c0cf07d63a7da9714a083",
        )
        self.assertEqual(
            r["provenance"]["externalAuthorityCloseout"]["observedProofSha256"],
            r["provenance"]["observedEnvelopeProof"]["fileSha256"],
        )
        self.assertGreaterEqual(len(r["limitations"]), 8)

    def test_provenance_and_public_allowlist(self) -> None:
        r = self.record
        self.assertEqual(
            set(r),
            {
                "schema",
                "recordDate",
                "chainId",
                "network",
                "observedAt",
                "source",
                "planSha256",
                "authorityBlock",
                "governor",
                "contracts",
                "bindings",
                "authority",
                "status",
                "reconciliation",
                "limitations",
                "provenance",
            },
        )
        self.assertEqual(
            r["provenance"]["observedEnvelopeProof"]["fileSha256"],
            "7a7f9e1f559852a4f066182da130a57666334cad5feab58f01ff10d66a8aae9c",
        )
        self.assertEqual(
            r["provenance"]["governorReadOnlyPreparation"]["fileSha256"],
            "10306152acf3e08781d991c0d678478c25a7154cc3df42f87191afc1306c41cc",
        )
        for name in ("observedEnvelopeProof", "governorReadOnlyPreparation", "externalAuthorityCloseout"):
            for key in ("fileSha256", "payloadSha256"):
                self.assertRegex(r["provenance"][name][key], r"^[0-9a-f]{64}$")
        self.assertEqual(
            r["provenance"]["authorityPayloadSha256"],
            "f09f78a80f3ac3d8cb69c366e4ddeaf70d3d509e2fb6a2bcdfbe99bdd3d67ce0",
        )
        raw = RECORD.read_text()
        for forbidden in (
            "/workspace/",
            "/home/",
            "/media/",
            "journalSha256",
            "signingBoundary",
            "observedSignedEnvelope",
            "privateKey",
            "signature",
            "accessToken",
        ):
            self.assertNotIn(forbidden, raw)
        self.assertFalse(re.search(r'"(?:r|s|data|rawTransaction)"\s*:', raw))
        self.assertEqual({p.name for p in RECORD.parent.iterdir()}, {"manifest.json", "README.md"})
        guide = (ROOT / "docs/agent/CURRENT_MAINNET_DEPLOYMENT.md").read_text()
        self.assertIn("both\noriginal actor leases were released", guide)
        self.assertNotIn("external closeout/reconciliation is pending", guide)
        for address, tx in EXPECTED.values():
            self.assertIn(address, guide)
            self.assertIn(tx, guide)
        for statement in ("There is no global pause", "sequence 20", "post hoc", "0.000221497159466359"):
            self.assertIn(statement, guide)


if __name__ == "__main__":
    unittest.main()
