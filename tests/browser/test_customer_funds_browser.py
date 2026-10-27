# SPDX-License-Identifier: Apache-2.0
"""Verify the actual bilingual receipt journey and its exported evidence."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    checks: list[str] = []
    errors: list[str] = []
    try:
        with tempfile.TemporaryDirectory(
            prefix="customer-funds-browser-"
        ) as directory, sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or None)
            page = browser.new_page(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/flywheel/")
            expect(page.locator("#customer-title")).to_contain_text("Accountable cash")
            expect(page.locator("#customer-stage option")).to_have_count(7)
            for index, expected in (
                (1, "$2,000.00"),
                (2, "$2,000.00"),
                (3, "$400.00"),
                (4, "$1,600.00"),
                (5, "$300.00"),
                (6, "$1,600.00"),
            ):
                page.locator("#customer-stage").select_option(str(index))
                expect(page.locator("#customer-balances")).to_contain_text(expected)
                expect(page.locator("#customer-operating-boundary")).to_contain_text("$0.00")
                checks.append(f"receipt stage {index}: synthetic funds excluded")
            expect(page.locator("#customer-margin")).to_contain_text("$2,900.21")
            expect(page.locator("#customer-margin-scope")).to_contain_text("Actual collections: USD 0")
            expect(page.locator("#customer-alpha")).to_contain_text("unmeasured")
            checks.append("modeled contribution, actual collections and separate Alpha limits")
            expected_packet = json.loads(
                (ROOT / "scripts/templates/alpha-flywheel/customer-evidence.json").read_bytes()
            )
            with page.expect_download() as downloading:
                page.locator("#customer-export").click()
            destination = Path(directory) / "receipt.json"
            downloading.value.save_as(destination)
            assert json.loads(destination.read_bytes()) == expected_packet
            checks.append("complete exact evidence export retains scope and source identities")
            page.locator("#customer-funds details").nth(1).locator("summary").click()
            expect(page.locator("#customer-confirmation")).to_contain_text("SHORTFALL")
            expect(page.locator("#customer-confirmation")).to_contain_text("-$720.00")
            checks.append("frozen policy keeps loss and prefunding shortfall visible")
            for language in ("en", "fr"):
                page.locator("#lang-" + language).click()
                expect(page.locator("#customer-stage")).to_have_value("6")
                expect(page.locator("#customer-title")).to_contain_text(
                    "Accountable cash" if language == "en" else "Trésorerie traçable"
                )
                for width in (320, 390, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
                    checks.append(f"{language} {width}px no horizontal document overflow")
            page.screenshot(path=str(ROOT.parent / "customer-mobile.png"), full_page=True)
            assert errors == [], errors
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print(json.dumps({"checks": checks, "count": len(checks), "page_errors": errors}, indent=2))


if __name__ == "__main__":
    main()
