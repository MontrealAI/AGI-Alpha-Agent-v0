# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the demo page verification helpers."""
from __future__ import annotations

import scripts.verify_demo_pages as verify_demo_pages


def test_timeout_ms_from_env(monkeypatch) -> None:
    """Timeout should read from PWA_TIMEOUT_MS."""
    monkeypatch.setenv("PWA_TIMEOUT_MS", "45000")
    assert verify_demo_pages.get_timeout_ms() == 45000


def test_timeout_ms_invalid_falls_back(monkeypatch) -> None:
    """Invalid timeouts should fall back to the default."""
    monkeypatch.setenv("PWA_TIMEOUT_MS", "not-a-number")
    assert verify_demo_pages.get_timeout_ms() == verify_demo_pages.DEFAULT_TIMEOUT_MS


def test_accept_patterns_include_expected_tokens() -> None:
    """Ensure disclaimer accept patterns include common confirmation tokens."""
    expected_tokens = {"accept", "continue"}
    assert expected_tokens.issubset(set(verify_demo_pages.ACCEPT_TEXT_PATTERNS))
