# SPDX-License-Identifier: Apache-2.0
"""Prominent research links preserve the original papers and current start paths."""

import hashlib
from pathlib import Path
import re

import pytest

from scripts.homepage_evidence import PAPER_ASSETS
from scripts.research_papers import load_catalog, verify_files

ROOT = Path(__file__).resolve().parents[1]
PAPERS = {
    "Transformational_Intelligence.pdf": "1f95db3b087d8dd0712012d34ba700d7dd2e1382",
    "Out_Learn.pdf": "400513e691c6045112ad211b6153f80480eb7c2f",
    "Out_Think.pdf": "1fdb6a3b0e15d9cf57edbfde2d5ad156eabde2b6",
    "Out_Design.pdf": "84416bc596176e1648be476489c9db07b07a4062",
    "Out_Strategise.pdf": "0e89969bc920eda19c366462b69a393b018206d1",
    "Out_Execute.pdf": "e7c2c61307a5bfe2136bf2a61c875208252ebca6",
    "Out_Evolve.pdf": "a2a333187388e961a91c2fd67696adc09641c3ed",
}


def test_historical_seven_paper_inventory_remains_in_release_evidence() -> None:
    assert len(PAPERS) == 7
    assert set(PAPERS) <= set(PAPER_ASSETS)
    source = (ROOT / "docs/Out_Execute.tex").read_bytes()
    assert hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest() == (
        "19b468ae269e338adfb49d9fadfe0327a7fa026d"
    )


def test_every_current_catalogue_original_matches_release_evidence_and_links() -> None:
    catalog = load_catalog(ROOT)
    assert PAPER_ASSETS == {row["pdf"]["path"].removeprefix("docs/"): row["pdf"]["sha256"] for row in catalog["papers"]}
    verify_files(ROOT, catalog)
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for row in catalog["papers"]:
        filename = row["pdf"]["path"].removeprefix("docs/")
        assert section.count(f'href="{filename}" type="application/pdf" hreflang="en"') == 1
        assert f'https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/{row["pdf"]["path"]}' in readme


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
    assert "### [TRANSFORMATIONAL INTELLIGENCE ∞]" in readme
    assert "This combined software candidate adds bounded OUT-EXECUTE execution" in readme
    assert "not a claim that every proposed capability is implemented" in readme
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    assert homepage.index('id="home"') < homepage.index('id="papers"') < homepage.index('id="alpha-journey"')
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    assert [section.index(filename) for filename in PAPERS] == sorted(section.index(filename) for filename in PAPERS)
    assert section.count('class="paper-card paper-featured"') == 1
    assert section.count('class="paper-card"') == len(PAPER_ASSETS) - 1
    assert 'href="#papers" data-home-key="nav-papers"' in homepage
    index = section.split('class="papers-index"', 1)[1].split("</nav>", 1)[0]
    identifiers = ["transformational", "learn", "think", "design", "strategise", "execute", "evolve"]
    current = [row["id"] for row in load_catalog(ROOT)["papers"]]
    assert re.findall(r'href="#paper-([a-z][a-z0-9-]{0,63})-title"', index) == current
    assert [slug for slug in current if slug in identifiers] == identifiers
    assert index.count("<li>") == len(current) - 1
    assert 'aria-labelledby="papers-index-title"' in index
    for slug in identifiers:
        assert f'id="paper-{slug}-title" lang="en" tabindex="-1"' in section
    assert section.index('class="papers-index"') < section.index('class="papers-grid"')


def test_paper_copy_has_french_equivalents_and_declared_scope() -> None:
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    french = (ROOT / "docs/assets/portal/welcome.mjs").read_text(encoding="utf-8")
    for key in re.findall(r'data-home-key="([^"]+)"', section):
        assert re.search(rf'"{re.escape(key)}":\s*"[^"]+"', french), key
    assert "Research proposals and bounded studies" in section
    assert "not claims of general autonomous capability or physical deployment" in section
    assert 'class="paper-subtitle" lang="en"' in section
    resource_count = sum(len(row.get("resources", {})) for row in load_catalog(ROOT)["papers"])
    assert section.count('class="sr-only" lang="en"') == len(PAPER_ASSETS) + resource_count
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
    assert "grid-column: 1 / -1" in featured
    assert "grid-row: span" not in featured
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    paper_css = css.split("/* Original manuscripts", 1)[1].split("/* Selected reading", 1)[0]
    mobile = paper_css.split("@media (max-width: 760px)", 1)[1].split("@media print", 1)[0]
    assert "grid-template-columns: minmax(0, 1fr)" in mobile
    assert ".paper-featured {\n        display: flex;" in mobile
    context = css.split(".paper-link .sr-only {", 1)[1].split("}", 1)[0]
    assert "clip-path: inset(50%)" in context and "position: absolute" in context
    assert "display: none" not in context and "visibility: hidden" not in context
