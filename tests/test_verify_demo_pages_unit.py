# SPDX-License-Identifier: Apache-2.0
"""Unit tests for verify_demo_pages helpers."""

from __future__ import annotations

from scripts import verify_demo_pages


def test_parse_timeout_ms_reads_env() -> None:
    assert verify_demo_pages.parse_timeout_ms({"PWA_TIMEOUT_MS": "120000"}) == 120000
    assert verify_demo_pages.parse_timeout_ms({"PWA_TIMEOUT_MS": "30000"}) == 30000
    assert verify_demo_pages.parse_timeout_ms({"PWA_TIMEOUT_MS": "not-a-number"}) == 30000


def test_disclaimer_markers_include_snippet_phrases() -> None:
    markers = verify_demo_pages.load_disclaimer_markers()
    combined = " ".join(markers)
    assert "conceptual research prototype" in combined
    assert "financial advice" in combined
