# SPDX-License-Identifier: Apache-2.0
"""Bind Business 3 public acceptance to exact source, cases and release assets."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import read_json, solve

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agialpha.business3.acceptance.v1"
ASSETS = (
    "alpha_agi_business_3_v1/index.html",
    "assets/compounding/engine.mjs",
    "alpha_factory_v1/demos/alpha_agi_business_3_v1/index.html",
    "alpha_agi_business_3_v1/assets/script.js",
    "alpha_agi_business_3_v1/assets/style.css",
    "alpha_agi_business_3_v1/assets/logs.json",
    "alpha_agi_business_3_v1/assets/preview.svg",
    "alpha_factory_v1/demos/alpha_agi_business_3_v1/assets/script.js",
    "assets/replay_chart.js",
    "assets/pyodide_demo.js",
    *(
        f"assets/business3/{name}"
        for name in ("studio.css", "studio.mjs", "engine.mjs", "worker.mjs", "artifacts.mjs", "scenarios.json")
    ),
)
CHECKS = frozenset(
    {
        "all-five-cases",
        "downloaded-dossier-python-replay",
        "seven-file-zip-exact-bytes",
        "ascension-jobs-compile",
        "changed-inputs-disable-exports",
        "zero-budget-holds",
        "forged-approval-rejected",
        "duplicate-json-rejected",
        "oversized-file-rejected",
        "worker-cancellation-and-retry",
        "explicit-draft-recovery",
        "untrusted-text-is-text",
        "canonical-and-mirrored-routes",
        "mobile-no-overflow",
        "axe-wcag-a-aa-no-violations",
        "offline-recalculation",
        "exact-current-assets",
        "candidate-chart-exact-values",
        "original-replay-preserved",
        "research-section-responsive",
    }
)


def asset_hashes() -> dict[str, str]:
    """Hash every entry point, module, stylesheet and canonical scenario fixture."""
    return {name: hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest() for name in ASSETS}


def expected_cases() -> list[dict[str, str]]:
    """Independently recompute the five shipped cases without browser dependencies."""
    cases = read_json(ROOT / "alpha_factory_v1/demos/alpha_agi_business_3_v1/scenarios.json")
    results = []
    for case in cases:
        report = solve(case)
        results.append({"id": case["id"], "sha256": report["sha256"], "status": report["result"]["status"]})
    return results


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Reject missing, stale, altered or incomplete public release acceptance."""
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
        raise ValueError("Business 3 must pass every public journey for the exact release assets and computed cases")
