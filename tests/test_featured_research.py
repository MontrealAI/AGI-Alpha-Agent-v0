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
# Required enterprise originals are independent of the rendered catalogue. Removing
# a record must fail even when both the renderer and release inventory follow it.
ENTERPRISE_PAPERS = {
    "autonomous-enterprises": (
        "docs/Autonomous_Enterprises.pdf",
        "docs/papers/autonomous-enterprises.pdf",
        "a677bb4727f3af35038d1c972081f83bcc2e1019b65dea17da195c6eb078e7af",
        "8b51f6a4b0d2b1c36875c18617be3a5312c7a19d",
    ),
    "autonomous-enterprises-activate-evolve-scale": (
        "docs/Autonomous_Enterprises_Activate_Evolve_Scale.pdf",
        "docs/papers/autonomous-enterprises-activate-evolve-scale.pdf",
        "9cc01c8143400dd2f4258e11b3a86295d346be0671afc19cb99249b4a47b3cd2",
        "d2e9a081bebc97aff2f3b19d6210480418a13094",
    ),
    "autonomous-enterprises-successor-omega": (
        "docs/Autonomous_Enterprises_SUCCESSOR_Omega.pdf",
        "docs/papers/autonomous-enterprises-successor-omega.pdf",
        "55aee29b3c8f89bbb2c5002c0874b0cc95dcb144da34f4199184c141bc40ad5f",
        "bf484b94b47bbfa0eb0d9a673062cabb6435f00b",
    ),
    "autonomous-enterprises-foundry-v2": (
        "docs/papers/autonomous-enterprises-foundry-v2.pdf",
        "docs/papers/autonomous-enterprises-foundry-v2.pdf",
        "67f2d38922cdaa1bf28e916a494679fabf1463ba84fe56e620dfd192b20d16b3",
        "1612d013ce6bb64fa236a8e4b306a40306bbc4e5",
    ),
}


def test_historical_seven_paper_inventory_remains_in_release_evidence() -> None:
    assert len(PAPERS) == 7
    assert set(PAPERS) <= set(PAPER_ASSETS)
    source = (ROOT / "docs/Out_Execute.tex").read_bytes()
    assert hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest() == (
        "19b468ae269e338adfb49d9fadfe0327a7fa026d"
    )


@pytest.mark.parametrize("slug,identity", ENTERPRISE_PAPERS.items())
def test_required_enterprise_originals_have_exact_catalogue_destinations(
    slug: str, identity: tuple[str, str, str, str]
) -> None:
    original, destination, digest, blob = identity
    rows = {row["id"]: row for row in load_catalog(ROOT)["papers"]}
    assert slug in rows
    assert sum(row["pdf"]["sha256"] == digest for row in rows.values()) == 1
    row = rows[slug]
    assert row["pdf"] == {"path": destination, "sha256": digest}
    source = (ROOT / original).read_bytes()
    assert source.startswith(b"%PDF-")
    assert hashlib.sha256(source).hexdigest() == digest
    assert hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest() == blob
    assert (ROOT / destination).read_bytes() == source
    # The maintained importer also retains the corresponding opaque TeX bytes.
    assert row["tex"]["path"] == destination.removesuffix(".pdf") + ".tex"
    tex = (ROOT / original).with_suffix(".tex").read_bytes()
    assert (ROOT / row["tex"]["path"]).read_bytes() == tex
    assert hashlib.sha256(tex).hexdigest() == row["tex"]["sha256"]
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    featured = readme.split("<!-- featured-research-papers -->", 1)[1].split(
        "<!-- /featured-research-papers -->", 1
    )[0]
    assert f"https://github.com/MontrealAI/AGI-Alpha-Agent-v0/blob/main/{destination}" in featured
    homepage = (ROOT / "docs/index.html").read_text(encoding="utf-8")
    section = homepage.split('id="papers"', 1)[1].split("</section>", 1)[0]
    relative = destination.removeprefix("docs/")
    assert section.count(f'href="{relative}" type="application/pdf" hreflang="en"') == 1


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
