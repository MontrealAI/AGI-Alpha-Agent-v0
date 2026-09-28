# SPDX-License-Identifier: Apache-2.0
"""Bind public Insight acceptance to exact release assets and native decisions."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import evaluate, read_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agialpha.discovery.acceptance.v1"
ASSETS = (
    "alpha_agi_insight_v0/index.html",
    "alpha_agi_insight_v0/research.html",
    "alpha_factory_v1/demos/alpha_agi_insight_v0/index.html",
    "alpha_factory_v1/demos/alpha_agi_insight_v0/research.html",
    "alpha_agi_insight_v0/assets/script.js",
    "alpha_agi_insight_v0/assets/logs.json",
    "alpha_agi_insight_v0/assets/preview.svg",
    "assets/compounding/engine.mjs",
    *(
        f"assets/discovery/{name}"
        for name in ("engine.mjs", "constants.mjs", "workbench.mjs", "workbench.css", "scenarios.json", "preview.svg")
    ),
)
CHECKS = frozenset(
    {
        "all-five-cases",
        "downloaded-dossier-native-replay",
        "six-file-zip-exact-bytes",
        "input-bound-ascension-jobs",
        "review-capacity-recalculation",
        "stale-exports-disabled",
        "edited-json-requires-apply",
        "rehash-forgery-rejected",
        "duplicate-json-rejected",
        "oversized-invalid-utf8-nonfinite-rejected",
        "explicit-draft-recovery",
        "untrusted-text-is-text",
        "canonical-and-mirrored-routes",
        "mobile-no-overflow",
        "keyboard-control-order",
        "axe-wcag-a-aa-no-violations",
        "offline-recalculation",
        "exact-current-assets",
        "original-replay-preserved",
    }
)


def asset_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest() for name in ASSETS}


def expected_cases() -> list[dict[str, str]]:
    cases = read_json(ROOT / "alpha_factory_v1/demos/alpha_agi_insight_v0/scenarios.json")
    return [
        {"id": case["id"], "sha256": (report := evaluate(case))["sha256"], "status": report["result"]["status"]}
        for case in cases
    ]


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    checks = report.get("checks")
    if (
        report.get("schema") != SCHEMA
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("origin") != origin
        or report.get("browser_errors") != []
        or report.get("http_failures") != []
        or not isinstance(checks, list)
        or not all(isinstance(item, str) for item in checks)
        or not CHECKS.issubset(checks)
        or report.get("assets") != asset_hashes()
        or report.get("cases") != expected_cases()
    ):
        raise ValueError(
            "Insight discovery must pass every public journey for the exact release assets and native decisions"
        )
