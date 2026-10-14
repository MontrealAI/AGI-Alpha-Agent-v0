# SPDX-License-Identifier: Apache-2.0
"""Bind MARK browser acceptance to exact shipped source and release identity."""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    ("ascension-protocol/mainnet/index.html",)
    + tuple(
        "assets/ascension-wallet/" + name
        for name in (
            "app.mjs",
            "client.mjs",
            "protocol.mjs",
            "recovery.mjs",
            "qualified-profiles.mjs",
            "qualification.mjs",
            "session.mjs",
            "wallet.css",
            "profile.json",
        )
    )
    + ("assets/ascension/crypto.mjs", "assets/successor/engine.mjs")
    + ("ascension/mainnet/index.html",)
    + tuple(
        "assets/nova-studio/" + name
        for name in (
            "app.mjs",
            "chain.mjs",
            "native-delivery.mjs",
            "package.mjs",
            "plan.mjs",
            "storage.mjs",
            "studio.css",
            "workflow.mjs",
            "cycle.mjs",
            "cycle-ui.mjs",
            "runtime.mjs",
            "reuse.mjs",
            "ledger.mjs",
            "vendor/ethers-6.17.0.mjs",
        )
    )
)
CHECKS = [
    "exact-assets",
    "inspection-no-permission",
    "blocked-funding",
    "explicit-signing",
    "declined-signing",
    "reload-recovery",
    "journal-import",
    "same-browser-lock",
    "replacement-finality",
    "reorg",
    "malicious-metadata",
    "keyboard",
    "en-fr",
    "mobile",
    "axe",
]


def hashes() -> dict[str, str]:
    """Hash the generated deployment profile and the wallet source."""
    from scripts.build_mark_wallet import build

    build(ROOT)
    return {name: hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest() for name in ASSETS}


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str | None = None) -> None:
    """Reject missing, partial, stale or differently served acceptance evidence."""
    if (
        report.get("schema") != "agialpha.mark-wallet.acceptance.v1"
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("assets") != hashes()
        or set(report.get("checks", [])) != set(CHECKS)
        or report.get("realMainnetTransactions") is not False
        or report.get("physicalWalletValidated") is not False
        or (origin is not None and report.get("origin") != origin.rstrip("/") + "/")
    ):
        raise ValueError("MARK wallet acceptance must match the exact commit, version, assets and complete checks")
