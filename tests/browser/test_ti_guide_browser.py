# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual guide controls, downloads, restoration and new computation."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright


def run_acceptance(entry: str, output: Path, expected: bytes, axe_script: Path) -> dict[str, Any]:
    """Require the complete browser-first workflow against the packaged guide."""
    output.mkdir(parents=True, exist_ok=True)
    checks: list[str] = []
    downloads: list[str] = []
    requests: list[dict[str, str]] = []

    def download(page: Page, selector: str, destination: str) -> bytes:
        with page.expect_download() as pending:
            page.locator(selector).click()
        raw = Path(pending.value.path()).read_bytes()
        (output / destination).write_bytes(raw)
        downloads.append(destination)
        return raw

    def finish(page: Page) -> None:
        page.locator("#try").click()
        expect(page.locator("#step-title")).to_have_text("What makes this difficult?")
        page.locator("#confirm").click()
        expect(page.locator("#step-title")).to_have_text("Try a better setup.")
        page.locator("#use-grouped").click()
        expect(page.locator("#step-title")).to_have_text("Use the result.")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1100})
        context.on(
            "request", lambda req: requests.append({"method": req.method, "url": req.url, "type": req.resource_type})
        )
        page = context.new_page()
        started = time.monotonic()
        response = page.goto(entry)
        if response is not None and response.body() != expected:
            raise AssertionError("Guide differs from exact packaged bytes")
        expect(page.locator("#try")).to_be_visible()
        before = len(requests)
        finish(page)
        sample_seconds = time.monotonic() - started
        expect(page.locator("#result-summary")).to_contain_text("4 items")
        actions = download(page, "#download-actions", "sample-actions.csv")
        differences = download(page, "#download-differences", "sample-differences.csv")
        assert len(list(csv.reader(io.StringIO(actions.decode())))) == 5
        assert len(list(csv.reader(io.StringIO(differences.decode())))) == 7
        page.locator(".how > summary").click()
        raw = download(page, "#download-json", "sample-workspace.json")
        saved = json.loads(raw)
        refs = [ref for action in saved["result"]["resolution"]["actions"] for ref in action["occurrences"]]
        assert len(refs) == len(set(refs)) == 6
        assert set(refs) == {x["occurrence"] for x in saved["result"]["differences"]}
        download(page, "#save", "sample-workspace.html")
        checks.extend(["fresh-no-account-sample", "three-click-result", "real-downloads", "every-original-reference"])
        page.locator("#result-details > summary").click()
        page.screenshot(path=str(output / "desktop.png"), full_page=True)
        assert not [
            r for r in requests[before:] if r["url"].startswith(("http:", "https:"))
        ], "Data interaction unexpectedly made a network request"
        checks.append("no-network-after-page-load")

        page.close()
        context.set_offline(True)
        offline = context.new_page()
        offline.goto((output / "sample-workspace.html").as_uri())
        expect(offline.locator("#step-title")).to_have_text("Use the result.")
        expect(offline.locator("#status")).to_contain_text("restored run")
        offline.locator(".how > summary").click()
        restored = json.loads(download(offline, "#download-json", "restored-workspace.json"))
        assert restored == saved
        checks.append("close-reopen-offline-same-results")

        offline.locator("#reuse").click()
        left = b"code,name,value\nX,First,1\nX,First,2\nY,Extra,4\n"
        right = b"record,name,value\nX,First,9\nZ,Other,5\n"
        offline.locator("#left-file").set_input_files({"name": "new-a.csv", "mimeType": "text/csv", "buffer": left})
        offline.locator("#right-file").set_input_files({"name": "new-b.csv", "mimeType": "text/csv", "buffer": right})
        offline.locator("#left-key").select_option("code")
        offline.locator("#right-key").select_option("record")
        finish(offline)
        changed = json.loads(download(offline, "#download-json", "changed-workspace.json"))
        assert changed["runId"] != saved["runId"]
        assert changed["result"]["leftIdentity"]["sha256"] == hashlib.sha256(left).hexdigest()
        assert changed["result"]["metrics"]["actionGroups"] == 3
        assert changed["result"]["metrics"]["evidenceReferences"] == 4
        download(offline, "#download-actions", "new-actions.csv")
        download(offline, "#download-differences", "new-differences.csv")
        checks.extend(["two-new-file-imports", "new-input-new-run-recomputation"])

        offline.locator("#reset").click()
        offline.locator("#workspace-file").set_input_files(
            {"name": "restore.json", "mimeType": "application/json", "buffer": raw}
        )
        expect(offline.locator("#step-title")).to_have_text("Use the result.")
        bad = json.loads(raw)
        bad["result"]["metrics"]["actionGroups"] = 0
        offline.locator("#reset").click()
        offline.locator("#workspace-file").set_input_files(
            {"name": "forged.json", "mimeType": "application/json", "buffer": json.dumps(bad).encode()}
        )
        expect(offline.locator("#error")).to_contain_text("differ from recomputation")
        checks.extend(["json-restore", "forged-result-refused"])

        offline.locator("#own-data > summary").click()
        offline.locator("#left-csv").fill("id,value\nA")
        expect(offline.locator("#left-error")).to_contain_text("header column count")
        expect(offline.locator("#try")).to_be_disabled()
        offline.locator("#left-csv").fill("id,id\nA,B")
        expect(offline.locator("#left-error")).to_contain_text("unique")
        offline.locator("#left-csv").fill('id,value\nA,"unfinished')
        expect(offline.locator("#left-error")).to_contain_text("Unclosed")
        checks.append("invalid-columns-and-malformed-rows")

        offline.locator("#left-csv").fill("id,value\n=evil,<img src=x onerror=alert(1)>\n")
        offline.locator("#right-csv").fill("id,value\n=evil,@danger\n")
        assert offline.locator("#left-preview img").count() == 0
        offline.locator("#try").click()
        expect(offline.locator("#step-title")).to_have_text("What makes this difficult?")
        offline.locator("#original-2").click()
        expect(offline.locator("#choice-summary")).to_contain_text("kept the original")
        safe = download(offline, "#download-differences", "injection-safe.csv").decode()
        assert "'=evil" in safe and "'@danger" in safe
        checks.extend(["html-remains-data", "spreadsheet-formulas-neutralized", "keep-original-approach"])

        axe = axe_script.read_text()
        for width in (390, 320):
            phone = browser.new_context(viewport={"width": width, "height": 844}, accept_downloads=True, offline=True)
            mobile = phone.new_page()
            mobile.goto((output / "sample-workspace.html").as_uri())
            expect(mobile.locator("#step-title")).to_have_text("Use the result.")
            mobile.locator("#reset").click()

            def tab_to(selector: str) -> None:
                for _ in range(50):
                    if mobile.locator(selector).evaluate("el=>el===document.activeElement"):
                        return
                    mobile.keyboard.press("Tab")
                raise AssertionError(f"Keyboard could not reach {selector}")

            tab_to("#try")
            mobile.keyboard.press("Enter")
            expect(mobile.locator("#step-title")).to_have_text("What makes this difficult?")
            mobile.keyboard.press("Tab")
            expect(mobile.locator("#confirm")).to_be_focused()
            mobile.keyboard.press("Enter")
            expect(mobile.locator("#step-title")).to_have_text("Try a better setup.")
            tab_to("#use-grouped")
            mobile.keyboard.press("Enter")
            expect(mobile.locator("#step-title")).to_have_text("Use the result.")
            assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth")
            mobile.evaluate(axe)
            audit = mobile.evaluate(
                "async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
            )
            assert not audit["violations"], audit["violations"]
            mobile.locator("#fr").click()
            expect(mobile.locator("#step-title")).to_have_text("Utilisez le résultat.")
            mobile.screenshot(path=str(output / f"phone-fr-{width}.png"), full_page=True)
            phone.close()
        checks.extend(["390-and-320-phone-flow", "keyboard-primary-flow", "en-fr", "axe-wcag2-aa"])
        browser.close()

    report = {
        "schema": "ti-guide-browser-acceptance/v1",
        "entry": entry,
        "pageSha256": hashlib.sha256(expected).hexdigest(),
        "passed": True,
        "checks": checks,
        "downloads": downloads,
        "requests": requests,
        "firstSampleSeconds": round(sample_seconds, 3),
        "clicksToFirstComputedObstacle": 1,
        "clicksToResult": 3,
        "humanTimeSavedMeasured": False,
        "authority": "none",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report
