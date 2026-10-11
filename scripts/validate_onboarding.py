# SPDX-License-Identifier: Apache-2.0
"""Exercise the first-use journey on a project subpath and the published HTTPS site."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Thread
import tomllib
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts.validate_ascension import Handler, inspect


def validate(site: Path, output: Path, public_url: str | None, axe_script: Path, executable: str | None) -> None:
    """Check actual computed results, downloads, failures, focus and accessible layouts."""
    root = Path(__file__).resolve().parents[1]
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public acceptance requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    report: dict[str, Any] = {
        "schema": "agialpha.onboarding.acceptance.v1",
        "passed": False,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "version": tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"],
        "origin": public_url or "local project subpath",
        "checks": [],
        "browser_errors": [],
        "accessibility": [],
    }
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=executable)
            report["browser_version"] = browser.version
            context = browser.new_context(viewport={"width": 1440, "height": 1100}, reduced_motion="reduce")
            page = context.new_page()
            page.goto(origin, wait_until="networkidle")
            entry = page.get_by_role("navigation", name="Main navigation").get_by_role(
                "link", name="Start here", exact=True
            )
            expect(entry).to_have_attribute("href", "start/")
            entry.click()
            expect(page.locator("#planner")).to_be_visible()
            expect(page.locator('meta[name="application-version"]')).to_have_attribute("content", report["version"])
            report["checks"].append("homepage-entry")
            page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
            requests: list[str] = []
            page.on("request", lambda request: requests.append(request.url))
            page.emulate_media(media="print")
            expect(page.locator("main")).to_be_visible()
            expect(page.locator("#print-copy")).not_to_be_visible()
            page.emulate_media(media="screen")
            page.screenshot(path=str(output / "desktop.png"), full_page=True)
            for language in ("en", "fr"):
                if language == "fr":
                    page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute("lang", language)
                page.locator("#minutes").fill("60")
                page.locator('#plan-form button[type="submit"]').focus()
                page.keyboard.press("Enter")
                expect(page.locator("#review-title")).to_be_focused()
                expect(page.locator("#continue")).to_be_disabled()
                expect(page.locator("#result .result-stats strong")).to_have_text(["60", "0", "12"])
                expect(page.locator("#result .result-list li")).to_have_count(2)
                page.locator("#reviewed").focus()
                page.keyboard.press("Space")
                page.locator("#continue").click()
                expect(page.locator("#keep-title")).to_be_focused()
                with page.expect_download() as download:
                    page.locator("#download").click()
                text_path = output / f"plan-{language}.txt"
                download.value.save_as(text_path)
                content = text_path.read_text()
                assert "60" in content and "12" in content and report["version"] in content
                page.locator(".readable-copy summary").click()
                expect(page.locator("#readable-plan")).to_be_visible()
                assert page.locator("#readable-plan").inner_text() == content
                page.emulate_media(media="print")
                expect(page.locator("#print-copy")).to_be_visible()
                expect(page.locator("main")).not_to_be_visible()
                assert page.locator("#print-text").inner_text() == content
                page.emulate_media(media="screen")
                page.locator(".readable-copy summary").click()
                with page.expect_download() as download:
                    page.locator("#evidence").click()
                json_path = output / f"plan-{language}.json"
                download.value.save_as(json_path)
                saved = json.loads(json_path.read_text())
                assert saved["result"]["evidence"]["selected"] == ["task-1", "task-2"]
                assert saved["result"]["evidence"]["totals"] == {"cost": 60, "value": 12, "risk": 0}
                assert saved["request"]["work"]["budget"] == 60 and saved["language"] == language
                assert saved["review"] == {"user_checked": True, "independent_review": False, "external_action": False}
                page.locator("#revise").click()
                expect(page.locator("#choose-title")).to_be_focused()
                page.locator("#minutes").fill("30")
                page.locator('#plan-form button[type="submit"]').click()
                expect(page.locator("#continue")).to_be_disabled()
                expect(page.locator("#reviewed")).not_to_be_checked()
                page.locator("#back").click()
            report["checks"] += [
                "english-and-french",
                "review-before-export",
                "changed-inputs-clear-review",
                "exact-downloads",
                "readable-and-printable-plan",
                "keyboard-focus",
            ]
            page.locator("#task-options summary").click()
            page.locator("#minutes").fill("0")
            page.locator("#duration-0").fill("1.5")
            page.locator("#importance-0").fill("11")
            page.locator("#name-0").fill(" ")
            page.locator('#plan-form button[type="submit"]').click()
            expect(page.locator("#errors")).to_be_focused()
            expect(page.locator("#errors li")).to_have_count(4)
            page.locator('#errors a[href="#minutes"]').click()
            expect(page.locator("#minutes")).to_be_focused()
            page.locator("#minutes").fill("1")
            page.locator("#duration-0").fill("30")
            page.locator("#importance-0").fill("6")
            page.locator("#name-0").fill('<img src=x onerror="alert(1)">')
            page.locator('#plan-form button[type="submit"]').click()
            expect(page.locator("#result .result-stats strong")).to_have_text(["0", "1", "0"])
            expect(page.locator("#result img")).to_have_count(0)
            expect(page.locator("#result")).to_contain_text('<img src=x onerror="alert(1)">')
            report["checks"] += ["invalid-input-recovery", "empty-plan", "user-text-escaped"]
            page.locator("#back").click()
            page.locator("#name-0").fill("Une tâche personnelle")
            for width, large in ((1440, False), (390, False), (320, False), (320, True), (640, True)):
                page.set_viewport_size({"width": width, "height": 1000})
                if large and page.locator("#text-size").get_attribute("aria-pressed") == "false":
                    page.locator("#text-size").click()
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1")
                inspect(page, axe_script.read_text() + "; void 0")
                audit = inspect(
                    page,
                    "axe.run(document, {runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}})",
                )
                report["accessibility"].append({"width": width, "large_text": large, "violations": audit["violations"]})
                assert not audit["violations"], audit["violations"]
            page.screenshot(path=str(output / "mobile-large-fr.png"), full_page=True)
            report["checks"] += ["mobile-and-larger-text", "axe-no-violations"]
            assert not requests, requests
            assert inspect(page, "localStorage.length === 0 && sessionStorage.length === 0")
            report["checks"].append("no-task-network-or-storage")
            no_js = browser.new_context(java_script_enabled=False)
            fallback = no_js.new_page()
            fallback.goto(origin + "start/")
            expect(fallback.locator("noscript")).to_be_visible()
            expect(fallback.locator("noscript a")).to_have_count(2)
            report["checks"].append("no-javascript-guidance")
            assert not report["browser_errors"], report["browser_errors"]
            report["passed"] = True
            browser.close()
    finally:
        (output / "onboarding.json").write_text(json.dumps(report, indent=2) + "\n")
        if server:
            server.shutdown()
            server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/onboarding"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path, default=Path("tests/browser/node_modules/axe-core/axe.min.js"))
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    validate(args.site, args.output, args.url, args.axe_script, args.browser_executable)


if __name__ == "__main__":
    main()
