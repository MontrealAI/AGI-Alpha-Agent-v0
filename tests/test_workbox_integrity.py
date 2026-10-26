# SPDX-License-Identifier: Apache-2.0
import http.server
import re
import shutil
import threading
from functools import partial
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect
sync_playwright = pw.sync_playwright
PlaywrightError = pw.Error


def _start_server(directory: Path):
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("localhost", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_workbox_hash_mismatch(tmp_path: Path, insight_dist: Path) -> None:
    assert (insight_dist / "index.html").is_file(), "Missing Insight dist index.html"
    assert (insight_dist / "service-worker.js").is_file(), "Missing Insight service-worker.js"
    dist = tmp_path / "dist"
    shutil.copytree(insight_dist, dist)
    sw_file = dist / "service-worker.js"
    text = sw_file.read_text()
    text, replacements = re.subn(r"WORKBOX_SW_HASH\s*=\s*(['\"])[^'\"]+\1", "WORKBOX_SW_HASH = 'sha384-invalid'", text)
    assert replacements == 1
    sw_file.write_text(text)

    server, thread = _start_server(dist)
    host, port = server.server_address
    url = f"http://{host}:{port}/index.html"
    try:
        with sync_playwright() as p:
            try:
                browser = p.chromium.launch()
            except PlaywrightError as exc:
                if "Executable doesn't exist" in str(exc):
                    pytest.skip(f"Playwright browser not installed: {exc}")
                raise
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(url)
                page.wait_for_selector("#controls")
                # Locator assertions run in Playwright's isolated world; the
                # application's CSP must continue to prohibit unsafe eval.
                expect(page.locator("#toast")).to_contain_text("offline mode disabled", timeout=30000)
                assert page.locator("html").evaluate("() => navigator.serviceWorker.controller === null")
            finally:
                browser.close()
    finally:
        server.shutdown()
        thread.join()
