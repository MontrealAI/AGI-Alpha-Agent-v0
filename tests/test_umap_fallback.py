# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


DEF_GEN = 3


def _run_sim(page):
    page.evaluate("document.querySelector('#simulator-panel #sim-seeds').value='1'")
    page.evaluate(f"document.querySelector('#simulator-panel #sim-gen').value={DEF_GEN}")
    page.evaluate("document.querySelector('#simulator-panel #sim-pop').value=3")
    page.click("#simulator-panel #sim-start")
    page.wait_for_function("window.pop && window.pop[0] && window.pop[0].umap")
    coords = page.evaluate("window.pop.map(p=>p.umap)")
    page.click("#simulator-panel #sim-cancel")
    return coords


def test_umap_fallback_random_coordinates(insight_dist: Path) -> None:
    url = (insight_dist / "index.html").as_uri()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.add_init_script("window.DEBUG = true")
            page.route("**/pyodide.js", lambda route: route.abort())
            page.goto(url)
            page.wait_for_selector("#controls")
            page.wait_for_selector("#simulator-panel")
            first = _run_sim(page)
            second = _run_sim(page)
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    assert first != second
    assert all(len(pt) == 2 for pt in first)
