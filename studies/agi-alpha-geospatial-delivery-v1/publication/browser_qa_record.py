# SPDX-License-Identifier: Apache-2.0
"""Optional Playwright checks; install Playwright and its Chromium separately."""

import argparse
import hashlib
import json
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
out.mkdir(exist_ok=True)
receipt = {
    "source": str(source.relative_to(root)),
    "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "viewports": [],
}
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.chromium_executable, headless=True, args=["--no-sandbox"])
    for name, width, height in [("desktop", 1440, 1050), ("mobile", 390, 844)]:
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
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
        evidence["all_local_links_exist"] = all(
            (publication / h.split("#")[0]).resolve().is_file() for h in evidence["localLinks"]
        )
        evidence["pass"] = (
            evidence["documentWidth"] <= width
            and evidence["allImagesLoaded"]
            and evidence["missingAlt"] == 0
            and all(a["target"] for a in evidence["internalLinks"])
            and evidence["all_local_links_exist"]
            and not errors
        )
        page.screenshot(path=str(out / f"{name}-top.png"))
        page.locator("img").first.scroll_into_view_if_needed()
        page.screenshot(path=str(out / f"{name}-figure.png"))
        receipt["viewports"].append(evidence)
        page.close()
    browser.close()
receipt["pass"] = all(v["pass"] for v in receipt["viewports"])
(out / "receipt.json").write_text(json.dumps(receipt, indent=2))
print(json.dumps(receipt, indent=2))
raise SystemExit(0 if receipt["pass"] else 1)
