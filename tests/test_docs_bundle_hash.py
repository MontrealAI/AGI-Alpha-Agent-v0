# SPDX-License-Identifier: Apache-2.0
"""Verify SRI for insight.bundle.js in the docs build."""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path

import pytest

DOCS_DIR = Path("docs/alpha_agi_insight_v1")


def _sha384(path: Path) -> str:
    digest = hashlib.sha384(path.read_bytes()).digest()
    return "sha384-" + base64.b64encode(digest).decode()


def test_docs_bundle_integrity() -> None:
    bundle = DOCS_DIR / "insight.bundle.js"
    if not bundle.is_file():
        pytest.skip("insight.bundle.js missing")
    html = (DOCS_DIR / "index.html").read_text()
    match = re.search(r"<script[^>]*src=['\"]insight.bundle.js['\"][^>]*>", html)
    assert match, "insight.bundle.js script tag missing"
    tag = match.group(0)
    integrity = re.search(r"integrity=['\"]([^'\"]+)['\"]", tag)
    assert integrity, "integrity attribute missing"
    expected = _sha384(bundle)
    assert integrity.group(1) == expected
