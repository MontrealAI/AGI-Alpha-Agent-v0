# SPDX-License-Identifier: Apache-2.0
"""Exercise the portable workbench in a real browser, with screenshots and offline reopening."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from playwright.sync_api import expect, sync_playwright
from scripts.validate_ascension import inspect

ROOT = Path(__file__).resolve().parents[1]


def validate(output: Path, url: str | None = None, axe: Path | None = None) -> dict[str, Any]:
    """Run all five families, input invalidation, keyboard, EN/FR, responsive and offline journeys."""
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = context.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url or (ROOT / "docs/successor/work/index.html").as_uri())
        expect(page.locator("#families button")).to_have_count(5)
        families = ["reliability", "performance", "documentation", "public-data", "numerical"]
        for index, family in enumerate(families):
            page.locator("#families button").nth(index).click()
            page.locator("#run").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#evidence")).to_be_enabled(timeout=15000)
            expect(page.locator("#jobs li")).to_have_count(7)
            with page.expect_download() as download:
                page.locator("#evidence").click()
            evidence = output / (family + ".json")
            download.value.save_as(evidence)
            pack = json.loads(evidence.read_text())
            assert pack["spec"]["family"] == family
            assert pack["result"]["artifacts"] and pack["evaluation"]["authority"] == []
            assert len(pack["compilation"]["graph"]["nodes"]) == 7
        page.locator("#language").click()
        expect(page.locator("html")).to_have_attribute("lang", "fr")
        page.locator("#families button").first.click()
        page.locator("#name").fill('</script><img src=x onerror="alert(1)">')
        page.locator("#run").click()
        expect(page.locator("#evidence")).to_be_enabled()
        expect(page.locator("#result-title img")).to_have_count(0)
        page.locator("#larger").click()
        layouts = []
        for width in (1440, 390, 320):
            page.set_viewport_size({"width": width, "height": 1000})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            if axe:
                inspect(page, axe.read_text() + "; void 0")
                result = inspect(
                    page, "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
                )
                assert not result["violations"], result["violations"]
            layouts.append(width)
            page.screenshot(path=str(output / f"workbench-{width}.png"), full_page=True)
        with page.expect_download() as download:
            page.locator("#save").click()
        portable = output.resolve() / "working-omega.html"
        download.value.save_as(portable)
        assert portable.stat().st_size < 1_000_000
        offline = browser.new_context(offline=True)
        local = offline.new_page()
        local.on("pageerror", lambda error: errors.append(str(error)))
        local.goto(portable.as_uri())
        expect(local.locator("#name")).to_have_value('</script><img src=x onerror="alert(1)">')
        expect(local.locator("html")).to_have_attribute("lang", "fr")
        local.locator("#run").click()
        expect(local.locator("#evidence")).to_be_enabled()
        local.locator("details").first.locator("summary").click()
        inputs = json.loads(local.locator("#inputs").input_value())
        inputs["low"] = 2
        local.locator("#inputs").fill(json.dumps(inputs))
        expect(local.locator("#evidence")).to_be_disabled()
        local.locator("#run").click()
        expect(local.locator("#evidence")).to_be_enabled()
        local.locator("#restore").set_input_files(output / "public-data.json")
        expect(local.locator("#evidence")).to_be_disabled()
        expect(local.locator("#history")).to_contain_text("UNAUTHENTICATED_HISTORICAL_IMPORT")
        local.locator("#run").click()
        expect(local.locator("#evidence")).to_be_enabled()
        assert not errors, errors
        browser.close()
    report = {
        "families": families,
        "offline_save_reopen": "PASS",
        "keyboard": "PASS",
        "languages": ["en", "fr"],
        "viewports": layouts,
        "axe": "PASS" if axe else "NOT_RUN",
        "errors": errors,
        "computer_provider": "NOT_RUN; separate native qualification",
    }
    (output / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.output, args.url, args.axe_script), indent=2))
