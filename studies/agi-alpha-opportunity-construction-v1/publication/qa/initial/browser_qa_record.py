# SPDX-License-Identifier: Apache-2.0
"""Optional Playwright checks; install Playwright and its Chromium separately."""

import argparse
import datetime
import hashlib
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--chromium-executable", default=None)
args = parser.parse_args()
root = Path(__file__).resolve().parent.parent
publication = root / "publication"
source = publication / "AGI_ALPHA_FLYWHEEL.html"
out = args.output
out.mkdir(parents=True, exist_ok=True)
receipt = {
    "source": str(source.relative_to(root)),
    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "command_argv": [sys.executable, *sys.argv],
    "checked_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "viewports": [],
}
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chromium_executable, headless=True, args=["--no-sandbox"])
    receipt["browser_version"] = browser.version
    for name, width, height in [("desktop", 1440, 1050), ("mobile", 390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        errors = []
        console_errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(source.as_uri(), wait_until="load")
        page.evaluate("""async () => {
          for (const i of document.images) { i.loading='eager'; }
          await Promise.all(Array.from(document.images).map(i => i.complete ? Promise.resolve() : new Promise(r => { i.onload=r; i.onerror=r; })));
        }""")
        evidence = page.evaluate("""() => ({
          title: document.title,
          h1: document.querySelector('h1')?.textContent,
          headings: document.querySelectorAll('h2,h3').length,
          viewport: window.innerWidth,
          documentWidth: document.documentElement.scrollWidth,
          allImagesLoaded: Array.from(document.images).every(i=>i.complete && i.naturalWidth>0),
          images: document.images.length,
          missingAlt: Array.from(document.images).filter(i=>!i.alt).length,
          internalLinks: Array.from(document.querySelectorAll('a[href^="#"]')).map(a=>({href:a.getAttribute('href'),target:!!document.getElementById(a.getAttribute('href').slice(1))})),
          localLinks: Array.from(document.querySelectorAll('a[href]')).map(a=>a.getAttribute('href')).filter(h=>!h.startsWith('http')&&!h.startsWith('#'))
        })""")
        evidence["viewport_name"] = name
        evidence["page_errors"] = errors
        evidence["console_errors"] = console_errors
        evidence["missing_local_links"] = [
            h for h in evidence["localLinks"] if not (publication / h.split("#")[0]).resolve().is_file()
        ]
        evidence["all_local_links_exist"] = not evidence["missing_local_links"]
        navigation = page.locator('a[href^="#"]').first
        target_href = navigation.get_attribute("href")
        # The first internal link is the accessibility skip link, which is
        # intentionally off-screen until focused. Exercise its keyboard path.
        navigation.focus()
        navigation.press("Enter")
        page.wait_for_function("expected => location.hash === expected", arg=target_href, timeout=5000)
        evidence["clicked_navigation"] = {
            "href": target_href,
            "observed_hash": page.evaluate("location.hash"),
            "interaction": "keyboard focus and Enter",
        }
        evidence["navigation_pass"] = evidence["clicked_navigation"]["observed_hash"] == target_href
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
        evidence["pass"] = (
            evidence["documentWidth"] <= width
            and evidence["allImagesLoaded"]
            and evidence["missingAlt"] == 0
            and all(a["target"] for a in evidence["internalLinks"])
            and evidence["all_local_links_exist"]
            and not errors
            and not console_errors
            and evidence["navigation_pass"]
        )
        page.screenshot(path=str(out / f"{name}-top.png"))
        page.locator("img").first.scroll_into_view_if_needed()
        page.screenshot(path=str(out / f"{name}-figure.png"))
        receipt["viewports"].append(evidence)
        page.close()
    browser.close()
receipt["pass"] = all(v["pass"] for v in receipt["viewports"])
receipt["source_sha256_after"] = hashlib.sha256(source.read_bytes()).hexdigest()
receipt["source_unchanged"] = receipt["sha256"] == receipt["source_sha256_after"]
receipt["pass"] = receipt["pass"] and receipt["source_unchanged"]
(out / "receipt.json").write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if receipt["pass"] else 1)
