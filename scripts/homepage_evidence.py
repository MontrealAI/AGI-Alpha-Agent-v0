# SPDX-License-Identifier: Apache-2.0
"""Bind homepage acceptance to a tested release without browser dependencies."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ASSETS = (
    "index.html",
    "assets/portal/welcome.css",
    "assets/portal/welcome.mjs",
    "start/index.html",
    "assets/start/start.css",
    "assets/start/start.mjs",
    "successor/play/index.html",
)

REQUIRED_CHECKS = {
    "exact-current-assets",
    "clear-first-step",
    "three-visible-steps",
    "readable-default-text",
    "working-faq",
    "keyboard-skip",
    "english-and-french",
    "larger-text",
    "guided-plan-preferences",
    "reading-preferences-survive-reload",
    "reading-preferences-follow-history",
    "shareable-reading-preferences",
    "mobile-reflow",
    "large-touch-targets",
    "axe-no-violations",
    "reduced-motion",
    "no-javascript-content-and-navigation",
}
REQUIRED_LAYOUTS = {(1440, "en", False), (390, "en", False), (320, "fr", False), (320, "fr", True)}


def asset_hashes(site: Path = ROOT / "docs") -> dict[str, str]:
    """Hash the generated entry pages and the changed welcome/first-plan assets."""
    return {name: hashlib.sha256((site / name).read_bytes()).hexdigest() for name in ASSETS}


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Require successful exact-origin journeys and every measured accessibility layout."""
    required_checks = set(REQUIRED_CHECKS)
    if tuple(int(part) for part in version.split(".")) >= (1, 26, 3):
        required_checks.add("direct-plan-entry")
    if (
        report.get("schema") != "agialpha.homepage.acceptance.v1"
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("origin") != origin
        or report.get("passed") is not True
        or report.get("browser_errors") != []
        or not report.get("browser_version")
        or not required_checks.issubset(report.get("checks", []))
        or report.get("assets") != asset_hashes()
    ):
        raise ValueError("Homepage must pass every required journey on the exact release and origin")
    audits = report.get("accessibility", [])
    measured = {(item.get("width"), item.get("language"), item.get("large_text"), item.get("scope")) for item in audits}
    required = {(*layout, scope) for layout in REQUIRED_LAYOUTS for scope in ("welcome", "document")}
    if not required.issubset(measured) or any(item.get("violations") != [] for item in audits):
        raise ValueError("Homepage requires clean welcome and document accessibility audits at every layout")
    layouts = report.get("layouts", [])
    if not REQUIRED_LAYOUTS.issubset(
        {(item.get("width"), item.get("language"), item.get("large_text")) for item in layouts}
    ):
        raise ValueError("Homepage requires desktop, mobile and larger-text layout measurements")
    for layout in layouts:
        controls = layout.get("controls", [])
        if not controls or any(min(control.get("width", 0), control.get("height", 0)) < 43.5 for control in controls):
            raise ValueError("Homepage welcome controls must measure at least 44 × 44 CSS pixels")
