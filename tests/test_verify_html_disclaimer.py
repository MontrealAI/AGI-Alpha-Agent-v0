# SPDX-License-Identifier: Apache-2.0
"""Validate real nested notice links without changing catalogued guide bytes."""

from pathlib import Path

import pytest

from scripts.verify_html_disclaimer import has_disclaimer


@pytest.mark.parametrize("suffix", ["", "?lang=fr#notice"])
def test_nested_anchor_resolves_to_the_existing_notice(tmp_path: Path, suffix: str) -> None:
    docs = tmp_path / "docs"
    page = docs / "reports" / "research-foundry-v2" / "index.html"
    text = f'<footer><a href="../../DISCLAIMER_SNIPPET.md{suffix}">Research prototype notice</a></footer>'
    assert has_disclaimer(text, page, docs)


@pytest.mark.parametrize(
    "text",
    [
        '<a href="../DISCLAIMER_SNIPPET.md">Wrong directory</a>',
        '<a href="https://elsewhere.invalid/DISCLAIMER_SNIPPET.md">External notice</a>',
        '<a href="../../OTHER_NOTICE.md">Wrong target</a>',
        '<p>../../DISCLAIMER_SNIPPET.md</p>',
    ],
)
def test_non_notice_targets_do_not_satisfy_the_check(tmp_path: Path, text: str) -> None:
    docs = tmp_path / "docs"
    page = docs / "reports" / "research-foundry-v2" / "index.html"
    assert not has_disclaimer(text, page, docs)


def test_existing_documented_marker_remains_accepted(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    assert has_disclaimer("See docs/DISCLAIMER_SNIPPET.md", docs / "index.html", docs)
