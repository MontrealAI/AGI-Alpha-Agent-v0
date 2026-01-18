# SPDX-License-Identifier: Apache-2.0
"""Verify quickstart PDF served from cache when offline."""

from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


def test_quickstart_offline(insight_dist: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    dist = insight_dist
    pdf_src = repo / "docs/insight_browser_quickstart.pdf"
    pdf_dest = dist / "insight_browser_quickstart.pdf"
    if not pdf_dest.exists() and pdf_src.exists():
        pdf_dest.write_bytes(pdf_src.read_bytes())

    url = (dist / "index.html").as_uri()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            page.wait_for_selector("#controls")
            page.wait_for_function("navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            assert page.evaluate("(await fetch('insight_browser_quickstart.pdf')).ok")
            context.set_offline(True)
            page.reload()
            page.wait_for_selector("#controls")
            assert page.evaluate("(await fetch('insight_browser_quickstart.pdf')).ok")
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
