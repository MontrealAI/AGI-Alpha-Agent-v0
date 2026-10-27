# SPDX-License-Identifier: Apache-2.0
"""Tests for generate_gallery_html.py."""

from pathlib import Path
import re
import pytest

from scripts import generate_demo_docs as gdd
from scripts import generate_gallery_html as ggh


def test_gallery_return_overlay_preserves_catalogued_research_bytes(tmp_path):
    protected = tmp_path / "reports" / "research-foundry-v2" / "index.html"
    protected.parent.mkdir(parents=True)
    raw = b'<html><body><a href="../../#papers">Research library</a></body></html>\n'
    protected.write_bytes(raw)
    ordinary = tmp_path / "index.html"
    ordinary.write_text("<html><body>Ordinary page</body></html>")
    ggh.insert_back_link([protected, ordinary], preserved_pages=[protected])
    assert protected.read_bytes() == raw
    assert "Back to Gallery" in ordinary.read_text()


@pytest.mark.parametrize("route", ["transformational-intelligence", "flywheel"])
def test_gallery_return_link_preserves_portable_ti_script_and_csp_bytes(tmp_path, route):
    page = tmp_path / "docs" / route / "index.html"
    page.parent.mkdir(parents=True)
    original = (
        b'<html><body><a href="../successor/alpha/">Return</a><script>\nwindow.fixture=true;\n</script></body></html>'
    )
    page.write_bytes(original)
    ordinary = tmp_path / "docs" / "ordinary.html"
    ordinary.write_text("<html><body>Ordinary gallery page</body></html>")
    ggh.insert_back_link([page, ordinary])
    assert page.read_bytes() == original
    assert "Back to Gallery" in ordinary.read_text()


@pytest.mark.parametrize(
    "name",
    ["solving_agi_governance", "muzero_planning", "muzeromctsllmagent_v0", "alpha_agi_insight_v1"],
)
def test_maintained_demo_card_opens_its_own_experience(name):
    _, preview, link, summary = ggh.parse_page(ggh.REPO_ROOT / "docs/demos" / f"{name}.md")
    assert link == f"{name}/"
    assert not preview.startswith("assets/studio/")
    assert summary


def test_release_updates_local_module_worker_and_data_urls(tmp_path):
    assets = tmp_path / "assets" / "workspace"
    assets.mkdir(parents=True)
    module = assets / "workbench.mjs"
    module.write_text(
        'import { calculate } from "../shared/engine.mjs?v=1.14.0";\n'
        "new Worker(new URL('./worker.mjs?v=1.14.0', import.meta.url));\n"
        'fetch(new URL("./scenarios.json?v=1.14.0", import.meta.url));\n'
        'const external = "https://example.com/engine.mjs?v=1.14.0";\n'
    )
    ggh.version_application_assets(tmp_path, "1.15.0")
    expected = (
        'import { calculate } from "../shared/engine.mjs?v=1.15.0";\n'
        "new Worker(new URL('./worker.mjs?v=1.15.0', import.meta.url));\n"
        'fetch(new URL("./scenarios.json?v=1.15.0", import.meta.url));\n'
        'const external = "https://example.com/engine.mjs?v=1.14.0";\n'
    )
    assert module.read_text() == expected
    ggh.version_application_assets(tmp_path, "1.15.0")
    assert module.read_text() == expected
    ggh.version_application_assets(tmp_path, "1.16.0")
    assert module.read_text() == expected.replace("v=1.15.0", "v=1.16.0")


def test_gallery_html(tmp_path, monkeypatch):
    repo = tmp_path
    demos = repo / "alpha_factory_v1" / "demos" / "demo_b"
    demos.mkdir(parents=True)
    (demos / "README.md").write_text("# Demo B\nText", encoding="utf-8")
    assets = repo / "docs" / "demo_b" / "assets"
    assets.mkdir(parents=True)
    (assets / "preview.png").write_text("data", encoding="utf-8")
    docs_demos = repo / "docs" / "demos"

    # generate docs
    monkeypatch.setattr(gdd, "REPO_ROOT", repo)
    monkeypatch.setattr(gdd, "DEMOS_DIR", repo / "alpha_factory_v1" / "demos")
    monkeypatch.setattr(gdd, "DOCS_DIR", docs_demos)
    gdd.generate_docs()

    # build gallery
    monkeypatch.setattr(ggh, "REPO_ROOT", repo)
    monkeypatch.setattr(ggh, "DEMOS_DIR", docs_demos)
    gallery = repo / "docs" / "gallery.html"
    monkeypatch.setattr(ggh, "GALLERY_FILE", gallery)
    index_file = repo / "docs" / "index.html"
    monkeypatch.setattr(ggh, "INDEX_FILE", index_file)

    html_text = ggh.build_html(ggh.collect_entries())
    gallery.write_text(html_text, encoding="utf-8")

    out = gallery.read_text(encoding="utf-8")
    assert "Demo B" in out
    assert "demo_b/assets/preview.png" in out
    assert 'href="demos/demo_b/"' in out


def test_generated_homepage_retains_successor_discovery_and_existing_workspaces() -> None:
    entries = [("Fixture demo", "preview.svg", "fixture/", "A retained gallery entry")]
    decision_cards = '<a href="studio/?case=fixture">Fixture decision</a>'
    generated = ggh.build_portal_html(entries, "9.8.7", decision_cards)
    navigation = re.search(r'<nav\b[^>]*aria-label="Main navigation"[^>]*>(.*?)</nav>', generated, re.S)
    assert navigation is not None
    directory = re.search(r'<nav\b[^>]*class="welcome-directory"[^>]*>(.*?)</nav>', generated, re.S)
    assert directory is not None
    # The flagship leads the short path; every advanced workspace remains discoverable.
    assert re.findall(r'<a\b[^>]*href="([^"]+)"', navigation[1]) == [
        "successor/alpha/",
        "flywheel/",
        "start/",
        "#papers",
        "#how-it-works",
        "#questions",
        "#research",
    ]
    assert 'data-home-key="nav-flagship">Flagship</a>' in navigation[1]
    assert 'href="start/"' in navigation[1] and "Start here" in navigation[1]
    assert 'href="successor/"' in directory[1] and "SUCCESSOR Ω" in directory[1]
    feature = re.search(
        r'<section\b[^>]*aria-labelledby="successor-feature-title"[^>]*>(.*?)</section>', generated, re.S
    )
    assert feature is not None
    assert '<h2 id="successor-feature-title">SUCCESSOR Ω</h2>' in feature[1]
    assert 'href="successor/"' in feature[1] and "Begin SUCCESSOR Ω" in feature[1]
    assert 'href="agent/SUCCESSOR/"' in feature[1]
    assert re.search(r'href="ascension/"\s*>Launch Ascension', generated)
    for route in ("compounding/", "bloom/", "insight/", "ascension-protocol/", "studio/"):
        assert f'href="{route}"' in directory[1]
    assert 'href="fixture/"' in generated and "A retained gallery entry" in generated
    assert decision_cards in generated
    assert 'name="application-version" content="9.8.7"' in generated
    assert "{{" not in generated
    assert ggh.build_portal_html(entries, "9.8.7", decision_cards) == generated


def test_paper_refresh_preserves_enterprise_preview_and_gallery_bytes() -> None:
    from scripts import research_papers as papers

    page = ggh.build_portal_html([], "1.39.0", "")
    refreshed = papers.replace_block(
        page, papers.HTML_START, papers.HTML_END, papers.render_section(papers.load_catalog(ggh.REPO_ROOT))
    )
    assert refreshed == page
    preview = re.search(r'<section\b[^>]*id="autonomous-enterprise-preview"[^>]*>.*?</section>', page, re.S)
    assert preview is not None
    assert preview.group() in refreshed
    assert page.index('id="autonomous-enterprise-preview"') < page.index(papers.HTML_START)
    assert 'href="successor/capabilities/#autonomous-enterprises"' in preview.group()
    assert 'href="Autonomous_Enterprises.pdf"' in preview.group()
    assert 'lang="fr"' in preview.group()


def test_generated_homepage_features_beginner_onboarding():
    page = ggh.build_portal_html([], "1.25.0", "")
    assert re.search(r'data-home-key="nav-start"\s*>\s*Start here\s*</a\s*>', page)
    assert "Start here — make a plan" in page
    assert page.index('id="home"') < page.index('id="research"') < page.index('id="workbench"')
    assert 'class="legacy-research" lang="en"' in page
    assert 'id="home-text-size"' in page
    assert 'id="home-fr"' in page
    assert page.count("<h1") == 1
    assert "Launch Ascension" in page
    assert "Begin SUCCESSOR Ω" in page
