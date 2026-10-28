# SPDX-License-Identifier: Apache-2.0
"""Check the complete offline reader; no external requests are permitted."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "publication/BROWSER_EDITION.html"
OUT = ROOT / "verification/publication_qa"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    report: dict = {"html_sha256": hashlib.sha256(PAGE.read_bytes()).hexdigest(), "views": []}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width, height, js in [(1440, 1000, True), (390, 844, True), (390, 844, False)]:
            context = browser.new_context(viewport={"width": width, "height": height}, java_script_enabled=js)
            errors: list[str] = []
            external: list[str] = []
            page = context.new_page()
            page.on("pageerror", lambda err: errors.append(str(err)))
            page.on("request", lambda req: external.append(req.url) if req.url.startswith(("https:", "http:")) else None)
            page.goto(PAGE.as_uri(), wait_until="load")
            page.screenshot(path=str(OUT / f"reader-{width}-js-{js}.png"))
            stats = page.evaluate("""() => ({
                width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
                images: [...document.images].map(i => ({loaded: i.complete && i.naturalWidth>0, alt: i.alt})),
                math: document.querySelectorAll('math').length,
                brokenFragments: [...document.querySelectorAll('a[href^="#"]')].filter(a =>
                    !document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a => a.hash),
                words: document.querySelector('main').innerText.split(/\\s+/).length,
                figures: document.querySelectorAll('figure').length,
                headings: document.querySelectorAll('main h1').length, tocLinks: document.querySelectorAll('.toc a').length
            })""")
            assert stats["scrollWidth"] <= width + 1, stats
            assert len(stats["images"]) == 4 and all(i["loaded"] and i["alt"] for i in stats["images"]), stats
            assert stats["math"] > 20 and stats["words"] > 6500, stats
            assert not stats["brokenFragments"] and stats["tocLinks"] == stats["headings"], stats
            if js:
                assert "0.03633" in page.locator("#verdict").inner_text()
                page.locator(".widget").scroll_into_view_if_needed()
                page.screenshot(path=str(OUT / f"reader-widget-{width}.png"))
                for access in ["old", "actuator", "sensor"]:
                    page.select_option("#access", access)
                    assert "identical response families" in page.locator("#verdict").inner_text()
                page.select_option("#access", "joint")
                page.locator("#noise").fill("40")
                page.locator("#noise").dispatch_event("input")
                assert "No guaranteed distinction" in page.locator("#verdict").inner_text()
                page.locator("#noise").fill("0")
                page.locator("#noise").dispatch_event("input")
                assert "0.04633" in page.locator("#verdict").inner_text()
            else:
                assert page.locator("noscript").is_visible()
            assert not external and not errors, (external, errors)
            report["views"].append({"width": width, "height": height, "javascript": js, **stats,
                                    "page_errors": errors, "external_requests": external})
            context.close()
        browser.close()
    report["passed"] = True
    (OUT / "browser_review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": True, "views": len(report["views"]), "html_sha256": report["html_sha256"]}))


if __name__ == "__main__":
    main()
