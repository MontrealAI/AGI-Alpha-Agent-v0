#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Smoke test that built demo pages load offline."""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from playwright.sync_api import Browser, Error as PlaywrightError, Page, sync_playwright

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
ARTIFACTS_DIR = Path("artifacts/demo-page-debug")
DEFAULT_TIMEOUT_MS = 30000
DEFAULT_ATTEMPTS = 3
MIN_BODY_TEXT_LENGTH = 20

READY_SELECTORS: tuple[tuple[str, str], ...] = (
    ("main h1", "main h1"),
    ("article h1", "article h1"),
    ("#root", "#root"),
    ("[data-testid='app']", "[data-testid='app']"),
)

DISCLAIMER_ACCEPT_SELECTORS: tuple[str, ...] = (
    "button:has-text('Accept')",
    "button:has-text('I Understand')",
    "button:has-text('Continue')",
    "button:has-text('I Agree')",
    "button:has-text('Agree')",
    "a:has-text('Accept')",
    "a:has-text('Continue')",
    "[role='button']:has-text('Accept')",
    "[role='button']:has-text('Continue')",
)


@dataclass(frozen=True)
class ReadyResult:
    selector_name: str
    selector: str
    response_status: int | None
    accepted_disclaimer_selector: str | None


class ReadyError(RuntimeError):
    """Raised when a demo page fails to reach a ready state."""


def parse_timeout_ms(raw: str | None) -> int:
    """Parse the timeout from the environment, falling back to defaults."""
    try:
        return int(raw) if raw is not None else DEFAULT_TIMEOUT_MS
    except ValueError:
        return DEFAULT_TIMEOUT_MS


def iter_demos() -> list[Path]:
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_dir() and (p / "index.html").exists())


def slugify(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()


def set_page_timeouts(page: Page, timeout_ms: int) -> None:
    page.set_default_timeout(timeout_ms)
    page.set_default_navigation_timeout(timeout_ms)


def capture_console(page: Page) -> list[str]:
    messages: list[str] = []

    def handle_console(msg: object) -> None:
        try:
            message = msg.text()  # type: ignore[attr-defined]
            message_type = msg.type()  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            message = str(msg)
            message_type = "console"
        messages.append(f"{message_type}: {message}")

    def handle_page_error(exc: object) -> None:
        messages.append(f"pageerror: {exc}")

    page.on("console", handle_console)
    page.on("pageerror", handle_page_error)
    return messages


def maybe_accept_disclaimer(page: Page, timeout_ms: int) -> str | None:
    for selector in DISCLAIMER_ACCEPT_SELECTORS:
        locator = page.locator(selector)
        try:
            if locator.count() == 0:
                continue
            locator.first.wait_for(state="visible", timeout=timeout_ms)
            locator.first.click(timeout=timeout_ms)
            locator.first.wait_for(state="hidden", timeout=timeout_ms)
            return selector
        except PlaywrightError:
            continue
    return None


def selector_summary(page: Page) -> str:
    parts: list[str] = []
    for name, selector in READY_SELECTORS:
        try:
            count = page.locator(selector).count()
        except PlaywrightError:
            count = -1
        parts.append(f"{name}={count}")
    return ", ".join(parts)


def body_text_length(page: Page) -> int:
    try:
        return int(
            page.evaluate(
                """
                () => {
                  if (!document.body) {
                    return 0;
                  }
                  return document.body.innerText.trim().length;
                }
                """
            )
        )
    except PlaywrightError:
        return 0


def safe_page_title(page: Page) -> str:
    try:
        return page.title()
    except PlaywrightError:
        return "<unavailable>"


def safe_page_url(page: Page) -> str:
    try:
        return page.url
    except PlaywrightError:
        return "<unavailable>"


def wait_for_page_ready(page: Page, url: str, timeout_ms: int) -> ReadyResult:
    response = page.goto(url, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")

    accepted = maybe_accept_disclaimer(page, timeout_ms)

    for selector_name, selector in READY_SELECTORS:
        locator = page.locator(selector)
        if locator.count() > 0:
            locator.first.wait_for(state="visible", timeout=timeout_ms)
            return ReadyResult(
                selector_name=selector_name,
                selector=selector,
                response_status=response.status if response else None,
                accepted_disclaimer_selector=accepted,
            )

    page.locator("body").wait_for(state="visible", timeout=timeout_ms)
    try:
        page.wait_for_function(
            """
            (minLen) => {
              if (!document.body) {
                return false;
              }
              return document.body.innerText.trim().length > minLen;
            }
            """,
            MIN_BODY_TEXT_LENGTH,
            timeout=timeout_ms,
        )
        return ReadyResult(
            selector_name="body text",
            selector="body",
            response_status=response.status if response else None,
            accepted_disclaimer_selector=accepted,
        )
    except PlaywrightError as exc:
        raise ReadyError(
            "Page did not reach a ready state. "
            f"url={url} final_url={safe_page_url(page)} title={safe_page_title(page)} "
            f"status={response.status if response else 'unknown'} "
            f"selectors=[{selector_summary(page)}] "
            f"body_text_length={body_text_length(page)}"
        ) from exc


def write_artifacts(
    *,
    demo: Path,
    attempt: int,
    page: Page | None,
    console_messages: Iterable[str],
    error: Exception,
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    slug = slugify(demo.name)
    base = ARTIFACTS_DIR / f"{slug}-attempt-{attempt}"

    metadata: dict[str, object] = {
        "demo": demo.name,
        "attempt": attempt,
        "error": str(error),
    }

    if page is not None:
        try:
            metadata.update(
                {
                    "url": safe_page_url(page),
                    "title": safe_page_title(page),
                }
            )
        except PlaywrightError:
            pass

    try:
        if page is not None:
            page.screenshot(path=str(base.with_suffix(".png")), full_page=True)
    except PlaywrightError:
        pass

    try:
        if page is not None:
            html = page.content()
            base.with_suffix(".html").write_text(html, encoding="utf-8")
    except PlaywrightError:
        pass

    base.with_suffix(".log").write_text("\n".join(console_messages), encoding="utf-8")
    base.with_suffix(".json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def verify_demo(browser: Browser, demo: Path, timeout_ms: int, attempts: int = DEFAULT_ATTEMPTS) -> None:
    url = (demo / "index.html").resolve().as_uri()
    for attempt in range(1, attempts + 1):
        context = browser.new_context()
        page = context.new_page()
        set_page_timeouts(page, timeout_ms)
        console_messages = capture_console(page)
        print(f"[demo] {demo.name} attempt {attempt}/{attempts}: {url}")
        try:
            result = wait_for_page_ready(page, url, timeout_ms)
            print(
                "[demo] {name} ready via {selector} "
                "(disclaimer={disclaimer}, status={status})".format(
                    name=demo.name,
                    selector=result.selector_name,
                    disclaimer=result.accepted_disclaimer_selector or "none",
                    status=result.response_status,
                )
            )
            context.close()
            return
        except Exception as exc:  # noqa: BLE001
            print(f"[demo] {demo.name} failed: {exc}", file=sys.stderr)
            write_artifacts(
                demo=demo,
                attempt=attempt,
                page=page,
                console_messages=console_messages,
                error=exc,
            )
            context.close()
            if attempt < attempts:
                time.sleep(2 ** (attempt - 1))
                continue
            raise


def main() -> int:
    demos = iter_demos()
    timeout_ms = parse_timeout_ms(os.environ.get("PWA_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS)))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for demo in demos:
                verify_demo(browser, demo, timeout_ms)
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
