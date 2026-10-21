# SPDX-License-Identifier: Apache-2.0
"""Prominent research links preserve the original papers and current start paths."""

import hashlib
from pathlib import Path
import re

import pytest

from scripts.homepage_evidence import PAPER_ASSETS

ROOT = Path(__file__).resolve().parents[1]
PAPERS = {
    "Transformational_Intelligence.pdf": "1f95db3b087d8dd0712012d34ba700d7dd2e1382",
    "Out_Learn.pdf": "400513e691c6045112ad211b6153f80480eb7c2f",
    "Out_Think.pdf": "1fdb6a3b0e15d9cf57edbfde2d5ad156eabde2b6",
    "Out_Strategise.pdf": "0e89969bc920eda19c366462b69a393b018206d1",
    "Out_Execute.pdf": "e7c2c61307a5bfe2136bf2a61c875208252ebca6",
    "Out_Evolve.pdf": "a2a333187388e961a91c2fd67696adc09641c3ed",
}


def test_six_paper_inventory_matches_release_evidence() -> None:
    assert len(PAPERS) == 6
    assert set(PAPERS) == set(PAPER_ASSETS)
    source = (ROOT / "docs/Out_Execute.tex").read_bytes()
    assert hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest() == (
        "19b468ae269e338adfb49d9fadfe0327a7fa026d"
    )


@pytest.mark.parametrize("filename,original_blob", PAPERS.items())
def test_original_pdf_bytes_and_reading_links(filename: str, original_blob: str) -> None:
    data = (ROOT / "docs" / filename).read_bytes()
    assert data.startswith(b"%PDF-")
    assert hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() == original_blob
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    section = readme.split("<!-- featured-research-papers -->", 1)[1].split("<!-- /featured-research-papers -->", 1)[0]
    assert f"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/docs/{filename}" in section
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    assert f'href="{filename}" type="application/pdf" hreflang="en"' in section
    assert "<script" not in section and "<iframe" not in section


def test_feature_follows_free_start_and_precedes_other_journeys() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.index("**[Start the flagship") < readme.index("<!-- featured-research-papers -->")
    assert readme.index("<!-- /featured-research-papers -->") < readme.index("## Choose your next step")
    assert readme.index("<!-- /featured-research-papers -->") < readme.index("<!-- /current-entrypoints -->")
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert homepage.index('id="home"') < homepage.index('id="papers"') < homepage.index('id="alpha-journey"')
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    assert [section.index(filename) for filename in PAPERS] == sorted(section.index(filename) for filename in PAPERS)
    assert section.count('class="paper-card paper-featured"') == 1
    assert section.count('class="paper-card"') == len(PAPER_ASSETS) - 1
    assert 'href="#papers" data-home-key="nav-papers"' in homepage


def test_paper_copy_has_french_equivalents_and_declared_scope() -> None:
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    french = (ROOT / "docs/assets/portal/welcome.mjs").read_text(encoding="utf-8")
    for key in re.findall(r'data-home-key="([^"]+)"', section):
        assert re.search(rf'"{re.escape(key)}":\s*"[^"]+"', french), key
    assert "Research proposals and bounded studies" in section
    assert "not claims of general autonomous capability or physical deployment" in section
    assert 'class="paper-subtitle" lang="en"' in section
    assert section.count('class="sr-only" lang="en"') == len(PAPER_ASSETS)
    assert "finite synthetic studies" in section


def test_feature_title_wraps_at_syllables_and_context_stays_accessible() -> None:
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert '<span class="paper-title-word">TRANS&shy;FORMA&shy;TIONAL</span> ' in homepage
    assert '<span class="paper-title-word">INTEL&shy;LIGENCE</span>' in homepage
    css = (ROOT / "docs/assets/portal/welcome.css").read_text(encoding="utf-8")
    title = css.split(".paper-featured h3 {", 1)[1].split("}", 1)[0]
    assert "hyphens: manual" in title and "overflow-wrap: normal" in title
    assert "max-width" not in title
    word = css.split(".paper-featured .paper-title-word {", 1)[1].split("}", 1)[0]
    assert "display: block" in word
    featured = css.split(".paper-featured {", 1)[1].split("}", 1)[0]
    assert "grid-row: span var(--paper-companion-count, 3)" in featured
    context = css.split(".paper-link .sr-only {", 1)[1].split("}", 1)[0]
    assert "clip-path: inset(50%)" in context and "position: absolute" in context
    assert "display: none" not in context and "visibility: hidden" not in context
