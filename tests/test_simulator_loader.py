# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


def test_simulator_loader_overlay(insight_dist: Path) -> None:
    url = (insight_dist / "index.html").as_uri()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_selector("#controls")
            page.evaluate("document.querySelector('#simulator-panel #sim-gen').value=1")
            page.evaluate("document.querySelector('#simulator-panel #sim-pop').value=1")
            page.click("#simulator-panel #sim-start")
            page.wait_for_selector("#sim-loader", state="visible")
            page.wait_for_function("document.querySelector('#sim-status').textContent.includes('gen 1')")
            page.wait_for_selector("#sim-loader", state="hidden")
            page.click("#simulator-panel #sim-cancel")
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
