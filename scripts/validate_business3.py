# SPDX-License-Identifier: Apache-2.0
"""Exercise Business 3 decisions, exports, boundaries, accessibility and recovery."""
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

from alpha_factory_v1.demos.alpha_agi_business_3_v1.enterprise import artifacts, canonical, digest, read_json, verify
from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_gallery_catalog import Handler
from scripts.business3_evidence import ASSETS, CHECKS

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
    cases = read_json(ROOT / "alpha_factory_v1/demos/alpha_agi_business_3_v1/scenarios.json")
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
                digest_value = hashlib.sha256(response.body()).hexdigest()
                assert digest_value == hashlib.sha256((site / relative).read_bytes()).hexdigest(), relative
                hashes[relative] = digest_value
            page.goto(origin + "alpha_agi_business_3_v1/")
            page.wait_for_function("document.documentElement.dataset.business3Ready === 'true'")
            page.screenshot(path=str(output / "enterprise-desktop.png"), full_page=True)
            for case in cases:
                page.locator("#b3-case").select_option(case["id"])
                page.locator("#b3-run").click()
                expect(page.locator("#b3-download")).to_be_enabled(timeout=30000)
                with page.expect_download() as download:
                    page.locator("#b3-download-json").click()
                dossier = output / f"{case['id']}.json"
                download.value.save_as(dossier)
                report = verify(read_json(dossier, 2_000_000))
                assert report["input"]["id"] == case["id"]
                plotted = page.locator("#b3-opportunity-chart > li").evaluate_all(
                    "rows => rows.map(row => ({id: row.dataset.projectId, selected: row.dataset.selected === 'true', "
                    "expected: Number(row.querySelector('.b3-value-bar.b3-expected').dataset.value), "
                    "downside: Number(row.querySelector('.b3-value-bar.b3-downside').dataset.value)}))"
                )
                selected = set((report["result"]["portfolio"] or {}).get("projectIds", []))
                expected = [
                    {
                        "id": row["id"],
                        "selected": row["id"] in selected,
                        "expected": row["expectedNpvUsd"],
                        "downside": row["downsideNpvUsd"],
                    }
                    for row in sorted(report["result"]["analysis"], key=lambda row: (-row["expectedNpvUsd"], row["id"]))
                ]
                assert plotted == expected, case["id"]
                assert page.locator("#b3-opportunity-chart").inner_text().count("Expected:") == len(expected)
                with page.expect_download() as archive:
                    page.locator("#b3-download").click()
                archive_path = output / f"{case['id']}.zip"
                archive.value.save_as(archive_path)
                with zipfile.ZipFile(archive_path) as bundle:
                    assert {name: bundle.read(name) for name in bundle.namelist()} == artifacts(report)
                if report["result"]["jobs"]:
                    assert verify_plan(compile_plan(report["result"]["jobs"]))["valid"]
                records.append({"id": case["id"], "sha256": report["sha256"], "status": report["result"]["status"]})
            page.locator("#b3-import").set_input_files(output / "industrial.json")
            expect(page.locator("#b3-status")).to_contain_text("Dossier verified", timeout=30000)
            page.locator("#b3-policy-budgetUsd").fill("0")
            expect(page.locator("#b3-results")).to_be_hidden()
            expect(page.locator("#b3-download")).to_be_disabled()
            page.locator("#b3-run").click()
            expect(page.locator("#b3-verdict")).to_have_text("HOLD NO POSITIVE VALUE", timeout=30000)
            expect(page.locator("#b3-download-jobs")).to_be_disabled()
            assert page.locator('#b3-opportunity-chart [data-selected="true"]').count() == 0
            forged = read_json(output / "industrial.json", 2_000_000)
            forged["result"]["approval"] = "APPROVED"
            forged["sha256"] = digest({k: v for k, v in forged.items() if k != "sha256"})
            forged_path = output / "forged.json"
            forged_path.write_bytes(canonical(forged))
            page.locator("#b3-import").set_input_files(forged_path)
            expect(page.locator("#b3-status")).to_contain_text("differs from recomputed", timeout=30000)
            expect(page.locator("#b3-results")).to_be_hidden()
            page.locator("#b3-import").set_input_files(
                {"name": "duplicate.json", "mimeType": "application/json", "buffer": b'{"schema":1,"schema":2}'}
            )
            expect(page.locator("#b3-status")).to_contain_text("Duplicate JSON key")
            page.locator("#b3-import").set_input_files(
                {"name": "large.json", "mimeType": "application/json", "buffer": b" " * 2_000_001}
            )
            expect(page.locator("#b3-status")).to_contain_text("exceeds")
            page.locator("#b3-case").select_option("lean-budget")
            page.evaluate("localStorage.setItem('unrelated-workspace','retain')")
            page.locator("#b3-save").click()
            page.locator("#b3-policy-budgetUsd").fill("1")
            page.locator("#b3-restore").click()
            expect(page.locator("#b3-policy-budgetUsd")).to_have_value("600000")
            page.locator("#b3-clear").click()
            assert page.evaluate("localStorage.getItem('unrelated-workspace')") == "retain"
            expect(page.locator("#b3-restore")).to_be_disabled()
            # Click both real controls in one event turn, before a worker can return.
            page.evaluate(
                "() => { document.getElementById('b3-run').click(); document.getElementById('b3-cancel').click(); }"
            )
            expect(page.locator("#b3-status")).to_contain_text("cancelled")
            page.locator("#b3-run").click()
            expect(page.locator("#b3-download")).to_be_enabled(timeout=30000)
            hostile = deepcopy(cases[0])
            hostile["projects"][0]["name"] = '<img src="invalid" onerror="window.business3Attack=1">'
            page.locator("#b3-import").set_input_files(
                {"name": "text.json", "mimeType": "application/json", "buffer": canonical(hostile)}
            )
            expect(page.locator("#b3-download")).to_be_enabled(timeout=30000)
            expect(page.locator("#b3-projects")).to_contain_text(hostile["projects"][0]["name"])
            assert page.evaluate("window.business3Attack === undefined")
            page.goto(origin + "alpha_factory_v1/demos/alpha_agi_business_3_v1/")
            page.wait_for_function("document.documentElement.dataset.business3Ready === 'true'")
            page.locator("#b3-run").click()
            expect(page.locator("#b3-download")).to_be_enabled(timeout=30000)
            page.get_by_role("button", name="Replay bundled sample offline").click()
            original = read_json(ROOT / "docs/alpha_agi_business_3_v1/assets/logs.json")
            replay = page.evaluate(
                "() => { const c = Chart.getChart(document.getElementById('chart')); "
                "return {steps: c.data.labels, values: c.data.datasets[0].data, "
                "label: c.data.datasets[0].label, axis: c.options.scales.y.title.text}; }"
            )
            assert replay["steps"] == original["steps"] and replay["values"] == original["values"]
            assert "unitless" in replay["label"] and "unitless" in replay["axis"]
            page.locator(".b3-replay-record > summary").click()
            assert page.locator("#logs-panel").inner_text().splitlines() == original["logs"]
            page.get_by_text("View chart data as a table", exact=True).click()
            assert page.locator(".b3-replay-record table tbody tr").count() == len(original["values"])
            page.locator(".b3-replay-record > summary").click()
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                assert page.locator("#b3-legacy img.preview").bounding_box()["width"] <= 144
                assert page.locator("#chart").bounding_box()["height"] >= 200
                page.screenshot(path=str(output / f"enterprise-{width}.png"), full_page=True)
                page.locator("#b3-legacy").screenshot(path=str(output / f"research-{width}.png"))
                page.locator(".b3-opportunity").screenshot(path=str(output / f"opportunity-{width}.png"))
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    violations = page.evaluate(
                        "async () => (await axe.run(document, {runOnly:['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
                    assert not violations, violations
            page.locator("#b3-policy-budgetUsd").focus()
            page.keyboard.press("Tab")
            assert page.locator("#b3-policy-staffDays").evaluate("element => element === document.activeElement")
            page.goto(origin + "alpha_agi_business_3_v1/")
            page.wait_for_function("document.documentElement.dataset.business3Ready === 'true'")
            page.evaluate("() => navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            page.wait_for_function("document.documentElement.dataset.business3Ready === 'true'")
            page.locator("#b3-run").click()
            expect(page.locator("#b3-download")).to_be_enabled(timeout=30000)
            assert not errors and not failures, {"browser_errors": errors, "http_failures": failures}
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {
        "schema": "agialpha.business3.acceptance.v1",
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
    (output / "business3.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/business3-browser"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    validate(args.site, args.output, args.url, args.axe_script)
    print("Verified Business 3 cases, exact portable evidence, admission boundaries, browser recovery and preservation")
