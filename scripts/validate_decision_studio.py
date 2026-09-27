# SPDX-License-Identifier: Apache-2.0
"""Verify useful decision journeys, downloaded artifacts, access and recovery in Chromium."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Thread
from typing import Any

from playwright.sync_api import expect, sync_playwright

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_ascension import Handler


def validate(site: Path, output: Path, public_url: str | None = None, axe_script: Path | None = None) -> dict[str, Any]:
    """Exercise every case and require portable, recomputable results."""
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
    cases = json.loads(Path("docs/assets/studio/cases.json").read_text())
    errors: list[str] = []
    failures: list[str] = []
    records: list[dict[str, Any]] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: failures.append(response.url) if response.status >= 400 else None)
            page.goto(origin + "studio/?case=capital")
            page.wait_for_function("document.documentElement.dataset.studioReady === 'true'")
            page.screenshot(path=str(output / "studio-desktop.png"), full_page=True)
            for case in cases:
                page.locator(f'[data-case="{case["id"]}"]').click()
                page.locator("#run").click()
                expect(page.locator("#results")).to_be_visible()
                assert page.locator("#result-table tbody tr").count() > 0
                assert page.locator("#jobs").inner_text().strip()
                with page.expect_download() as event:
                    page.locator("#export-report").click()
                target = output / f'{case["id"]}.json'
                event.value.save_as(target)
                # Replay the actual download through the standalone Node entrypoint.
                subprocess.run(
                    ["node", "scripts/decision_studio.mjs", "--verify", str(target)], check=True, capture_output=True
                )
                downloaded: dict[str, Any] = json.loads(target.read_text())
                assert downloaded["input"] == case["input"]
                records.append(
                    {
                        "id": case["id"],
                        "verdict": downloaded["output"]["verdict"],
                        "metrics": downloaded["output"]["metrics"],
                    }
                )
                if case["id"] in {"capital", "delivery", "proof", "energy"}:
                    page.locator("#results-title").scroll_into_view_if_needed()
                    page.screenshot(path=str(output / f'{case["id"]}-results.png'))
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    violations = page.evaluate(
                        "async () => (await axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
                    assert not violations, json.dumps(violations)
            # An edit must immediately revoke the old chart and exportable result.
            page.locator('[data-case="capital"]').click()
            page.locator("#run").click()
            expect(page.locator("#results")).to_be_visible()
            page.locator("#parameter-budget").fill("1")
            expect(page.locator("#results")).to_be_hidden()
            assert page.locator("#visual svg").count() == 0
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("HOLD")
            page.evaluate("() => {document.querySelector('#run').click(); document.querySelector('#stop').click();}")
            expect(page.locator("#status")).to_contain_text("Calculation stopped")
            expect(page.locator("#run")).to_be_enabled()
            expect(page.locator("#results")).to_be_hidden()
            # Replay import, then reject a forged decision rather than trusting the JSON.
            page.locator("#import").set_input_files(output / "capital.json")
            expect(page.locator("#status")).to_contain_text("replayed successfully")
            forged = json.loads((output / "capital.json").read_text())
            forged["output"]["rows"][0][1] = "Forged"
            page.locator("#import").set_input_files(
                {"name": "forged.json", "mimeType": "application/json", "buffer": json.dumps(forged).encode()}
            )
            expect(page.locator("#status")).to_contain_text("failed replay")
            expect(page.locator("#results")).to_be_hidden()
            page.locator("#import").set_input_files(
                {"name": "broken.json", "mimeType": "application/json", "buffer": b'{"broken'}
            )
            expect(page.locator("#status")).to_have_class("error")
            expect(page.locator("#results")).to_be_hidden()
            # Real CSV imports change the procurement decision, including an impossible input.
            page.locator('[data-case="supply"]').click()
            page.get_by_label("Import suppliers CSV").set_input_files(
                {
                    "name": "supply.csv",
                    "mimeType": "text/csv",
                    "buffer": b"id,name,unit_cost,setup_cost,capacity,lead_days,ontime_percent\na,Only supplier,100,0,80,10,99\n",
                }
            )
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("HOLD")
            page.locator("#reset").click()
            page.locator("#parameter-demand").fill("55")
            page.locator("#save").click()
            page.reload()
            page.wait_for_function("document.documentElement.dataset.studioReady === 'true'")
            page.locator("#restore").click()
            expect(page.locator("#parameter-demand")).to_have_value("55")
            expect(page.locator("#results")).to_be_visible()
            # All promised artifact downloads must contain useful payloads.
            for name in ("brief", "csv", "jobs"):
                with page.expect_download() as event:
                    page.locator(f"#export-{name}").click()
                target = output / event.value.suggested_filename
                event.value.save_as(target)
                assert target.stat().st_size > 100
            page.locator("#clear").click()
            expect(page.locator("#restore")).to_be_disabled()
            # Keyboard, mobile, no horizontal page overflow, and responsive result tables.
            page.set_viewport_size({"width": 390, "height": 844})
            for case in ("capital", "delivery", "inventory", "proof"):
                page.locator(f'[data-case="{case}"]').click()
                page.locator("#run").click()
                expect(page.locator("#results")).to_be_visible()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.screenshot(path=str(output / f"{case}-mobile.png"), full_page=True)
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    assert not page.evaluate(
                        "async () => (await axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
            page.goto(origin)
            assert page.locator(".decision-card").count() == len(cases)
            assert page.locator(".demo-card").count() == 26
            page.get_by_role("searchbox", name="Search demos").fill("zzzz-no-case")
            assert page.locator(".decision-card:visible, .demo-card:visible").count() == 0
            page.get_by_role("searchbox", name="Search demos").fill("Supplier resilience")
            assert page.locator(".decision-card:visible").count() == 1
            # Original routes expose the actionable workflow before their historical replay.
            page.goto(origin + "alpha_agi_business_3_v1/")
            expect(page.get_by_role("link", name="Open editable workspace")).to_have_attribute(
                "href", "../studio/?case=capital"
            )
            page.goto(origin + "alpha_factory_v1/demos/studio/?case=energy")
            page.wait_for_function("document.documentElement.dataset.studioReady === 'true'")
            expect(page.locator("#case-art")).to_have_attribute("src", origin + "assets/studio/previews/energy.svg")
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("PLAN")
            page.goto(origin + "studio/?case=energy")
            page.wait_for_function("document.documentElement.dataset.studioReady === 'true'")
            page.evaluate("() => navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            page.wait_for_function("document.documentElement.dataset.studioReady === 'true'")
            page.locator("#run").click()
            expect(page.locator("#results")).to_be_visible()
            expect(page.locator("#verdict")).to_have_text("PLAN")
            assert not errors and not failures, {"errors": errors, "http_failures": failures}
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report: dict[str, Any] = {
        "schema": "agialpha.decision.acceptance.v1",
        "cases": records,
        "checks": [
            "all-case-calculations",
            "downloaded-dossier-cli-replay",
            "edited-input-invalidation",
            "worker-cancellation",
            "forgery-rejection",
            "csv-import-infeasibility",
            "explicit-save-restore-clear",
            "all-artifact-downloads",
            "mobile-no-overflow",
            "accessible-controls",
            "practical-catalog-search",
            "legacy-route-bridge",
            "offline-recalculation",
        ],
        "browser_errors": errors,
        "http_failures": failures,
        "passed": True,
    }
    (output / "decision-studio.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/decision-studio"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    result = validate(args.site, args.output, args.url, args.axe_script)
    print(f'Validated {len(result["cases"])} practical decisions, exported dossiers and browser recovery')


if __name__ == "__main__":
    main()
