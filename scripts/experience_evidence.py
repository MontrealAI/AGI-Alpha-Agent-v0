# SPDX-License-Identifier: Apache-2.0
"""Bind public Experience Lab acceptance to exact release assets and native runs."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from alpha_factory_v1.demos.era_of_experience.lab import evaluate, read_json

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "agialpha.experience.acceptance.v1"
ASSETS = (
    "era_of_experience/index.html",
    "era_of_experience/research.html",
    "alpha_factory_v1/demos/era_of_experience/index.html",
    "alpha_factory_v1/demos/era_of_experience/research.html",
    "era_of_experience/assets/script.js",
    "era_of_experience/assets/logs.json",
    "era_of_experience/assets/preview.svg",
    "assets/discovery/engine.mjs",
    "assets/discovery/constants.mjs",
    "assets/compounding/engine.mjs",
    "assets/ascension/crypto.mjs",
    *(
        f"assets/experience/{name}"
        for name in ("engine.mjs", "constants.mjs", "lab.mjs", "lab.css", "scenarios.json", "preview.svg")
    ),
)
CHECKS = frozenset(
    {
        "all-four-environments",
        "downloaded-run-native-replay",
        "six-file-zip-exact-bytes",
        "input-bound-review-jobs",
        "reward-trap-blocked",
        "settings-recalculation",
        "training-episode-inspection",
        "stale-exports-disabled",
        "edited-json-requires-apply",
        "rehashed-forgery-rejected",
        "invalid-inputs-rejected",
        "explicit-settings-recovery",
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
    cases = read_json(ROOT / "alpha_factory_v1/demos/era_of_experience/scenarios.json")
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
        raise ValueError("Experience Lab must pass every public journey for the exact release assets and native runs")
