# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual Nova Studio preparation and recovery UI without signing."""
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
from typing import Any

from playwright.sync_api import expect, sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.nova_studio_evidence import CHECKS, ROOT, hashes, verify_report
from scripts.validate_ascension import Handler, inspect

PHRASE = "public browser acceptance capsule phrase 2026"
PROVIDER = """
window.__novaRequests=[];
window.ethereum={request:async({method})=>{window.__novaRequests.push(method);
  throw new Error('No wallet call is authorized by this preparation test');},on(){},removeListener(){}};
"""


def validate(site: Path, output: Path, url: str | None = None) -> dict[str, Any]:
    """Check UI crypto, exact exports, hostile imports and readable EN/FR layouts."""
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
    target = origin + "ascension/mainnet/"
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            context.add_init_script(script=PROVIDER)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            for name in expected:
                response = context.request.get(origin + name)
                assert response.ok and hashlib.sha256(response.body()).hexdigest() == expected[name], name
            if url:
                identity = context.request.get(origin + "release.json?nova=" + commit).json()
                assert identity["commit"] == commit and identity["version"] == version
            page.goto(target)
            page.locator("#start-create").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#plan-title")).to_be_visible()
            page.locator("#project-name").fill("Public fixture · Montréal")
            page.locator("#project-description").fill("A public, reproducible numerical check.")
            page.locator(".job-goal").first.fill("Calculate and export the exact reference totals.")
            page.locator(".job-success").first.fill("The exported integer totals equal the supplied public fixture.")
            page.locator(".job-bounty").first.fill("10.000000000000000001")
            page.locator(".job-duration").first.fill("3600")
            page.locator(".job-weight").first.fill("6000")
            page.locator("#compile").click()
            expect(page.locator("#plan-next")).to_be_enabled()
            expect(page.locator("#plan-output")).to_contain_text("10000000000000000001")
            page.locator("#plan-next").click()
            page.locator("#evidence-text").fill(
                "Public acceptance fixture. Only synthetic inputs. Compare exact totals."
            )
            page.locator("#passphrase").fill(PHRASE)
            page.locator("#passphrase-confirm").fill(PHRASE)
            page.locator("#seal-package").click()
            expect(page.locator("#package-result")).to_be_visible(timeout=30000)
            page.locator("#recovery-disclosure").check()
            expect(page.locator("#export-kit")).to_be_enabled(timeout=30000)
            with page.expect_download() as download:
                page.locator("#export-kit").click()
            backup = output / "synthetic-recovery-kit.json"
            download.value.save_as(backup)
            raw = backup.read_text()
            kit = json.loads(raw)
            assert kit["schema"] == "agialpha.novaseed.recovery-kit.v1"
            assert PHRASE not in raw
            assert kit["content"]["package"]["plan"]["totalBounty"] == "10000000000000000001"
            assert page.evaluate("window.__novaRequests") == []
            assert PHRASE not in page.evaluate("JSON.stringify(localStorage)")
            archive_blocked = page.evaluate(
                """async()=>{const {MarkClient}=await import('../../assets/ascension-wallet/client.mjs');
                const p=await (await fetch('../../assets/ascension-wallet/profile.json',{cache:'no-store'})).json();
                const c=new MarkClient(p);try{c.allowed('seal',[]);return false;}
                catch(e){return p.newExposureEnabled===false&&e.message.includes('not commissioned');}}"""
            )
            assert archive_blocked
            page.screenshot(path=str(output / "studio-protected.png"), full_page=True)

            restored = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            restored.add_init_script(script=PROVIDER)
            recovery = restored.new_page()
            recovery.on("pageerror", lambda error: errors.append(str(error)))
            recovery.goto(target)
            recovery.locator("#start-resume").click()
            recovery.locator("#import-kit").set_input_files(backup)
            expect(recovery.locator("#reopen-package")).to_be_enabled(timeout=30000)
            recovery.locator("#reopen-passphrase").fill("deliberately incorrect capsule phrase")
            recovery.locator("#reopen-package").click()
            expect(recovery.locator("#status")).to_contain_text("Could not open", timeout=30000)
            recovery.locator("#reopen-passphrase").fill(PHRASE)
            recovery.locator("#reopen-package").click()
            expect(recovery.locator("#export-kit-again")).to_be_enabled(timeout=30000)
            recovery.locator("#recovery-disclosure-again").check()
            with recovery.expect_download() as download:
                recovery.locator("#export-kit-again").click()
            restored_path = output / "synthetic-restored-kit.json"
            download.value.save_as(restored_path)
            assert json.loads(restored_path.read_text())["content"]["package"] == kit["content"]["package"]
            assert recovery.evaluate("window.__novaRequests") == []
            assert PHRASE not in recovery.evaluate("JSON.stringify(localStorage)")
            tampered = json.loads(raw)
            tampered["content"]["package"]["plan"]["jobs"][0]["spec"]["goal"] = "Altered project"
            altered = output / "tampered-recovery-kit.json"
            altered.write_text(json.dumps(tampered))
            recovery.locator("#import-kit").set_input_files(altered)
            expect(recovery.locator("#status")).to_contain_text("checksum", timeout=30000)

            axe = (ROOT / "tests/browser/node_modules/axe-core/axe.min.js").read_text()
            for language in ("en", "fr"):
                if language == "fr":
                    recovery.locator("#language").click()
                expect(recovery.locator("html")).to_have_attribute("lang", language)
                for width in (1440, 390, 320):
                    recovery.set_viewport_size({"width": width, "height": 1000})
                    assert recovery.evaluate("document.documentElement.scrollWidth <= innerWidth+1"), (language, width)
                    for step in range(7):
                        recovery.locator(f'[data-step="{step}"]').click()
                        inspect(recovery, axe + ";void 0")
                        result = inspect(
                            recovery,
                            "axe.run(document,{runOnly:{type:'tag',"
                            "values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})",
                        )
                        assert not result["violations"], (language, width, step, result["violations"])
                    recovery.screenshot(path=str(output / f"studio-{language}-{width}.png"), full_page=True)
            recovery.locator("#large-text").click()
            assert recovery.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
            mirror = restored.new_page()
            mirror.on("pageerror", lambda error: errors.append(str(error)))
            mirror.goto(origin + "alpha_factory_v1/demos/ascension/mainnet/")
            mirror.locator("#start-explore").click()
            expect(mirror.locator("#project-name")).to_be_visible()
            assert mirror.evaluate("window.__novaRequests") == []
            assert not errors, errors
            browser.close()
    finally:
        if server:
            server.shutdown()
    report = {
        "schema": "agialpha.nova-studio.acceptance.v1",
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
