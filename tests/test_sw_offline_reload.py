# SPDX-License-Identifier: Apache-2.0
import http.server
import threading
from functools import partial
from pathlib import Path

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


def test_offline_reload_no_errors(insight_dist: Path) -> None:
    server, thread = _start_server(insight_dist)
    host, port = server.server_address
    url = f"http://{host}:{port}/index.html"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            errors: list[str] = []
            page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda err: errors.append(str(err)))

            page.goto(url)
            page.wait_for_selector("#controls")
            page.wait_for_function("navigator.serviceWorker.ready")

            context.set_offline(True)
            page.reload()
            page.wait_for_selector("#controls")
            context.set_offline(False)

            assert not errors, f"Console errors: {errors}"
            assert page.evaluate("navigator.serviceWorker.controller !== null")
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    finally:
        server.shutdown()
        thread.join()
