# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual protocol desk, its arithmetic, evidence filters and offline delivery."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from threading import Thread

from playwright.sync_api import expect, sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_ascension import Handler, inspect, wait_for


def validate(site: Path, output: Path, url: str | None = None) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if url:
        if not url.startswith("https://"):
            raise ValueError("Public validation requires HTTPS")
        origin = url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "ascension-protocol/")
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            expect(page.locator("#funded")).to_have_text("158")
            expect(page.locator("#burned")).to_have_text("0.8")
            expect(page.locator("#quote")).to_have_text("158 $AGIALPHA")
            expect(page.locator("#auction-note")).to_contain_text("Wins against")
            page.screenshot(path=str(output / "protocol-desktop.png"), full_page=False)
            page.locator("#lots").fill("25")
            expect(page.locator("#quote")).to_have_text("80 $AGIALPHA")
            page.locator("#supply").fill("1000000")
            expect(page.locator("#quote")).to_have_text("Check inputs")
            page.locator("#supply").fill("0")
            page.locator("#bid-time").fill("86400")
            expect(page.locator("#auction-note")).to_contain_text("Loses to")
            page.locator("#stage").select_option(label="Validation")
            expect(page.locator("#trace-count")).to_have_text("2 recorded transactions")
            page.locator("#trace details").first.locator("summary").click()
            expect(page.locator("#trace pre").first).to_contain_text('"resultHash"')
            with page.expect_download() as downloaded:
                page.get_by_role("link", name="Download complete evidence").click()
            artifact = output / "downloaded-evidence.json"
            downloaded.value.save_as(artifact)
            assert json.loads(artifact.read_text())["chainId"] == "31337"
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(origin + "ascension-protocol/")
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            assert inspect(page, "document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "protocol-mobile.png"), full_page=False)
            wait_for(page, "navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            assert not errors, errors
            browser.close()
        report: dict[str, object] = {
            "desktop": True,
            "mobile": True,
            "calculators": True,
            "receipts": True,
            "download": True,
            "offline": True,
        }
        (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
        return report
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url")
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url), indent=2))
