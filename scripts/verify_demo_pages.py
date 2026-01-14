#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Smoke test that built demo pages load offline."""
from __future__ import annotations

import os
import sys
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
READY_SELECTORS = (
    "main h1",
    "article h1",
    "html[data-insight-ready='1']",
    "#root",
    "[data-testid='app']",
)
DEFAULT_TIMEOUT_MS = int(os.environ.get("PWA_TIMEOUT_MS", "60000"))
MAX_ATTEMPTS = int(os.environ.get("PWA_DEMO_ATTEMPTS", "3"))


class _SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def iter_demos() -> list[Path]:
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_dir() and (p / "index.html").exists())


def _readiness_state(page) -> dict[str, object]:
    return page.evaluate(
        """
        (selectors) => {
          const findMatch = selectors.find((sel) => document.querySelector(sel));
          const main = document.querySelector('main');
          const mainHeading = main ? main.querySelector('h1') : null;
          const root = document.querySelector('#root');
          const bodyText = document.body ? document.body.innerText.trim() : '';
          const mainText = main ? main.textContent.trim() : '';
          const bundle = document.querySelector('script[src*="insight.bundle"]');
          const insightReady = document.documentElement?.dataset?.insightReady === '1';
          return {
            match: findMatch || null,
            hasMain: Boolean(main),
            hasRoot: Boolean(root),
            rootChildCount: root ? root.childElementCount : 0,
            mainHeadingText: mainHeading ? mainHeading.textContent.trim() : '',
            bodyTextLen: bodyText.length,
            mainTextLen: mainText.length,
            hasBundle: Boolean(bundle),
            insightReady,
            title: document.title || ''
          };
        }
        """,
        list(READY_SELECTORS),
    )


def _is_ready(demo: Path, state: dict[str, object]) -> tuple[bool, str]:
    match = state.get("match")
    if match in {"main h1", "article h1"}:
        return True, f"selector:{match}"
    if match == "html[data-insight-ready='1']":
        return True, "insight-ready"
    if match in {"#root", "[data-testid='app']"}:
        root_child_count = int(state.get("rootChildCount") or 0)
        if root_child_count > 0:
            return True, "root+children"
    has_main = bool(state.get("hasMain"))
    has_root = bool(state.get("hasRoot"))
    body_text_len = int(state.get("bodyTextLen") or 0)
    main_text_len = int(state.get("mainTextLen") or 0)
    if has_main and body_text_len > 40:
        return True, "main+body-text"
    if has_root and body_text_len > 40:
        return True, "root+body-text"
    if body_text_len > 120:
        return True, "body-text"
    if demo.name == "alpha_agi_insight_v1" and has_main and state.get("hasBundle"):
        heading = str(state.get("mainHeadingText") or "")
        title = str(state.get("title") or "")
        if state.get("insightReady"):
            return True, "insight marker"
        if main_text_len > 0 or body_text_len > 0:
            if heading or "Insight" in title:
                return True, "insight bundle+main"
    return False, ""


def _selector_status(page) -> str:
    try:
        status = page.evaluate(
            """
            (selectors) => selectors.map((sel) => {
              return {selector: sel, count: document.querySelectorAll(sel).length};
            })
            """,
            list(READY_SELECTORS),
        )
    except PlaywrightError:
        return "unavailable"
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


def _extract_failure_text(failure: object | None) -> str:
    """Extract a failure message from a Playwright request failure payload."""
    if failure is None:
        return "unknown"
    if callable(failure):
        try:
            failure = failure()
        except Exception:
            return "unknown"
    if isinstance(failure, str):
        return failure
    if isinstance(failure, dict):
        return str(failure.get("errorText") or failure.get("error_text") or "unknown")
    error_text = getattr(failure, "error_text", None) or getattr(failure, "errorText", None)
    if error_text:
        return str(error_text)
    return str(failure)


def _start_docs_server() -> tuple[ThreadingHTTPServer, Thread, str]:
    handler = partial(_SilentHandler, directory=str(DOCS_DIR))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, name="docs-server", daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    return server, thread, f"http://{host}:{port}"


def _build_demo_url(base_url: str, demo: Path) -> str:
    rel_path = demo.relative_to(DOCS_DIR).as_posix()
    return f"{base_url.rstrip('/')}/{rel_path}/index.html"


def _log_diagnostics(
    demo: Path,
    page,
    url: str,
    response_status: int | None,
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
    if url:
        status = response_status if response_status is not None else "unknown"
        print(f"URL: {url} (status={status})", file=sys.stderr)
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
    server: ThreadingHTTPServer | None = None
    server_thread: Thread | None = None
    base_url = ""
    try:
        server, server_thread, base_url = _start_docs_server()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(service_workers="block")
            for demo in demos:
                last_error: str | None = None
                last_url = ""
                last_status: int | None = None
                last_console: list[str] = []
                last_page_errors: list[str] = []
                last_request_failures: list[str] = []
                last_response_failures: list[str] = []
                last_missing_assets: list[str] = []
                ready = False
                page_for_diagnostics = None

                for attempt in range(1, MAX_ATTEMPTS + 1):
                    page = context.new_page()
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
                        try:
                            failure = _extract_failure_text(req.failure)
                            request_failures.append(f"{req.url} -> {failure}")
                        except Exception as exc:  # noqa: BLE001
                            request_failures.append(f"{req.url} -> handler error: {exc}")

                    def _record_response(response) -> None:
                        if response.status >= 400:
                            response_failures.append(f"{response.url} -> {response.status}")
                        if response.url.startswith(base_url):
                            if response.status == 404:
                                missing_assets.append(f"{response.url} -> missing")

                    page.on("console", _record_console)
                    page.on("pageerror", _record_page_error)
                    page.on("requestfailed", _record_request_failure)
                    page.on("response", _record_response)

                    try:
                        response = page.goto(
                            _build_demo_url(base_url, demo),
                            wait_until="load",
                            timeout=DEFAULT_TIMEOUT_MS,
                        )
                        last_url = page.url
                        last_status = response.status if response else None
                        page.wait_for_selector("body", timeout=DEFAULT_TIMEOUT_MS)
                        deadline = time.monotonic() + DEFAULT_TIMEOUT_MS / 1000
                        while time.monotonic() < deadline:
                            state = _readiness_state(page)
                            ready, reason = _is_ready(demo, state)
                            if ready:
                                print(f"{demo.name}: ready ({reason})")
                                break
                            page.wait_for_timeout(250)
                        if ready:
                            break
                        last_error = "readiness timeout"
                    except PlaywrightError as exc:
                        last_error = str(exc)
                    finally:
                        last_console = console_messages
                        last_page_errors = page_errors
                        last_request_failures = request_failures
                        last_response_failures = response_failures
                        last_missing_assets = missing_assets
                        if attempt == MAX_ATTEMPTS and not ready:
                            page_for_diagnostics = page
                        else:
                            page.close()

                    if attempt < MAX_ATTEMPTS:
                        time.sleep(1)

                if not ready:
                    failures.append(demo.name)
                    if last_error:
                        last_page_errors.append(last_error)
                    _log_diagnostics(
                        demo,
                        page_for_diagnostics or page,
                        last_url,
                        last_status,
                        last_console,
                        last_page_errors,
                        last_request_failures,
                        last_response_failures,
                        last_missing_assets,
                    )
                    if page_for_diagnostics:
                        page_for_diagnostics.close()
            context.close()
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
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if server_thread:
            server_thread.join(timeout=2)


if __name__ == "__main__":
    raise SystemExit(main())
