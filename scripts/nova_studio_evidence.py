# SPDX-License-Identifier: Apache-2.0
"""Require exact Studio browser and local lifecycle evidence before packaging."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from scripts.mark_wallet_evidence import ROOT, hashes

BROWSER_CHECKS = [
    "exact-assets",
    "no-wallet-preparation",
    "portable-recovery",
    "wrong-passphrase",
    "tampered-kit",
    "no-secret-persistence",
    "keyboard",
    "en-fr",
    "mobile",
    "axe",
]
REQUIRED_ACTIONS = {
    "seal",
    "openReview",
    "attest",
    "open",
    "approveFunding",
    "buy",
    "bloom",
    "route",
    "bid",
    "award",
    "submit",
    "validate",
    "collect",
    "close",
    "reclaim",
    "revoke",
    "transferSeed",
}
HEX32 = re.compile(r"0x[0-9a-fA-F]{64}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
STEPS = ("project", "protect", "publish", "mint", "review", "fund", "launch", "resume")


def verify_browser(report: dict[str, Any], commit: str, version: str, origin: str | None = None) -> None:
    """Reject stale assets, missing UI checks and claims beyond the actual trial."""
    audits = report.get("audits", [])
    expected_audits = {
        (language, width, step) for language in ("en", "fr") for width in (1440, 390, 320) for step in STEPS
    }
    if (
        report.get("schema") != "agialpha.nova-studio.browser.v1"
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("assets") != hashes()
        or set(report.get("checks", [])) != set(BROWSER_CHECKS)
        or report.get("pageErrors") != []
        or report.get("walletRequests") != 0
        or report.get("mainnetTransactions") != 0
        or report.get("physicalWalletValidated") is not False
        or len(audits) != len(expected_audits)
        or {(audit.get("language"), audit.get("width"), audit.get("step")) for audit in audits} != expected_audits
        or any(audit.get("violations") != [] for audit in audits)
        or (origin is not None and report.get("origin") != origin.rstrip("/") + "/")
    ):
        raise ValueError("Studio browser evidence must match the exact commit, assets and complete local journey")


def verify_lifecycle(folder: Path, commit: str) -> None:
    """Check the committed source, complete local lifecycle and its retained bytes."""
    index = json.loads((folder / "evidence-index.json").read_text())
    expected_assets = {"docs/" + name: digest for name, digest in hashes().items()}
    recorded = index.get("sourceHashes", {})
    if (
        index.get("schema") != "agialpha.nova-studio.evidence-index.v1"
        or index.get("commit") != commit
        or index.get("mainnetTransactions") != 0
        or index.get("profile", {}).get("chainId") != 31337
        or index.get("profile", {}).get("environment") != "local-exact-source"
        or index.get("profile", {}).get("mainnetQualification") is not False
        or any(recorded.get(name) != digest for name, digest in expected_assets.items())
        or not index.get("notPerformed")
    ):
        raise ValueError("Studio lifecycle evidence is missing, stale or not the disposable local deployment")
    # A digest map is useful only when every named source still has those bytes.
    for name, digest in recorded.items():
        path = Path(name)
        if path.is_absolute() or ".." in path.parts or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise ValueError("Unsafe Studio source inventory")
        if hashlib.sha256((ROOT / path).read_bytes()).hexdigest() != digest:
            raise ValueError("Studio evidence names different source bytes")
    inventory = index.get("artifacts", {})
    required = {
        "exact-source-report.json",
        "browser-report.json",
        "local-recovery-example.json",
        "local-work-example.json",
    }
    if not required.issubset(inventory):
        raise ValueError("Studio lifecycle artifacts are incomplete")
    for name, item in inventory.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError("Unsafe Studio artifact name")
        content = (folder / name).read_bytes()
        if item != {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}:
            raise ValueError("Studio artifact bytes no longer match their evidence index")
    report = json.loads((folder / "exact-source-report.json").read_text())
    browser = json.loads((folder / "browser-report.json").read_text())
    actions = report.get("actions", [])
    if (
        report.get("schema") != "agialpha.nova-studio.acceptance.v1"
        or report.get("passed") is not True
        or report.get("mainnetTransactions") != 0
        or report.get("compilerSizes") != [1, 2, 3, 7, 127, 128]
        or report.get("proofsVerified") != 268
        or len(actions) < 20
        or not REQUIRED_ACTIONS.issubset({entry.get("action") for entry in actions})
        or browser.get("passed") is not True
        or browser.get("mainnetTransactions") != 0
        or browser.get("pageErrors") != []
        or browser.get("nativeDeliveryVerified") is not True
        or browser.get("unwrappedNativeFetch") is not True
        or not browser.get("checks")
        or not browser.get("audits")
        or any(audit.get("violations") != [] for audit in browser["audits"])
    ):
        raise ValueError("Studio exact-source and actual browser lifecycles must both pass")
    failures = report.get("failureCases", {})
    if (
        failures.get("foreignMintEvent") != "effect-unverified"
        or failures.get("restoredEffectBarrier") is not True
        or failures.get("staleWalletPreview") is not True
        or failures.get("removedReceipt", {}).get("observationCleared") is not True
        or failures.get("removedReceipt", {}).get("resubmitted") is not False
    ):
        raise ValueError("Studio receipt interruption and reorg cases must retain their uncertainty barriers")
    seen = set()
    for entry in actions:
        receipt = entry.get("receipt", {})
        tx_hash = entry.get("hash", "")
        if (
            not HEX32.fullmatch(tx_hash)
            or tx_hash.lower() in seen
            or entry.get("status") != "finalized"
            or receipt.get("status") != "0x1"
            or receipt.get("transactionHash", "").lower() != tx_hash.lower()
            or not HEX32.fullmatch(receipt.get("blockHash", ""))
            or not re.fullmatch(r"0x[0-9a-fA-F]+", receipt.get("blockNumber", ""))
        ):
            raise ValueError("Studio lifecycle has a missing, duplicate or unsuccessful receipt")
        seen.add(tx_hash.lower())
    browser_receipts = report.get("browserReceipts", [])
    # The browser's 17 transitions omit the Node trial's revocation and two NFT transfers.
    if len(browser_receipts) < 17:
        raise ValueError("The actual browser lifecycle must retain all transaction receipts")
    for receipt in browser_receipts:
        tx_hash = receipt.get("transactionHash", "")
        if (
            not HEX32.fullmatch(tx_hash)
            or tx_hash.lower() in seen
            or receipt.get("status") != "0x1"
            or not HEX32.fullmatch(receipt.get("blockHash", ""))
            or not re.fullmatch(r"0x[0-9a-fA-F]+", receipt.get("blockNumber", ""))
        ):
            raise ValueError("Studio browser has missing, duplicate or unsuccessful transaction evidence")
        seen.add(tx_hash.lower())
    for native_key, settlement_key in (
        ("nativeDelivery", "settlement"),
        ("browserNativeDelivery", "browserSettlement"),
    ):
        native = report.get(native_key, {})
        settlement = report.get(settlement_key, {})
        if (
            native.get("signatureVerified") is not True
            or native.get("executionReplayed") is not True
            or native.get("connected") is not False
            or not HEX32.fullmatch(native.get("resultHash", ""))
            or not SHA256.fullmatch(native.get("byteSHA256", ""))
            or not HEX32.fullmatch(native.get("planRoot", ""))
            or not SHA256.fullmatch(native.get("signer", ""))
            or not isinstance(native.get("artifact"), str)
            or inventory.get(native.get("artifact"), {}).get("sha256") != native.get("byteSHA256")
            or not settlement.get("before")
            or set(settlement.get("after", {})) != set(settlement.get("before", {}))
            or set(settlement.get("delta", {})) != set(settlement.get("before", {}))
            or settlement.get("confirmed") is not True
            or settlement.get("expected") != settlement.get("delta")
        ):
            raise ValueError("Both Studio runs require verified native delivery and reconciled settlement accounting")
        for key, before in settlement["before"].items():
            if int(settlement["after"][key]) - int(before) != int(settlement["delta"][key]):
                raise ValueError("Studio settlement balance deltas do not reconcile")
    for action in ("attest", "validate"):
        actors = {entry["receipt"].get("from", "").lower() for entry in actions if entry["action"] == action}
        if len(actors) < 2 or "" in actors:
            raise ValueError("Studio lifecycle needs distinct observed reviewer wallets")
