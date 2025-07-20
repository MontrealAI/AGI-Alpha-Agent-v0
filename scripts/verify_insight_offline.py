#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Smoke test that the Insight PWA loads offline."""

from __future__ import annotations

import sys
from playwright.sync_api import Error as PlaywrightError, sync_playwright
import time


URL = "http://localhost:8000/alpha_agi_insight_v1/"

TIMEOUT_MS = 90_000


def _print_console(logs: list[str]) -> None:
    if logs:
        print("--- Browser console logs ---", file=sys.stderr)
        for line in logs:
            print(line, file=sys.stderr)


def _attempt() -> bool:
    logs: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            page.on("console", lambda msg: logs.append(f"[{msg.type}] {msg.text}"))
            page.goto(URL)
            page.wait_for_function("navigator.serviceWorker.ready", timeout=TIMEOUT_MS)
            page.wait_for_selector("body", timeout=TIMEOUT_MS)
            context.set_offline(True)
            page.reload()
            page.wait_for_selector("body", timeout=TIMEOUT_MS)
            page.wait_for_selector("#tree-container .node", timeout=TIMEOUT_MS)
            browser.close()
        return True
    except PlaywrightError as exc:
        print(f"Playwright error: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001
        print(f"Offline check failed: {exc}", file=sys.stderr)

    _print_console(logs)
    return False


def main() -> int:
    for attempt in range(2):
        if _attempt():
            return 0
        if attempt == 0:
            print("Retrying offline check...", file=sys.stderr)
            time.sleep(2)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
