# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


def test_install_button_shows_on_event(insight_dist: Path) -> None:
    url = (insight_dist / "index.html").as_uri()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_selector("#controls")
            assert page.is_hidden("#install-btn")
            page.evaluate("window.dispatchEvent(new Event('beforeinstallprompt'))")
            page.wait_for_selector("#install-btn", state="visible")
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
