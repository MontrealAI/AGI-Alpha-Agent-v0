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
    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright
except ModuleNotFoundError:  # pragma: no cover - covered in environments with Playwright.
    PlaywrightError = RuntimeError
    sync_playwright = None

DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
DISCLAIMER_SNIPPET_PATH = DOCS_DIR / "DISCLAIMER_SNIPPET.md"
ARTIFACTS_DIR = Path("artifacts") / "demo-page-debug"
READY_TEXT_MIN_CHARS = 60
READY_SELECTORS = ("main h1", "article h1", "#root", "[data-testid='app']")
DISCLAIMER_CONTAINER_SELECTORS = (
    "#disclaimer",
    ".disclaimer",
    "[data-testid='disclaimer']",
    "[id*='disclaimer' i]",
    "[class*='disclaimer' i]",
    "[role='dialog']",
)
ACCEPT_TEXT_PATTERNS = ("accept", "i understand", "continue", "i agree", "agree")
MAX_ATTEMPTS = 3


def iter_demos() -> list[Path]:
    return sorted(p for p in DOCS_DIR.iterdir() if p.is_dir() and (p / "index.html").exists())


def parse_timeout_ms(env: dict[str, str] | None = None) -> int:
    """Return the Playwright timeout value in milliseconds."""
    env = env or os.environ
    raw_value = env.get("PWA_TIMEOUT_MS", "30000")
    try:
        return int(raw_value)
    except ValueError:
        print(f"Invalid PWA_TIMEOUT_MS value {raw_value!r}; defaulting to 30000ms.", file=sys.stderr)
        return 30000


def load_disclaimer_markers() -> list[str]:
    """Return disclaimer text fragments used to detect overlay gates."""
    fallback = [
        "conceptual research prototype",
        "use at your own risk",
        "nothing herein constitutes financial advice",
    ]
    try:
        text = DISCLAIMER_SNIPPET_PATH.read_text(encoding="utf-8")
    except OSError:
        return fallback
    fragments = [fragment.strip().lower() for fragment in re.split(r"[.!?]", text) if fragment.strip()]
    return fragments or fallback


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-") or "demo"


@dataclass
class PageDiagnostics:
    """Capture debug data for a demo page verification attempt."""

    url: str
    final_url: str | None = None
    title: str | None = None
    status: int | None = None
    ready_selector: str | None = None
    selector_summary: str | None = None


def format_selector_summary(page: Any, selectors: Iterable[str]) -> str:
    parts = []
    for selector in selectors:
        count = page.locator(selector).count()
        parts.append(f"{selector}={count}")
    return ", ".join(parts)


def maybe_dismiss_disclaimer(page: Any, markers: Iterable[str]) -> bool:
    combined_selector = ", ".join(DISCLAIMER_CONTAINER_SELECTORS)
    has_disclaimer_container = page.locator(combined_selector).count() > 0
    has_marker = any(
        page.evaluate(
            "marker => document.body && document.body.innerText.toLowerCase().includes(marker)", marker
        )
        for marker in markers
    )
    if not has_disclaimer_container and not has_marker:
        return False
    for pattern in ACCEPT_TEXT_PATTERNS:
        matcher = re.compile(pattern, re.IGNORECASE)
        button = page.get_by_role("button", name=matcher)
        if button.count() > 0:
            button.first.click()
            if has_disclaimer_container:
                page.locator(combined_selector).first.wait_for(state="detached")
            return True
        link = page.locator("a", has_text=matcher)
        if link.count() > 0:
            link.first.click()
            if has_disclaimer_container:
                page.locator(combined_selector).first.wait_for(state="detached")
            return True
    return False


def wait_for_page_ready(page: Any, url: str, diagnostics: PageDiagnostics) -> None:
    response = page.goto(url, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    diagnostics.status = response.status if response else None
    diagnostics.final_url = page.url
    diagnostics.title = page.title()
    maybe_dismiss_disclaimer(page, load_disclaimer_markers())
    selector_summary = format_selector_summary(page, READY_SELECTORS)
    diagnostics.selector_summary = selector_summary
    for selector in READY_SELECTORS:
        if page.locator(selector).count() > 0:
            diagnostics.ready_selector = selector
            try:
                page.locator(selector).first.wait_for(state="visible")
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "Timed out waiting for readiness selector "
                    f"{selector!r} ({selector_summary}). "
                    f"url={diagnostics.url}, final_url={diagnostics.final_url}, "
                    f"title={diagnostics.title!r}, status={diagnostics.status}"
                ) from exc
            return
    diagnostics.ready_selector = f"body text >= {READY_TEXT_MIN_CHARS}"
    try:
        page.wait_for_selector("body", state="visible")
        page.wait_for_function(
            "minChars => document.body && document.body.innerText.trim().length > minChars",
            READY_TEXT_MIN_CHARS,
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "Timed out waiting for body text readiness "
            f"({selector_summary}). url={diagnostics.url}, final_url={diagnostics.final_url}, "
            f"title={diagnostics.title!r}, status={diagnostics.status}"
        ) from exc


def write_failure_artifacts(
    slug: str,
    page: Any,
    console_logs: list[str],
    diagnostics: PageDiagnostics,
) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = ARTIFACTS_DIR / f"{slug}.png"
    html_path = ARTIFACTS_DIR / f"{slug}.html"
    log_path = ARTIFACTS_DIR / f"{slug}.console.log"
    meta_path = ARTIFACTS_DIR / f"{slug}.meta.log"
    page.screenshot(path=str(screenshot_path), full_page=True)
    html_path.write_text(page.content(), encoding="utf-8")
    log_path.write_text("\n".join(console_logs), encoding="utf-8")
    meta_path.write_text(
        "\n".join(
            [
                f"url={diagnostics.url}",
                f"final_url={diagnostics.final_url}",
                f"title={diagnostics.title}",
                f"status={diagnostics.status}",
                f"ready_selector={diagnostics.ready_selector}",
                f"selector_summary={diagnostics.selector_summary}",
            ]
        ),
        encoding="utf-8",
    )


def main() -> int:
    demos = iter_demos()
    try:
        if sync_playwright is None:
            print("Playwright is not installed. Run `python -m playwright install chromium`.", file=sys.stderr)
            return 1
        timeout_ms = parse_timeout_ms()
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for demo in demos:
                url = (demo / "index.html").resolve().as_uri()
                demo_slug = slugify(demo.name)
                last_error: Exception | None = None
                for attempt in range(1, MAX_ATTEMPTS + 1):
                    context = browser.new_context()
                    page = context.new_page()
                    page.set_default_timeout(timeout_ms)
                    page.set_default_navigation_timeout(timeout_ms)
                    console_logs: list[str] = []
                    diagnostics = PageDiagnostics(url=url)
                    page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
                    try:
                        print(f"[demo:{demo.name}] Attempt {attempt}/{MAX_ATTEMPTS} -> {url}")
                        wait_for_page_ready(page, url, diagnostics)
                        print(
                            f"[demo:{demo.name}] Ready via {diagnostics.ready_selector} "
                            f"(status={diagnostics.status}, title={diagnostics.title!r})"
                        )
                        last_error = None
                        page.close()
                        context.close()
                        break
                    except Exception as exc:  # noqa: BLE001
                        last_error = exc
                        print(
                            f"[demo:{demo.name}] Attempt {attempt} failed for {url}: {exc}",
                            file=sys.stderr,
                        )
                        try:
                            write_failure_artifacts(demo_slug, page, console_logs, diagnostics)
                        except Exception as artifact_exc:  # noqa: BLE001
                            print(
                                f"[demo:{demo.name}] Failed to write artifacts: {artifact_exc}",
                                file=sys.stderr,
                            )
                        finally:
                            page.close()
                            context.close()
                        if attempt < MAX_ATTEMPTS:
                            backoff = 2 ** (attempt - 1)
                            print(f"[demo:{demo.name}] Retrying after {backoff}s...", file=sys.stderr)
                            time.sleep(backoff)
                if last_error is not None:
                    raise last_error
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
