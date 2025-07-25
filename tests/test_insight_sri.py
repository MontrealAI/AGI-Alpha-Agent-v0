# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path


def test_insight_bundle_sri() -> None:
    repo = Path(__file__).resolve().parents[1]
    insight_dir = repo / "docs" / "alpha_agi_insight_v1"
    bundle = insight_dir / "insight.bundle.js"
    html = insight_dir / "index.html"

    digest = hashlib.sha384(bundle.read_bytes()).digest()
    expected = "sha384-" + base64.b64encode(digest).decode()

    text = html.read_text()
    match = re.search(r"<script[^>]*src=['\"]insight.bundle.js['\"][^>]*>", text)
    assert match, "script tag for insight.bundle.js missing"
    sri = re.search(r"integrity=['\"]([^'\"]+)['\"]", match.group(0))
    assert sri, "integrity attribute missing"
    assert sri.group(1) == expected
