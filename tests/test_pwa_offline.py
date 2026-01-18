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


def test_quickstart_pdf_offline(insight_dist: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    pdf_src = repo / "docs/insight_browser_quickstart.pdf"
    dist = insight_dist
    pdf_dest = dist / "insight_browser_quickstart.pdf"
    if not pdf_dest.exists() and pdf_src.exists():
        pdf_dest.write_bytes(pdf_src.read_bytes())

    server, thread = _start_server(insight_dist)
    host, port = server.server_address
    url = f"http://{host}:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.goto(url + "/index.html")
            page.wait_for_selector("#controls")
            page.wait_for_function("navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            pdf_cached = page.evaluate(
                """
                (async () => {
                  const names = await caches.keys();
                  for (const n of names) {
                    const c = await caches.open(n);
                    if (await c.match('insight_browser_quickstart.pdf')) {
                      return true;
                    }
                  }
                  return false;
                })()
                """
            )
            assert pdf_cached, "PDF not cached by service worker"
            context.set_offline(True)
            resp = page.goto(url + "/insight_browser_quickstart.pdf")
            assert resp and resp.ok, "PDF not served offline"
            page.reload()
            resp = page.goto(url + "/insight_browser_quickstart.pdf")
            assert resp and resp.ok, "PDF not served offline after reload"
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    finally:
        server.shutdown()
        thread.join()


def test_cache_cleanup_on_activate(insight_dist: Path) -> None:
    server, thread = _start_server(insight_dist)
    host, port = server.server_address
    url = f"http://{host}:{port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            context.add_init_script("caches.open('legacy-cache')")
            page = context.new_page()
            page.goto(url + "/index.html")
            page.wait_for_selector("#controls")
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            names = page.evaluate("caches.keys()")
            assert "legacy-cache" not in names
            browser.close()
    except PlaywrightError as exc:
        pytest.skip(f"Playwright browser not installed: {exc}")
    finally:
        server.shutdown()
        thread.join()
