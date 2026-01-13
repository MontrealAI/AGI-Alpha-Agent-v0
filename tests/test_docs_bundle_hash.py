# SPDX-License-Identifier: Apache-2.0
"""Verify SRI for the Insight bundle in the docs build."""
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
    html = (DOCS_DIR / "index.html").read_text()
    match = re.search(
        r"<script[^>]*src=['\"]([^'\"]*insight[\w.-]*\.bundle\.js(?:[?#][^'\"]+)?)['\"][^>]*>",
        html,
    )
    assert match, "insight bundle script tag missing"
    src = match.group(1).split("?", 1)[0].split("#", 1)[0]
    bundle = (DOCS_DIR / src.lstrip("./")).resolve()
    if not bundle.is_file():
        pytest.skip("insight bundle missing")
    tag = match.group(0)
    integrity = re.search(r"integrity=['\"]([^'\"]+)['\"]", tag)
    assert integrity, "integrity attribute missing"
    expected = _sha384(bundle)
    assert integrity.group(1) == expected
