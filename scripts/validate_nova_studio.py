# SPDX-License-Identifier: Apache-2.0
"""Exercise the shipped Studio without granting a wallet or contacting Mainnet."""
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

from scripts.mark_wallet_evidence import ROOT, hashes
from scripts.nova_studio_evidence import BROWSER_CHECKS, verify_browser
from scripts.validate_ascension import Handler, inspect
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def validate(site: Path, output: Path, url: str | None = None) -> dict[str, Any]:
    """Require actual UI recovery, no signing, exact assets and accessible layouts."""
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
    errors: list[str] = []
    requests: list[str] = []
    audits: list[dict[str, Any]] = []
    # This provider records attempts and refuses every request. It supplies no RPC data.
    sentinel = (
        "window.__novaReadinessRequests=[];window.ethereum={request:async function(p){"
        "window.__novaReadinessRequests.push(p.method);throw Error('No wallet permission in this trial');}};"
    )
    phrase = "public Studio recovery fixture 2026"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True)
            context.add_init_script(script=sentinel)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            for name, digest in expected.items():
                response = context.request.get(origin + name)
                assert response.ok and hashlib.sha256(response.body()).hexdigest() == digest, name
            if url:
                identity = context.request.get(origin + "release.json?nova=" + commit).json()
                assert identity["commit"] == commit and identity["version"] == version
            target = origin + "ascension/mainnet/"
            page.goto(target)
            expect(page.locator("#status")).to_contain_text("Start locally")
            page.locator("#example").click()
            page.locator("#compile").click()
            expect(page.locator("#compile-summary")).to_contain_text("1 jobs")
            page.locator('[data-step="protect"]').click()
            page.locator("#passphrase").fill(phrase)
            page.locator("#passphrase-again").fill(phrase)
            page.locator("#seal-package").click()
            expect(page.locator("#recovery-result")).to_contain_text("successfully", timeout=30000)
            expect(page.locator("#passphrase")).to_have_value("")
            with page.expect_download() as download:
                page.locator("#export-kit").click()
            kit_path = output / "preparation-recovery-kit.json"
            download.value.save_as(kit_path)
            kit_text = kit_path.read_text()
            assert phrase not in kit_text
            original = json.loads(kit_text)
            assert original["body"]["package"]["plan"]["jobs"]
            assert inspect(page, "window.__novaReadinessRequests") == []
            assert phrase not in inspect(page, "JSON.stringify({...localStorage})")
            page.screenshot(path=str(output / "studio-prepared.png"), full_page=True)
            context.close()
            # New context has no project, journal, permissions or local storage.
            context = browser.new_context(viewport={"width": 1440, "height": 1080}, accept_downloads=True)
            context.add_init_script(script=sentinel)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("request", lambda request: requests.append(request.url))
            page.goto(target)
            expect(page.locator("#status")).to_contain_text("Start locally")
            page.locator('[data-step="resume"]').click()
            page.locator("#kit-file").set_input_files(kit_path)
            page.locator("#restore-passphrase").fill("incorrect public fixture phrase")
            page.locator("#restore-kit").click()
            expect(page.locator("#status")).to_have_class("error", timeout=30000)
            changed = json.loads(kit_text)
            changed["body"]["seedId"] = "999"
            page.locator("#kit-file").set_input_files(
                {"name": "tampered.json", "mimeType": "application/json", "buffer": json.dumps(changed).encode()}
            )
            page.locator("#restore-passphrase").fill(phrase)
            page.locator("#restore-kit").click()
            expect(page.locator("#status")).to_contain_text("checksum", timeout=30000)
            page.locator("#kit-file").set_input_files(kit_path)
            page.locator("#restore-passphrase").fill(phrase)
            page.locator("#restore-kit").click()
            expect(page.locator("#status")).to_contain_text("recovered locally", timeout=30000)
            assert inspect(page, "window.__novaReadinessRequests") == []
            assert phrase not in inspect(page, "JSON.stringify({...localStorage})")
            page.locator('[data-step="protect"]').click()
            with page.expect_download() as download:
                page.locator("#export-kit").click()
            recovered_path = output / "restored-recovery-kit.json"
            download.value.save_as(recovered_path)
            assert json.loads(recovered_path.read_text())["body"]["package"] == original["body"]["package"]
            axe = (ROOT / "tests/browser/node_modules/axe-core/axe.min.js").read_text()
            for language in ("en", "fr"):
                if language == "fr":
                    page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute("lang", language)
                for width in (1440, 390, 320):
                    page.set_viewport_size({"width": width, "height": 1080})
                    for step in ("project", "protect", "publish", "mint", "review", "fund", "launch", "resume"):
                        page.locator(f'[data-step="{step}"]').click()
                        assert inspect(page, "document.documentElement.scrollWidth <= innerWidth+1"), (
                            language,
                            width,
                            step,
                        )
                        inspect(page, axe + ";void 0")
                        audit = inspect(
                            page,
                            "axe.run(document,{runOnly:{type:'tag',"
                            "values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})",
                        )
                        assert audit["violations"] == [], audit["violations"]
                        audits.append({"language": language, "width": width, "step": step, "violations": []})
                    if width == 390:
                        page.screenshot(path=str(output / f"studio-recovered-{language}.png"), full_page=True)
            page.locator('[data-step="project"]').focus()
            page.keyboard.press("Enter")
            expect(page.locator("#step-project")).to_be_visible()
            assert inspect(page, "window.__novaReadinessRequests") == []
            assert all(request.startswith(origin) or request.startswith("data:") for request in requests), requests
            assert errors == [], errors
            browser.close()
    finally:
        if server:
            server.shutdown()
    report = {
        "schema": "agialpha.nova-studio.browser.v1",
        "passed": True,
        "commit": commit,
        "version": version,
        "origin": origin,
        "assets": expected,
        "checks": BROWSER_CHECKS,
        "audits": audits,
        "pageErrors": errors,
        "walletRequests": 0,
        "mainnetTransactions": 0,
        "physicalWalletValidated": False,
    }
    verify_browser(report, commit, version, origin)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=ROOT / "docs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url")
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url), indent=2))
