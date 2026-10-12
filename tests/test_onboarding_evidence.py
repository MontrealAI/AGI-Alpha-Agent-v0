# SPDX-License-Identifier: Apache-2.0
"""Release publication must reject incomplete, stale or failed onboarding evidence."""
import pytest
from scripts.onboarding_evidence import REQUIRED_CHECKS, verify_report


def test_onboarding_evidence_requires_exact_release_and_every_journey():
    report = {
        "schema": "agialpha.onboarding.acceptance.v1",
        "passed": True,
        "commit": "a" * 40,
        "version": "1.25.0",
        "origin": "https://site/",
        "browser_errors": [],
        "checks": sorted(REQUIRED_CHECKS),
    }
    verify_report(report, "a" * 40, "1.25.0", "https://site/")
    for field, value in [
        ("passed", False),
        ("commit", "b" * 40),
        ("version", "1.24.1"),
        ("origin", "local project subpath"),
        ("browser_errors", ["TypeError"]),
    ]:
        with pytest.raises(ValueError):
            verify_report({**report, field: value}, "a" * 40, "1.25.0", "https://site/")
    for check in REQUIRED_CHECKS:
        with pytest.raises(ValueError):
            verify_report({**report, "checks": sorted(REQUIRED_CHECKS - {check})}, "a" * 40, "1.25.0", "https://site/")


def test_printable_copy_is_required_from_1_26_only():
    report = {
        "schema": "agialpha.onboarding.acceptance.v1",
        "passed": True,
        "commit": "a" * 40,
        "version": "1.26.0",
        "origin": "https://site/",
        "browser_errors": [],
        "checks": sorted(REQUIRED_CHECKS),
    }
    with pytest.raises(ValueError):
        verify_report(report, "a" * 40, "1.26.0", "https://site/")
    report["checks"].append("readable-and-printable-plan")
    verify_report(report, "a" * 40, "1.26.0", "https://site/")


@pytest.mark.parametrize(
    "missing", ["essential-readable-text", "preferences-after-initialization", "module-failure-guidance"]
)
def test_refinement_evidence_is_required_from_1_26_3(missing):
    report = {
        "schema": "agialpha.onboarding.acceptance.v1",
        "passed": True,
        "commit": "a" * 40,
        "version": "1.26.3",
        "origin": "https://site/",
        "browser_errors": [],
        "checks": sorted(
            REQUIRED_CHECKS
            | {
                "readable-and-printable-plan",
                "essential-readable-text",
                "preferences-after-initialization",
                "module-failure-guidance",
            }
        ),
    }
    verify_report(report, "a" * 40, "1.26.3", "https://site/")
    report["checks"].remove(missing)
    with pytest.raises(ValueError):
        verify_report(report, "a" * 40, "1.26.3", "https://site/")
    report["version"] = "1.26.2"
    verify_report(report, "a" * 40, "1.26.2", "https://site/")
