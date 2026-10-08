# SPDX-License-Identifier: Apache-2.0
"""Validate the exact SUCCESSOR public journey required for release publication."""

from __future__ import annotations

from typing import Any

SCHEMA = "agialpha.successor.acceptance.v1"
REQUIRED_CHECKS = {
    "lifecycle",
    "changed-input-stale",
    "cancel-retry",
    "bilingual",
    "narrow-mobile",
    "native-roundtrip",
    "malformed-import",
    "cache-upgrade",
    "offline-cached",
    "mirrored-route",
}


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Require actual matching-site acceptance without interpreting it as external proof."""
    if (
        report.get("schema") != SCHEMA
        or report.get("passed") is not True
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("origin") != origin
        or report.get("browser_errors") != []
        or not isinstance(report.get("checks"), list)
        or not all(isinstance(item, str) for item in report["checks"])
        or not REQUIRED_CHECKS.issubset(report["checks"])
    ):
        raise ValueError("SUCCESSOR must pass every required journey for the exact public release")
