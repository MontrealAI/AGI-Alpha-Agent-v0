# SPDX-License-Identifier: Apache-2.0
"""Rendered MARK wallet acceptance using a synthetic EIP-1193 provider; no real signing."""
from __future__ import annotations
import argparse
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Thread
import tomllib
from playwright.sync_api import expect, sync_playwright
from scripts.validate_ascension import Handler, inspect
from scripts.mark_wallet_evidence import ASSETS, CHECKS, ROOT, hashes, verify_report


def validate(site: Path, output: Path, url: str | None = None) -> dict:
    """Exercise signing boundaries, recovery, accessibility and exact served assets."""
    output.mkdir(parents=True, exist_ok=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    expected = hashes()
    server = None
    if url:
        if not url.startswith("https://"):
            raise ValueError("Public acceptance requires HTTPS")
        origin = url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    runtimes = json.loads((ROOT / "deployments/ethereum-mainnet/2026-10-11/runtime-code.json").read_text())
    manifest = json.loads((ROOT / "deployments/ethereum-mainnet/2026-10-11/manifest.json").read_text())
    codes = {item["address"].lower(): runtimes[name] for name, item in manifest["contracts"].items()}
    fixture = "window.__markFixtureConfig=" + json.dumps({"origin": origin, "codes": codes}) + ";\n"
    fixture += (ROOT / "tests/mark-wallet/browser-provider.js").read_text()
    target = origin + "ascension-protocol/mainnet/"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            context.add_init_script(script=fixture)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            for name in ASSETS:
                response = context.request.get(origin + name)
                assert response.ok and hashlib.sha256(response.body()).hexdigest() == expected[name], name
            if url:
                identity = context.request.get(origin + "release.json?wallet=" + commit).json()
                assert identity["commit"] == commit and identity["version"] == version
            page.goto(target)
            expect(page.locator("#wallet-choice option")).to_have_count(2)
            assert page.locator("#wallet-choice img").count() == 0
            page.locator("#wallet-choice").select_option("0")
            page.locator("#inspect").click()
            expect(page.locator("#status")).to_contain_text("Observation complete", timeout=30000)
            assert "eth_requestAccounts" not in page.evaluate("window.__markFixture.calls")
            page.locator("#connect").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#status")).to_contain_text("Account connected")
            page.locator("#action").select_option("buy")
            for field, value in (("id", "1"), ("count", "1"), ("maxCost", "2")):
                page.locator("#field-" + field).fill(value)
            page.locator("#prepare").click()
            expect(page.locator("#status")).to_contain_text("not commissioned")
            assert page.evaluate("window.__markFixture.sends") == 0

            def prepare() -> None:
                page.locator("#action").select_option("reclaim")
                page.locator("#field-id").fill("1")
                page.locator("#prepare").click()
                expect(page.locator("#preview-panel")).to_be_visible(timeout=30000)
                expect(page.locator("#confirm")).to_be_disabled()
                page.locator("#ack").check()

            prepare()
            page.evaluate("window.__markFixture.mode='reject'")
            page.locator("#confirm").click()
            expect(page.locator("#status")).to_contain_text("rejected")
            prepare()
            page.evaluate("window.__markFixture.mode='unknown'")
            page.locator("#confirm").click()
            expect(page.locator("#status")).to_contain_text("unknown")
            with page.expect_download() as download:
                page.locator("#export-journal").click()
            backup = output / "synthetic-journal.json"
            download.value.save_as(backup)
            page.reload()
            page.locator("#wallet-choice").select_option("0")
            page.locator("#action").select_option("reclaim")
            page.locator("#field-id").fill("1")
            page.locator("#prepare").click()
            expect(page.locator("#status")).to_contain_text("outstanding")
            page.locator("#reconcile-hash").fill("0x" + "ab" * 32)
            page.evaluate("window.__markFixture.finalized=false")
            page.locator("#reconcile").click()
            expect(page.locator("#status")).to_contain_text("mined-not-finalized")
            page.evaluate("window.__markFixture.reorg=true")
            page.locator("#reconcile").click()
            expect(page.locator("#status")).to_contain_text("canonical")
            page.evaluate(
                "window.__markFixture.reorg=false;window.__markFixture.finalized=true;"
                "window.__markFixture.cancelled=true"
            )
            page.locator("#reconcile-hash").fill("0x" + "cd" * 32)
            page.locator("#reconcile").click()
            expect(page.locator("#status")).to_contain_text("cancelled")
            expect(page.locator("#transaction-link a")).to_have_attribute(
                "href", "https://etherscan.io/tx/0x" + "cd" * 32
            )
            page.locator("#import-journal").set_input_files(backup)
            expect(page.locator("#status")).to_contain_text("Journal imported")
            page.locator("#reconcile").click()
            expect(page.locator("#status")).to_contain_text("cancelled")
            other = context.new_page()
            other.goto(target)
            other.evaluate(
                "window.__held=false;void navigator.locks.request('agialpha.mark-wallet-journal.v2',"
                "async()=>{window.__held=true;await new Promise(r=>window.__release=r)})"
            )
            other.wait_for_function("window.__held")
            prepare()
            page.locator("#confirm").click()
            expect(page.locator("#status")).to_contain_text("Another MARK tab")
            assert page.evaluate("window.__markFixture.sends") == 0
            other.evaluate("window.__release()")
            other.close()
            page.locator("#cancel").click()
            page.locator("#language").click()
            expect(page.locator("html")).to_have_attribute("lang", "fr")
            axe = (ROOT / "tests/browser/node_modules/axe-core/axe.min.js").read_text()
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
                inspect(page, axe + ";void 0")
                result = inspect(
                    page, "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
                )
                assert not result["violations"], result["violations"]
                page.screenshot(path=str(output / f"wallet-{width}.png"), full_page=True)
            assert not errors, errors
            browser.close()
    finally:
        if server:
            server.shutdown()
    report = {
        "schema": "agialpha.mark-wallet.acceptance.v1",
        "passed": True,
        "commit": commit,
        "version": version,
        "origin": origin,
        "assets": expected,
        "checks": CHECKS,
        "realMainnetTransactions": False,
        "physicalWalletValidated": False,
    }
    verify_report(report, commit, version, origin)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "docs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url")
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url), indent=2))
