# SPDX-License-Identifier: Apache-2.0
"""Exercise governance decisions, exports, import boundaries and accessible recovery."""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Thread
from typing import Any
import zipfile

from playwright.sync_api import expect, sync_playwright

from alpha_factory_v1.demos.solving_agi_governance.workbench import artifacts, canonical, digest, read_json, verify
from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_gallery_catalog import Handler
from scripts.governance_evidence import ASSETS, CHECKS, SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def validate(site: Path, output: Path, public_url: str | None = None, axe_script: Path | None = None) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public acceptance requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    cases = read_json(ROOT / "alpha_factory_v1/demos/solving_agi_governance/scenarios.json")
    errors: list[str] = []
    failures: list[str] = []
    records: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            context.route(
                "https://**", lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort()
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: failures.append(response.url) if response.status >= 400 else None)
            for relative in ASSETS:
                response = context.request.get(origin + relative, headers={"Cache-Control": "no-cache"})
                assert response.ok, relative
                value = hashlib.sha256(response.body()).hexdigest()
                assert value == hashlib.sha256((site / relative).read_bytes()).hexdigest(), relative
                hashes[relative] = value
            page.goto(origin + "solving_agi_governance/")
            expect(page.locator("#gov-run")).to_be_enabled()
            page.screenshot(path=str(output / "governance-desktop.png"), full_page=True)
            for case in cases:
                page.locator("#gov-case").select_option(case["id"])
                page.locator("#gov-run").click()
                expect(page.locator("#gov-download")).to_be_enabled()
                with page.expect_download() as download:
                    page.locator("#gov-dossier").click()
                dossier = output / f"{case['id']}.json"
                download.value.save_as(dossier)
                report = verify(read_json(dossier))
                assert report["input"]["id"] == case["id"]
                assert page.locator(".gov-gate.blocked").count() == sum(
                    not g["passed"] for g in report["result"]["gates"]
                )
                with page.expect_download() as archive:
                    page.locator("#gov-download").click()
                archive_path = output / f"{case['id']}.zip"
                archive.value.save_as(archive_path)
                with zipfile.ZipFile(archive_path) as bundle:
                    assert {name: bundle.read(name) for name in bundle.namelist()} == artifacts(report)
                assert verify_plan(compile_plan(report["result"]["jobs"]))["valid"]
                assert all(report["result"]["inputSha256"] in job["goal"] for job in report["result"]["jobs"])
                records.append({"id": case["id"], "sha256": report["sha256"], "status": report["result"]["status"]})
            page.locator("#gov-import").set_input_files(output / "accountable-upgrade.json")
            expect(page.locator("#gov-status")).to_contain_text("independently recomputed")
            page.locator("#gov-discountBps").fill("20")
            expect(page.locator("#gov-results")).to_be_hidden()
            expect(page.locator("#gov-download")).to_be_disabled()
            page.locator(".gov-advanced > summary").click()
            page.locator("#gov-json").fill(canonical(cases[3]).decode())
            page.locator("#gov-run").click()
            expect(page.locator("#gov-status")).to_contain_text("Apply the edited JSON")
            page.locator("#gov-apply").click()
            page.locator("#gov-run").click()
            expect(page.locator("#gov-verdict")).to_have_text("BLOCKED")
            page.locator(".gov-advanced > summary").click()
            forged = read_json(output / "accountable-upgrade.json")
            forged["result"]["status"] = "APPROVED"
            forged["sha256"] = digest({k: v for k, v in forged.items() if k != "sha256"})
            for name, data, message in (
                ("forged", canonical(forged), "differs from recomputation"),
                ("duplicate", b'{"schema":1,"schema":2}', "Duplicate JSON key"),
                ("large", b" " * 256001, "exceeds"),
                ("utf8", b"\xff", "Import rejected"),
            ):
                page.locator("#gov-import").set_input_files(
                    {"name": f"{name}.json", "mimeType": "application/json", "buffer": data}
                )
                expect(page.locator("#gov-status")).to_contain_text(message)
                expect(page.locator("#gov-download")).to_be_disabled()
            page.locator("#gov-case").select_option("accountable-upgrade")
            page.locator("#gov-perActionFemto").fill("1e-16")
            # Programmatic submit bypasses native step validation to exercise the exact parser as well.
            page.locator("#gov-form").evaluate("form => form.dispatchEvent(new Event('submit', {cancelable:true}))")
            expect(page.locator("#gov-status")).to_contain_text("cannot be represented exactly")
            page.locator("#gov-case").select_option("weak-deterrence")
            page.evaluate("localStorage.setItem('unrelated-workspace','retain')")
            page.locator("#gov-save").click()
            page.locator("#gov-discountBps").fill("99")
            page.locator("#gov-restore").click()
            expect(page.locator("#gov-discountBps")).to_have_value("20")
            page.locator("#gov-clear").click()
            assert page.evaluate("localStorage.getItem('unrelated-workspace')") == "retain"
            expect(page.locator("#gov-restore")).to_be_disabled()
            hostile = deepcopy(cases[0])
            hostile["note"] = '<img src="invalid" onerror="window.governanceAttack=1">'
            page.locator("#gov-import").set_input_files(
                {"name": "text.json", "mimeType": "application/json", "buffer": canonical(hostile)}
            )
            expect(page.locator("#gov-case-note")).to_have_text(hostile["note"])
            assert page.evaluate("window.governanceAttack === undefined")
            page.goto(origin + "alpha_factory_v1/demos/solving_agi_governance/")
            expect(page.locator("#gov-run")).to_be_enabled()
            page.locator("#gov-run").click()
            expect(page.locator("#gov-download")).to_be_enabled()
            page.locator(".gov-original > summary").click()
            page.get_by_role("button", name="Replay bundled sample offline").click()
            original = read_json(ROOT / "docs/solving_agi_governance/assets/logs.json")
            replay = page.evaluate("() => Chart.getChart(document.getElementById('chart')).data.datasets[0].data")
            assert replay == original["values"]
            assert page.locator("#logs-panel").inner_text().splitlines() == original["logs"]
            expect(page.get_by_role("link", name="Open editable workspace ↗")).to_be_visible()
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                page.screenshot(path=str(output / f"governance-{width}.png"), full_page=True)
                page.locator("#gov-research").screenshot(path=str(output / f"research-{width}.png"))
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    violations = page.evaluate(
                        "async () => (await axe.run(document, {runOnly:['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
                    assert not violations, violations
            page.locator("#gov-discountBps").focus()
            page.keyboard.press("Tab")
            assert page.locator("#gov-detectionBps").evaluate("element => element === document.activeElement")
            page.goto(origin + "solving_agi_governance/")
            expect(page.locator("#gov-run")).to_be_enabled()
            page.evaluate("() => navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            expect(page.locator("#gov-run")).to_be_enabled()
            page.locator("#gov-case").select_option("scale-risk")
            page.locator("#gov-run").click()
            expect(page.locator("#gov-verdict")).to_have_text("BLOCKED")
            assert not errors and not failures, {"browser_errors": errors, "http_failures": failures}
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {
        "schema": SCHEMA,
        "passed": True,
        "origin": origin,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "version": json.loads((ROOT / "alpha_factory_v1/demos/catalog.json").read_text())["release"],
        "cases": records,
        "checks": sorted(CHECKS - (set() if axe_script else {"axe-wcag-a-aa-no-violations"})),
        "assets": hashes,
        "browser_errors": errors,
        "http_failures": failures,
    }
    (output / "governance.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/governance-browser"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    validate(args.site, args.output, args.url, args.axe_script)
    print("Verified governance decisions, exact exports, hostile imports, accessible recovery and preserved replay")
