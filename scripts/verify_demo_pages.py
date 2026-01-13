#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Smoke test that built demo pages load offline."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
READY_SELECTORS = ("main h1", "article h1", "#root", "[data-testid='app']")
DEFAULT_TIMEOUT_MS = int(os.environ.get("PWA_TIMEOUT_MS", "60000"))


def iter_demos() -> list[Path]:
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_dir() and (p / "index.html").exists())


def _readiness_state(page) -> dict[str, object]:
    return page.evaluate(
        """
        (selectors) => {
          const findMatch = selectors.find((sel) => document.querySelector(sel));
          const main = document.querySelector('main');
          const mainHeading = main ? main.querySelector('h1') : null;
          const bodyText = document.body ? document.body.innerText.trim() : '';
          const mainText = main ? main.textContent.trim() : '';
          const bundle = document.querySelector('script[src*="insight.bundle.js"]');
          return {
            match: findMatch || null,
            hasMain: Boolean(main),
            mainHeadingText: mainHeading ? mainHeading.textContent.trim() : '',
            bodyTextLen: bodyText.length,
            mainTextLen: mainText.length,
            hasBundle: Boolean(bundle),
            title: document.title || ''
          };
        }
        """,
        list(READY_SELECTORS),
    )


def _is_ready(demo: Path, state: dict[str, object]) -> tuple[bool, str]:
    match = state.get("match")
    if match:
        return True, f"selector:{match}"
    has_main = bool(state.get("hasMain"))
    body_text_len = int(state.get("bodyTextLen") or 0)
    main_text_len = int(state.get("mainTextLen") or 0)
    if has_main and body_text_len > 40:
        return True, "main+body-text"
    if demo.name == "alpha_agi_insight_v1" and has_main and state.get("hasBundle"):
        heading = str(state.get("mainHeadingText") or "")
        title = str(state.get("title") or "")
        if main_text_len > 0 or body_text_len > 0:
            if heading or "Insight" in title:
                return True, "insight bundle+main"
    return False, ""


def _selector_status(page) -> str:
    status = page.evaluate(
        """
        (selectors) => selectors.map((sel) => {
          return {selector: sel, count: document.querySelectorAll(sel).length};
        })
        """,
        list(READY_SELECTORS),
    )
    return ", ".join(f"{item['selector']}={item['count']}" for item in status)


def _main_snippet(page) -> str:
    try:
        snippet = page.eval_on_selector("main", "el => el.outerHTML")
    except PlaywrightError:
        return ""
    if not snippet:
        return ""
    snippet = " ".join(snippet.split())
    return snippet[:400]


def _log_diagnostics(
    demo: Path,
    page,
    console_messages: list[str],
    page_errors: list[str],
    request_failures: list[str],
    response_failures: list[str],
    missing_assets: list[str],
) -> None:
    selector_status = _selector_status(page)
    print(
        f"No readiness selector found for {demo.name}: selectors={selector_status}",
        file=sys.stderr,
    )
    main_snippet = _main_snippet(page)
    if main_snippet:
        print("<main> snippet:", main_snippet, file=sys.stderr)
    if console_messages:
        print("Console output:", file=sys.stderr)
        for msg in console_messages:
            print(f"  {msg}", file=sys.stderr)
    if page_errors:
        print("Page errors:", file=sys.stderr)
        for err in page_errors:
            print(f"  {err}", file=sys.stderr)
    if request_failures:
        print("Failed requests:", file=sys.stderr)
        for failure in request_failures:
            print(f"  {failure}", file=sys.stderr)
    if response_failures:
        print("Error responses:", file=sys.stderr)
        for failure in response_failures:
            print(f"  {failure}", file=sys.stderr)
    if missing_assets:
        print("Missing local assets:", file=sys.stderr)
        for failure in missing_assets:
            print(f"  {failure}", file=sys.stderr)


def main() -> int:
    demos = iter_demos()
    failures: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for demo in demos:
                page = browser.new_page()
                console_messages: list[str] = []
                page_errors: list[str] = []
                request_failures: list[str] = []
                response_failures: list[str] = []
                missing_assets: list[str] = []

                def _record_console(msg) -> None:
                    if msg.type in {"error", "warning"}:
                        console_messages.append(f"[{msg.type}] {msg.text}")

                def _record_page_error(exc: Exception) -> None:
                    page_errors.append(str(exc))

                def _record_request_failure(req) -> None:
                    failure = req.failure.error_text if req.failure else "unknown"
                    request_failures.append(f"{req.url} -> {failure}")

                def _record_response(response) -> None:
                    if response.status >= 400:
                        response_failures.append(f"{response.url} -> {response.status}")
                    if response.url.startswith("file://"):
                        path = Path(unquote(urlparse(response.url).path))
                        if not path.exists():
                            missing_assets.append(f"{response.url} -> missing")

                page.on("console", _record_console)
                page.on("pageerror", _record_page_error)
                page.on("requestfailed", _record_request_failure)
                page.on("response", _record_response)

                try:
                    page.goto(
                        (demo / "index.html").resolve().as_uri(),
                        wait_until="load",
                        timeout=DEFAULT_TIMEOUT_MS,
                    )
                    page.wait_for_selector("body", timeout=DEFAULT_TIMEOUT_MS)
                    deadline = time.monotonic() + DEFAULT_TIMEOUT_MS / 1000
                    ready = False
                    while time.monotonic() < deadline:
                        state = _readiness_state(page)
                        ready, reason = _is_ready(demo, state)
                        if ready:
                            print(f"{demo.name}: ready ({reason})")
                            break
                        page.wait_for_timeout(250)
                    if not ready:
                        failures.append(demo.name)
                        _log_diagnostics(
                            demo,
                            page,
                            console_messages,
                            page_errors,
                            request_failures,
                            response_failures,
                            missing_assets,
                        )
                finally:
                    page.close()
            browser.close()
        if failures:
            print(f"Demo readiness failed for: {', '.join(failures)}", file=sys.stderr)
            return 1
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
