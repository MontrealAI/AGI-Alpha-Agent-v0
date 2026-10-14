# SPDX-License-Identifier: Apache-2.0
"""Bind Nova Studio browser evidence to the exact shipped source and release."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CHECKS = [
    "exact-assets",
    "no-wallet-preparation",
    "compiler-ui",
    "encrypted-recovery-roundtrip",
    "wrong-passphrase",
    "portable-recovery-kit",
    "archived-write-policy",
    "en-fr",
    "keyboard",
    "mobile",
    "axe",
    "mirrored-route",
]
EVM_CHECKS = [
    "ui-no-wallet-preparation",
    "ui-compile-seal-recover-export",
    "ui-publication-roundtrip-fixture-transport",
    "ui-explicit-wallet-selection",
    "ui-mint-receipt-and-readback",
    "ui-separate-validator-review-transactions",
    "ui-campaign-open-and-funding",
    "ui-bloom-phase-transition",
    "ui-committed-first-job-routing",
    "ui-runtime-not-connected-truth",
    "ui-recovery-kit-after-routing",
    "ui-worker-delivery-review-settlement",
    "production-profile-unchanged",
]


def hashes() -> dict[str, str]:
    """Hash all executable Studio dependencies and the generated archive profile."""
    from scripts.build_mark_wallet import build

    build(ROOT)
    docs = ROOT / "docs"
    paths = [docs / "ascension/mainnet/index.html", docs / "assets/ascension/crypto.mjs"]
    for folder in ("nova-studio", "ascension-wallet"):
        paths.extend(
            p
            for p in (docs / "assets" / folder).rglob("*")
            if p.is_file() and p.suffix in {".mjs", ".js", ".css", ".json"}
        )
    return {p.relative_to(docs).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str | None = None) -> None:
    """Reject partial, stale, or incorrectly attributed browser acceptance."""
    if (
        report.get("schema") != "agialpha.nova-studio.acceptance.v1"
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("assets") != hashes()
        or set(report.get("checks", [])) != set(CHECKS)
        or report.get("realMainnetTransactions") is not False
        or report.get("physicalWalletValidated") is not False
        or (origin is not None and report.get("origin") != origin.rstrip("/") + "/")
    ):
        raise ValueError("Nova Studio acceptance must match the exact commit, assets, version and required checks")


def verify_evm_report(report: dict[str, Any], commit: str, version: str) -> None:
    """Require actual UI transactions against the identified disposable deployment."""
    import re

    receipts = report.get("receipts")
    valid_receipts = isinstance(receipts, list) and len(receipts) >= 18
    if isinstance(receipts, list) and valid_receipts:
        valid_receipts = all(
            isinstance(item, dict)
            and re.fullmatch(r"0x[0-9a-fA-F]{64}", str(item.get("hash", "")))
            and isinstance(item.get("receipt"), dict)
            and item["receipt"].get("transactionHash") == item["hash"]
            and item["receipt"].get("status") == "0x1"
            for item in receipts
        )
        if valid_receipts:
            valid_receipts = len({item["hash"] for item in receipts}) == len(receipts)
            valid_receipts = valid_receipts and {
                "seal",
                "openReview",
                "attest",
                "open",
                "buy",
                "bloom",
                "route",
                "agentDeposit",
                "bid",
                "award",
                "submit",
                "validate",
            }.issubset({item.get("action") for item in receipts})
    settlement = report.get("settlement", {})
    if not isinstance(settlement, dict):
        settlement = {}
    accounting = settlement.get("accounting", {})
    expected_deltas = {
        "agent": "75240000000000000000",
        "validator1": "1980000000000000000",
        "validator2": "1980000000000000000",
        "funder": "0",
        "totalSupply": "-800000000000000000",
    }
    try:
        valid_accounting = (
            settlement.get("state") == "paid"
            and settlement.get("job", {}).get("state") == "4"
            and settlement.get("job", {}).get("refund") == "20000000000000000000"
            and accounting.get("verified") is True
            and all(accounting["deltas"][key] == value for key, value in expected_deltas.items())
            and all(
                int(accounting["after"][key]) - int(accounting["before"][key]) == int(value)
                for key, value in expected_deltas.items()
            )
        )
    except (KeyError, TypeError, ValueError):
        valid_accounting = False
    native = report.get("nativeDelivery", {})
    valid_native = (
        isinstance(native, dict)
        and native.get("uiHashAutofilled") is True
        and native.get("uiSubmission") is True
        and native.get("runtimeConnected") is False
        and isinstance(native.get("verification"), dict)
        and native["verification"].get("valid") is True
        and re.fullmatch(r"0x[0-9a-f]{64}", str(native["verification"].get("resultHash", "")))
        and native["verification"].get("resultHash") == settlement.get("job", {}).get("resultHash")
    )
    if (
        report.get("schema") != "agialpha.nova-studio.evm-browser.v1"
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("sourceAssets") != hashes()
        or set(report.get("checks", [])) != set(EVM_CHECKS)
        or report.get("exactSource") is not True
        or report.get("chainId") != 31337
        or not re.fullmatch(r"[0-9a-f]{64}", str(report.get("profileHash", "")))
        or report.get("realMainnetTransactions") is not False
        or report.get("physicalWalletValidated") is not False
        or report.get("realStorageProviderValidated") is not False
        or not valid_receipts
        or not valid_accounting
        or not valid_native
    ):
        raise ValueError(
            "Nova Studio EVM browser acceptance requires the exact source, profile and full observed UI lifecycle"
        )
