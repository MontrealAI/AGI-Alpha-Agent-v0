#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Smoke test that built demo pages load offline."""
from __future__ import annotations

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, Error as PlaywrightError

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"


def iter_demos() -> list[Path]:
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_dir() and (p / "index.html").exists())


def main() -> int:
    demos = iter_demos()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for demo in demos:
                page = browser.new_page()
                page.goto((demo / "index.html").resolve().as_uri())
                page.wait_for_selector("body")
                page.wait_for_selector("h1")
                page.close()
            browser.close()
        return 0
    except PlaywrightError as exc:
        print(f"Playwright error: {exc}", file=sys.stderr)
        if "Executable doesn't exist" in str(exc):
            print(
                "Browsers are missing. Run `python -m playwright install chromium` "
                "(plus `python -m playwright install-deps` on Linux) to install them.",
                file=sys.stderr,
            )
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"Demo check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
