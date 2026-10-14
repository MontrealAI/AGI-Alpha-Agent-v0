# SPDX-License-Identifier: Apache-2.0
"""Check the report reader, not the original computer-use experiment."""
from __future__ import annotations

import hashlib
import json
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / "docs/reports/computer-use-study"


def main() -> None:
    from playwright.sync_api import sync_playwright

    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(STUDY))
    )
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    records: list[dict[str, object]] = []
    try:
        with TemporaryDirectory() as temporary, sync_playwright() as driver:
            output = Path(temporary)
            browser = driver.chromium.launch()
            for width in (320, 390, 900, 1440):
                for french in (False, True):
                    for large in (False, True):
                        page = browser.new_page(viewport={"width": width, "height": 1000})
                        errors: list[str] = []
                        page.on("pageerror", lambda error: errors.append(str(error)))
                        page.goto(origin + "/index.html" + ("?lang=fr" if french else ""))
                        if large:
                            page.locator("#text-size").click()
                        assert page.locator("html").get_attribute("lang") == ("fr" if french else "en")
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                        assert not errors, errors
                        page.locator("#language").click()
                        assert page.locator("html").get_attribute("lang") == ("en" if french else "fr")
                        records.append({"width": width, "french": french, "large": large, "passed": True})
                        page.close()
            page = browser.new_page(accept_downloads=True)
            page.goto(origin + "/index.html")
            with page.expect_download() as downloaded:
                page.locator('a[href="REPORT.md"][download]').click()
            downloaded.value.save_as(output / "REPORT.md")
            assert (output / "REPORT.md").read_bytes() == (STUDY / "REPORT.md").read_bytes()
            response = page.request.get(origin + "/report-pack.zip")
            assert response.ok and response.body() == (STUDY / "report-pack.zip").read_bytes()
            page.goto(origin + "/report.html")
            assert page.locator("h1").count() == 1
            page.emulate_media(media="print")
            assert page.locator("html").evaluate("e => getComputedStyle(e).colorScheme") == "light"
            assert page.locator("html").evaluate("e => getComputedStyle(e).backgroundColor") == "rgb(255, 255, 255)"
            assert page.locator("thead th").first.evaluate("e => getComputedStyle(e).color") == "rgb(17, 17, 17)"
            page.pdf(path=str(output / "report.pdf"), prefer_css_page_size=True)
            records.append({"markdownDownloadExact": True, "localPackBytesExact": True, "printContrast": True, "whitePrintMargins": True})
            page.close()
            extracted = output / "offline"
            extracted.mkdir()
            with ZipFile(STUDY / "report-pack.zip") as archive:
                for name in archive.namelist():
                    target = (extracted / name).resolve()
                    assert target.is_relative_to(extracted.resolve())
                    target.write_bytes(archive.read(name))
            for line in (extracted / "SHA256SUMS").read_text().splitlines():
                expected, name = line.split("  ", 1)
                assert hashlib.sha256((extracted / name).read_bytes()).hexdigest() == expected
            offline = browser.new_context(offline=True)
            page = offline.new_page()
            page.goto((extracted / "START_HERE.html").as_uri())
            page.locator("#language").click()
            assert page.locator("html").get_attribute("lang") == "fr"
            page.locator("#text-size").click()
            assert page.locator("#text-size").get_attribute("aria-pressed") == "true"
            records.append({"offlineFileReopen": True, "internalChecksums": True})
            offline.close()
            plain = browser.new_context(java_script_enabled=False)
            page = plain.new_page()
            page.goto(origin + "/index.html")
            assert "Useful work." in page.locator("h1").inner_text()
            assert "Zero human participants" in page.locator("main").inner_text()
            records.append({"noJavaScriptReader": True})
            plain.close()
            print(json.dumps({"scope": "Public report only; local HTTP and offline file paths, not live Pages or the original study", "browser": browser.version, "checks": records}, indent=2))
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
