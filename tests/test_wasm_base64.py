# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import http.server
import threading
from functools import partial
import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402
from playwright._impl._errors import Error as PlaywrightError  # noqa: E402


def test_pyodide_base64_global(insight_dist: Path) -> None:
    handler = partial(http.server.SimpleHTTPRequestHandler, directory=str(insight_dist))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(url)
            page.wait_for_function(
                "typeof window.PYODIDE_WASM_BASE64 === 'string' && window.PYODIDE_WASM_BASE64.length > 0"
            )
            val = page.evaluate("window.PYODIDE_WASM_BASE64")
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    finally:
        server.shutdown()
        thread.join()
    assert val, "PYODIDE_WASM_BASE64 not set"
