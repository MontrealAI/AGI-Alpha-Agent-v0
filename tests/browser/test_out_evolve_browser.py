# SPDX-License-Identifier: Apache-2.0
"""Real-browser acceptance of generated Out-Evolve programs, lineage and recovery."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING, Any

from playwright.sync_api import Page, expect, sync_playwright

if TYPE_CHECKING:
    from tests.browser.out_evolve_recovery import verify_archive_recovery, verify_new_history_recovery
else:
    from out_evolve_recovery import verify_archive_recovery, verify_new_history_recovery

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("OUT_EVOLVE_EVIDENCE", "/tmp/out-evolve-browser-evidence"))
AXE = Path(os.environ.get("AXE_SCRIPT", str(ROOT / "tests/browser/node_modules/axe-core/axe.min.js")))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        """Suppress ordinary local fixture traffic."""


def idle(page: Page) -> None:
    """Wait for persisted evidence and unlocked founder controls."""
    expect(page.locator("#evolve-import")).to_be_enabled(timeout=120000)
    expect(page.locator("#evolve-form")).to_have_attribute("aria-busy", "false")


def history(page: Page) -> dict[str, Any]:
    """Read the actual visible exported event record."""
    value: dict[str, Any] = json.loads(page.locator("#evolve-history-json").text_content() or "{}")
    return value


def pending_construct_guard(page: Page) -> None:
    """A forced form submission cannot supersede a retained pending checkpoint."""
    retained = history(page)
    expect(page.locator("#evolve-construct")).to_be_disabled()
    page.locator("#evolve-form").dispatch_event("submit")
    idle(page)
    expect(page.locator("#evolve-status")).to_contain_text("original checkpoint is unchanged")
    assert history(page) == retained


def audit(page: Page, label: str) -> None:
    """Require the same accessibility tags as the preserved v1 lane."""
    assert AXE.is_file()
    page.evaluate(AXE.read_text())
    result = page.evaluate(
        "async () => await axe.run(document, {runOnly: {type: 'tag', "
        "values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice']}})"
    )
    (OUTPUT / f"accessibility-{label}.json").write_text(json.dumps(result, indent=2))
    assert not result["violations"], [(item["id"], item["nodes"]) for item in result["violations"]]


def main() -> None:
    """Exercise actual construction, independent checks, decisions, successor and durable lineage."""
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    url = base + "/docs/successor/capabilities/index.html"
    errors: list[str] = []
    requests: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="out-evolve-browser-") as temporary, sync_playwright() as playwright:
            executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            browser = playwright.chromium.launch(executable_path=executable)
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            context.on("request", lambda request: requests.append(request.url))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            idle(page)
            audit(page, "initial")
            page.locator("#out-evolve").screenshot(path=str(OUTPUT / "desktop-ready.png"))

            page.locator("#evolve-budget").fill("1")
            page.locator("#evolve-construct").click()
            idle(page)
            expect(page.locator("#evolve-status")).to_contain_text("within budget")
            failed = history(page)
            assert any(event["payload"].get("status") == "exhausted" for event in failed["events"])

            page.locator("#evolve-budget").fill("100000")
            page.locator("#evolve-construct").click()
            idle(page)
            expect(page.locator("#evolve-status")).to_contain_text("Capability qualified.")
            built = history(page)
            assert built["events"][: len(failed["events"])] == failed["events"]
            frozen = next(event["payload"]["package"] for event in built["events"] if event["kind"] == "package-frozen")
            assert frozen["certificate"]["productiveGain"] == 1
            assert frozen["certificate"]["errorBound"] == 0
            assert frozen["ast"]["installations"] or frozen["ast"]["prepare"]["steps"]
            with page.expect_download() as downloaded:
                page.locator("#evolve-export-package").click()
            package_path = Path(temporary) / "capability.json"
            downloaded.value.save_as(package_path)
            assert json.loads(package_path.read_text()) == frozen

            page.locator("#evolve-reuse").click()
            idle(page)
            expect(page.locator("#evolve-status")).to_contain_text("Frozen-package reuse: PASS")
            reused = history(page)
            reuse = reused["events"][-1]["payload"]
            assert {case["kind"] for case in reuse["cases"]} == {
                "threshold-screening",
                "inverse-design",
                "constrained-selection",
            }
            assert reuse["packageDigestBefore"] == reuse["packageDigestAfter"] == frozen["digest"]

            page.locator("#evolve-successor").click()
            idle(page)
            expect(page.locator("#evolve-status")).to_contain_text("Scope-expanding successor: PASS")
            evolved = history(page)
            successor = evolved["events"][-1]["payload"]
            assert successor["oldScope"]["status"] == "FAIL"
            assert successor["obligations"]["preserved"] and successor["newFunction"]["accepted"]
            assert successor["costs"]["cumulative"] >= successor["costs"]["remaining"]
            expect(page.locator("#evolve-retained")).to_contain_text("failed attempt")
            audit(page, "successor")
            page.locator("#out-evolve").screenshot(path=str(OUTPUT / "desktop-successor.png"))
            page.reload()
            idle(page)
            expect(page.locator("#evolve-status")).to_contain_text("recovered")
            assert history(page) == evolved

            with page.expect_download() as downloaded:
                page.locator("#evolve-export-history").click()
            history_path = Path(temporary) / "history.json"
            downloaded.value.save_as(history_path)
            assert json.loads(history_path.read_text()) == evolved
            portable = browser.new_context(accept_downloads=True)
            recovered = portable.new_page()
            recovered.goto(url)
            idle(recovered)
            recovered.locator("#evolve-import").set_input_files(history_path)
            idle(recovered)
            expect(recovered.locator("#evolve-status")).to_contain_text("History imported")
            assert history(recovered) == evolved
            tampered = json.loads(package_path.read_text())
            tampered["certificate"]["productiveGain"] = 0
            bad_path = Path(temporary) / "tampered.json"
            bad_path.write_text(json.dumps(tampered))
            recovered.locator("#evolve-import").set_input_files(bad_path)
            idle(recovered)
            expect(recovered.locator("#evolve-error")).to_be_visible()
            rejected = history(recovered)
            assert rejected["events"][: len(evolved["events"])] == evolved["events"]
            assert rejected["events"][-1]["kind"] == "failure"
            portable.close()

            conflict_context = browser.new_context(accept_downloads=True)
            writer = conflict_context.new_page()
            writer.goto(url)
            idle(writer)
            writer.locator("#evolve-import").set_input_files(history_path)
            idle(writer)
            stale = conflict_context.new_page()
            stale.on("dialog", lambda dialog: dialog.accept())
            stale.goto(url)
            idle(stale)
            writer.locator("#evolve-reuse").click()
            idle(writer)
            stored = history(writer)
            stale.locator("#evolve-reuse").click()
            expect(stale.locator("#evolve-form")).to_have_attribute("aria-busy", "false", timeout=120000)
            expect(stale.locator("#evolve-error")).to_contain_text("Another tab changed")
            expect(stale.locator("#evolve-construct")).to_be_disabled()
            with stale.expect_download() as downloaded:
                stale.locator("#evolve-export-history").click()
            conflict_path = OUTPUT / "conflicting-unsaved-history.json"
            downloaded.value.save_as(conflict_path)
            assert json.loads(conflict_path.read_text())["revision"] > evolved["revision"]
            stale.reload()
            idle(stale)
            assert history(stale) == stored
            conflict_context.close()

            interrupted_context = browser.new_context()
            interrupted = interrupted_context.new_page()
            interrupted.on("dialog", lambda dialog: dialog.accept())
            interrupted.goto(url)
            idle(interrupted)
            interrupted.locator("#evolve-topology").select_option("referenced")
            manifest = json.loads(interrupted.locator("#evolve-apparatus").input_value())
            for suffix in ("a", "b", "c"):
                name = "dust-" + suffix
                channel = dict(manifest["channels"][0], id=name)
                manifest["channels"].append(channel)
                manifest["edges"].append({"id": name + "-readout", "from": name, "to": "readout", "gain": 1})
                for kind in ("shield", "attenuate"):
                    original = next(primitive for primitive in manifest["primitives"] if primitive["kind"] == kind)
                    primitive = dict(original, id=original["kind"] + "-" + name, target=name)
                    manifest["primitives"].append(primitive)
            interrupted.locator("#evolve-form details summary").click()
            interrupted.locator("#evolve-apparatus").fill(json.dumps(manifest))
            interrupted.locator("#evolve-construct").click()
            interrupted.locator("#evolve-cancel").click()
            idle(interrupted)
            expect(interrupted.locator("#evolve-status")).to_contain_text("cancelled")
            cancelled = history(interrupted)
            assert cancelled["events"][-1]["payload"]["status"] == "cancelled"
            original_checkpoint = cancelled["events"][-1]["payload"]["checkpoint"]
            assert original_checkpoint["apparatus"] == manifest
            assert manifest["id"] != frozen["apparatus"]["id"]
            interrupted.locator("#evolve-topology").select_option("shielded")
            pending_construct_guard(interrupted)
            expect(interrupted.locator("#evolve-resume")).to_be_enabled()
            interrupted.locator("#evolve-import").set_input_files(package_path)
            idle(interrupted)
            expect(interrupted.locator("#evolve-status")).to_contain_text("unfinished search remains resumable")
            expect(interrupted.locator("#evolve-resume")).to_be_enabled()
            imported_pause = history(interrupted)
            imported_event_count = len(imported_pause["events"])
            assert imported_pause["events"][: len(cancelled["events"])] == cancelled["events"]
            assert imported_pause["events"][-1]["payload"]["package"]["digest"] == frozen["digest"]
            with interrupted.expect_download() as downloaded:
                interrupted.locator("#evolve-export-history").click()
            paused_path = OUTPUT / "paused-with-import-history.json"
            downloaded.value.save_as(paused_path)
            assert json.loads(paused_path.read_text()) == imported_pause
            interrupted.reload()
            idle(interrupted)
            assert history(interrupted) == imported_pause
            expect(interrupted.locator("#evolve-resume")).to_be_enabled()
            portable_pause = browser.new_context()
            resumed_page = portable_pause.new_page()
            resumed_page.goto(url)
            idle(resumed_page)
            resumed_page.locator("#evolve-import").set_input_files(paused_path)
            idle(resumed_page)
            resumed_page.reload()
            idle(resumed_page)
            assert history(resumed_page) == imported_pause
            expect(resumed_page.locator("#evolve-resume")).to_be_enabled()
            pending_construct_guard(resumed_page)
            resumed_page.locator("#evolve-resume").click()
            idle(resumed_page)
            resumed = history(resumed_page)
            (OUTPUT / "cancel-resume.json").write_text(json.dumps(resumed, indent=2))
            assert resumed["events"][:imported_event_count] == imported_pause["events"]
            resumed_stops = [
                event["payload"]["checkpoint"]
                for event in resumed["events"][imported_event_count:]
                if event["kind"] in ("search-stopped", "search-paused")
            ]
            assert resumed_stops
            assert all(token["apparatus"] == manifest for token in resumed_stops)
            assert all(token["options"] == original_checkpoint["options"] for token in resumed_stops)
            assert (
                resumed_stops[-1]["summary"]["work"]["synthesis"] >= original_checkpoint["summary"]["work"]["synthesis"]
            )
            assert any(
                event["payload"].get("status") in ("qualified", "exhausted", "infeasible")
                for event in resumed["events"]
            ), resumed["events"][-1]["payload"].get("message", "No terminal construction event")
            portable_pause.close()
            interrupted_context.close()

            mixed_context = browser.new_context(viewport={"width": 1440, "height": 1000})
            mixed = mixed_context.new_page()
            mixed.goto(url)
            idle(mixed)
            manifest = json.loads(mixed.locator("#evolve-apparatus").input_value())
            manifest["tolerance"] = 100
            mixed.locator("#evolve-form details summary").click()
            mixed.locator("#evolve-apparatus").fill(json.dumps(manifest))
            mixed.locator("#evolve-construct").click()
            idle(mixed)
            expect(mixed.locator("#evolve-status")).to_contain_text("Capability qualified.")
            mixed.evaluate("() => { crypto.getRandomValues = array => { array[0] = 1; return array; }; }")
            mixed.locator("#evolve-reuse").click()
            idle(mixed)
            expect(mixed.locator("#evolve-status")).to_contain_text("Frozen-package reuse: FAIL")
            mixed_history = history(mixed)
            assert {case["status"] for case in mixed_history["events"][-1]["payload"]["cases"]} == {"PASS", "FAIL"}
            manifest["tolerance"] = 0
            mixed.locator("#evolve-apparatus").fill(json.dumps(manifest))
            mixed.locator("#evolve-construct").click()
            idle(mixed)
            expect(mixed.locator("#evolve-status")).to_contain_text("Capability qualified.")
            assert history(mixed)["events"][: len(mixed_history["events"])] == mixed_history["events"]
            expect(mixed.locator("#evolve-retained")).to_contain_text("failed attempt")
            mixed.reload()
            idle(mixed)
            assert history(mixed)["events"][: len(mixed_history["events"])] == mixed_history["events"]
            mixed.locator("#out-evolve").screenshot(path=str(OUTPUT / "mixed-failure-retained.png"))
            (OUTPUT / "mixed-history.json").write_text(json.dumps(history(mixed), indent=2))
            mixed_context.close()

            reference_context = browser.new_context()
            reference = reference_context.new_page()
            reference.goto(url)
            idle(reference)
            reference.locator("#evolve-topology").select_option("referenced")
            reference.locator("#evolve-construct").click()
            idle(reference)
            reference_history = history(reference)
            comparison = next(
                event["payload"] for event in reference_history["events"] if event["kind"] == "comparison"
            )
            sensing = comparison["sensingCorrection"]
            assert comparison["relation"] == "tie"
            assert sensing["ledger"]["total"] == 20
            assert sensing["qualification"]["status"] == "not-qualified"
            assert sensing["search"]["complete"]
            expect(reference.locator("#evolve-work-total")).to_contain_text("20 model units; did not qualify")
            (OUTPUT / "common-reference-comparison.json").write_text(json.dumps(comparison, indent=2))
            reference_context.close()

            unfunded_successor_context = browser.new_context(accept_downloads=True)
            unfunded_successor = unfunded_successor_context.new_page()
            unfunded_successor.goto(url)
            idle(unfunded_successor)
            unfunded_successor.locator("#evolve-budget").fill("600")
            unfunded_successor.locator("#evolve-construct").click()
            idle(unfunded_successor)
            expect(unfunded_successor.locator("#evolve-status")).to_contain_text("Capability qualified.")
            funded_parent_history = history(unfunded_successor)
            funded_parent = next(
                event["payload"]["package"]
                for event in funded_parent_history["events"]
                if event["kind"] == "package-frozen"
            )
            assert funded_parent["costLedger"]["total"] <= 600
            unfunded_successor.locator("#evolve-successor").click()
            idle(unfunded_successor)
            expect(unfunded_successor.locator("#evolve-status")).to_contain_text(
                "Scope-expanding successor: INCONCLUSIVE"
            )
            expect(unfunded_successor.locator("#evolve-status")).to_contain_text("Candidate found")
            unfunded_successor_history = history(unfunded_successor)
            assert (
                unfunded_successor_history["events"][: len(funded_parent_history["events"])]
                == funded_parent_history["events"]
            )
            successor_event = unfunded_successor_history["events"][-1]
            assert successor_event["kind"] == "failure" and successor_event["payload"]["status"] == "INCONCLUSIVE"
            expect(unfunded_successor.locator("#evolve-events > li").last.locator("h4")).to_contain_text(
                "Inconclusive attempt retained"
            )
            unfunded_report = successor_event["payload"]["report"]
            assert unfunded_report["oldScope"]["status"] == "FAIL"
            assert unfunded_report["status"] == "INCONCLUSIVE"
            assert not any(key in unfunded_report for key in ("package", "reuse", "newFunction"))
            candidate = unfunded_report["result"]
            assert candidate["constructionStatus"] == "qualified" and candidate["status"] == "exhausted"
            assert candidate["checkpoint"]["status"] == "qualified" and candidate["ledger"]["total"] == 424
            assert candidate["acceptanceLedger"] is None
            assert candidate["freeze"]["status"] == "not-run"
            assert candidate["freeze"]["requiredTotal"] == 1157 and candidate["freeze"]["maxCost"] == 600
            expect(unfunded_successor.locator("#evolve-work-total")).to_contain_text(
                "No successor package was accepted"
            )
            assert json.loads(unfunded_successor.locator("#evolve-evidence").text_content() or "{}") == unfunded_report
            unfunded_successor.reload()
            idle(unfunded_successor)
            assert history(unfunded_successor) == unfunded_successor_history
            assert json.loads(unfunded_successor.locator("#evolve-evidence").text_content() or "{}") == unfunded_report
            expect(unfunded_successor.locator("#evolve-work-total")).to_contain_text(
                "No successor package was accepted"
            )
            with unfunded_successor.expect_download() as downloaded:
                unfunded_successor.locator("#evolve-export-package").click()
            retained_parent_path = OUTPUT / "unfunded-successor-retained-parent.json"
            downloaded.value.save_as(retained_parent_path)
            assert json.loads(retained_parent_path.read_text()) == funded_parent
            (OUTPUT / "unfunded-successor-history.json").write_text(json.dumps(unfunded_successor_history, indent=2))
            unfunded_successor_context.close()

            bounded_context = browser.new_context()
            bounded = bounded_context.new_page()
            bounded.goto(url)
            idle(bounded)
            bounded.locator("#evolve-budget").fill("1500")
            bounded.locator("#evolve-construct").click()
            idle(bounded)
            bounded.locator("#evolve-successor").click()
            idle(bounded)
            expect(bounded.locator("#evolve-status")).to_contain_text("Scope-expanding successor: PASS")
            bounded_history = history(bounded)
            bounded_successor = bounded_history["events"][-1]["payload"]
            assert bounded_successor["status"] == "PASS"
            assert bounded_successor["package"]["digest"]
            assert bounded_successor["costs"]["scratchQualified"] is False
            assert bounded_successor["costs"]["scratchConstructionWork"] == 1399
            assert bounded_successor["costs"]["constructionFromScratch"] is None
            expect(bounded.locator("#evolve-work-total")).to_contain_text("Scratch comparator inconclusive; 1399")
            (OUTPUT / "bounded-successor-history.json").write_text(json.dumps(bounded_history, indent=2))
            bounded.reload()
            idle(bounded)
            assert history(bounded) == bounded_history
            bounded_context.close()

            qualified_context = browser.new_context(accept_downloads=True)
            qualified = qualified_context.new_page()
            qualified.on("dialog", lambda dialog: dialog.accept())
            qualified.goto(url)
            idle(qualified)
            qualified.locator("#evolve-topology").select_option("referenced")
            qualified_abort_script = """() => {
                    let pending = true;
                    const put = IDBObjectStore.prototype.put;
                    IDBObjectStore.prototype.put = function(value, ...args) {
                        const request = put.call(this, value, ...args);
                        const event = value?.events?.at(-1);
                        if (pending && event?.kind === 'search-stopped' && event.payload.status === 'qualified') {
                            pending = false;
                            const transaction = this.transaction;
                            queueMicrotask(() => transaction.abort());
                        }
                        return request;
                    };
                }"""
            qualified.evaluate(qualified_abort_script)
            qualified.locator("#evolve-construct").click()
            expect(qualified.locator("#evolve-retry-save")).to_be_visible(timeout=120000)
            expect(qualified.locator("#evolve-form")).to_have_attribute("aria-busy", "false")
            pending_history = history(qualified)
            pending_event_count = len(pending_history["events"])
            pending_token = pending_history["events"][-1]["payload"]["checkpoint"]
            assert pending_token["status"] == "qualified"
            assert not any(event["kind"] == "package-frozen" for event in pending_history["events"])
            (OUTPUT / "qualified-pending-history.json").write_text(json.dumps(pending_history, indent=2))
            qualified.locator("#evolve-retry-save").click()
            idle(qualified)
            expect(qualified.locator("#evolve-retry-save")).to_be_hidden()
            expect(qualified.locator("#evolve-resume")).to_have_text("Finish qualifying package")
            expect(qualified.locator("#evolve-resume")).to_be_enabled()
            assert history(qualified) == pending_history
            pending_construct_guard(qualified)
            qualified.reload()
            idle(qualified)
            assert history(qualified) == pending_history
            expect(qualified.locator("#evolve-resume")).to_be_enabled()
            expect(qualified.locator("#evolve-export-package")).to_be_disabled()
            qualified.locator("#evolve-import").set_input_files(package_path)
            idle(qualified)
            expect(qualified.locator("#evolve-status")).to_contain_text("candidate checkpoint remains pending")
            qualified_import = history(qualified)
            assert qualified_import["events"][:pending_event_count] == pending_history["events"]
            (OUTPUT / "qualified-pending-with-import.json").write_text(json.dumps(qualified_import, indent=2))
            qualified.reload()
            idle(qualified)
            expect(qualified.locator("#evolve-resume")).to_be_enabled()
            qualified.locator("#evolve-resume").click()
            idle(qualified)
            expect(qualified.locator("#evolve-status")).to_contain_text("Capability qualified.")
            finalized = history(qualified)
            assert finalized["events"][: len(qualified_import["events"])] == qualified_import["events"]
            assert not any(event["kind"] == "search-stopped" for event in finalized["events"][pending_event_count:])
            final_package = next(
                event["payload"]["package"]
                for event in reversed(finalized["events"])
                if event["kind"] == "package-frozen"
            )
            assert final_package["search"]["checkpoint"] == pending_token
            assert final_package["search"]["work"] == pending_token["summary"]["work"]
            assert final_package["apparatus"] == pending_token["apparatus"]
            expect(qualified.locator("#evolve-resume")).to_be_disabled()
            (OUTPUT / "qualified-save-recovered.json").write_text(json.dumps(finalized, indent=2))
            final_package_path = OUTPUT / "qualified-final-package.json"
            final_package_path.write_text(json.dumps(final_package, indent=2))
            matching_context = browser.new_context()
            matching = matching_context.new_page()
            matching.goto(url)
            idle(matching)
            matching.locator("#evolve-import").set_input_files(OUTPUT / "qualified-pending-history.json")
            idle(matching)
            expect(matching.locator("#evolve-resume")).to_be_enabled()
            matching.locator("#evolve-import").set_input_files(final_package_path)
            idle(matching)
            expect(matching.locator("#evolve-resume")).to_be_disabled()
            expect(matching.locator("#evolve-status")).not_to_contain_text("remains pending")
            matching.reload()
            idle(matching)
            expect(matching.locator("#evolve-resume")).to_be_disabled()
            assert history(matching)["events"][-1]["payload"]["package"]["digest"] == final_package["digest"]
            (OUTPUT / "matching-package-completed-history.json").write_text(json.dumps(history(matching), indent=2))
            matching_context.close()
            qualified_context.close()

            unfunded_context = browser.new_context(accept_downloads=True)
            unfunded = unfunded_context.new_page()
            unfunded.goto(url)
            idle(unfunded)
            unfunded.locator("#evolve-budget").fill("500")
            unfunded.locator("#evolve-construct").click()
            idle(unfunded)
            expect(unfunded.locator("#evolve-status")).to_contain_text("Package qualification is inconclusive")
            expect(unfunded.locator("#evolve-resume")).to_be_disabled()
            unfunded_history = history(unfunded)
            assert unfunded_history["events"][-1]["payload"]["status"] == "qualified"
            assert not any(event["kind"] == "package-frozen" for event in unfunded_history["events"])
            unfunded.reload()
            idle(unfunded)
            expect(unfunded.locator("#evolve-status")).to_contain_text("exceeds its frozen budget")
            expect(unfunded.locator("#evolve-resume")).to_be_disabled()
            expect(unfunded.locator("#evolve-export-package")).to_be_disabled()
            assert history(unfunded) == unfunded_history
            pending_construct_guard(unfunded)
            (OUTPUT / "unfunded-finalization-history.json").write_text(json.dumps(unfunded_history, indent=2))
            unfunded.locator("#evolve-new-history").click()
            idle(unfunded)
            separate = history(unfunded)
            assert separate["id"] != unfunded_history["id"] and not separate["events"]
            expect(unfunded.locator("#evolve-construct")).to_be_enabled()
            unfunded.locator("#evolve-budget").fill("100000")
            unfunded.locator("#evolve-construct").click()
            idle(unfunded)
            expect(unfunded.locator("#evolve-status")).to_contain_text("Capability qualified.")
            separate = history(unfunded)
            assert separate["id"] != unfunded_history["id"]
            assert any(event["kind"] == "package-frozen" for event in separate["events"])
            (OUTPUT / "separate-after-unfunded-history.json").write_text(json.dumps(separate, indent=2))
            saved_disclosure = unfunded.locator("details").filter(has=unfunded.locator("#evolve-saved"))
            saved_disclosure.locator("summary").click()
            unfunded.locator("#evolve-saved").select_option(unfunded_history["id"])
            unfunded.locator("#evolve-open").click()
            idle(unfunded)
            assert history(unfunded) == unfunded_history
            expect(unfunded.locator("#evolve-construct")).to_be_disabled()
            expect(unfunded.locator("#evolve-resume")).to_be_disabled()
            with unfunded.expect_download() as downloaded:
                unfunded.locator("#evolve-export-history").click()
            reopened_path = OUTPUT / "reopened-unfunded-history.json"
            downloaded.value.save_as(reopened_path)
            assert json.loads(reopened_path.read_text()) == unfunded_history
            unfunded.reload()
            idle(unfunded)
            assert history(unfunded) == unfunded_history
            expect(unfunded.locator("#evolve-construct")).to_be_disabled()
            unfunded_context.close()
            verify_new_history_recovery(browser, url, OUTPUT / "unfunded-finalization-history.json", OUTPUT)

            repeated_path = OUTPUT / "repeated-successor-history.json"
            repeated_script = """
                import {readFileSync, writeFileSync} from 'node:fs';
                const {buildSuccessor} = await import(process.argv[1]);
                const {appendOutEvolveEvent} = await import(process.argv[2]);
                const history = JSON.parse(readFileSync(process.argv[3], 'utf8'));
                const parent = history.events.filter(event => event.kind === 'successor').at(-1).payload.package;
                const report = await buildSuccessor(parent, {seed: 314159});
                if (report.status !== 'FAIL' || report.oldScope.status !== 'UNEXPECTED-PASS') {
                    throw Error('Expected repeated-scope negative.');
                }
                const updated = await appendOutEvolveEvent(history, 'successor', report);
                writeFileSync(process.argv[4], JSON.stringify(updated));
                console.log(JSON.stringify({
                    node: process.version, status: report.status, oldScope: report.oldScope.status
                }));
            """
            repeated_run = subprocess.run(
                [
                    os.environ.get("NODE_EXECUTABLE", "node"),
                    "--input-type=module",
                    "-e",
                    repeated_script,
                    (ROOT / "examples/successor-capability/evaluation.mjs").as_uri(),
                    (ROOT / "examples/successor-capability/out-evolve-workspace.mjs").as_uri(),
                    str(history_path),
                    str(repeated_path),
                ],
                check=True,
                text=True,
                capture_output=True,
                timeout=120,
            )
            (OUTPUT / "repeated-successor-fixture.log").write_text(repeated_run.stdout + repeated_run.stderr)
            assert json.loads(repeated_run.stdout)["node"] == "v22.17.1"
            repeated_context = browser.new_context()
            repeated = repeated_context.new_page()
            repeated.goto(url)
            idle(repeated)
            repeated.locator("#evolve-import").set_input_files(repeated_path)
            idle(repeated)
            repeated_event = history(repeated)["events"][-1]
            assert repeated_event["payload"]["status"] == "FAIL"
            assert repeated_event["payload"]["oldScope"]["status"] == "UNEXPECTED-PASS"
            expect(repeated.locator("#evolve-events li").last).to_contain_text(
                "Recorded prior-scope result: UNEXPECTED-PASS"
            )
            expect(repeated.locator("#evolve-events li").last).not_to_contain_text("The old package is insufficient")
            repeated.reload()
            idle(repeated)
            expect(repeated.locator("#evolve-events li").last).to_contain_text(
                "Recorded prior-scope result: UNEXPECTED-PASS"
            )
            repeated_context.close()

            verify_archive_recovery(browser, url, package_path, history_path, OUTPUT)

            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
                if width in (390, 1440):
                    page.locator("#out-evolve").screenshot(path=str(OUTPUT / f"layout-{width}.png"))
            page.set_viewport_size({"width": 390, "height": 1000})
            page.evaluate("document.documentElement.style.fontSize = '200%'")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            audit(page, "mobile-text-200")
            assert not errors, errors
            assert all(request.startswith((base, "blob:")) for request in requests), requests
            (OUTPUT / "history.json").write_text(json.dumps(evolved, indent=2))
            (OUTPUT / "browser-result.json").write_text(
                json.dumps({"status": "PASS", "errors": errors, "requests": requests, "widths": [320, 390, 768, 1440]})
            )
            context.close()
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print("Out-Evolve browser journey, frozen reuse, successor, recovery, tamper, mobile and accessibility: PASS")


if __name__ == "__main__":
    main()
