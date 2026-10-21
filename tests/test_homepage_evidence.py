# SPDX-License-Identifier: Apache-2.0
"""Reject stale, incomplete or failed public homepage acceptance before publication."""

from copy import deepcopy
import hashlib
import json

import pytest

from scripts.homepage_evidence import (
    ASSETS,
    ECOSYSTEM_CHECKS,
    ECOSYSTEM_LAYOUTS,
    PAPER_ASSETS,
    REQUIRED_CHECKS,
    REQUIRED_LAYOUTS,
    ROOT,
    asset_hashes,
    verify_report,
)


@pytest.fixture
def report():
    return {
        "schema": "agialpha.homepage.acceptance.v1",
        "passed": True,
        "commit": "a" * 40,
        "version": "1.26.2",
        "origin": "https://site/",
        "browser_version": "Chromium fixture",
        "browser_errors": [],
        "checks": sorted(REQUIRED_CHECKS),
        "assets": asset_hashes(),
        "accessibility": [
            {"width": width, "language": language, "large_text": large, "scope": scope, "violations": []}
            for width, language, large in REQUIRED_LAYOUTS
            for scope in ("welcome", "document")
        ],
        "layouts": [
            {"width": width, "language": language, "large_text": large, "controls": [{"width": 100, "height": 44}]}
            for width, language, large in REQUIRED_LAYOUTS
        ],
    }


def verify(report):
    verify_report(report, "a" * 40, "1.26.2", "https://site/")


def test_complete_bound_homepage_evidence_is_accepted(report):
    verify(report)


def test_direct_plan_entry_is_required_from_1_26_3(report):
    verify(report)
    report["version"] = "1.26.3"
    with pytest.raises(ValueError):
        verify_report(report, "a" * 40, "1.26.3", "https://site/")
    report["checks"].append("direct-plan-entry")
    verify_report(report, "a" * 40, "1.26.3", "https://site/")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema", "other"),
        ("passed", False),
        ("commit", "b" * 40),
        ("version", "1.26.1"),
        ("origin", "local project subpath"),
        ("browser_version", ""),
        ("browser_errors", ["TypeError"]),
    ],
)
def test_homepage_evidence_rejects_stale_or_failed_journeys(report, field, value):
    with pytest.raises(ValueError):
        verify({**report, field: value})


@pytest.mark.parametrize("missing", sorted(REQUIRED_CHECKS))
def test_homepage_evidence_requires_every_journey(report, missing):
    report["checks"].remove(missing)
    with pytest.raises(ValueError):
        verify(report)


def test_homepage_evidence_rejects_missing_or_failed_accessibility_layouts(report):
    incomplete = deepcopy(report)
    incomplete["accessibility"].pop()
    with pytest.raises(ValueError):
        verify(incomplete)
    report["accessibility"][0]["violations"] = [{"id": "color-contrast"}]
    with pytest.raises(ValueError):
        verify(report)


@pytest.mark.parametrize("controls", [[], [{"width": 100, "height": 30}], [{"width": 30, "height": 100}]])
def test_homepage_evidence_rejects_missing_or_small_controls(report, controls):
    report["layouts"][0]["controls"] = controls
    with pytest.raises(ValueError):
        verify(report)


def test_homepage_evidence_requires_all_mobile_and_large_text_measurements(report):
    report["layouts"].pop()
    with pytest.raises(ValueError):
        verify(report)


@pytest.mark.parametrize("asset", ASSETS)
def test_homepage_evidence_rejects_stale_or_missing_asset_bytes(report, asset):
    stale = deepcopy(report)
    stale["assets"][asset] = "0" * 64
    with pytest.raises(ValueError):
        verify(stale)
    del report["assets"][asset]
    with pytest.raises(ValueError):
        verify(report)


def paired_report(report):
    """Represent the required public directory evidence without a browser fixture."""
    report = deepcopy(report)
    report["version"] = "1.27.2"
    report["checks"] += ["direct-plan-entry", "paired-system-guide"]
    directory = json.loads((ROOT / "docs/assets/ecosystem/contracts.json").read_text())
    report["ecosystem"] = {
        "schema": "agialpha.ecosystem.acceptance.v1",
        "passed": True,
        "checks": sorted(ECOSYSTEM_CHECKS),
        "browser_errors": [],
        "addresses": sorted(c["address"] for s in ("alpha", "jobs") for c in directory[s]["contracts"]),
        "layouts": [
            {
                "width": width,
                "language": language,
                "large_text": large,
                "controls": [{"width": 100, "height": 44}],
                "violations": [],
            }
            for width, language, large in ECOSYSTEM_LAYOUTS
        ],
    }
    return report


def test_paired_system_evidence_is_required_from_1_27_2(report):
    complete = paired_report(report)
    verify_report(complete, "a" * 40, "1.27.2", "https://site/")
    del complete["ecosystem"]
    with pytest.raises(ValueError):
        verify_report(complete, "a" * 40, "1.27.2", "https://site/")


@pytest.mark.parametrize("missing", ["address", "layout", "clipboard", "accessible_controls", "clean_audit"])
def test_paired_system_evidence_rejects_missing_directory_or_accessibility_checks(report, missing):
    report = paired_report(report)
    paired = report["ecosystem"]
    if missing == "address":
        paired["addresses"].pop()
    elif missing == "layout":
        paired["layouts"].pop()
    elif missing == "clipboard":
        paired["checks"].remove("clipboard-denial-fallback")
    elif missing == "accessible_controls":
        paired["layouts"][0]["controls"] = [{"width": 100, "height": 20}]
    else:
        paired["layouts"][0]["violations"] = [{"id": "color-contrast"}]
    with pytest.raises(ValueError):
        verify_report(report, "a" * 40, "1.27.2", "https://site/")


def featured_paper_report(report, version="1.37.1"):
    report = paired_report(report)
    report["version"] = version
    report["checks"].append("original-paper-bytes")
    report["paper_assets"] = {
        name: hashlib.sha256((ROOT / "docs" / name).read_bytes()).hexdigest() for name in PAPER_ASSETS
    }
    return report


@pytest.mark.parametrize("version", ["1.37.1", "1.38.0"])
def test_featured_paper_evidence_accepts_exact_originals(report, version):
    from scripts.finalize_pages_release import verify_homepage_report

    complete = featured_paper_report(report, version)
    assert complete["paper_assets"] == PAPER_ASSETS
    verify_homepage_report(complete, "a" * 40, version, "https://site/")


def test_pre_feature_release_keeps_legacy_report_compatibility(report):
    legacy = paired_report(report)
    legacy["version"] = "1.37.0"
    verify_report(legacy, "a" * 40, "1.37.0", "https://site/")
    legacy["version"] = "1.37.1"
    with pytest.raises(ValueError, match="original PDF digests"):
        verify_report(legacy, "a" * 40, "1.37.1", "https://site/")


@pytest.mark.parametrize("damage", ["marker", "map", "null", "invalid", "extra"])
def test_featured_paper_evidence_rejects_incomplete_or_invalid_records(report, damage):
    from scripts.finalize_pages_release import verify_homepage_report

    complete = featured_paper_report(report)
    if damage == "marker":
        complete["checks"].remove("original-paper-bytes")
    elif damage == "map":
        del complete["paper_assets"]
    elif damage == "null":
        complete["paper_assets"] = None
    elif damage == "invalid":
        complete["paper_assets"] = list(PAPER_ASSETS)
    else:
        complete["paper_assets"]["unexpected.pdf"] = "0" * 64
    with pytest.raises(ValueError):
        verify_homepage_report(complete, "a" * 40, "1.37.1", "https://site/")


@pytest.mark.parametrize("filename", PAPER_ASSETS)
@pytest.mark.parametrize("damage", ["missing", "stale", "invalid"])
def test_featured_paper_evidence_rejects_each_missing_or_mismatched_digest(report, filename, damage):
    complete = featured_paper_report(report)
    if damage == "missing":
        del complete["paper_assets"][filename]
    else:
        complete["paper_assets"][filename] = "0" * 64 if damage == "stale" else {"sha256": PAPER_ASSETS[filename]}
    with pytest.raises(ValueError, match="original PDF digests"):
        verify_report(complete, "a" * 40, "1.37.1", "https://site/")
