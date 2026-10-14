# SPDX-License-Identifier: Apache-2.0
"""Check the actual HTTP-loaded kit, local files, downloads and pilot evidence boundary."""

from __future__ import annotations
import argparse
import functools
import hashlib
import json
import os
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--memory-preview", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    server = None
    if not args.memory_preview:
        handler = functools.partial(Quiet, directory=str(ROOT))
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}" if server else None
    results = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                executable_path=os.environ.get("BROWSER_EXECUTABLE")
                or shutil.which("chromium")
                or shutil.which("google-chrome"),
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            for width in [320, 390, 900, 1440]:
                for french in [False, True]:
                    for large in [False, True]:
                        context = browser.new_context(viewport={"width": width, "height": 900}, accept_downloads=True)
                        page = context.new_page()
                        errors = []
                        page.on("pageerror", lambda e: errors.append(str(e)))
                        if args.memory_preview:
                            page.set_content((ROOT / "START_HERE.html").read_text())
                        else:
                            page.goto(origin + "/START_HERE.html", wait_until="load")
                        if french:
                            page.locator("#language").click()
                        if large:
                            page.locator("#size").click()
                        assert page.locator("html").get_attribute("lang") == ("fr" if french else "en")
                        dimensions = page.evaluate("({w:document.documentElement.scrollWidth,v:innerWidth})")
                        assert dimensions["w"] <= dimensions["v"] + 1, dimensions
                        assert not errors, errors
                        assert page.locator("#language").get_attribute("lang") == ("en" if french else "fr")
                        assert page.locator("#size").get_attribute("aria-pressed") == str(large).lower()
                        for control in ["#language", "#size"]:
                            box = page.locator(control).bounding_box()
                            assert box and box["height"] >= 44, control
                        assert page.locator("#people").inner_text().find("0 OBSERVED PARTICIPANTS") >= 0
                        for anchor in page.locator('a[href^="#"]').all():
                            assert page.locator(anchor.get_attribute("href")).count() == 1
                        if width == 1440 and not french and not large:
                            page.screenshot(path=str(args.output / "desktop.png"), full_page=True)
                        if width == 320 and french and large:
                            page.screenshot(path=str(args.output / "mobile-fr-large.png"), full_page=True)
                        results.append({"width": width, "french": french, "large": large, "passed": True})
                        context.close()
            if not args.memory_preview:
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                for relative in [
                    "START_HERE.html",
                    "PILOT_PROTOCOL.html",
                    "pilot/status.json",
                    "SOURCE_PROVENANCE.json",
                    "02_Work_Products/Task_A/after/index.html",
                    "02_Work_Products/Task_B/after/index.html",
                ]:
                    response = page.request.get(origin + "/" + relative)
                    assert response.ok and response.body() == (ROOT / relative).read_bytes(), relative
                page.goto(origin + "/START_HERE.html?lang=fr&text=large")
                assert page.locator("html").get_attribute("lang") == "fr"
                assert page.locator("#size").get_attribute("aria-pressed") == "true"
                page.locator("#language").focus()
                page.keyboard.press("Enter")
                assert page.locator("html").get_attribute("lang") == "en"
                page.locator("#size").focus()
                page.keyboard.press("Space")
                assert page.locator("#size").get_attribute("aria-pressed") == "false"
                page.reload()
                assert page.locator("html").get_attribute("lang") == "en"
                assert page.locator("#size").get_attribute("aria-pressed") == "false"
                page.goto(origin + "/02_Work_Products/Task_A/after/index.html")
                page.locator("#service").select_option("foundations")
                page.locator("#seats").fill("10")
                page.locator("#calculate").click()
                assert "445.50" in page.locator("#total").inner_text()
                assert page.locator("#download").is_disabled()
                page.locator("#accept").check()
                with page.expect_download() as download:
                    page.locator("#download").click()
                quote = args.output / "quote-before.json"
                download.value.save_as(quote)
                with page.expect_download() as download:
                    page.locator("#save-draft").click()
                draft = args.output / "saved-draft.json"
                download.value.save_as(draft)
                context.close()
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()
                page.goto(origin + "/02_Work_Products/Task_A/after/index.html")
                page.locator("#restore").set_input_files(draft)
                page.wait_for_function("document.querySelector('#status').textContent.includes('restored')")
                assert not page.locator("#accept").is_checked() and page.locator("#download").is_disabled()
                page.locator("#calculate").click()
                page.locator("#accept").check()
                with page.expect_download() as download:
                    page.locator("#download").click()
                restored = args.output / "quote-restored.json"
                download.value.save_as(restored)
                assert quote.read_bytes() == restored.read_bytes()
                page.goto((ROOT / "START_HERE.html").as_uri())
                page.locator("#language").click()
                assert page.locator("html").get_attribute("lang") == "fr"
                page.goto((ROOT / "02_Work_Products/Task_B/after/index.html").as_uri())
                page.locator("#service").select_option("design")
                page.locator("#seats").fill("8")
                page.locator("#calculate").click()
                assert "433.50" in page.locator("#total").inner_text()
                page.goto(origin + "/PILOT_PROTOCOL.html")
                page.pdf(path=str(args.output / "PILOT_PROTOCOL.pdf"), format="A4")
                if (ROOT / "01_Report/report.html").exists():
                    page.goto(origin + "/01_Report/report.html")
                    page.pdf(path=str(args.output / "REPORT.pdf"), format="A4", print_background=False)
                context.close()
                context = browser.new_context(java_script_enabled=False)
                page = context.new_page()
                page.goto(origin + "/START_HERE.html")
                assert "Try the work." in page.locator("h1").inner_text()
                context.close()
            report = {
                "schema": "study-kit-browser/v1",
                "mode": "memory-preview-only" if args.memory_preview else "HTTP-and-file",
                "combinations": results,
                "source": hashlib.sha256((ROOT / "START_HERE.html").read_bytes()).hexdigest(),
                "browser": browser.version,
                "humanParticipants": 0,
                "actualRepositoryExecutorTested": False,
                "httpDownloadsAndRecovery": not args.memory_preview,
                "localFileOpening": not args.memory_preview,
                "productionIsolationQualified": False,
                "keyboardAndReadingPreferences": not args.memory_preview,
            }
            (args.output / "PUBLICATION_CHECKS.json").write_text(json.dumps(report, indent=2) + "\n")
            browser.close()
            print(json.dumps(report, indent=2))
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
