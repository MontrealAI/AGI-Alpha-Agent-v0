# SPDX-License-Identifier: Apache-2.0
"""Exercise the paired-system guide within local and public homepage acceptance."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from playwright.sync_api import Browser, Page, expect

from scripts.homepage_evidence import ECOSYSTEM_CHECKS, ECOSYSTEM_LAYOUTS
from scripts.validate_ascension import inspect


def inspect_directory(page: Page, data: dict[str, Any]) -> None:
    """Require the exact complete inventory in ordinary rendered HTML and explorer links."""
    contracts = data["alpha"]["contracts"] + data["jobs"]["contracts"]
    expect(page.locator("#token-address")).to_have_text(data["token"]["address"])
    expect(page.locator(".contract-directory tbody tr")).to_have_count(len(contracts))
    for contract in contracts:
        link = page.locator(f'.contract-directory a[href="https://etherscan.io/address/{contract["address"]}#code"]')
        expect(link).to_have_count(1)
        expect(link.locator("code")).to_have_text(contract["address"])
        expect(link.locator("xpath=../..").locator('th[scope="row"]')).to_have_text(contract["name"])
    for suite in ("alpha", "jobs"):
        expect(page.locator(f'a[href="{data[suite]["source"]}"]')).to_be_visible()
    for directory in page.locator(".contract-directory").all():
        if directory.get_attribute("open") is None:
            directory.locator("summary").click()
    for address in page.locator(".contract-directory td code").all():
        expect(address).to_be_visible()


def validate(browser: Browser, origin: str, output: Path, axe_source: str) -> dict[str, Any]:
    """Test public directory facts and controls without sending transactions or opening wallets."""
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "docs/assets/ecosystem/contracts.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "schema": "agialpha.ecosystem.acceptance.v1",
        "passed": False,
        "checks": [],
        "browser_errors": [],
        "layouts": [],
        "addresses": sorted(c["address"] for s in ("alpha", "jobs") for c in data[s]["contracts"]),
    }
    contexts = []
    try:
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            reduced_motion="reduce",
            permissions=["clipboard-read", "clipboard-write"],
        )
        contexts.append(context)
        page = context.new_page()
        page.on("pageerror", lambda error: report["browser_errors"].append(str(error)))
        for width, language, large in sorted(ECOSYSTEM_LAYOUTS):
            page.set_viewport_size({"width": width, "height": 1000})
            path = "ecosystem/" + ("fr/" if language == "fr" else "")
            page.goto(origin + path + ("?text=large" if large else ""), wait_until="networkidle")
            expect(page.locator("html")).to_have_attribute("lang", language)
            expect(page.get_by_role("heading", level=1)).to_be_visible()
            expect(page.locator("#text-size")).to_have_attribute("aria-pressed", str(large).lower())
            inspect_directory(page, data)
            assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1"), "Guide overflow"
            controls = inspect(
                page,
                """[...document.querySelectorAll(`header a, header button, .hero .button, .token-actions a,
                .token-actions button, summary, .contract-directory td a, .invitation a, footer a`)]
                .filter(el => el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden')
                .map(el => { const r = el.getBoundingClientRect(); return {
                  label: (el.innerText || el.id).trim(), width: r.width, height: r.height }; })""",
            )
            assert controls and all(min(c["width"], c["height"]) >= 43.5 for c in controls), controls
            inspect(page, axe_source + "; void 0")
            audit = inspect(page, "axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})")
            report["layouts"].append(
                {
                    "width": width,
                    "language": language,
                    "large_text": large,
                    "controls": controls,
                    "violations": audit["violations"],
                }
            )
            assert not audit["violations"], audit["violations"]
            page.locator("header").scroll_into_view_if_needed()
            page.screenshot(path=str(output / f"ecosystem-{language}-{width}{'-large' if large else ''}.png"))
            if width == 1440 and language == "en":
                page.locator("#contracts").screenshot(path=str(output / "ecosystem-contract-directory.png"))

        page.goto(origin + "ecosystem/", wait_until="networkidle")
        page.keyboard.press("Tab")
        expect(page.locator("a.skip")).to_be_focused()
        page.keyboard.press("Enter")
        expect(page.locator("#main")).to_be_focused()
        base_size = inspect(page, "parseFloat(getComputedStyle(document.body).fontSize)")
        page.locator("#text-size").click()
        assert inspect(page, "parseFloat(getComputedStyle(document.body).fontSize)") > base_size
        page.reload(wait_until="networkidle")
        expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
        page.locator('nav a[hreflang="fr"]').click()
        expect(page.locator("html")).to_have_attribute("lang", "fr")
        expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
        assert parse_qs(urlsplit(page.url).query) == {"text": ["large"]}
        page.locator("#copy-token").click()
        expect(page.locator('[role="status"]')).to_have_text("Adresse complète du jeton copiée.")
        assert inspect(page, "navigator.clipboard.readText()") == data["token"]["address"]
        # Inject a denied clipboard operation in this test context and require usable fallback guidance.
        inspect(
            page,
            "Object.defineProperty(navigator.clipboard, 'writeText', {configurable:true, "
            "value:() => Promise.reject(new Error('Injected clipboard denial'))}); true",
        )
        page.locator("#copy-token").click()
        expect(page.locator('[role="status"]')).to_have_text("Sélectionnez et copiez l’adresse complète ci-dessus.")
        expect(page.locator("#token-address")).to_have_text(data["token"]["address"])
        page.locator("header a.brand").click()
        expect(page.locator("html")).to_have_attribute("lang", "fr")
        expect(page.locator("#home-text-size")).to_have_attribute("aria-pressed", "true")
        page.locator('[data-home-key="ecosystem-contracts"]').click()
        expect(page).to_have_url(origin + "ecosystem/fr/?text=large#contracts")

        unavailable = browser.new_context()
        contexts.append(unavailable)
        unavailable.add_init_script("Object.defineProperty(navigator, 'clipboard', {value:undefined});")
        unavailable_page = unavailable.new_page()
        unavailable_page.goto(origin + "ecosystem/", wait_until="networkidle")
        expect(unavailable_page.locator("#copy-token")).to_be_hidden()
        expect(unavailable_page.locator("#token-address")).to_have_text(data["token"]["address"])

        no_js = browser.new_context(java_script_enabled=False, viewport={"width": 320, "height": 1000})
        contexts.append(no_js)
        fallback = no_js.new_page()
        for language in ("en", "fr"):
            fallback.goto(origin + "ecosystem/" + ("fr/" if language == "fr" else ""))
            expect(fallback.locator("html")).to_have_attribute("lang", language)
            expect(fallback.get_by_role("heading", level=1)).to_be_visible()
            expect(fallback.locator("#copy-token")).to_be_hidden()
            expect(fallback.locator("#text-size")).to_be_hidden()
            inspect_directory(fallback, data)
            assert inspect(fallback, "document.documentElement.scrollWidth <= innerWidth + 1")
            fallback.locator("header").scroll_into_view_if_needed()
            fallback.screenshot(path=str(output / f"ecosystem-{language}-no-javascript.png"))
        assert not report["browser_errors"], report["browser_errors"]
        report["checks"] = sorted(ECOSYSTEM_CHECKS)
        report["passed"] = True
    finally:
        for context in contexts:
            context.close()
        (output / "ecosystem.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report
