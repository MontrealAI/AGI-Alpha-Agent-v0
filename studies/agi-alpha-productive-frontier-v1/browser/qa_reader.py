# SPDX-License-Identifier: Apache-2.0
"""Verify exact PDF extraction, local links and no-JavaScript reading layouts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import fitz
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def main(chromium: str, screenshots: Path, structure_only: bool = False) -> None:
    root = Path(__file__).resolve().parent
    screenshots.mkdir(parents=True, exist_ok=True)
    reader = root / "paper.html"
    source = reader.read_bytes()
    soup = BeautifulSoup(source, "html.parser")
    manifest = json.loads((root / "paper_reader_manifest.json").read_text())
    sections = soup.select(".page-text")
    assert len(sections) == manifest["pages"]
    assert not soup.find_all("script")
    assert hashlib.sha256(source).hexdigest() == manifest["html_sha256"]
    report = {
        "pages": len(sections),
        "javascript_elements": 0,
        "source_binding": "not_run_structure_only" if structure_only else "exact_pdf_page_text",
        "html_sha256": manifest["html_sha256"],
        "source_pdf_sha256": manifest["source_pdf_sha256"],
        "local_links": [],
        "viewports": {},
    }
    if not structure_only:
        raw = (root / manifest["source_pdf"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["source_pdf_sha256"]
        with fitz.open(stream=raw, filetype="pdf") as document:
            assert len(document) == len(sections)
            for section, page, record in zip(sections, document, manifest["page_text"]):
                exact = page.get_text("text", sort=True)
                assert section.get_text() == exact
                assert hashlib.sha256(exact.encode()).hexdigest() == record["sha256"]
    hrefs = sorted({element["href"] for element in soup.find_all("a", href=True)})
    for href in hrefs:
        if href.startswith("#"):
            assert soup.find(id=href[1:]) is not None, href
        else:
            assert not href.startswith(("https:", "http:", "//")), href
            assert (root / href.split("#", 1)[0]).is_file(), href
            report["local_links"].append(href)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium, headless=True, args=["--no-sandbox"])
        context = browser.new_context(
            java_script_enabled=False, reduced_motion="reduce", viewport={"width": 1440, "height": 1000}
        )
        page = context.new_page()
        page.goto(reader.as_uri())
        assert page.locator(".page-text").count() == manifest["pages"]
        assert page.locator("#page-1 .page-text").is_visible()
        page.screenshot(path=str(screenshots / "reader_desktop.png"))
        page.locator('a[href="#page-10"]').first.click()
        assert page.locator("#page-10 .page-text").is_visible()
        assert page.evaluate("Math.abs(document.getElementById('page-10').getBoundingClientRect().top) < 30")
        page.screenshot(path=str(screenshots / "reader_page10.png"))
        for width in [1440, 390, 320]:
            page.set_viewport_size({"width": width, "height": 900})
            page.goto(reader.as_uri())
            overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
            assert not overflow, width
            report["viewports"][str(width)] = {"page_overflow": overflow, "javascript_disabled": True}
            if width == 390:
                page.screenshot(path=str(screenshots / "reader_mobile.png"))
        browser.close()
    name = "reader_structure_qa.json" if structure_only else "reader_qa_report.json"
    (root / name).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--screenshots", type=Path, required=True)
    parser.add_argument("--structure-only", action="store_true")
    args = parser.parse_args()
    main(args.chromium, args.screenshots, args.structure_only)
