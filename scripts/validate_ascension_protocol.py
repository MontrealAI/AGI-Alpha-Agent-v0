# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual protocol desk, its arithmetic, evidence filters and offline delivery."""
from __future__ import annotations

import argparse
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Thread

from playwright.sync_api import expect, sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_ascension import Handler, inspect, wait_for
from scripts.ascension_protocol_evidence import ASSETS, CHECKS, ROOT, SCHEMA, asset_hashes, verify_report


def validate(site: Path, output: Path, url: str | None = None, axe_script: Path | None = None) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    version = json.loads((ROOT / "alpha_factory_v1/demos/catalog.json").read_text())["release"]
    expected_assets = asset_hashes()
    axe_script = axe_script or ROOT / "tests/browser/node_modules/axe-core/axe.min.js"
    if not axe_script.is_file():
        raise ValueError(
            "Install the browser test dependencies before protocol acceptance: npm ci --prefix tests/browser"
        )
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
            failures: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: failures.append(response.url) if response.status >= 400 else None)
            for name in ASSETS:
                response = context.request.get(origin + name + "?acceptance=" + commit)
                assert response.ok and hashlib.sha256(response.body()).hexdigest() == expected_assets[name], name
            if url:
                published = context.request.get(origin + "release.json?acceptance=" + commit).json()
                assert published["commit"] == commit and published["version"] == version
            page.goto(origin + "ascension-protocol/?acceptance=" + commit)
            assert page.locator('meta[name="application-version"]').get_attribute("content") == version
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
            assert (
                hashlib.sha256(artifact.read_bytes()).hexdigest()
                == expected_assets["assets/ascension-protocol/receipt.json"]
            )
            assert json.loads(artifact.read_text())["chainId"] == "31337"
            page.locator("#lots").focus()
            page.keyboard.press("ArrowUp")
            expect(page.locator("#lots")).to_have_value("26")
            expect(page.locator("#lots")).to_be_focused()
            axe_url = origin + "__acceptance__/axe.min.js"
            page.route(
                axe_url, lambda route: route.fulfill(path=str(axe_script.resolve()), content_type="text/javascript")
            )
            page.add_script_tag(url=axe_url)
            violations = page.evaluate(
                "async () => (await axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa']})).violations"
            )
            assert not violations, json.dumps(violations)
            page.set_viewport_size({"width": 390, "height": 844})
            page.goto(origin + "ascension-protocol/")
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            assert inspect(page, "document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(output / "protocol-mobile.png"), full_page=False)
            wait_for(page, "navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            page.goto(origin + "alpha_factory_v1/demos/ascension-protocol/")
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            assert inspect(page, "document.documentElement.scrollWidth <= innerWidth")
            context.set_offline(False)
            page.reload()
            expect(page.locator("#status")).to_contain_text("accounting reconciled")
            assert not errors and not failures, {"browser_errors": errors, "http_failures": failures}
            browser.close()
        report: dict[str, object] = {
            "schema": SCHEMA,
            "passed": True,
            "origin": origin,
            "commit": commit,
            "version": version,
            "asset_sha256": expected_assets,
            "checks": sorted(CHECKS),
            "browser_errors": errors,
            "http_failures": failures,
            "desktop": True,
            "mobile": True,
            "calculators": True,
            "receipts": True,
            "download": True,
            "offline": True,
        }
        verify_report(report, commit, version, origin)
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
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script), indent=2))
