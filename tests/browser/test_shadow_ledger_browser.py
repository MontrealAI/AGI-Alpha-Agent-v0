# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs/successor/alpha/index.html"
LEFT = "code,name,price\nPUB-01,Public manual,20\nPUB-02,Source guide,40\nPUB-03,Test catalogue,60\n"
RIGHT = "code,name,price\nPUB-01,Public manual,20\nPUB-02,Source guide,45\nPUB-04,New catalogue,80\n"


def download(page: Page, selector: str) -> bytes:
    with page.expect_download() as pending:
        page.locator(selector).click()
    return Path(pending.value.path()).read_bytes()


def upload(page: Page, raw: bytes) -> None:
    page.locator("#shadow-file").set_input_files(
        {"name": "planning.json", "mimeType": "application/json", "buffer": raw}
    )


def economic_value(page: Page, label: str) -> str:
    return (
        page.locator("#shadow-result dt").filter(has_text=label).locator("xpath=following-sibling::dd[1]").inner_text()
    )


def run_custom(page: Page, left: str, right: str) -> None:
    page.locator("#mode-custom").click()
    page.locator("#left-csv").fill(left)
    page.locator("#right-csv").fill(right)
    page.locator("#check-columns").click()
    page.locator("#left-key").select_option("code")
    page.locator("#right-key").select_option("code")
    page.locator("#custom-start").click()
    expect(page.locator("#pane-evidence")).to_be_visible()
    page.locator("#keep-capability").click()
    expect(page.locator("#pane-successor")).to_be_visible()
    if page.locator("#shadow-panel").get_attribute("open") is None:
        page.locator("#shadow-panel > summary").click()


def run_acceptance(
    report_path: Path, *, entry_url: str | None = None, expected_page_sha256: str | None = None
) -> dict[str, Any]:
    checks: list[str] = []
    errors: list[str] = []
    requests: list[str] = []
    entry = entry_url or PAGE.as_uri()
    initial_navigation: list[str] = []

    def observe_request(request: Any) -> None:
        if not request.url.startswith(("http:", "https:")):
            return
        if not initial_navigation and request.url == entry and request.is_navigation_request():
            initial_navigation.append(request.url)
        else:
            requests.append(request.url)

    with tempfile.TemporaryDirectory(prefix="alpha-shadow-browser-") as folder, sync_playwright() as runtime:
        options: dict[str, Any] = {}
        if os.environ.get("CHROMIUM_EXECUTABLE"):
            options = {
                "executable_path": os.environ["CHROMIUM_EXECUTABLE"],
                "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            }
        browser = runtime.chromium.launch(**options)
        context = browser.new_context(
            accept_downloads=True, reduced_motion="reduce", viewport={"width": 1440, "height": 1100}
        )
        context.add_init_script(
            "document.addEventListener('securitypolicyviolation', e => console.error('CSP:' + e.violatedDirective))"
        )
        context.on("request", observe_request)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("console", lambda message: errors.append(message.text) if message.text.startswith("CSP:") else None)
        response = page.goto(entry)
        if response is not None:
            assert response.status < 400, f"Initial page failed: {response.status}"
            loaded_page_sha256 = hashlib.sha256(response.body()).hexdigest()
        else:
            assert entry == PAGE.as_uri(), "Cannot bind loaded page bytes"
            loaded_page_sha256 = hashlib.sha256(PAGE.read_bytes()).hexdigest()
        if expected_page_sha256 is not None:
            assert loaded_page_sha256 == expected_page_sha256, "Loaded page differs from qualified bytes"
        checks.append("initial-page-byte-identity")
        expect(page.locator("#hero-start")).to_be_visible()
        run_custom(page, LEFT, RIGHT)
        project = json.loads(download(page, "#download-project"))
        assert len(project["cycles"]) == 1 and project["authority"] == "none"
        cycle = project["cycles"][0]
        assert cycle["mission"]["left"]["rows"][0][0] == "PUB-01"
        assert cycle["result"]["reconciliation"]["matchedPairs"] == 2
        checks.append("fresh-input-local-mission-and-retained-cycle")

        expect(page.locator("#shadow-acceptance")).to_have_value("unknown")
        expect(page.locator("#shadow-reinvestment")).to_have_value("0")
        page.locator("#shadow-calculate").click()
        expect(page.locator("#shadow-result")).to_be_visible()
        assert economic_value(page, "Provider full cost") == "Unknown"
        assert economic_value(page, "Potential capability investment") == "Unknown"
        unknown_raw = download(page, "#shadow-download")
        assert json.loads(unknown_raw)["entries"][0]["inputs"]["totalOperatingCostCents"] is None
        checks.append("unknown-costs-and-acceptance-stay-unknown-zero-reinvestment-default")

        values = {
            "shadow-cost": "0.50",
            "shadow-price": "100",
            "shadow-collected": "0",
            "shadow-construction": "10",
            "shadow-reserve": "20",
            "shadow-obligation": "5",
            "shadow-traditional-minutes": "120",
            "shadow-hourly": "100",
            "shadow-attention": "5",
        }
        for selector, value in values.items():
            page.locator("#" + selector).fill(value)
        page.locator("#shadow-cost-complete").check()
        page.locator("#shadow-acceptance").select_option("accepted")
        page.locator("#shadow-reinvestment").select_option("50")
        page.locator("#shadow-calculate").click()
        expect(page.locator("#shadow-result")).to_be_visible()
        assert economic_value(page, "Traditional workflow").endswith("200.00")
        assert economic_value(page, "Provider full cost").endswith("10.50")
        assert economic_value(page, "After reserves and obligations").endswith("64.50")
        assert economic_value(page, "Potential capability investment").endswith("32.25")
        assert economic_value(page, "Collected revenue").endswith("0.00")
        assert economic_value(page, "Available cash surplus") == "Unknown"
        assert economic_value(page, "Customer price + remaining attention").endswith("108.34")
        checks.append("conditional-economics-reconciles-price-cash-cost-reserve-obligation-investment")
        checks.append("human-attention-displayed-without-provider-double-count")

        known_raw = download(page, "#shadow-download")
        known = json.loads(known_raw)
        assert known["projectId"] == project["id"] and known["authority"] == "none"
        assert len(known["entries"]) == 2
        assert known["entries"][-1]["cycleId"] == cycle["id"]
        assert known["entries"][-1]["sourceHash"] == cycle["sourceHash"]
        page.locator("#shadow-calculate").click()
        assert json.loads(download(page, "#shadow-download")) == known
        checks.append("actual-json-download-mission-source-binding-idempotent-recalculate")

        tampered = json.loads(known_raw)
        tampered["entries"][0]["inputs"]["totalOperatingCostCents"] = 1
        upload(page, json.dumps(tampered).encode())
        expect(page.locator("#shadow-error")).to_contain_text("replace or remove")
        assert json.loads(download(page, "#shadow-download")) == known
        foreign = json.loads(known_raw)
        foreign["projectId"] = "00000000-0000-4000-8000-000000000000"
        upload(page, json.dumps(foreign).encode())
        expect(page.locator("#shadow-error")).to_contain_text("different project")
        assert json.loads(download(page, "#shadow-download")) == known
        checks.append("tamper-cross-project-import-refused-with-existing-history-preserved")

        page.locator("#automation-panel > summary").click()
        page.locator("#automation-calculate").click()
        expect(page.locator("#automation-result")).to_contain_text("Unknown")
        unknown_costs = json.loads(download(page, "#automation-download"))
        assert unknown_costs["schema"] == "alpha-automated-costs/v1"
        assert unknown_costs["scenarios"][0]["operations"][0]["unitCostMicros"]["value"] is None
        page.locator("#automation-example").click()
        expect(page.locator("#automation-result tbody tr")).to_have_count(3)
        expect(page.locator("#automation-result")).to_contain_text("Loses")
        automated_record = json.loads(download(page, "#automation-download"))
        assert automated_record == json.loads(
            (ROOT / "examples/successor-alpha/fixtures/automated-costs-example.json").read_text()
        )
        assert automated_record["scenarios"][0]["humanBaseline"]["hourlyCostMicros"]["basis"] == "sourced"
        page.locator("#shadow-currency").select_option("CAD")
        page.locator("#automation-apply").click()
        expect(page.locator("#automation-error")).to_contain_text("currency differs")
        expect(page.locator("#shadow-currency")).to_have_value("CAD")
        for selector, value in values.items():
            expect(page.locator("#" + selector)).to_have_value(value)
        assert page.locator("#shadow-cost-complete").is_checked()
        assert json.loads(download(page, "#shadow-download")) == known
        checks.append("foreign-currency-allocation-refused-with-mission-amounts-and-history-intact")
        page.locator("#shadow-currency").select_option("USD")
        page.locator("#automation-apply").click()
        expect(page.locator("#automation-error")).to_be_hidden()
        assert page.locator("#shadow-cost").input_value() != ""
        assert page.locator("#shadow-construction").input_value() == ""
        assert not page.locator("#shadow-cost-complete").is_checked()
        assert json.loads(download(page, "#shadow-download")) == known
        checks.append("automated-three-cost-tiers-shared-record-and-loss-scenario")
        checks.append("amortization-never-converted-to-spendable-cash-or-duplicated-investment")

        page.locator("#lang-fr").click()
        expect(page.locator("#shadow-panel > summary")).to_have_text("Combien cette livraison a-t-elle coûté ?")
        expect(page.locator("#shadow-acceptance option[value=unknown]")).to_have_text("Acceptation du client inconnue")
        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 1100})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
            ), f"French overflow at {width}"
        checks.append("french-panel-and-320-390px-no-horizontal-overflow")
        page.set_viewport_size({"width": 1440, "height": 1100})
        page.locator("#lang-en").click()
        portable_raw = download(page, "#download-workspace")
        portable_path = Path(folder) / "portable.html"
        portable_path.write_bytes(portable_raw)
        context.close()

        context = browser.new_context(
            accept_downloads=True, offline=True, reduced_motion="reduce", viewport={"width": 1440, "height": 1100}
        )
        context.on("request", observe_request)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(portable_path.as_uri())
        expect(page.locator("#restored-note")).to_contain_text("historical")
        embedded = page.locator("#saved-shadow-ledger").text_content()
        assert json.loads(embedded or "null") == known
        automated_embedded = json.loads(page.locator("#saved-automated-costs").text_content() or "null")
        assert automated_embedded["projectId"] == project["id"]
        assert automated_embedded["record"] == automated_record
        page.locator("#custom-start").click()
        expect(page.locator("#pane-evidence")).to_be_visible()
        page.locator("#keep-capability").click()
        if page.locator("#shadow-panel").get_attribute("open") is None:
            page.locator("#shadow-panel > summary").click()
        assert json.loads(download(page, "#shadow-download")) == known
        current_project = json.loads(download(page, "#download-project"))
        assert current_project["id"] == project["id"] and len(current_project["cycles"]) == 2
        assert current_project["cycles"][0] == project["cycles"][0]
        checks.append("whole-html-close-reopen-offline-restores-planning-and-mission-history")

        upload(page, known_raw)
        expect(page.locator("#shadow-cost")).to_have_value("")
        expect(page.locator("#shadow-price")).to_have_value("")
        expect(page.locator("#shadow-acceptance")).to_have_value("unknown")
        expect(page.locator("#shadow-reinvestment")).to_have_value("0")
        assert json.loads(download(page, "#shadow-download")) == known
        checks.append("earlier-cycle-ledger-import-keeps-unplanned-current-cycle-unknown")
        unplanned_path = Path(folder) / "portable-unplanned-cycle.html"
        unplanned_path.write_bytes(download(page, "#download-workspace"))
        restored_context = browser.new_context(offline=True, reduced_motion="reduce")
        restored_context.on("request", observe_request)
        restored_page = restored_context.new_page()
        restored_page.on("pageerror", lambda error: errors.append(str(error)))
        restored_page.goto(unplanned_path.as_uri())
        expect(restored_page.locator("#restored-note")).to_contain_text("historical")
        expect(restored_page.locator("#shadow-cost")).to_have_value("")
        expect(restored_page.locator("#shadow-price")).to_have_value("")
        expect(restored_page.locator("#shadow-acceptance")).to_have_value("unknown")
        expect(restored_page.locator("#shadow-reinvestment")).to_have_value("0")
        assert json.loads(restored_page.locator("#saved-shadow-ledger").text_content()) == known
        restored_context.close()
        checks.append("portable-restore-never-inherits-earlier-cycle-finances-or-acceptance")

        page.locator("#next-cycle").click()
        run_custom(page, LEFT, RIGHT.replace("45", "48").replace("80", "82"))
        expect(page.locator("#shadow-cost")).to_have_value("")
        expect(page.locator("#shadow-price")).to_have_value("")
        expect(page.locator("#shadow-acceptance")).to_have_value("unknown")
        expect(page.locator("#shadow-reinvestment")).to_have_value("0")
        page.locator("#shadow-calculate").click()
        final = json.loads(download(page, "#shadow-download"))
        assert len(final["entries"]) == 3
        assert final["entries"][:2] == known["entries"]
        assert final["entries"][-1]["cycleId"] != known["entries"][-1]["cycleId"]
        assert final["entries"][-1]["inputs"]["totalOperatingCostCents"] is None
        assert final["entries"][-1]["inputs"]["acceptance"] == "unknown"
        assert "2 planned mission(s)" in page.locator("#shadow-result").inner_text()
        checks.append("fresh-changed-mission-retains-prior-ledger-and-adds-new-cycle")
        assert not errors, errors
        assert not requests, requests
        checks.extend(["no-page-errors-or-csp-violations", "no-network-data-or-executor-calls"])
        context.close()
        browser.close()
    report = {
        "schema": "alpha-shadow-ledger-browser-acceptance/v1",
        "scope": "Actual local Chromium; no approved executor or public deployment qualification",
        "pageSha256": loaded_page_sha256,
        "checks": checks,
        "passed": len(checks),
        "errors": errors,
        "initialNavigation": initial_navigation,
        "httpRequests": requests,
        "screenshotsRetained": False,
        "axeRun": False,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report", type=Path, default=ROOT / "contrib/productive-capability-ledger/evidence/browser-report.json"
    )
    args = parser.parse_args()
    print(json.dumps(run_acceptance(args.report), indent=2))
