# SPDX-License-Identifier: Apache-2.0
"""Local functional/viewport QA; requires Playwright and an installed Chromium."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


def main(chromium: str, screenshots: Path) -> None:
    root = Path(__file__).resolve().parent
    screenshots.mkdir(parents=True, exist_ok=True)
    report = {"checks": {}, "errors": []}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=chromium, headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)
        page.on("pageerror", lambda e: report["errors"].append(str(e)))
        page.goto((root / "index.html").as_uri())
        page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
        assert page.locator("#comparison tr").count() == 6
        assert page.locator("#selection tr").count() == 4
        assert page.locator("#workflow-contracts tr").count() == 3
        report["checks"]["data_tables"] = True
        report["checks"]["workflow_reservations"] = page.locator(
            "#workflow-contracts tr td:last-child"
        ).all_text_contents()
        assert report["checks"]["workflow_reservations"] == ["95 s", "125 s", "182 s"]
        local_links = []
        for href in page.locator("a[href]").evaluate_all("els => els.map(e => e.getAttribute('href'))"):
            if not href.startswith(("http:", "https:", "mailto:", "#", "data:")):
                assert (root / href).is_file(), href
                local_links.append(href)
        report["checks"]["local_download_links_resolve"] = local_links
        report["checks"]["default_scenario"] = page.evaluate("scenario()")
        assert report["checks"]["default_scenario"]["net"] < 0
        assert report["checks"]["default_scenario"]["gymExtra"] == 0
        page.locator("#capability").select_option("gym")
        assert page.locator("#gym-cost").is_visible()
        assert page.evaluate("scenario().gymExtra") == 25
        page.locator("#capability").select_option("work")
        assert not page.locator("#gym-cost").is_visible()
        assert page.evaluate("scenario().gymExtra") == 0
        report["checks"]["optional_gym_cost_disjoint"] = True
        page.locator("#fr").click()
        assert page.locator("html").get_attribute("lang") == "fr"
        assert page.locator("h1").inner_text() == "Rendre possible la prochaine occasion"
        assert page.locator("#selection tr").first.locator("td").last.inner_text() == "Non"
        report["checks"]["french_toggle"] = True
        page.screenshot(path=str(screenshots / "french.png"), full_page=True)
        page.locator("#en").click()
        page.locator("#regime").select_option("shift")
        shifted = page.evaluate("scenario()")
        assert shifted["unit"] < 0 and shifted["breakEven"] is None
        report["checks"]["shift_rejects_investment"] = shifted
        page.locator("#regime").select_option("confirmation")
        page.locator("#overhead").fill("500")
        page.locator("#overhead").dispatch_event("input")
        assert page.evaluate("scenario().unit") < 0
        report["checks"]["overhead_rejects_investment"] = True
        page.locator("#overhead").fill("0")
        page.locator("#rate").fill("0")
        page.locator("#rate").dispatch_event("input")
        assert page.evaluate("scenario().breakEven") is None
        report["checks"]["zero_rate_no_break_even"] = True
        page.locator("#rate").fill("100")
        page.locator("#workload").fill("7")
        page.locator("#workload").dispatch_event("input")
        assert page.evaluate("scenario().net") > 0
        report["checks"]["conditional_positive_scenario"] = True
        with page.expect_download() as item:
            page.locator("#download").click()
        downloaded = json.loads(Path(item.value.path()).read_text())
        assert downloaded["scenario"]["net"] > 0
        assert downloaded["actual_customer_collections"] == 0
        report["checks"]["scenario_json_download"] = True
        page.reload()
        for width in [390, 320]:
            page.set_viewport_size({"width": width, "height": 844})
            overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
            report["checks"][f"overflow_{width}"] = overflow
            assert not overflow
            page.screenshot(path=str(screenshots / f"mobile_{width}.png"), full_page=True)
        nojs = browser.new_context(java_script_enabled=False, viewport={"width": 390, "height": 844})
        nojspage = nojs.new_page()
        nojspage.goto((root / "index.html").as_uri())
        assert "Evidence summary / Résumé des résultats" in nojspage.locator("noscript").inner_text()
        report["checks"]["no_js_summary"] = True
        browser.close()
    assert not report["errors"]
    (root / "qa_report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", required=True)
    parser.add_argument("--screenshots", type=Path, required=True)
    args = parser.parse_args()
    main(args.chromium, args.screenshots)
