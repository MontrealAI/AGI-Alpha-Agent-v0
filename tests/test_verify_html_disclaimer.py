# SPDX-License-Identifier: Apache-2.0
"""Disclaimer checks follow real anchors to the exact source or published notice."""

from pathlib import Path

import pytest

from scripts import verify_html_disclaimer as disclaimer
from scripts.verify_html_disclaimer import references_disclaimer


@pytest.mark.parametrize(
    "target",
    [
        "../../DISCLAIMER_SNIPPET.md",
        "../../DISCLAIMER_SNIPPET/",
        "../../DISCLAIMER_SNIPPET",
        "../../DISCLAIMER_SNIPPET/index.html",
        "../../DISCLAIMER_SNIPPET.md#notice",
        "../../DISCLAIMER_SNIPPET.md?lang=fr#notice",
        "../../DISCLAIMER%5FSNIPPET.md",
        "https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/DISCLAIMER_SNIPPET.md",
        "https://montrealai.github.io/AGI-Alpha-Agent-v0/DISCLAIMER_SNIPPET/",
    ],
)
def test_recognizes_notice_links_at_the_research_page_depth(tmp_path: Path, target: str) -> None:
    docs = tmp_path / "docs"
    page = docs / "reports/edition/index.html"
    assert references_disclaimer(f'<a href="{target}">Notice</a>', page, docs)


@pytest.mark.parametrize(
    "markup",
    [
        "docs/DISCLAIMER_SNIPPET.md",
        "<!-- docs/DISCLAIMER_SNIPPET.md -->",
        '<script>const source = "docs/DISCLAIMER_SNIPPET.md";</script>',
        "<script>const source = '<a href=\"../../DISCLAIMER_SNIPPET.md\">Notice</a>';</script>",
        '<span data-source="docs/DISCLAIMER_SNIPPET.md">Notice</span>',
        '<a href="../DISCLAIMER_SNIPPET.md">Wrong depth</a>',
        '<a href="../../OTHER_NOTICE.md">Other file</a>',
        '<a href="https://example.invalid/docs/DISCLAIMER_SNIPPET.md">Other host</a>',
        '<a href="https://github.com/Other/Repo/blob/main/docs/DISCLAIMER_SNIPPET.md">Other repo</a>',
        '<a href="https://montrealai.github.io/Other/DISCLAIMER_SNIPPET/">Other site</a>',
        '<a href="https://[invalid/docs/DISCLAIMER_SNIPPET.md">Malformed URL</a>',
        '<a href="javascript:docs/DISCLAIMER_SNIPPET.md">Not a document</a>',
    ],
)
def test_rejects_text_mentions_and_links_to_other_resources(tmp_path: Path, markup: str) -> None:
    docs = tmp_path / "docs"
    assert not references_disclaimer(markup, docs / "reports/edition/index.html", docs)


def test_cli_still_reports_missing_notice_and_accepts_the_corrected_link(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    page = tmp_path / "docs/reports/edition/index.html"
    page.parent.mkdir(parents=True)
    page.write_text("<!-- docs/DISCLAIMER_SNIPPET.md -->", encoding="utf-8")
    monkeypatch.setattr(disclaimer, "__file__", str(tmp_path / "scripts/verify_html_disclaimer.py"))
    assert disclaimer.main() == 1
    assert "docs/reports/edition/index.html" in capsys.readouterr().err.replace("\\", "/")
    page.write_text('<a href="../../DISCLAIMER_SNIPPET.md">Notice</a>', encoding="utf-8")
    assert disclaimer.main() == 0
    assert capsys.readouterr().err == ""
