# SPDX-License-Identifier: Apache-2.0
"""Verify a new build reloads the Insight demo."""

import http.server
import threading
import subprocess
from functools import partial
from pathlib import Path
import shutil

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


@pytest.mark.skipif(not shutil.which("npm"), reason="npm not installed")  # type: ignore[misc]
def test_update_triggers_reload(tmp_path: Path, insight_repo: Path, insight_dist: Path) -> None:
    repo = insight_repo
    subprocess.check_call(["npm", "run", "build"], cwd=repo)

    dist = insight_dist
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
            page.wait_for_function("navigator.serviceWorker.ready")
            page.evaluate("window.__loadCount = (window.__loadCount || 0) + 1")

            # rebuild to create a new service worker
            subprocess.check_call(["npm", "run", "build"], cwd=repo)
            page.evaluate("navigator.serviceWorker.getRegistration().then(r => r.update())")
            page.wait_for_function("document.getElementById('toast').textContent.includes('Refreshing')")
            page.wait_for_function("performance.getEntriesByType('navigation').length > 1")
            assert page.evaluate("performance.getEntriesByType('navigation').length") >= 2
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    finally:
        server.shutdown()
        thread.join()
