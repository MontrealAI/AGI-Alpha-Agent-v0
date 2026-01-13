# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import re
from pathlib import Path

from scripts.check_insight_sri import _hash


def test_insight_bundle_sri() -> None:
    repo = Path(__file__).resolve().parents[1]
    insight_dir = repo / "docs" / "alpha_agi_insight_v1"
    html = insight_dir / "index.html"

    text = html.read_text()
    match = re.search(
        r"<script[^>]*src=['\"]([^'\"]*insight[\w.-]*\.bundle\.js(?:[?#][^'\"]+)?)['\"][^>]*>",
        text,
    )
    assert match, "script tag for insight bundle missing"
    src = match.group(1).split("?", 1)[0].split("#", 1)[0]
    bundle = (insight_dir / src.lstrip("./")).resolve()
    assert bundle.is_file(), "insight bundle missing"
    expected = _hash(bundle)
    sri = re.search(r"integrity=['\"]([^'\"]+)['\"]", match.group(0))
    assert sri, "integrity attribute missing"
    assert sri.group(1) == expected
