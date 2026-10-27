# SPDX-License-Identifier: Apache-2.0
"""Read-only browser checks of demo navigation and the full paper edition."""

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
    records, errors = {}, []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=CHROME, args=["--no-sandbox"])
        page = await browser.new_page(viewport={"width": 1440, "height": 1050})
        page.on("pageerror", lambda error: errors.append(str(error)))
        await page.goto((HERE / "index.html").as_uri())
        assert not await page.locator("#econPending").is_visible()
        assert "10,000 resamples, seed 854201" in await page.locator('[data-i18n="timingNote"]').inner_text()
        links = await page.locator(".actions a").evaluate_all(
            "es => es.map(e=>({text:e.textContent,path:e.getAttribute('href')}))"
        )
        for link in links:
            target = (HERE / link["path"]).resolve()
            assert target.exists(), target
            if target.suffix == ".pdf":
                assert target.read_bytes().startswith(b"%PDF"), target
        await page.locator("#fr").click()
        assert "10 000 rééchantillonnages" in await page.locator('[data-i18n="timingNote"]').inner_text()
        assert "Encaissements bruts" in await page.locator("#economicMetrics").inner_text()
        assert "Réserves et expositions" in await page.locator("#economicMetrics").inner_text()
        await page.locator(".actions").screenshot(path=output / "publication-links-fr.png")
        await page.set_viewport_size({"width": 320, "height": 800})
        assert not await page.evaluate("document.documentElement.scrollWidth > innerWidth")
        records["demo"] = {
            "relative_links": links,
            "all_targets_exist": True,
            "actual_economy_visible": True,
            "separate_bootstrap_disclosed_en_fr": True,
            "mobile_french_overflow": False,
        }
        for filename in ["paper.html", "evidence.html"]:
            await page.set_viewport_size({"width": 1440, "height": 1050})
            await page.goto((HERE / filename).as_uri())
            await page.screenshot(path=output / f"{filename[:-5]}-desktop.png")
            record = await page.evaluate("""() => ({
                title:document.title, language:document.documentElement.lang,
                headings:document.querySelectorAll('h1,h2,h3').length,
                figures:document.querySelectorAll('figure').length,
                images:document.querySelectorAll('img').length,
                brokenImages:[...document.images].filter(e=>!e.complete||!e.naturalWidth).length,
                math:document.querySelectorAll('math').length,
                displayMath:document.querySelectorAll('math[display="block"]').length,
                emptyMath:[...document.querySelectorAll('math')].filter(e=>!e.getBoundingClientRect().height).length,
                citations:document.querySelectorAll('[data-cites]').length,
                missingCitationTargets:[...document.querySelectorAll('[data-cites]')].flatMap(e=>e.dataset.cites.split(' ')).filter(k=>!document.getElementById('ref-'+k)),
                brokenInternalLinks:[...document.querySelectorAll('a[href^="#"]')].map(a=>a.getAttribute('href').slice(1)).filter(id=>id&&!document.getElementById(id)),
                desktopOverflow:document.documentElement.scrollWidth>innerWidth,
                author:document.body.innerText.includes('Vincent Boucher'),
                president:document.body.innerText.includes('President of MONTREAL.AI')
            })""")
            if record["figures"]:
                await page.locator("figure").first.screenshot(path=output / f"{filename[:-5]}-figure.png")
            if record["displayMath"]:
                await page.locator('math[display="block"]').first.screenshot(
                    path=output / f"{filename[:-5]}-equation.png"
                )
            for width in [390, 320]:
                await page.set_viewport_size({"width": width, "height": 844})
                await page.evaluate("scrollTo(0,0)")
                if width == 390:
                    await page.screenshot(path=output / f"{filename[:-5]}-mobile.png")
                record[f"overflow_{width}"] = await page.evaluate("document.documentElement.scrollWidth>innerWidth")
                if record[f"overflow_{width}"]:
                    record[f"overflow_elements_{width}"] = await page.evaluate(
                        """() => [...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+2).slice(0,15).map(e=>({tag:e.tagName,cls:e.className.baseVal||e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,80)}))"""
                    )
            records[filename] = record
        await browser.close()
    report = {
        "records": records,
        "javascript_errors": errors,
        "source_hashes": {
            f: hashlib.sha256((HERE / f).read_bytes()).hexdigest()
            for f in ["index.html", "paper.html", "evidence.html"]
        },
        "scope": "Read-only local Chromium qualification; no public served-byte acceptance",
    }
    (output / "PUBLICATION_QA.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


asyncio.run(main())
