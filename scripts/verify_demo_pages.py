#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Smoke test that built demo pages load offline."""
from __future__ import annotations

import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from playwright.sync_api import Error as PlaywrightError, Page, sync_playwright
except ImportError:  # pragma: no cover - Playwright may be absent outside CI.
    PlaywrightError = Exception  # type: ignore[assignment]
    Page = Any  # type: ignore[misc,assignment]
    sync_playwright = None

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
ARTIFACTS_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "demo-page-debug"
DEFAULT_TIMEOUT_MS = 30000
MIN_BODY_TEXT_LENGTH = 40
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1
ACCEPT_TEXT_PATTERNS = (
    "accept",
    "i understand",
    "i agree",
    "continue",
    "got it",
)
DISCLAIMER_TEXT_PATTERNS = (
    "disclaimer",
    "use at your own risk",
    "financial advice",
)
@dataclass(frozen=True)
class ReadyCandidate:
    """Describe a selector used to detect page readiness."""

    label: str
    selector: str
    state: str = "visible"


READY_CANDIDATES: tuple[ReadyCandidate, ...] = (
    ReadyCandidate("main h1", "main h1", "visible"),
    ReadyCandidate("article h1", "article h1", "visible"),
    ReadyCandidate("#root", "#root", "visible"),
    ReadyCandidate("[data-testid=\"app\"]", "[data-testid=\"app\"]", "visible"),
    ReadyCandidate("#power-panel", "#power-panel", "attached"),
    ReadyCandidate("#analytics-panel", "#analytics-panel", "attached"),
    ReadyCandidate("#arena-panel", "#arena-panel", "attached"),
    ReadyCandidate("#toolbar", "#toolbar", "attached"),
    ReadyCandidate("#canvas", "#canvas", "attached"),
    ReadyCandidate("#toast", "#toast", "attached"),
    ReadyCandidate("canvas", "canvas", "attached"),
)


class PageReadyError(RuntimeError):
    """Raised when a page does not reach a ready state."""

    def __init__(self, message: str, status_code: int | None, selector_summary: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.selector_summary = selector_summary


def iter_demos() -> list[Path]:
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_dir() and (p / "index.html").exists())


def get_timeout_ms() -> int:
    """Return the Playwright timeout in milliseconds."""
    raw_value = os.environ.get("PWA_TIMEOUT_MS", str(DEFAULT_TIMEOUT_MS))
    try:
        return int(raw_value)
    except ValueError:
        print(f"Invalid PWA_TIMEOUT_MS value: {raw_value!r}. Falling back to {DEFAULT_TIMEOUT_MS}.", file=sys.stderr)
        return DEFAULT_TIMEOUT_MS


def build_accept_text_regex() -> re.Pattern[str]:
    """Return a regex that matches disclaimer accept buttons."""
    pattern = "|".join(re.escape(text) for text in ACCEPT_TEXT_PATTERNS)
    return re.compile(pattern, re.IGNORECASE)


def build_disclaimer_text_regex() -> re.Pattern[str]:
    """Return a regex for disclaimer copy that might gate content."""
    pattern = "|".join(re.escape(text) for text in DISCLAIMER_TEXT_PATTERNS)
    return re.compile(pattern, re.IGNORECASE)


def slugify(value: str) -> str:
    """Return a filesystem-safe slug for artifact names."""
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", value).strip("-").lower()
    return slug or "demo-page"


def collect_console_logs(console_messages: list[str], entry: str) -> None:
    """Store console output for diagnostics."""
    console_messages.append(entry)


def wait_for_disclaimer_accept(page: Page) -> None:
    """Dismiss a disclaimer gate if one is present."""
    accept_regex = build_accept_text_regex()
    disclaimer_regex = build_disclaimer_text_regex()
    if page.get_by_text(disclaimer_regex).count() == 0:
        return
    accept_button = page.get_by_role("button", name=accept_regex)
    if accept_button.count() == 0:
        accept_button = page.locator("a, input[type='button'], input[type='submit']").filter(has_text=accept_regex)
    if accept_button.count() == 0:
        return
    if accept_button.first.is_visible():
        accept_button.first.click()
        accept_button.first.wait_for(state="hidden")


def summarize_ready_candidate_state(page: Page, candidates: Iterable[ReadyCandidate]) -> list[str]:
    """Return selector counts for readiness candidates."""
    summary = []
    for candidate in candidates:
        count = page.locator(candidate.selector).count()
        summary.append(f"{candidate.label}={count}")
    return summary


def wait_for_any_ready_candidate(page: Page, timeout_ms: int) -> tuple[str | None, float]:
    """Wait for any readiness selector to appear, honoring priority."""
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        for candidate in READY_CANDIDATES:
            locator = page.locator(candidate.selector)
            if locator.count() == 0:
                continue
            locator.first.wait_for(state=candidate.state, timeout=timeout_ms)
            return candidate.label, deadline
        page.wait_for_timeout(200)
    return None, deadline


def wait_for_page_ready(page: Page, url: str, timeout_ms: int) -> tuple[str, int | None]:
    """Navigate to a page and wait for the main content to be visible."""
    response = page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
    page.wait_for_load_state("domcontentloaded")
    wait_for_disclaimer_accept(page)

    candidate_label, deadline = wait_for_any_ready_candidate(page, timeout_ms)
    if candidate_label:
        return candidate_label, response.status if response else None

    try:
        remaining_ms = max(0, int((deadline - time.monotonic()) * 1000))
        page.wait_for_selector("body", state="visible", timeout=remaining_ms)
        page.wait_for_function(
            f"() => document.body && document.body.innerText.trim().length > {MIN_BODY_TEXT_LENGTH}",
            timeout=remaining_ms,
        )
        return f"body text > {MIN_BODY_TEXT_LENGTH}", response.status if response else None
    except PlaywrightError as exc:
        summary = ", ".join(summarize_ready_candidate_state(page, READY_CANDIDATES))
        status_code = response.status if response else None
        message = (
            "No readiness selector found. "
            f"url={url} final_url={page.url} title={page.title()} status={status_code} selectors={summary}"
        )
        raise PageReadyError(message, status_code=status_code, selector_summary=summary) from exc


def write_debug_artifacts(
    page: Page,
    slug: str,
    url: str,
    console_messages: list[str],
    status_code: int | None,
    error: Exception,
) -> None:
    """Write screenshot, HTML, and console logs for debugging."""
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / f"{slug}.png").write_bytes(page.screenshot(full_page=True))
    (ARTIFACTS_DIR / f"{slug}.html").write_text(page.content(), encoding="utf-8")
    (ARTIFACTS_DIR / f"{slug}.console.txt").write_text("\n".join(console_messages), encoding="utf-8")
    metadata = [
        f"url: {url}",
        f"final_url: {page.url}",
        f"title: {page.title()}",
        f"status: {status_code}",
        f"error: {error}",
    ]
    if isinstance(error, PageReadyError):
        metadata.append(f"selector_summary: {error.selector_summary}")
    (ARTIFACTS_DIR / f"{slug}.meta.txt").write_text("\n".join(metadata), encoding="utf-8")


def format_console_message(message: str, location: dict[str, object] | None) -> str:
    """Format console messages for logs."""
    location = location or {}
    url = location.get("url", "")
    line = location.get("lineNumber", "")
    return f"{message} ({url}:{line})"


def main() -> int:
    demos = iter_demos()
    try:
        if sync_playwright is None:
            print("Playwright is not installed. Run `python -m playwright install chromium` to continue.", file=sys.stderr)
            return 1
        with sync_playwright() as p:
            browser = p.chromium.launch()
            timeout_ms = get_timeout_ms()
            for demo in demos:
                slug = slugify(demo.name)
                url = (demo / "index.html").resolve().as_uri()
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    console_messages: list[str] = []
                    context = browser.new_context()
                    page = context.new_page()
                    page.set_default_timeout(timeout_ms)
                    page.set_default_navigation_timeout(timeout_ms)
                    page.on(
                        "console",
                        lambda msg: collect_console_logs(
                            console_messages,
                            f"[{msg.type}] {format_console_message(msg.text, msg.location)}",
                        ),
                    )
                    try:
                        print(f"Verifying demo page {demo.name} ({url}) attempt {attempt}/{MAX_ATTEMPTS}")
                        readiness, status = wait_for_page_ready(page, url, timeout_ms)
                        print(f"Ready selector for {demo.name}: {readiness} (status={status})")
                        context.close()
                        break
                    except Exception as exc:  # noqa: BLE001
                        print(f"Failure verifying {demo.name} ({url}) on attempt {attempt}: {exc}", file=sys.stderr)
                        if attempt == MAX_ATTEMPTS:
                            status_code = exc.status_code if isinstance(exc, PageReadyError) else None
                            write_debug_artifacts(page, slug, url, console_messages, status_code, exc)
                            context.close()
                            raise
                        context.close()
                        time.sleep(BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))
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
