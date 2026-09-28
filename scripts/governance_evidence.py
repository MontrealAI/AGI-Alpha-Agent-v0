# SPDX-License-Identifier: Apache-2.0
"""Bind public governance acceptance to exact release assets and native decisions."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from alpha_factory_v1.demos.solving_agi_governance.workbench import evaluate, read_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agialpha.governance.acceptance.v1"
ASSETS = (
    "solving_agi_governance/index.html",
    "alpha_factory_v1/demos/solving_agi_governance/index.html",
    "solving_agi_governance/assets/script.js",
    "solving_agi_governance/assets/logs.json",
    "solving_agi_governance/assets/preview.svg",
    "assets/compounding/engine.mjs",
    "assets/replay_chart.js",
    "assets/pyodide_demo.js",
    *(
        f"assets/governance/{name}"
        for name in ("engine.mjs", "constants.mjs", "workbench.mjs", "workbench.css", "scenarios.json")
    ),
)
CHECKS = frozenset(
    {
        "all-five-cases",
        "downloaded-dossier-native-replay",
        "five-file-zip-exact-bytes",
        "input-bound-ascension-jobs",
        "stale-exports-disabled",
        "edited-json-requires-apply",
        "rehash-forgery-rejected",
        "duplicate-json-rejected",
        "oversized-and-invalid-utf8-rejected",
        "sub-femto-risk-rejected",
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
    cases = read_json(ROOT / "alpha_factory_v1/demos/solving_agi_governance/scenarios.json")
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
        raise ValueError("Governance must pass every public journey for the exact release assets and native decisions")
