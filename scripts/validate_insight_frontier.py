# SPDX-License-Identifier: Apache-2.0
"""Check the additive Insight browser inspection, replay, translations and downloads."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from scripts.validate_alpha_flywheel import verify_packaged

ROOT = Path(__file__).resolve().parents[1]


def validate(page_path: Path, screenshots: Path | None = None, axe_script: Path | None = None) -> dict[str, Any]:
    page_path = page_path.resolve()
    verify_packaged(page_path.parent.parent, ROOT)
    evidence = json.loads((ROOT / "scripts/templates/alpha-flywheel/insight-evidence.json").read_bytes())
    checks: list[str] = []
    errors: list[str] = []
    requests: list[str] = []
    with sync_playwright() as playwright, tempfile.TemporaryDirectory(prefix="insight-browser-downloads-") as temp:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=True)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        page.goto(page_path.as_uri())
        page.locator("#insight-frontier").wait_for()
        assert page.locator("#insight-frontier a[href='../ascension-protocol/']").count() == 1
        assert (ROOT / "docs/ascension-protocol/index.html").is_file()
        checks.append("existing-mark-route")
        for language in ("en", "fr"):
            page.locator("#lang-" + language).click()
            assert page.locator("html").get_attribute("lang") == language
            for width in (320, 390, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth<=innerWidth+1"), (language, width)
                if screenshots:
                    screenshots.mkdir(parents=True, exist_ok=True)
                    page.locator("#insight-frontier").screenshot(
                        path=str(screenshots / f"insight-{language}-{width}.png")
                    )
                checks.append(f"layout-{language}-{width}")
            for identity in ("calibration-cohort", "heat-access", "usable-research-access"):
                page.locator("#insight-candidate").select_option(identity)
                assert len(page.locator("#insight-candidate-detail").inner_text()) > 40
                checks.append(f"candidate-{language}-{identity}")
            for case in ("origin", "denied", "incomplete"):
                page.locator("#insight-case").select_option(case)
                text = page.locator("#insight-construction").inner_text()
                assert "NONE" not in text or "authority" in text.lower()
                if case == "origin":
                    assert page.locator("#insight-construction li").count() == 5
                    assert "3" in text
                else:
                    assert page.locator("#insight-construction li").count() == 0
                checks.append(f"replay-{language}-{case}")
            for level in ("low", "base", "high"):
                for price in (400, 800, 1000, 1200):
                    page.locator("#insight-cost").select_option(level)
                    page.locator("#insight-price").select_option(str(price))
                    policy = next(
                        p
                        for p in evidence["economics"]["policies"]
                        if p["cost_case"] == level and p["price_usd"] == price
                    )
                    actual = page.locator("#insight-economics dd").all_text_contents()
                    assert actual[0] == f"{policy['assumed_participants']} / 4"
                    forecast = policy["assessment"]["expected_economic_contribution_micro_usd"]
                    expected = int(forecast["numerator"]) / int(forecast["denominator"]) / 1_000_000
                    display = page.evaluate(
                        "([language,value])=>new Intl.NumberFormat(language==='fr'?'fr-CA':'en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(value)",
                        [language, expected],
                    )
                    assert actual[2] == display
                    checks.append(f"economics-{language}-{level}-{price}")
            assert (
                "USD 0" in page.locator("#insight-economics").inner_text()
                or "0 USD" in page.locator("#insight-economics").inner_text()
            )
            if axe_script:
                page.evaluate(axe_script.read_text() + ";void 0")
                audit = page.evaluate(
                    "axe.run(document.querySelector('#insight-frontier'),{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}})"
                )
                assert not audit["violations"], audit["violations"]
                checks.append("axe-" + language)
        for button, field in (
            ("insight-seed-export", "seed"),
            ("insight-plan-export", "plan"),
            ("insight-export", None),
        ):
            with page.expect_download() as pending:
                page.locator("#" + button).click()
            download = pending.value
            destination = Path(temp) / download.suggested_filename
            download.save_as(destination)
            value = json.loads(destination.read_bytes())
            assert value == (evidence[field] if field else evidence)
            checks.append("download-" + button)
        assert not errors, errors
        assert all(request.startswith("file:") or request.startswith("blob:") for request in requests), requests
        checks.extend(["no-page-errors", "no-external-requests", "exact-embedded-downloads"])
        browser.close()
    return {
        "schema": "insight-frontier-browser-check/v1",
        "page_sha256": hashlib.sha256(page_path.read_bytes()).hexdigest(),
        "checks": checks,
        "passed": len(checks),
        "errors": errors,
        "scope": "Local browser inspection; not public HTTPS, live execution, identity or market acceptance",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--page", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--screenshots", type=Path)
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    report = validate(args.page, args.screenshots, args.axe_script)
    text = json.dumps(report, indent=2) + "\n"
    if args.report:
        with args.report.open("x") as stream:
            stream.write(text)
    else:
        print(text)


if __name__ == "__main__":
    main()
