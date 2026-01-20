# SPDX-License-Identifier: Apache-2.0
import http.server
import threading
import shutil
from functools import partial
from pathlib import Path
import re

import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


def _start_server(directory: Path):
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("localhost", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def test_workbox_hash_mismatch(tmp_path: Path, insight_dist: Path) -> None:
    dist = tmp_path / "dist"
    shutil.copytree(insight_dist, dist)
    sw_file = dist / "service-worker.js"
    text = sw_file.read_text()
    text = re.sub(r"(WORKBOX_SW_HASH = ')([^']+)(')", r"\1sha384-invalid\3", text)
    sw_file.write_text(text)

    server, thread = _start_server(dist)
    host, port = server.server_address
    url = f"http://{host}:{port}/index.html"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.goto(url)
            page.wait_for_selector("#controls")
            page.wait_for_function("document.getElementById('toast').textContent.includes('offline mode disabled')")
            assert page.evaluate("navigator.serviceWorker.controller") is None
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    finally:
        server.shutdown()
        thread.join()
