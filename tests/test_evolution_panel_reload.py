# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


def test_evolution_panel_persists_after_reload(insight_dist: Path) -> None:
    url = (insight_dist / "index.html").as_uri() + "#s=1&p=3&g=3"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_selector("#controls")
            page.wait_for_function("window.gen >= 3")
            page.reload()
            page.wait_for_selector("#controls")
            page.wait_for_function("document.querySelectorAll('#evolution-panel table tr').length > 1")
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
