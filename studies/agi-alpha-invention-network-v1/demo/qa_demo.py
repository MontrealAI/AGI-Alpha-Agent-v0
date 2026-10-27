# SPDX-License-Identifier: Apache-2.0
"""Exercise the self-contained EN/FR evidence companion in a real browser."""

import asyncio
import hashlib
import json
import os
from pathlib import Path

from playwright.async_api import async_playwright

HERE = Path(__file__).resolve().parent
CHROME = os.environ.get("CHROME_EXECUTABLE")
LOCAL_CHROME = Path("/tmp/breakthrough-relay-browser/chrome-headless-shell-linux64/chrome-headless-shell")
if CHROME is None and LOCAL_CHROME.exists():
    CHROME = str(LOCAL_CHROME)


async def main():
    output = HERE / "qa"
    output.mkdir(exist_ok=True)
    errors, remote, checks = [], [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1440, "height": 1050}, device_scale_factor=1)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda req: remote.append(req.url) if req.url.startswith(("https:", "http:")) else None)
        await page.goto((HERE / "index.html").as_uri(), wait_until="load")
        await page.get_by_role("heading", name="The network that learns to invent.").wait_for()
        checks.append("English edition rendered")
        await page.screenshot(path=output / "desktop-en.png", full_page=True)
        await page.screenshot(path=output / "desktop-en-hero.png")
        await page.locator(".heatmaps").screenshot(path=output / "desktop-fields.png")
        await page.locator(".latency-grid").screenshot(path=output / "desktop-comparison.png")
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        await page.locator("#fieldCase").select_option("4")
        await page.locator("#fieldScale").select_option("individual")
        assert "transfer-" in await page.locator("#caseMeta").inner_text()
        checks.append("Fresh field and scale controls update")
        await page.locator("#family").select_option("ood")
        await page.locator("#baseline").select_option("improved_generalist")
        assert "Negative transfer" in await page.locator("#comparisonNote").inner_text()
        await page.locator("#sensorCondition").select_option("6")
        checks.append("Strong baseline, shifted cases and composition controls update")
        await page.locator("#scaleFactor").focus()
        await page.locator("#scaleFactor").press("End")
        assert "1,000,000" in await page.locator("#scaleValue").inner_text()
        checks.append("Counterfactual arithmetic responds without changing observed results")
        economy_ready = await page.evaluate("!!window.RESEARCH.economy")
        if economy_ready:
            assert not await page.locator("#econPending").is_visible()
            assert await page.locator("#economicMetrics .kpi").count() == 9
            await page.locator("#economicMetrics").screenshot(path=output / "desktop-economics.png")
            await page.locator("#economicScenario").select_option("forced_retention")
            await page.locator("#economicPolicy").select_option("shared_gym_composition")
            assert len(await page.locator("#economicTable tr").all()) == 5
            checks.append("Actual enterprise results, stress and policy controls update")
        else:
            checks.append("Economic section honestly marked pending")
        await page.locator("#fr").click()
        assert await page.locator("html").get_attribute("lang") == "fr"
        assert "apprend à inventer" in await page.locator("h1").inner_text()
        assert "transfert négatif" in (await page.locator("#comparisonNote").inner_text()).lower()
        checks.append("French text and live result labels update")
        await page.locator("#family").select_option("all")
        await page.locator("#baseline").select_option("spectral_pcg")
        await page.locator("#scaleFactor").press("Home")
        await page.screenshot(path=output / "desktop-fr.png", full_page=True)
        async with page.expect_download() as download:
            await page.locator("#downloadReceipt").click()
        exported = await download.value
        await exported.save_as(output / "downloaded-receipt.json")
        receipt = json.loads((output / "downloaded-receipt.json").read_text())
        assert receipt["language"] == "fr"
        assert receipt["identities"]["technical_results"]
        checks.append("Receipt download contains actual source/result identities")
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.evaluate("scrollTo(0,0)")
        await page.screenshot(path=output / "mobile-fr.png", full_page=True)
        await page.screenshot(path=output / "mobile-fr-hero.png")
        await page.locator(".heatmaps").screenshot(path=output / "mobile-fr-fields.png")
        if economy_ready:
            await page.locator("#economicMetrics").screenshot(path=output / "mobile-fr-economics.png")
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        await page.locator("#en").click()
        await page.screenshot(path=output / "mobile-en.png", full_page=True)
        await page.set_viewport_size({"width": 320, "height": 800})
        await page.locator("#fr").click()
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        await page.locator("#en").click()
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        checks.append("390px and 320px mobile widths have no document overflow")
        label_check = await page.evaluate("""() => [...document.querySelectorAll('select,input')].every(e =>
            document.querySelector('label[for="' + e.id + '"]'))""")
        assert label_check
        checks.append("All interactive inputs have associated labels")
        await browser.close()
    assert not errors, errors
    assert not remote, remote
    checks.extend(["No JavaScript errors", "No external network requests"])
    report = {
        "checks": checks,
        "pass_count": len(checks),
        "javascript_errors": errors,
        "external_requests": remote,
        "economics_ready": economy_ready,
        "index_sha256": hashlib.sha256((HERE / "index.html").read_bytes()).hexdigest(),
        "screenshots": sorted(x.name for x in output.glob("*.png")),
        "scope": "Actual Chromium automation of local standalone HTML; no public deployment qualification",
    }
    (output / "QA_REPORT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


asyncio.run(main())
