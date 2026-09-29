# SPDX-License-Identifier: Apache-2.0
"""Exercise actual paper runs, uploads, downloads, retry and offline reports in Chromium."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from threading import Thread

from alpha_factory_v1.demos.finance_alpha.delivery import export, verify
from alpha_factory_v1.demos.finance_alpha.paper import run, synthetic
from alpha_factory_v1.demos.finance_alpha.server import create_server
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401


def validate(output: Path) -> dict[str, object]:
    """Block nonlocal requests and inspect reports produced by the running app."""
    from playwright.sync_api import expect, sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    server = create_server(0)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_port}"
    failures: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
            context.route(
                "**/*",
                lambda route: (
                    route.continue_()
                    if route.request.url.startswith((origin + "/", output.resolve().as_uri() + "/"))
                    else route.abort()
                ),
            )
            page = context.new_page()
            page.on("pageerror", lambda error: failures.append(str(error)))
            page.goto(origin, wait_until="networkidle")
            button = page.get_by_role("button", name="Run paper experiment")
            button.click()
            expect(page.locator("#status")).to_contain_text("Complete.")
            expect(page.locator("#comparison tr")).to_have_count(10)
            assert page.locator("#equity-chart polyline").count() == 2
            page.evaluate("window.scrollTo(0, 0)")
            page.screenshot(path=str(output / "desktop.png"), full_page=True)
            page.locator("#case").select_option("crash")
            expect(page.locator("#result")).to_be_hidden()
            button.click()
            expect(page.locator("#risk-state")).to_contain_text("HALT")
            with page.expect_download() as download:
                page.get_by_role("button", name="Download full JSON").click()
            downloaded = output / "browser-report.json"
            download.value.save_as(downloaded)
            report = json.loads(downloaded.read_text())
            assert verify(report)["verified"]
            assert report["result"]["summary"]["net_return"] < 0
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            page.screenshot(path=str(output / "mobile.png"), full_page=True)
            page.get_by_text("Risk limits & CSV import", exact=True).click()
            page.locator("#csv-file").set_input_files(
                {"name": "invalid.csv", "mimeType": "text/csv", "buffer": b"bad,input\n1,2\n"}
            )
            button.click()
            expect(page.locator("#error")).to_contain_text("CSV header")
            expect(page.locator("#result")).to_be_hidden()
            page.locator("#csv-file").set_input_files(
                {"name": "prices.csv", "mimeType": "text/csv", "buffer": synthetic("reversal").encode()}
            )
            button.click()
            expect(page.locator("#data-label")).to_contain_text("USER DATA")
            page.get_by_role("button", name="Clear imported file").click()
            page.locator("#strategy").select_option("cash")
            button.click()
            expect(page.locator("#net-return")).to_have_text("0.00%")
            # Changing settings while a request is pending must not display its stale result.
            pending = []
            page.route("**/api/run", lambda route: pending.append(route))
            with page.expect_request(origin + "/api/run"):
                button.click()
            page.locator("#strategy").select_option("momentum")
            with page.expect_response(origin + "/api/run"):
                pending[0].continue_()
            expect(button).to_be_enabled()
            expect(page.locator("#result")).to_be_hidden()
            expect(page.locator("#status")).to_contain_text("Settings changed")
            page.unroute("**/api/run")
            # A standalone export must remain useful without a server or network.
            target = output / "offline-report"
            export(run(case="crash"), target)
            page.goto((target / "report.html").resolve().as_uri())
            expect(page.locator("#risk-state")).to_contain_text("HALT")
            expect(page.locator("#start-locally")).to_be_visible()
            assert page.locator("#equity-chart polyline").count() == 2
            # Check the committed gallery itself, including downloaded engine fingerprints.
            gallery = output / "gallery.html"
            source = Path(__file__).resolve().parents[1] / "docs/finance_alpha/index.html"
            gallery.write_bytes(source.read_bytes())
            page.goto(gallery.resolve().as_uri())
            expect(page.locator("#mode-note")).to_contain_text("RECORDED PAPER EVIDENCE")
            for case in ("trend", "reversal", "crash"):
                page.locator("#case").select_option(case)
                page.get_by_role("button", name="Inspect scenario").click()
                with page.expect_download() as download:
                    page.get_by_role("button", name="Download full JSON").click()
                artifact = output / f"gallery-{case}.json"
                download.value.save_as(artifact)
                recorded = json.loads(artifact.read_text())
                assert recorded["data"]["case"] == case
                assert verify(recorded)["verified"]
            assert not failures, failures
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    result = {
        "actual_local_runs": True,
        "cash_and_loss_scenarios": True,
        "download_exact_replay": True,
        "csv_import": True,
        "failure_clears_stale_result": True,
        "retry": True,
        "pending_result_invalidated": True,
        "recorded_gallery_exact_replay": True,
        "mobile_no_overflow": True,
        "offline_export": True,
        "external_requests_blocked": True,
        "browser_errors": failures,
    }
    (output / "browser.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.output), indent=2))
