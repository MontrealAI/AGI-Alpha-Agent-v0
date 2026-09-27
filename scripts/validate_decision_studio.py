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
from scripts.validate_ascension import Handler, wait_for, inspect


def validate_cache_upgrade(site: Path) -> None:
    """Upgrade an actual v1.8.1 worker and its cached portal to the current site."""
    previous = "6ee044b678397e6fa8ed2bd9b299741a19be54fa"
    inherited = {
        path: subprocess.check_output(["git", "show", f"{previous}:docs/{path}"])
        for path in ("index.html", "service-worker.js", "assets/portal/portal.css", "assets/portal/portal.mjs")
    }
    state = {"old": True}

    class UpgradeHandler(Handler):
        def do_GET(self) -> None:
            relative = self.path.split("?", 1)[0].removeprefix("/project/") or "index.html"
            if state["old"] and relative in inherited:
                payload = inherited[relative]
                self.send_response(200)
                self.send_header(
                    "Content-Type",
                    (
                        "text/html"
                        if relative.endswith("html")
                        else "text/css"
                        if relative.endswith("css")
                        else "text/javascript"
                    ),
                )
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(payload)
            else:
                super().do_GET()

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(UpgradeHandler, directory=str(site.resolve())))
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(reduced_motion="reduce")
            context.route("https://**", lambda route: route.abort())
            page = context.new_page()
            origin = f"http://127.0.0.1:{server.server_port}/project/"
            page.goto(origin)
            wait_for(page, "navigator.serviceWorker.controller !== null")
            page.reload()
            assert page.locator(".decision-card").count() == 0
            state["old"] = False
            page.reload()
            wait_for(
                page,
                "document.querySelector('.decision-card') && "
                "getComputedStyle(document.querySelector('.decision-card')).display === 'flex'",
            )
            current_cache = (site / "service-worker.js").read_text().split('const CACHE = "')[1].split('"')[0]
            wait_for(
                page, f"caches.keys().then(names => names.length === 1 && names.includes({json.dumps(current_cache)}))"
            )
            page.reload()
            expect(page.locator("#result-count")).to_contain_text("37 of 37")
            page.get_by_role("searchbox", name="Search demos").fill("supplier")
            inspect(page, "navigator.serviceWorker.dispatchEvent(new Event('controllerchange'))")
            expect(page.get_by_role("status", name="Workspace update")).to_be_visible()
            expect(page.get_by_role("searchbox", name="Search demos")).to_have_value("supplier")
            page.get_by_role("button", name="Reload updated workspace").click()
            expect(page.locator("#result-count")).to_contain_text("37 of 37")
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


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
    if not public_url:
        validate_cache_upgrade(site)
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
            wait_for(page, "document.documentElement.dataset.studioReady === 'true'")
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
                assert downloaded["calculation_version"] == "1.10.0"
                records.append(
                    {
                        "id": case["id"],
                        "verdict": downloaded["output"]["verdict"],
                        "metrics": downloaded["output"]["metrics"],
                    }
                )
                if case["id"] in {"capital", "delivery", "proof", "energy", "service"}:
                    page.locator("#results-title").scroll_into_view_if_needed()
                    page.screenshot(path=str(output / f'{case["id"]}-results.png'))
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    violations = page.evaluate(
                        "async () => (await axe.run(document, {runOnly: ['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
                    assert not violations, json.dumps(violations)
            # Staffing is a distinct executable workflow, with visible caps and forward backlog.
            page.locator('[data-case="service"]').click()
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("PLAN")
            expect(page.locator("#supporting-tables")).to_contain_text("Forecast validation")
            page.get_by_label("coverage row 1 Additional staff cap", exact=True).fill("0")
            expect(page.locator("#results")).to_be_hidden()
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("HOLD")
            expect(page.locator("#jobs")).to_contain_text("Resolve uncovered service demand")
            # Paging an editable table preserves its expanded state and keyboard position.
            page.locator('[data-case="inventory"]').click()
            page.get_by_role("button", name="Next rows", exact=True).click()
            expect(page.get_by_label("demand row 13 ID", exact=True)).to_be_focused()
            page.get_by_role("button", name="Remove demand row 13", exact=True).click()
            expect(page.get_by_label("demand row 13 ID", exact=True)).to_be_focused()
            page.get_by_role("button", name="Add row", exact=True).click()
            expect(page.get_by_label("demand row 84 ID", exact=True)).to_be_focused()
            # Existing released reports replay with their archived policy and explicit version.
            legacy = Path("tests/fixtures/decision-studio/service-1.9.json").read_bytes()
            page.locator("#import").set_input_files(
                {"name": "legacy.json", "mimeType": "application/json", "buffer": legacy}
            )
            expect(page.locator("#status")).to_contain_text("replayed successfully")
            expect(page.locator("#method")).to_contain_text("1.9.0 (archived replay)")
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
                    "buffer": (
                        b"id,name,unit_cost,setup_cost,capacity,lead_days,ontime_percent\n"
                        b"a,Only supplier,100,0,80,10,99\n"
                    ),
                }
            )
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("HOLD")
            page.locator("#reset").click()
            page.locator("#parameter-demand").fill("55")
            page.locator("#save").click()
            page.reload()
            wait_for(page, "document.documentElement.dataset.studioReady === 'true'")
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
            for case in ("capital", "delivery", "inventory", "proof", "service"):
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
            wait_for(page, "document.documentElement.dataset.studioReady === 'true'")
            expect(page.locator("#case-art")).to_have_attribute("src", origin + "assets/studio/previews/energy.svg")
            page.locator("#run").click()
            expect(page.locator("#verdict")).to_have_text("PLAN")
            page.goto(origin + "studio/?case=energy")
            wait_for(page, "document.documentElement.dataset.studioReady === 'true'")
            page.evaluate("() => navigator.serviceWorker.ready")
            page.reload()
            wait_for(page, "navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            wait_for(page, "document.documentElement.dataset.studioReady === 'true'")
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
        "origin": origin,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "version": json.loads(Path("alpha_factory_v1/demos/catalog.json").read_text())["release"],
        "calculation_version": "1.10.0",
        "cases": records,
        "checks": [
            "all-case-calculations",
            "staffing-cap-and-backlog-hold",
            "editable-table-keyboard-focus",
            "archived-dossier-replay",
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
            "v1.8.1-cache-upgrade" if not public_url else "public-current-assets",
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
