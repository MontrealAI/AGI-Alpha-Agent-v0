# SPDX-License-Identifier: Apache-2.0
"""Reject stale, incomplete or failed public homepage acceptance before publication."""

from copy import deepcopy

import pytest

from scripts.homepage_evidence import ASSETS, REQUIRED_CHECKS, REQUIRED_LAYOUTS, asset_hashes, verify_report


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
