# SPDX-License-Identifier: Apache-2.0
"""Execute the manuscript transfer journey and replay its actual browser downloads."""

from __future__ import annotations

import argparse
from copy import deepcopy
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

from alpha_factory_v1.core.runtime import transfer
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_ascension import Handler, inspect, wait_for


def ready(page: Page) -> None:
    wait_for(
        page,
        "document.documentElement.dataset.compoundingReady === 'true' && "
        "document.querySelector('#laboratory').getAttribute('aria-busy') === 'false'",
    )


def click(page: Page, selector: str) -> None:
    page.locator(selector).click()
    ready(page)


def download(page: Page, selector: str, path: Path) -> None:
    with page.expect_download() as event:
        click(page, selector)
    event.value.save_as(path)


def upload(page: Page, value: dict[str, Any]) -> None:
    page.locator("#import-run").set_input_files(
        {"name": "run.json", "mimeType": "application/json", "buffer": json.dumps(value).encode()}
    )
    ready(page)


def review(page: Page) -> None:
    for arm in ("control", "treatment"):
        click(page, f"#timer-{arm}")
        page.locator("#raw-results").text_content()
        click(page, f"#timer-{arm}")
    page.locator("#reviewer").fill("Automated acceptance operator")
    page.locator("#review-reason").fill(
        "UI acceptance exercise. Native replay checks every prediction; no external review claimed."
    )
    click(page, "#accept")


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
    result: dict[str, Any] = {
        "schema": "agialpha.transfer.acceptance.v1",
        "origin": public_url or "local project subpath",
        "checks": [],
        "scenarios": [],
        "passed": False,
    }
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin + "compounding/", wait_until="networkidle")
            ready(page)
            page.screenshot(path=str(output / "compounding-desktop.png"), full_page=True)
            manuscript = context.request.get(origin + "manuscript/AGI_ALPHA_Unified_Publication_Final.pdf")
            assert manuscript.ok
            assert hashlib.sha256(manuscript.body()).hexdigest() == transfer.MANUSCRIPT_SHA256
            result["manuscript_sha256"] = transfer.MANUSCRIPT_SHA256
            result["checks"].append("exact-198-page-manuscript")
            for scenario in ("seasonal", "shift", "ablation"):
                click(page, f'[data-scenario="{scenario}"]')
                expect(page.locator("#prediction-chart")).to_have_attribute(
                    "aria-label", "Forecast comparison appears after execution"
                )
                click(page, "#freeze")
                expect(page.locator("#policy-name")).to_contain_text("period 5")
                click(page, "#compare")
                expect(page.locator("#local-verdict")).to_have_text("HOLD")
                review(page)
                expect(page.locator("#local-verdict")).to_have_text("ACCEPTED" if scenario == "seasonal" else "HOLD")
                path = output / f"{scenario}.json"
                download(page, "#export-run", path)
                report = transfer.parse(path.read_text())
                outcome = transfer.verify(report)
                assert outcome["bounded_transfer"] == ("accepted" if scenario == "seasonal" else "hold")
                assert report["core"] == transfer.compute(transfer.example(scenario))
                docket = output / f"{scenario}-docket.zip"
                download(page, "#export-docket", docket)
                assert transfer.verify_docket(docket.read_bytes()) == outcome
                result["scenarios"].append(
                    {"id": scenario, "outcome": outcome, "core_sha256": transfer.digest(report["core"])}
                )
            result["checks"].extend(
                [
                    "all-three-scenarios",
                    "python-javascript-exact-replay",
                    "complete-docket-zip-replay",
                    "review-does-not-override-loss",
                    "archive-ablation-zero-gain",
                    "eci-e2-no-independent-claim",
                ]
            )
            # Native CLI generates a report; the browser must accept the unchanged artifact.
            native = output / "native.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alpha_factory_v1.core.runtime.cli",
                    "transfer-run",
                    "--seed",
                    "91",
                    "--output",
                    str(native),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            native_reviewed = output / "native-reviewed.json"
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alpha_factory_v1.core.runtime.cli",
                    "transfer-review",
                    str(native),
                    "--decision",
                    "accept",
                    "--reviewer",
                    "Automated native acceptance",
                    "--reason",
                    "Acceptance fixture with illustrative reported durations, not independent human review",
                    "--control-ms",
                    "123000",
                    "--treatment-ms",
                    "456000",
                    "--output",
                    str(native_reviewed),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            native_report = transfer.parse(native_reviewed.read_text())
            page.locator("#import-run").set_input_files(str(native_reviewed))
            ready(page)
            expect(page.locator("#lab-status")).to_contain_text("Imported run")
            result["checks"].append("native-cli-browser-handoff")
            expect(page.locator("#accept")).to_be_disabled()
            page.reload(wait_until="networkidle")
            ready(page)
            expect(page.locator("#accept")).to_be_disabled()
            unchanged = output / "recovered-native-review.json"
            download(page, "#export-run", unchanged)
            assert transfer.parse(unchanged.read_text()) == native_report
            result["checks"].append("imported-review-keeps-timing-provenance")
            for kind in ("prediction", "stale-review", "unknown-field"):
                changed = deepcopy(native_report)
                if kind == "prediction":
                    changed["core"]["arms"]["B6"]["tasks"][0]["predictions_milli"][0] += 1
                elif kind == "unknown-field":
                    changed["validator_verdict"] = "accepted"
                else:
                    changed = transfer.review_run(changed, "accept", "Operator", "Test stale binding", 1, 1)
                    changed["review"]["run_sha256"] = "0" * 64
                upload(page, changed)
                expect(page.locator("#lab-status")).to_have_class("status error")
                preserved = output / f"after-{kind}.json"
                download(page, "#export-run", preserved)
                assert transfer.parse(preserved.read_text()) == native_report
            result["checks"].append("tampered-and-stale-import-rejected-atomically")
            review(page)
            measured = output / "browser-reviewed.json"
            download(page, "#export-run", measured)
            measured_report = transfer.parse(measured.read_text())
            assert measured_report["review"]["timing_source"] == "browser-elapsed"
            assert measured_report["review"]["control_ms"] != 123000
            assert measured_report["review"]["treatment_ms"] != 456000
            transfer.verify(measured_report)
            # Custom high cost must invalidate the prior review and close local acceptance.
            page.locator("#call-cost").fill("10000")
            page.locator("#call-cost").press("Tab")
            ready(page)
            expect(page.locator("#export-run")).to_be_disabled()
            expect(page.locator("#prediction-chart")).to_have_attribute(
                "aria-label", "Forecast comparison appears after execution"
            )
            click(page, "#freeze")
            click(page, "#compare")
            review(page)
            expect(page.locator("#local-verdict")).to_have_text("HOLD")
            result["checks"].extend(["cost-overhead-closes-gate", "changed-inputs-clear-review"])
            page.locator('[data-scenario="seasonal"]').focus()
            page.keyboard.press("Enter")
            ready(page)
            expect(page.locator('[data-scenario="seasonal"]')).to_be_focused()
            result["checks"].append("keyboard-focus-preserved")
            click(page, "#freeze")
            click(page, "#compare")
            page.locator("#laboratory").screenshot(path=str(output / "compounding-workspace.png"))
            if axe_script:
                inspect(page, axe_script.read_text() + ";true")
                audit = inspect(
                    page, "axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}})"
                )
                (output / "accessibility.json").write_text(json.dumps(audit, indent=2))
                assert audit["violations"] == [], audit["violations"]
                result["checks"].append("axe-wcag-a-aa-no-violations")
            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth"), "Mobile horizontal overflow"
                page.screenshot(path=str(output / f"compounding-mobile-{width}.png"), full_page=True)
            result["checks"].append("mobile-no-overflow")
            # Recovery and execution must work with the real installed service worker offline.
            wait_for(page, "navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload(wait_until="domcontentloaded")
            ready(page)
            expect(page.locator("#lab-status")).to_contain_text("recovered")
            click(page, "#compare")
            expect(page.locator("#run-state")).to_contain_text("EXECUTED")
            context.set_offline(False)
            result["checks"].append("offline-recovery-and-execution")
            page.goto(origin + "alpha_factory_v1/demos/compounding/", wait_until="networkidle")
            ready(page)
            click(page, "#freeze")
            click(page, "#compare")
            result["checks"].append("mirrored-page")
            assert not errors, errors
            result["browser_errors"] = errors
            result["passed"] = True
            browser.close()
    finally:
        if server:
            server.shutdown()
        (output / "compounding.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--url")
    parser.add_argument("--output", type=Path, default=Path("evidence/compounding"))
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.site, args.output, args.url, args.axe_script), indent=2))


if __name__ == "__main__":
    main()
