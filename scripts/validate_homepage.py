# SPDX-License-Identifier: Apache-2.0
"""Verify the welcoming homepage, accessible controls and guided-plan handoff."""

from __future__ import annotations

import argparse
import importlib.util
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
from threading import Thread
import tomllib
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import Page, expect, sync_playwright

from scripts.homepage_evidence import ASSETS, EXPERIENCE_ASSETS, PAPER_ASSETS, RESOURCE_LINKS, asset_hashes
from scripts.research_papers import MAX_EXPERIENCE, RESOURCE_LABELS, load_catalog, ordinary_path, resource_href
from scripts.validate_ascension import Handler, inspect
from scripts.validate_ecosystem import validate as validate_ecosystem


def assert_paper_links(page: Page, language: str) -> None:
    """Keep original PDFs and accessible link names intact through reading changes."""
    papers = page.locator("#papers")
    records = load_catalog()["papers"]
    expect(papers.locator("article")).to_have_count(len(records))
    expect(papers.locator(".paper-link")).to_have_count(len(records))
    expect(papers.locator(".paper-resource-link")).to_have_count(
        sum(len(record.get("resources", {})) for record in records)
    )
    reading_index = papers.locator(".papers-index")
    expect(reading_index).to_have_accessible_name(
        "Choose your reading path" if language == "en" else "Choisissez votre parcours de lecture"
    )
    expect(reading_index.locator("a")).to_have_count(len(records))
    expect(reading_index.locator("ol > li")).to_have_count(len(records) - 1)
    grid_box = papers.locator(".papers-grid").bounding_box()
    lead_box = papers.locator(".paper-featured").bounding_box()
    assert grid_box is not None and lead_box is not None
    assert abs(grid_box["width"] - lead_box["width"]) < 1, "The foundation spans the reading grid"
    card_boxes = []
    for card in papers.locator("article").all():
        box = card.bounding_box()
        assert box is not None
        card_boxes.append(box)
    for first, box in enumerate(card_boxes):
        remaining_start = first + 1
        for other in card_boxes[remaining_start:]:
            horizontal = min(box["x"] + box["width"], other["x"] + other["width"]) - max(box["x"], other["x"])
            vertical = min(box["y"] + box["height"], other["y"] + other["height"]) - max(box["y"], other["y"])
            assert min(horizontal, vertical) <= 1, "Paper cards must not overlap"
    title_element = papers.locator(".paper-featured h3")
    assert " ".join(title_element.inner_text().replace("\u00ad", "").split()) == records[0]["display_title"]
    words = title_element.locator(".paper-title-word")
    expect(words).to_have_count(len(records[0]["title_words"]))
    for word in words.all():
        assert word.evaluate("element => getComputedStyle(element).display") == "block"
    title_fragments = title_element.evaluate(
        """element => {
            const fragments = new Map();
            let word = 0;
            const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
            while (walker.nextNode()) {
                const node = walker.currentNode;
                for (let index = 0; index < node.length; index++) {
                    const character = node.textContent[index];
                    if (/\\s/.test(character)) { word += 1; continue; }
                    if (!/[A-Z]/.test(character)) continue;
                    const range = document.createRange();
                    range.setStart(node, index);
                    range.setEnd(node, index + 1);
                    const top = Math.round(range.getBoundingClientRect().top);
                    const key = `${word}:${top}`;
                    fragments.set(key, (fragments.get(key) || '') + character);
                }
            }
            return [...fragments.values()];
        }"""
    )
    if records[0]["title_words"]:
        assert title_fragments and all(len(fragment) >= 4 for fragment in title_fragments), title_fragments
    for index, record in enumerate(records):
        filename = record["pdf"]["path"].removeprefix("docs/")
        title = record["title"]
        index_link = papers.locator(".papers-index a").nth(index)
        expect(index_link).to_have_attribute("href", f'#paper-{record["id"]}-title')
        expect(index_link).to_have_accessible_name(record["display_title"])
        expect(papers.locator(f'#paper-{record["id"]}-title')).to_have_attribute("tabindex", "-1")
        expect(papers.locator(f'[data-paper-key="{record["id"]}-summary"]')).to_have_text(record["summary"][language])
        link = papers.locator(".paper-link").nth(index)
        expect(link).to_have_attribute("href", filename)
        expect(link).to_have_attribute("type", "application/pdf")
        expect(link).to_have_attribute("hreflang", "en")
        expect(link.locator(".sr-only")).to_have_text(": " + title)
        expect(link.locator(".paper-format")).to_have_text("English PDF" if language == "en" else "PDF en anglais")
        expect(link.locator("span[aria-hidden='true']")).to_have_text("↗")
        expected = (
            ("Read the featured paper" if index == 0 else "Read the paper")
            if language == "en"
            else ("Lire la publication à la une" if index == 0 else "Lire la publication")
        )
        expect(link.locator("span[data-paper-key$='-read']")).to_have_text(expected)
        expect(link).to_have_accessible_name(re.compile(re.escape(expected) + r"\s*:\s*" + re.escape(title)))
        context = link.locator(".sr-only").evaluate(
            """element => {
                const style = getComputedStyle(element);
                const rect = element.getBoundingClientRect();
                return {position: style.position, clip: style.clipPath, width: rect.width, height: rect.height};
            }"""
        )
        assert context["position"] == "absolute" and context["clip"] == "inset(50%)", context
        assert context["width"] <= 1 and context["height"] <= 1, context
        card = papers.locator("article").nth(index)
        resources = record.get("resources", {})
        expect(card.locator(".paper-resource-link")).to_have_count(len(resources))
        for role, resource in resources.items():
            extra = card.locator(f'[data-paper-resource="{role}"]')
            label = RESOURCE_LABELS[role][language]
            expect(extra).to_have_attribute("href", resource_href(role, resource))
            expect(extra.locator("span[data-paper-key]")).to_have_text(label)
            expect(extra.locator(".sr-only")).to_have_text(": " + title)
            expect(extra).to_have_accessible_name(re.compile(re.escape(label) + r"\s*:\s*" + re.escape(title)))
            expect(extra).to_be_visible()
    expect(papers.locator("[data-home-key]")).not_to_have_count(0)
    assert "undefined" not in papers.inner_text()


def assert_research_edition_guides(page: Page, origin: str, output: Path) -> None:
    """Exercise the catalogued reading guides on the same accepted page origin."""
    records = [record for record in load_catalog()["papers"] if "reading" in record.get("resources", {})]
    assert records, "The published research reading guides must remain available"
    for record in records:
        href = resource_href("reading", record["resources"]["reading"])
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            page.goto(origin + href + "?lang=en", wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "en")
            page.keyboard.press("Tab")
            expect(page.locator(".skip")).to_be_focused()
            page.keyboard.press("Enter")
            assert urlsplit(page.url).fragment == "main"
            pdf_only_pages = {"when-paid-work-teaches-the-network": 22, "the-network-that-learns-to-invent": 19}
            if record["id"] in pdf_only_pages:
                page_count = pdf_only_pages[record["id"]]
                assert record["tex"] is None
                expect(page.locator("html")).to_have_attribute("data-reader-format", "pdf-extracted-text-v1")
                # PDF-only originals have no fabricated TeX or translated paper.
                # Check their accessible, no-script original/text reading path.
                page.keyboard.press("Tab")
                pdf = page.locator('a[type="application/pdf"]')
                expect(pdf).to_be_focused()
                assert inspect(page, "parseFloat(getComputedStyle(document.activeElement).outlineWidth)") > 0
                target = origin + record["pdf"]["path"].removeprefix("docs/")
                assert pdf.evaluate("(link) => link.href") == target
                expect(page.locator("iframe")).to_have_attribute("title", re.compile(re.escape(record["title"])))
                assert page.locator("iframe").evaluate("(frame) => frame.src.split('#')[0]") == target
                response = page.request.get(target)
                assert response.ok
                assert hashlib.sha256(response.body()).hexdigest() == record["pdf"]["sha256"]
                expect(page.locator("details")).to_have_count(page_count)
                first = page.locator("details").first
                first.locator("summary").focus()
                page.keyboard.press("Enter")
                expect(first).to_have_attribute("open", "")
                expect(first.locator("pre")).to_contain_text(re.compile(re.escape(record["title"].split()[0]), re.I))
                page.keyboard.press("Enter")
                assert first.get_attribute("open") is None
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1")
                page.reload(wait_until="networkidle")
                expect(page.locator("html")).to_have_attribute("lang", "en")
                expect(page.locator("details")).to_have_count(page_count)
                page.screenshot(path=str(output / f"homepage-research-guide-{record['id']}-en-{width}.png"))
                continue
            page.keyboard.press("Tab")
            pdf = page.locator('.actions a[type="application/pdf"]')
            expect(pdf).to_be_focused()
            assert inspect(page, "parseFloat(getComputedStyle(document.activeElement).outlineWidth)") > 0
            assert pdf.evaluate("(link) => link.href") == origin + record["pdf"]["path"].removeprefix("docs/")
            tex = page.locator(".actions a[download]")
            assert tex.evaluate("(link) => link.href") == origin + record["tex"]["path"].removeprefix("docs/")
            expect(page.locator('aside a[download][href="./index.html"]')).to_be_visible()
            history_length = inspect(page, "history.length")
            for language in ("fr", "en"):
                control = page.locator(f'.languages a[data-set-language="{language}"]')
                control.focus()
                page.keyboard.press("Enter")
                expect(page.locator("html")).to_have_attribute("lang", language)
                expect(page.locator("html")).to_have_attribute("data-ui-language", language)
                expect(control).to_have_attribute("aria-current", "true")
                expect(page.locator(f'main [data-language="{language}"]').first).to_be_visible()
                other = "en" if language == "fr" else "fr"
                expect(page.locator(f'main [data-language="{other}"]').first).not_to_be_visible()
                assert parse_qs(urlsplit(page.url).query).get("lang") == [language]
                assert inspect(page, "history.length") == history_length
                links = page.locator("[data-site-language]")
                assert links.count() > 0
                for link in links.all():
                    target = link.evaluate("(element) => element.href")
                    assert parse_qs(urlsplit(target).query).get("lang") == [language]
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1")
                if language == "fr":
                    page.reload(wait_until="networkidle")
                    expect(page.locator("html")).to_have_attribute("lang", "fr")
                    expect(page.locator('main [data-language="fr"]').first).to_be_visible()
                if (width, language) in {(1440, "en"), (320, "fr")}:
                    page.screenshot(
                        path=str(output / f"homepage-research-guide-{record['id']}-{language}-{width}.png"),
                        full_page=True,
                    )


def assert_reading_links(page: Page, language: str) -> None:
    """Language switches preserve each guide's visible text and hidden context."""
    guides = page.locator("#reading .reading-card .reading-guide")
    expect(guides).to_have_count(4)
    contexts = (
        ("Governed improvement", "Sustainable improvement", "Discovery & invention", "Evidence & memory")
        if language == "en"
        else ("Amélioration encadrée", "Amélioration durable", "Découverte et invention", "Preuves et mémoire")
    )
    for guide, context in zip(guides.all(), contexts):
        expect(guide.locator("span[data-home-key^='reading-copy-']")).to_have_text(
            "Explore the current guide" if language == "en" else "Explorer le guide actuel"
        )
        expect(guide.locator(".sr-only")).to_have_text(": " + context)
        expect(guide.locator("span[aria-hidden='true']")).to_have_text("↗")
    expect(page.locator("#reading a[data-home-key]")).to_have_count(0)
    expect(page.locator("#reading > .reading-guide > span[aria-hidden='true']")).to_have_text("↗")


def assert_handoff(page: Page, language: str, large: bool) -> None:
    """Require every first-plan entry to retain the visitor's reading preferences."""
    assert_paper_links(page, language)
    assert_reading_links(page, language)
    for selector, path, fragments in (
        ("[data-ti-link]", "try/", {""}),
        ("[data-alpha-link]", "successor/alpha/", {"", "computer-mission"}),
        ("[data-discovery-link]", "successor/discover/", {""}),
        ("[data-mission-link]", "successor/mission/", {"guided-journey"}),
    ):
        guided = page.locator(selector)
        assert guided.count() >= 1, "Offer discovery and the retained project journey"
        for link in guided.all():
            target = urlsplit(link.get_attribute("href") or "")
            assert not target.scheme and not target.netloc and target.path == path
            assert target.fragment in fragments
            assert parse_qs(target.query) == ({"lang": ["fr"]} if language == "fr" else {}) | (
                {"text": ["large"]} if large else {}
            )
    nova_links = page.locator("[data-nova-link]")
    assert nova_links.count() >= 4, "Offer Studio in the hero, project section and directory"
    for link in nova_links.all():
        target = urlsplit(link.get_attribute("href") or "")
        assert not target.scheme and not target.netloc and target.path == "ascension/mainnet/"
        assert target.fragment in ("", "resume")
        query = parse_qs(target.query)
        assert query == ({"lang": ["fr"]} if language == "fr" else {}) | ({"text": ["large"]} if large else {})
    pocket_links = page.locator("[data-omega-link]")
    assert pocket_links.count() >= 2, "Offer the personal lab at both main invitations"
    for link in pocket_links.all():
        target = urlsplit(link.get_attribute("href") or "")
        assert not target.scheme and not target.netloc and target.path == "successor/play/"
        query = parse_qs(target.query)
        assert set(query) <= {"lang", "text"}
        assert query.get("lang", ["en"]) == [language]
        assert query.get("text", ["standard"]) == (["large"] if large else ["standard"])
    ecosystem_links = page.locator("[data-ecosystem-link]")
    assert ecosystem_links.count() >= 3, "Offer the shared guide near the introduction and in the directory"
    for link in ecosystem_links.all():
        target = urlsplit(link.get_attribute("href") or "")
        assert not target.scheme and not target.netloc
        assert target.path == ("ecosystem/fr/" if language == "fr" else "ecosystem/")
        assert parse_qs(target.query) == ({"text": ["large"]} if large else {})
        assert target.fragment == ("contracts" if link.get_attribute("data-home-key") == "ecosystem-contracts" else "")
    links = page.locator("[data-start-link]")
    assert links.count() >= 2, "Offer the guided plan at the top and after the introduction"
    for link in links.all():
        href = link.get_attribute("href")
        assert href is not None
        target = urlsplit(href)
        assert not target.scheme and not target.netloc and target.path == "start/", href
        expected_fragment = "" if link.get_attribute("data-home-key") == "nav-start" else "journey"
        assert target.fragment == expected_fragment, href
        query = parse_qs(target.query)
        assert set(query) <= {"lang", "text"}, href
        assert query.get("lang", ["en"]) == [language], href
        assert query.get("text", ["standard"]) == (["large"] if large else ["standard"]), href


def assert_reading_url(
    page: Page,
    language: str,
    large: bool,
    *,
    path: str,
    fragment: str = "",
    extra_query: dict[str, list[str]] | None = None,
) -> None:
    """Require a bookmarkable reading choice without altering the page's other URL state."""
    target = urlsplit(page.url)
    assert target.path == path and target.fragment == fragment, page.url
    expected = dict(extra_query or {})
    if language == "fr":
        expected["lang"] = ["fr"]
    if large:
        expected["text"] = ["large"]
    assert parse_qs(target.query, keep_blank_values=True) == expected, page.url


def assert_home_handoff(page: Page, language: str, large: bool) -> None:
    """Require every planner return link to retain preferences and its intended section."""
    for selector, fragment in (
        ("header a.brand", ""),
        ("footer a.brand", ""),
        ('footer a[data-i18n="all"]', "explore"),
    ):
        link = page.locator(selector)
        expect(link).to_have_count(1)
        href = link.get_attribute("href")
        assert href is not None
        assert urlsplit(href).fragment == fragment, href
    home_links = 0
    for link in page.locator("a[href]").all():
        href = link.get_attribute("href")
        assert href is not None
        target = urlsplit(href)
        if target.path != "../":
            continue
        home_links += 1
        assert not target.scheme and not target.netloc, href
        query = parse_qs(target.query, keep_blank_values=True)
        expected: dict[str, list[str]] = {}
        if language == "fr":
            expected["lang"] = ["fr"]
        if large:
            expected["text"] = ["large"]
        assert query == expected, href
    assert home_links >= 3, "Offer the homepage through both brands and All workspaces"


def check_layout(page: Page) -> list[dict[str, Any]]:
    """Measure real rendered controls and horizontal reflow, including mobile text."""
    assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1"), "Horizontal page overflow"
    overflowing_headings = inspect(
        page,
        """(() => [...document.querySelectorAll('h1,h2,h3')].filter(el =>
          el.getClientRects().length && el.clientWidth && el.scrollWidth > el.clientWidth + 2
        ).map(el => ({text: el.innerText, width: el.clientWidth, scroll: el.scrollWidth})))()""",
    )
    assert not overflowing_headings, f"Heading text overflows its column: {overflowing_headings}"
    overlapping_columns = inspect(
        page,
        """(() => [...document.querySelectorAll('.flagship-heading')].filter(el => {
          const children = [...el.children].filter(child => child.getClientRects().length);
          return children.some((child, i) => children.slice(i + 1).some(other => {
            const a = child.getBoundingClientRect(), b = other.getBoundingClientRect();
            return Math.min(a.right, b.right) - Math.max(a.left, b.left) > 1 &&
              Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) > 1;
          }));
        }).map(el => el.innerText))()""",
    )
    assert not overlapping_columns, f"Feature heading and description overlap: {overlapping_columns}"
    controls = inspect(
        page,
        """(() => [...document.querySelectorAll(
          'header a, header button, #home a, #home button, #papers a, #questions summary, .welcome-ecosystem a'
        )].filter(el => !el.closest('#research') && el.getClientRects().length &&
          getComputedStyle(el).visibility !== 'hidden').map(el => {
          const box = el.getBoundingClientRect();
          return {label: (el.innerText || el.getAttribute('aria-label') || el.id).trim(),
            width: box.width, height: box.height};
        }))()""",
    )
    assert controls, "No visible welcome controls"
    small = [control for control in controls if min(control["width"], control["height"]) < 43.5]
    assert not small, f"Welcome controls need at least 44 × 44 CSS pixels: {small}"
    return cast(list[dict[str, Any]], controls)


def audit(page: Page, axe_source: str, *, beginner_only: bool) -> dict[str, Any]:
    """Run axe against the shipped CSP and retain exact failures for review."""
    inspect(page, axe_source + "; void 0")
    context = (
        "{include:['header','#home','#papers','.welcome-ecosystem'],exclude:['#research']}"
        if beginner_only
        else "document"
    )
    tags = "['wcag2a','wcag2aa','wcag21aa','best-practice']" if beginner_only else "['wcag2a','wcag2aa','wcag21aa']"
    return cast(dict[str, Any], inspect(page, f"axe.run({context}, {{runOnly:{{type:'tag',values:{tags}}}}})"))


def validate(
    site: Path,
    output: Path,
    public_url: str | None,
    axe_script: Path,
    executable: str | None,
) -> dict[str, Any]:
    """Exercise the homepage as a new visitor, without changing app data or settings."""
    root = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public homepage acceptance requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    report: dict[str, Any] = {
        "schema": "agialpha.homepage.acceptance.v1",
        "passed": False,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "version": tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
        "origin": public_url or "local project subpath",
        "checks": [],
        "browser_errors": [],
        "layouts": [],
        "accessibility": [],
        "assets": {},
        "paper_assets": {},
        "research_experience_assets": {},
        "research_resources": {},
    }
    try:
        expected_assets = asset_hashes()
        if asset_hashes(site) != expected_assets:
            raise ValueError("Homepage site assets differ from the current generated source")
        for relative in ASSETS:
            # Fetch the same directory entry points and versioned assets as a visitor.
            target = relative.removesuffix("index.html") if relative.endswith("index.html") else relative
            if not relative.endswith("index.html"):
                target += f"?v={report['version']}"
            request = Request(origin + target, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != origin + target:
                    raise ValueError(f"Unexpected homepage asset response: {relative}")
                digest = hashlib.sha256(response.read()).hexdigest()
            if digest != expected_assets[relative]:
                raise ValueError(f"Homepage asset differs from the tested source: {relative}")
            report["assets"][relative] = digest
        report["checks"].append("exact-current-assets")
        for filename, expected in PAPER_ASSETS.items():
            if hashlib.sha256((root / "docs" / filename).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Source research paper differs from the original: {filename}")
            if hashlib.sha256((site / filename).read_bytes()).hexdigest() != expected:
                raise ValueError(f"Built research paper differs from the original: {filename}")
            request = Request(origin + filename, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != origin + filename:
                    raise ValueError(f"Unexpected research paper response: {filename}")
                received = hashlib.sha256(response.read()).hexdigest()
            if received != expected:
                raise ValueError(f"Served research paper differs from the original: {filename}")
            report["paper_assets"][filename] = received
        report["checks"].append("original-paper-bytes")
        for filename, expected in EXPERIENCE_ASSETS.items():
            for folder, relative in ((root, "docs/" + filename), (site, filename)):
                path = ordinary_path(folder, relative)
                if (
                    not 0 < path.stat().st_size <= MAX_EXPERIENCE
                    or hashlib.sha256(path.read_bytes()).hexdigest() != expected
                ):
                    raise ValueError(f"Research experience differs from the catalogued source: {filename}")
            request = Request(origin + filename, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != origin + filename:
                    raise ValueError(f"Unexpected research experience response: {filename}")
                raw = response.read(MAX_EXPERIENCE + 1)
            if len(raw) > MAX_EXPERIENCE or hashlib.sha256(raw).hexdigest() != expected:
                raise ValueError(f"Served research experience differs from the tested source: {filename}")
            report["research_experience_assets"][filename] = expected
        if EXPERIENCE_ASSETS:
            report["checks"].append("qualified-research-experience-bytes")
        axe_source = axe_script.read_text(encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=executable)
            report["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
            page.goto(origin, wait_until="networkidle")
            expect(page.locator("body")).to_have_class(re.compile(r"\bwelcome-page\b"))
            expect(page.locator("html")).to_have_attribute("lang", "en")
            expect(page.locator('meta[name="application-version"]')).to_have_attribute("content", report["version"])
            heading = page.get_by_role("heading", level=1).first
            expect(heading).to_be_visible()
            english_heading = heading.inner_text().strip()
            assert english_heading, "Explain the first experience with a visible heading"
            base_size = inspect(page, "parseFloat(getComputedStyle(document.body).fontSize)")
            assert base_size >= 18, base_size
            navigation = page.get_by_role("navigation", name="Main navigation")
            expect(navigation.get_by_role("link", name="Start here", exact=True)).to_have_attribute("href", "start/")
            expect(page.locator("#how-it-works")).to_be_visible()
            steps = page.locator("#how-it-works ol > li")
            expect(steps).to_have_count(3)
            for step in steps.all():
                expect(step).to_be_visible()
                assert step.inner_text().strip()
            expect(page.locator("#questions")).to_be_visible()
            questions = page.locator("#questions details")
            assert questions.count() >= 3, "Explain common questions before technical exploration"
            for question in questions.all():
                summary = question.locator("summary")
                expect(summary).to_be_visible()
                summary.click()
                expect(question).to_have_attribute("open", "")
                assert len(question.inner_text().strip()) > len(summary.inner_text().strip())
                summary.click()
            assert_handoff(page, "en", False)
            if RESOURCE_LINKS:
                report["research_resources"] = RESOURCE_LINKS
                report["checks"].append("research-resource-links")
            report["checks"] += ["clear-first-step", "three-visible-steps", "readable-default-text", "working-faq"]

            # Index links move to focusable headings, not duplicate PDF downloads.
            first_paper, last_paper = load_catalog()["papers"][0], load_catalog()["papers"][-1]
            first_target = f'#paper-{first_paper["id"]}-title'
            last_target = f'#paper-{last_paper["id"]}-title'
            page.locator(".papers-index a").first.focus()
            page.keyboard.press("Enter")
            expect(page.locator(first_target)).to_be_focused()
            expect(page).to_have_url(origin + first_target)
            page.locator(".papers-index a").last.click()
            expect(page.locator(last_target)).to_be_focused()
            expect(page).to_have_url(origin + last_target)
            page.go_back()
            expect(page).to_have_url(origin + first_target)
            page.go_forward()
            expect(page).to_have_url(origin + last_target)
            assert_handoff(page, "en", False)

            # A keyboard-only visitor reaches the main content before navigating the header.
            page.goto(origin, wait_until="networkidle")
            page.keyboard.press("Tab")
            expect(page.locator('a[href="#home"]').first).to_be_focused()
            page.keyboard.press("Enter")
            expect(page.locator("#home")).to_be_focused()
            home_path = urlsplit(origin).path
            history_length = inspect(page, "history.length")
            page.locator("#home-fr").focus()
            page.keyboard.press("Enter")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-fr")).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#home-en")).to_have_attribute("aria-pressed", "false")
            expect(page.locator(".welcome-directory")).to_have_attribute("lang", "en")
            for legacy in page.locator(".legacy-research").all():
                expect(legacy).to_have_attribute("lang", "en")
            assert heading.inner_text().strip() != english_heading
            assert_handoff(page, "fr", False)
            assert_reading_url(page, "fr", False, path=home_path, fragment="home")
            page.locator("#home-text-size").click()
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert inspect(page, "parseFloat(getComputedStyle(document.body).fontSize)") > base_size
            assert_handoff(page, "fr", True)
            assert_reading_url(page, "fr", True, path=home_path, fragment="home")
            assert inspect(page, "history.length") == history_length, "Reading controls must not add history entries"
            page.reload(wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert_reading_url(page, "fr", True, path=home_path, fragment="home")
            assert_handoff(page, "fr", True)

            # Native anchor navigation creates entries; Back/Forward restores each entry's choices.
            page.locator('header a[href="#questions"]').click()
            expect(page).to_have_url(re.compile(r"#questions$"))
            question_history_length = inspect(page, "history.length")
            page.locator("#home-en").click()
            assert_reading_url(page, "en", True, path=home_path, fragment="questions")
            assert inspect(page, "history.length") == question_history_length
            page.go_back()
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert_reading_url(page, "fr", True, path=home_path, fragment="home")
            assert_handoff(page, "fr", True)
            page.go_forward()
            expect(page.locator("html")).to_have_attribute("lang", "en")
            assert_reading_url(page, "en", True, path=home_path, fragment="questions")
            assert_handoff(page, "en", True)
            page.locator("#home-fr").click()
            page.locator("#home [data-start-link]").focus()
            page.keyboard.press("Enter")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#planner")).to_be_visible()
            expect(page.locator("#journey")).to_be_focused()
            expect(page.locator("#minutes")).to_be_visible()
            expect(page.locator("#minutes")).to_have_value("60")
            page.keyboard.press("Tab")
            expect(page.locator("#minutes")).to_be_focused()
            assert_reading_url(page, "fr", True, path=home_path + "start/", fragment="journey")

            # Planner controls update only reading preferences, never task input or storage.
            page.goto(origin + "start/?lang=fr&text=large&source=bookmark#planner", wait_until="networkidle")
            expect(page.locator("#planner")).to_be_visible()
            page.locator("#task-options summary").click()
            page.locator("#name-0").fill("My private task, kept on this page")
            planner_history_length = inspect(page, "history.length")
            page.locator("#language").click()
            expect(page.locator("html")).to_have_attribute("lang", "en")
            page.locator("#text-size").click()
            assert_reading_url(
                page, "en", False, path=home_path + "start/", fragment="planner", extra_query={"source": ["bookmark"]}
            )
            expect(page.locator("#name-0")).to_have_value("My private task, kept on this page")
            assert_home_handoff(page, "en", False)
            page.locator("#language").click()
            page.locator("#text-size").click()
            assert inspect(page, "history.length") == planner_history_length
            assert_reading_url(
                page, "fr", True, path=home_path + "start/", fragment="planner", extra_query={"source": ["bookmark"]}
            )
            assert inspect(page, "localStorage.length === 0 && sessionStorage.length === 0")
            page.reload(wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#name-0")).not_to_have_value("My private task, kept on this page")
            assert_home_handoff(page, "fr", True)
            page.locator('footer a[data-i18n="all"]').click()
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert_reading_url(page, "fr", True, path=home_path, fragment="explore")

            # The historical nested gallery rewrites the return path; retain that destination too.
            page.goto(origin + "alpha_factory_v1/demos/start/?lang=fr&text=large", wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
            mirror_return = page.locator('footer a[data-i18n="all"]')
            expect(mirror_return).to_have_attribute("href", "../../..?lang=fr&text=large#explore")
            mirror_return.click()
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert_reading_url(page, "fr", True, path=home_path, fragment="explore")
            report["checks"] += [
                "keyboard-skip",
                "english-and-french",
                "larger-text",
                "guided-plan-preferences",
                "direct-plan-entry",
                "reading-preferences-survive-reload",
                "reading-preferences-follow-history",
            ]

            # Shared links reproduce preferences without requiring a saved browser setting.
            page.goto(origin + "?lang=fr&text=large&source=bookmark#home", wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert_handoff(page, "fr", True)
            page.locator("#home-en").click()
            expect(page.locator("html")).to_have_attribute("lang", "en")
            assert heading.inner_text().strip() == english_heading
            assert_handoff(page, "en", True)
            page.locator("#home-text-size").click()
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "false")
            assert_handoff(page, "en", False)
            assert_reading_url(page, "en", False, path=home_path, fragment="home", extra_query={"source": ["bookmark"]})
            page.reload(wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "en")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "false")
            assert_handoff(page, "en", False)
            report["checks"].append("shareable-reading-preferences")

            for language, width, large in (
                ("en", 1440, False),
                ("en", 2048, False),
                ("en", 1024, False),
                ("en", 900, False),
                ("en", 720, False),
                ("fr", 1024, True),
                ("en", 390, False),
                ("fr", 320, False),
                ("fr", 320, True),
            ):
                page.set_viewport_size({"width": width, "height": 1000})
                page.goto(origin + f"?lang={language}" + ("&text=large" if large else ""), wait_until="networkidle")
                expect(page.locator("html")).to_have_attribute("lang", language)
                controls = check_layout(page)
                report["layouts"].append(
                    {"width": width, "language": language, "large_text": large, "controls": controls}
                )
                page.screenshot(path=str(output / f"homepage-{language}-{width}{'-large' if large else ''}.png"))
                assert_paper_links(page, language)
                page.locator("#papers").screenshot(
                    path=str(output / f"homepage-papers-{language}-{width}{'-large' if large else ''}.png")
                )
                page.locator("#alpha-journey").screenshot(
                    path=str(output / f"homepage-journey-{language}-{width}{'-large' if large else ''}.png")
                )
                page.locator('.welcome-ecosystem[aria-labelledby="ecosystem-title"]').screenshot(
                    path=str(output / f"homepage-ecosystem-{language}-{width}{'-large' if large else ''}.png")
                )
                page.locator("#nova-title").click()
                page.locator("#nova-seed").screenshot(
                    path=str(output / f"homepage-nova-{language}-{width}{'-large' if large else ''}.png")
                )
                for beginner_only in (True, False):
                    result = audit(page, axe_source, beginner_only=beginner_only)
                    report["accessibility"].append(
                        {
                            "width": width,
                            "language": language,
                            "large_text": large,
                            "scope": "welcome" if beginner_only else "document",
                            "violations": result["violations"],
                        }
                    )
                    assert not result["violations"], result["violations"]
            assert inspect(page, "matchMedia('(prefers-reduced-motion: reduce)').matches")
            assert inspect(page, "getComputedStyle(document.documentElement).scrollBehavior !== 'smooth'")
            report["checks"] += ["mobile-reflow", "large-touch-targets", "axe-no-violations", "reduced-motion"]

            no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
            fallback = no_js.new_page()
            fallback.goto(origin)
            expect(fallback.get_by_role("heading", level=1).first).to_be_visible()
            expect(
                fallback.get_by_role("navigation", name="Main navigation").get_by_role(
                    "link", name="Start here", exact=True
                )
            ).to_have_attribute("href", "start/")
            expect(fallback.locator("#how-it-works")).to_be_visible()
            expect(fallback.locator("#questions summary").first).to_be_visible()
            fallback.locator("#questions summary").first.click()
            expect(fallback.locator("#questions details").first).to_have_attribute("open", "")
            assert_handoff(fallback, "en", False)
            fallback.locator(".papers-index a").last.click()
            expect(fallback).to_have_url(origin + last_target)
            expect(fallback.locator(last_target)).to_be_focused()
            fallback.locator("#home [data-start-link]").click()
            expect(fallback).to_have_url(origin + "start/#journey")
            expect(fallback.locator("#journey")).to_be_focused()
            expect(fallback.locator("#journey noscript .notice")).to_be_visible()
            report["checks"].append("no-javascript-content-and-navigation")
            report["ecosystem"] = validate_ecosystem(browser, origin, output / "ecosystem", axe_source)
            report["checks"].append("paired-system-guide")
            assert_research_edition_guides(page, origin, output)
            report["checks"].append("bilingual-research-edition-guides")
            assert not report["browser_errors"], report["browser_errors"]
            browser.close()
        guide_spec = importlib.util.spec_from_file_location(
            "ti_guide_browser_acceptance", root / "tests/browser/test_ti_guide_browser.py"
        )
        if guide_spec is None or guide_spec.loader is None:
            raise RuntimeError("Catalogue guide browser acceptance is unavailable")
        guide_module = importlib.util.module_from_spec(guide_spec)
        guide_spec.loader.exec_module(guide_module)
        guide_module.run_acceptance(
            origin + "try/", output / "ti-guide", (site / "try/index.html").read_bytes(), axe_script
        )
        report["passed"] = True
    finally:
        (output / "homepage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if server:
            server.shutdown()
            server.server_close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/homepage"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path, default=Path("tests/browser/node_modules/axe-core/axe.min.js"))
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script, args.browser_executable), indent=2))


if __name__ == "__main__":
    main()
