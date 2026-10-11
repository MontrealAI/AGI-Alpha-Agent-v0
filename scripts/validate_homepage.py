# SPDX-License-Identifier: Apache-2.0
"""Verify the welcoming homepage, accessible controls and guided-plan handoff."""

from __future__ import annotations

import argparse
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import re
import subprocess
from threading import Thread
import tomllib
from typing import Any
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

from playwright.sync_api import Page, expect, sync_playwright

from scripts.homepage_evidence import ASSETS, asset_hashes
from scripts.validate_ascension import Handler, inspect


def assert_handoff(page: Page, language: str, large: bool) -> None:
    """Require every first-plan entry to retain the visitor's reading preferences."""
    links = page.locator("[data-start-link]")
    assert links.count() >= 2, "Offer the guided plan at the top and after the introduction"
    for link in links.all():
        href = link.get_attribute("href")
        assert href is not None
        target = urlsplit(href)
        assert not target.scheme and not target.netloc and target.path == "start/", href
        query = parse_qs(target.query)
        assert query.get("lang", ["en"]) == [language], href
        assert query.get("text", ["standard"]) == (["large"] if large else ["standard"]), href


def check_layout(page: Page) -> list[dict[str, Any]]:
    """Measure real rendered controls and horizontal reflow, including mobile text."""
    assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1"), "Horizontal page overflow"
    controls = inspect(
        page,
        """(() => [...document.querySelectorAll(
          'header a, header button, #home a, #home button, #questions summary'
        )].filter(el => !el.closest('#research') && el.getClientRects().length &&
          getComputedStyle(el).visibility !== 'hidden').map(el => {
          const box = el.getBoundingClientRect();
          return {label: (el.innerText || el.getAttribute('aria-label') || el.id).trim(),
            width: box.width, height: box.height};
        }))()""",
    )
    assert controls, "No visible welcome controls"
    small = [control for control in controls if min(control["width"], control["height"]) < 43.5]
    assert not small, f"Welcome controls need at least 44 × 44 CSS pixels: {small}"
    return controls


def audit(page: Page, axe_source: str, *, beginner_only: bool) -> dict[str, Any]:
    """Run axe against the shipped CSP and retain exact failures for review."""
    inspect(page, axe_source + "; void 0")
    context = "{include:['header','#home'],exclude:['#research']}" if beginner_only else "document"
    tags = "['wcag2a','wcag2aa','wcag21aa','best-practice']" if beginner_only else "['wcag2a','wcag2aa','wcag21aa']"
    return inspect(page, f"axe.run({context}, {{runOnly:{{type:'tag',values:{tags}}}}})")


def validate(
    site: Path,
    output: Path,
    public_url: str | None,
    axe_script: Path,
    executable: str | None,
) -> dict[str, Any]:
    """Exercise the homepage as a new visitor, without changing app data or settings."""
    root = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public homepage acceptance requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    report: dict[str, Any] = {
        "schema": "agialpha.homepage.acceptance.v1",
        "passed": False,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "version": tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
        "origin": public_url or "local project subpath",
        "checks": [],
        "browser_errors": [],
        "layouts": [],
        "accessibility": [],
        "assets": {},
    }
    try:
        expected_assets = asset_hashes()
        if asset_hashes(site) != expected_assets:
            raise ValueError("Homepage site assets differ from the current generated source")
        for relative in ASSETS:
            # Fetch the same directory entry points and versioned assets as a visitor.
            target = relative.removesuffix("index.html") if relative.endswith("index.html") else relative
            if not relative.endswith("index.html"):
                target += f"?v={report['version']}"
            request = Request(origin + target, headers={"Cache-Control": "no-cache"})
            with urlopen(request, timeout=20) as response:
                if response.status != 200 or response.geturl() != origin + target:
                    raise ValueError(f"Unexpected homepage asset response: {relative}")
                digest = hashlib.sha256(response.read()).hexdigest()
            if digest != expected_assets[relative]:
                raise ValueError(f"Homepage asset differs from the tested source: {relative}")
            report["assets"][relative] = digest
        report["checks"].append("exact-current-assets")
        axe_source = axe_script.read_text(encoding="utf-8")
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=executable)
            report["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
            page.goto(origin, wait_until="networkidle")
            expect(page.locator("body")).to_have_class(re.compile(r"\bwelcome-page\b"))
            expect(page.locator("html")).to_have_attribute("lang", "en")
            expect(page.locator('meta[name="application-version"]')).to_have_attribute("content", report["version"])
            heading = page.get_by_role("heading", level=1).first
            expect(heading).to_be_visible()
            english_heading = heading.inner_text().strip()
            assert english_heading, "Explain the first experience with a visible heading"
            base_size = inspect(page, "parseFloat(getComputedStyle(document.body).fontSize)")
            assert base_size >= 18, base_size
            navigation = page.get_by_role("navigation", name="Main navigation")
            expect(navigation.get_by_role("link", name="Start here", exact=True)).to_have_attribute("href", "start/")
            expect(page.locator("#how-it-works")).to_be_visible()
            steps = page.locator("#how-it-works ol > li")
            expect(steps).to_have_count(3)
            for step in steps.all():
                expect(step).to_be_visible()
                assert step.inner_text().strip()
            expect(page.locator("#questions")).to_be_visible()
            questions = page.locator("#questions details")
            assert questions.count() >= 3, "Explain common questions before technical exploration"
            for question in questions.all():
                summary = question.locator("summary")
                expect(summary).to_be_visible()
                summary.click()
                expect(question).to_have_attribute("open", "")
                assert len(question.inner_text().strip()) > len(summary.inner_text().strip())
                summary.click()
            assert_handoff(page, "en", False)
            report["checks"] += ["clear-first-step", "three-visible-steps", "readable-default-text", "working-faq"]

            # A keyboard-only visitor reaches the main content before navigating the header.
            page.goto(origin, wait_until="networkidle")
            page.keyboard.press("Tab")
            expect(page.locator('a[href="#home"]').first).to_be_focused()
            page.keyboard.press("Enter")
            expect(page.locator("#home")).to_be_focused()
            page.locator("#home-fr").focus()
            page.keyboard.press("Enter")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-fr")).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#home-en")).to_have_attribute("aria-pressed", "false")
            expect(page.locator(".welcome-directory")).to_have_attribute("lang", "en")
            for legacy in page.locator(".legacy-research").all():
                expect(legacy).to_have_attribute("lang", "en")
            assert heading.inner_text().strip() != english_heading
            assert_handoff(page, "fr", False)
            page.locator("#home-text-size").click()
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert inspect(page, "parseFloat(getComputedStyle(document.body).fontSize)") > base_size
            assert_handoff(page, "fr", True)
            page.locator("[data-start-link]").first.click()
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
            expect(page.locator("#planner")).to_be_visible()
            report["checks"] += ["keyboard-skip", "english-and-french", "larger-text", "guided-plan-preferences"]

            # Shared links reproduce preferences without requiring a saved browser setting.
            page.goto(origin + "?lang=fr&text=large", wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
            assert_handoff(page, "fr", True)
            page.locator("#home-en").click()
            expect(page.locator("html")).to_have_attribute("lang", "en")
            assert heading.inner_text().strip() == english_heading
            assert_handoff(page, "en", True)
            page.locator("#home-text-size").click()
            expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "false")
            assert_handoff(page, "en", False)
            report["checks"].append("shareable-reading-preferences")

            for language, width, large in (
                ("en", 1440, False),
                ("en", 390, False),
                ("fr", 320, False),
                ("fr", 320, True),
            ):
                page.set_viewport_size({"width": width, "height": 1000})
                page.goto(origin + f"?lang={language}" + ("&text=large" if large else ""), wait_until="networkidle")
                expect(page.locator("html")).to_have_attribute("lang", language)
                controls = check_layout(page)
                report["layouts"].append(
                    {"width": width, "language": language, "large_text": large, "controls": controls}
                )
                page.screenshot(path=str(output / f"homepage-{language}-{width}{'-large' if large else ''}.png"))
                for beginner_only in (True, False):
                    result = audit(page, axe_source, beginner_only=beginner_only)
                    report["accessibility"].append(
                        {
                            "width": width,
                            "language": language,
                            "large_text": large,
                            "scope": "welcome" if beginner_only else "document",
                            "violations": result["violations"],
                        }
                    )
                    assert not result["violations"], result["violations"]
            assert inspect(page, "matchMedia('(prefers-reduced-motion: reduce)').matches")
            assert inspect(page, "getComputedStyle(document.documentElement).scrollBehavior !== 'smooth'")
            report["checks"] += ["mobile-reflow", "large-touch-targets", "axe-no-violations", "reduced-motion"]

            no_js = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
            fallback = no_js.new_page()
            fallback.goto(origin)
            expect(fallback.get_by_role("heading", level=1).first).to_be_visible()
            expect(
                fallback.get_by_role("navigation", name="Main navigation").get_by_role(
                    "link", name="Start here", exact=True
                )
            ).to_have_attribute("href", "start/")
            expect(fallback.locator("#how-it-works")).to_be_visible()
            expect(fallback.locator("#questions summary").first).to_be_visible()
            fallback.locator("#questions summary").first.click()
            expect(fallback.locator("#questions details").first).to_have_attribute("open", "")
            assert_handoff(fallback, "en", False)
            report["checks"].append("no-javascript-content-and-navigation")
            assert not report["browser_errors"], report["browser_errors"]
            report["passed"] = True
            browser.close()
    finally:
        (output / "homepage.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if server:
            server.shutdown()
            server.server_close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/homepage"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path, default=Path("tests/browser/node_modules/axe-core/axe.min.js"))
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script, args.browser_executable), indent=2))


if __name__ == "__main__":
    main()
