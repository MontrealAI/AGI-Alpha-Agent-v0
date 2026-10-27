#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Check all recorded cases, bilingual controls, downloads and responsive layout."""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

WEB = Path(__file__).resolve().parent
OUT = WEB / "qa"
OUT.mkdir(exist_ok=True)
errors: list[str] = []
checks: list[str] = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.emulate_media(reduced_motion="reduce")
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto((WEB / "index.html").as_uri())
    assert page.locator("#case-select option").count() == 24
    missing = page.evaluate("Object.keys(copy.en).filter(k => !copy.fr[k])")
    assert not missing, missing
    for language in ["en", "fr"]:
        page.locator("#lang-" + language).click()
        assert page.locator("html").get_attribute("lang") == language
        for i in range(24):
            page.locator("#case-select").select_option(str(i))
            state = page.evaluate(
                "({id: DATA.cases[index].task.id, invalid: DATA.cases[index].report.input_errors.length > 0, findings: DATA.cases[index].report.blockers.length + DATA.cases[index].report.original_unmet_obligations.length})"
            )
            assert page.locator("#case-title").inner_text() == state["id"]
            assert page.locator("#invalid-box").is_visible() == state["invalid"]
            if not state["invalid"]:
                assert page.locator("#case-findings .finding").count() == state["findings"]
            checks.append(language + ":" + state["id"])
        page.locator("#witness-nectar").click()
        assert page.locator("#witness-source").inner_text() == "0 / 0 / 0"
        assert page.locator("#witness-blockers").inner_text() == "14"
        page.locator("#witness-flower").click()
        assert page.locator("#witness-source").inner_text() == "5 / 5 / 3"
        assert page.locator("#witness-blockers").inner_text() == "2"
    page.locator("#saving").fill("6")
    assert page.evaluate('document.getElementById("econ-decision").textContent === txt("equal")')
    page.locator("#saving").fill("6.25")
    assert page.evaluate('document.getElementById("econ-decision").textContent === txt("approve")')
    page.locator("#saving").fill("0")
    assert page.evaluate('document.getElementById("econ-decision").textContent === txt("stop")')
    page.locator("#case-select").select_option("19")
    with page.expect_download() as d:
        page.locator("#download-case").click()
    download = d.value
    saved = OUT / "download-test.json"
    download.save_as(saved)
    assert json.loads(saved.read_text())["task"]["id"] == "B-20261027-08"
    saved.unlink()
    page.locator("#lang-en").click()
    page.locator("#case-select").select_option("0")
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(OUT / "desktop-en.png"), full_page=True)
    page.locator(".topbar").evaluate("el => el.style.visibility = 'hidden'")
    page.locator("#experiment").screenshot(path=str(OUT / "explorer-en.png"))
    page.locator(".topbar").evaluate("el => el.style.visibility = ''")
    page.locator("#lang-fr").click()
    page.locator("#case-select").select_option("19")
    page.locator(".topbar").evaluate("el => el.style.visibility = 'hidden'")
    page.locator("#experiment").screenshot(path=str(OUT / "explorer-fr.png"))
    page.locator(".topbar").evaluate("el => el.style.visibility = ''")
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(OUT / "desktop-fr.png"), full_page=True)
    responsive = []
    for width in [390, 768, 1440]:
        page.set_viewport_size({"width": width, "height": 844})
        overflow = page.evaluate("document.documentElement.scrollWidth > innerWidth")
        assert not overflow, width
        responsive.append({"width": width, "horizontal_overflow": overflow})
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0, 0)")
    page.screenshot(path=str(OUT / "mobile-fr.png"), full_page=True)
    page.locator(".topbar").evaluate("el => el.style.visibility = 'hidden'")
    page.locator("#experiment").screenshot(path=str(OUT / "explorer-mobile-fr.png"))
    assert not errors, errors
    browser.close()
report = {
    "schema": "agialpha.demo-qa.v1",
    "recorded_case_renders": len(checks),
    "languages": ["en", "fr"],
    "cases": checks,
    "witness_toggles": "passed both languages",
    "retention_boundary": "25 uses: $6 break-even; $6.25 positive; $0 negative",
    "download_json": "passed: B-20261027-08",
    "responsive": responsive,
    "page_errors": errors,
    "missing_translations": missing,
    "status": "passed",
    "not_claimed": ["ecological execution", "live model call", "publication", "external link availability"],
}
(OUT / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k != "cases"}, indent=2))
