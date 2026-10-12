# SPDX-License-Identifier: Apache-2.0
"""Bind onboarding acceptance evidence without importing browser dependencies."""
from __future__ import annotations

from typing import Any

REQUIRED_CHECKS = {
    "homepage-entry",
    "english-and-french",
    "review-before-export",
    "changed-inputs-clear-review",
    "exact-downloads",
    "invalid-input-recovery",
    "empty-plan",
    "user-text-escaped",
    "keyboard-focus",
    "mobile-and-larger-text",
    "axe-no-violations",
    "no-task-network-or-storage",
    "no-javascript-guidance",
}


def verify_report(report: dict[str, Any], commit: str, version: str, origin: str) -> None:
    """Bind all required onboarding checks to the release source and public origin."""
    required = set(REQUIRED_CHECKS)
    if tuple(int(part) for part in version.split(".")) >= (1, 26, 0):
        required.add("readable-and-printable-plan")
    if tuple(int(part) for part in version.split(".")) >= (1, 26, 3):
        required.update({"essential-readable-text", "preferences-after-initialization", "module-failure-guidance"})
    if (
        report.get("schema") != "agialpha.onboarding.acceptance.v1"
        or report.get("commit") != commit
        or report.get("version") != version
        or report.get("origin") != origin
        or report.get("passed") is not True
        or report.get("browser_errors") != []
        or not required.issubset(report.get("checks", []))
    ):
        raise ValueError("Onboarding must pass every required journey on the exact release and origin")
