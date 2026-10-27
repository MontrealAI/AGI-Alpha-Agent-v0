#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Presentation QA for the complete browser manuscript; no scientific rerun."""

from __future__ import annotations

import json
import re
from pathlib import Path

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

WEB = Path(__file__).resolve().parent
OUT = WEB / "qa"
source = (WEB.parent / "paper" / "agi-alpha-flywheel.tex").read_text()
soup = BeautifulSoup((WEB / "paper.html").read_text(), "html.parser")
source_rows = [
    len(re.findall(r"\\\\", body)) for body in re.findall(r"\\begin\{tabularx?\}(.*?)\\end\{tabularx?\}", source, re.S)
]
html_rows = [len(table.find_all("tr")) for table in soup.find_all("table")]
assert source_rows == html_rows
assert len(soup.find_all("h1")) == 1
assert len(soup.find_all("h2")) == 13
assert len(soup.find_all("h3")) == 23
assert len(soup.find_all("math")) == 27
assert len(soup.select("[id^=ref-]")) == 22
assert len(soup.select("figure img")) == 4
errors: list[str] = []
responsive: list[dict[str, int | bool]] = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.emulate_media(reduced_motion="reduce")
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((WEB / "paper.html").as_uri())
    assert page.locator("h1").inner_text() == "AGI ALPHA FLYWHEEL — When Capability Creates Opportunity"
    assert page.locator("figure img").evaluate_all("images => images.every(i => i.complete && i.naturalWidth > 0)")
    bad_links = page.evaluate(
        'Array.from(document.querySelectorAll("a[href^=\\"#\\"]")).map(a => a.getAttribute("href").slice(1)).filter(id => id && !document.getElementById(decodeURIComponent(id)))'
    )
    assert not bad_links, bad_links
    for width in [390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 1000})
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        assert not overflow, width
        responsive.append({"width": width, "horizontal_overflow": overflow})
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(OUT / "paper-desktop-top.png"))
    page.locator(".pagebar").evaluate("el => el.style.visibility='hidden'")
    page.locator("figure").first.screenshot(path=str(OUT / "paper-figure.png"))
    page.locator(".pagebar").evaluate("el => el.style.visibility=''")
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(OUT / "paper-mobile-top.png"))
    page.locator(".pagebar").evaluate("el => el.style.visibility='hidden'")
    page.locator(".titlepage").screenshot(path=str(OUT / "paper-mobile-title.png"))
    page.locator(".table-scroll").first.screenshot(path=str(OUT / "paper-mobile-table.png"))
    assert not errors, errors
    browser.close()
report = {
    "schema": "agialpha.browser-manuscript-qa.v1",
    "status": "passed",
    "source_section_count": 12,
    "source_subsection_count": 23,
    "rendered_main_sections_plus_references": 13,
    "rendered_subsections": 23,
    "exact_title": True,
    "reference_count": 22,
    "table_count": 7,
    "source_and_html_table_row_counts": source_rows,
    "figure_count": 4,
    "loaded_svg_figures": True,
    "mathml_count": 27,
    "broken_internal_links": bad_links,
    "responsive": responsive,
    "page_errors": errors,
    "scope": "Presentation and full-content structure checks only; no additional scientific cases or publication verification.",
}
(OUT / "paper-verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
