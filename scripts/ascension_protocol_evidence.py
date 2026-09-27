# SPDX-License-Identifier: Apache-2.0
"""Pin public protocol acceptance to the release commit and exact shipped assets."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agialpha.ascension.protocol.acceptance.v1"
ASSETS = (
    "ascension-protocol/index.html",
    "alpha_factory_v1/demos/ascension-protocol/index.html",
    "assets/ascension-protocol/desk.mjs",
    "assets/ascension-protocol/desk.css",
    "assets/ascension-protocol/receipt.json",
    "assets/ascension/engine.mjs",
)
CHECKS = frozenset(
    {
        "bonding-curve-integer-arithmetic",
        "reputation-weighted-auction",
        "validation-receipt-filter",
        "exact-evidence-download",
        "exact-published-assets",
        "canonical-and-mirrored-routes",
        "offline-canonical-and-mirror",
        "mobile-no-overflow",
        "keyboard-controls",
        "axe-wcag-a-aa-no-violations",
    }
)


def asset_hashes() -> dict[str, str]:
    """Hash the current source files, including both real HTML entry points."""
    return {name: hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest() for name in ASSETS}


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Require complete acceptance of the intended release before publication."""
    if (
        report.get("schema") != SCHEMA
        or report.get("passed") is not True
        or report.get("origin") != origin
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("browser_errors") != []
        or report.get("http_failures") != []
        or not CHECKS.issubset(report.get("checks", []))
        or report.get("asset_sha256") != asset_hashes()
    ):
        raise ValueError("Ascension protocol must pass every journey against the exact packaged commit and assets")
