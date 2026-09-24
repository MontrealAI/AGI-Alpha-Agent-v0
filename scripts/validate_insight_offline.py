#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require the real Insight build to load and reload through its service worker."""

from __future__ import annotations

import argparse
from functools import partial
import http.server
import json
from pathlib import Path
import threading

from playwright.sync_api import sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(http.server.SimpleHTTPRequestHandler, directory=str(args.dist.resolve()))
    )
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f"http://127.0.0.1:{server.server_port}/index.html"
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            page.wait_for_function(
                "typeof window.PYODIDE_WASM_BASE64 === 'string' && window.PYODIDE_WASM_BASE64.length > 0"
            )
            page.wait_for_function("navigator.serviceWorker.controller !== null", timeout=60000)
            page.evaluate("caches.open('unrelated-application-cache')")
            context.set_offline(True)
            response = page.reload()
            assert response and response.ok and response.from_service_worker
            page.wait_for_function(
                "typeof window.PYODIDE_WASM_BASE64 === 'string' && window.PYODIDE_WASM_BASE64.length > 0"
            )
            assert page.locator("#controls").is_visible()
            assert page.evaluate("typeof window.d3 !== 'undefined'")
            assert page.evaluate("async () => (await fetch('style.css')).ok")
            assert page.evaluate("async () => (await fetch('assets/src/i18n/en.json')).ok")
            assert "unrelated-application-cache" in page.evaluate("caches.keys()")
            assert not errors, errors
            evidence = {
                "passed": True,
                "offline_document_from_service_worker": True,
                "checks": [
                    "application initialized",
                    "embedded WASM",
                    "D3",
                    "styles",
                    "translations",
                    "unrelated cache preserved",
                ],
                "page_errors": errors,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(evidence, indent=2) + "\n")
            browser.close()
    finally:
        server.shutdown()
        worker.join()
        server.server_close()
    print(json.dumps(evidence))


if __name__ == "__main__":
    main()
