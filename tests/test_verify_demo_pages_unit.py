from __future__ import annotations

import os

import scripts.verify_demo_pages as verify_demo_pages


def test_parse_timeout_ms_uses_env(monkeypatch):
    monkeypatch.setenv("PWA_TIMEOUT_MS", "45000")
    timeout = verify_demo_pages.parse_timeout_ms(os.environ.get("PWA_TIMEOUT_MS"))
    assert timeout == 45000


def test_disclaimer_accept_selectors_include_expected_terms():
    selectors = " ".join(verify_demo_pages.DISCLAIMER_ACCEPT_SELECTORS)
    assert "Accept" in selectors
    assert "Continue" in selectors
    assert "I Understand" in selectors
