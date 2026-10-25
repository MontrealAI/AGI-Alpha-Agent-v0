# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

KEY = "agialpha.software-capability-foundry.workspace.v1"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8767/browser/")
    parser.add_argument("--browser")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "evidence")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.screenshots:
        args.screenshots.mkdir(parents=True, exist_ok=True)
    checks = []
    started = time.time()

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=args.browser, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
        page = context.new_page()
        errors = []
        requests = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        page.goto(args.url)
        page.wait_for_function("document.documentElement.dataset.ready !== undefined")
        check("source_bound_initialization", page.locator("html").get_attribute("data-ready") == "true")
        page.locator("#try").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===1")
        state = lambda: page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}'))")
        check("mission_A_verified_public_bytes", state()["completed"][0]["result"]["summary"] == {"stage": "A", "files": 8, "bytes": 31837, "differences": 0, "parentInvocations": 0})
        with page.expect_download() as download:
            page.locator("#download-result").click()
        download.value.save_as(args.output / "mission-a-pack.json")
        check("actual_result_download", json.loads((args.output / "mission-a-pack.json").read_text())["integrityDigest"] == state()["completed"][0]["integrityDigest"])
        page.reload()
        page.wait_for_function("document.documentElement.dataset.ready==='true'")
        check("reopen_no_reexecution", len(state()["completed"]) == 1 and state()["pending"] is None)
        page.evaluate("document.getElementById('continue').click();document.getElementById('stop').click();")
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).status==='stopped'")
        check("actual_STOP_preserves_completed_prefix", len(state()["completed"]) == 1 and state()["pending"]["stage"] == "B")
        page.reload()
        page.wait_for_function("document.documentElement.dataset.ready==='true'")
        check("interrupted_reopen_inactive", len(state()["completed"]) == 1 and "Interrupted" in page.locator("#notice").inner_text())
        page.evaluate("document.getElementById('continue').click();document.getElementById('pause').click();")
        page.wait_for_timeout(100)
        check("pause_prevents_completion", len(state()["completed"]) == 1 and page.locator("#pause").inner_text() == "Resume")
        page.locator("#pause").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===2")
        check("resume_same_mission_parent_trace", state()["completed"][1]["result"]["summary"]["parentInvocations"] == 1 and len(state()["completed"]) == 2)
        page.locator("#continue").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===3")
        output = state()["completed"][2]["result"]["evidence"]["output"]
        check("distinct_drift_output_four_classes", all(len(output[k]) == 1 for k in ["changed", "missing", "unexpected", "modeChanged"]) and not output["exact"])
        check("selected_C_execution_uses_parent_twice", state()["completed"][2]["result"]["summary"]["parentInvocations"] == 2)
        with page.expect_download() as download:
            page.locator("#download-result").click()
        download.value.save_as(args.output / "mission-c-pack.json")
        check("actual_diagnostic_download", json.loads((args.output / "mission-c-pack.json").read_text())["result"]["evidence"]["output"] == output)
        if args.screenshots:
            page.screenshot(path=args.screenshots / "desktop-mission-c.png", full_page=True)
        page.locator("#continue").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===4")
        check("D_refuses_out_of_scope", state()["completed"][3]["result"]["decision"] == "REFUSED_OUT_OF_SCOPE" and state()["completed"][3]["result"]["summary"]["bytes"] == 0)
        with page.expect_download() as download:
            page.locator("#export").click()
        download.value.save_as(args.output / "completed-workspace.json")
        original = (args.output / "completed-workspace.json").read_bytes()
        check("actual_workspace_download", len(json.loads(original)["completed"]) == 4)
        page.locator("#rollback").click()
        check("rollback_retires_instrument_preserves_history", state()["instrument"] is None and len(state()["completed"]) == 4 and len(state()["retirements"]) == 1)
        page.locator("#restore").set_input_files({"name": "workspace.json", "mimeType": "application/json", "buffer": original})
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).instrument!==null")
        check("restore_validates_and_stays_inactive", "restored inactive" in page.locator("#notice").inner_text() and len(state()["completed"]) == 4 and state()["pending"] is None)
        corrupt = json.loads(original)
        corrupt["completed"][0]["result"]["summary"]["files"] = 999
        page.locator("#restore").set_input_files({"name": "tampered.json", "mimeType": "application/json", "buffer": json.dumps(corrupt).encode()})
        page.wait_for_function("!document.getElementById('error').hidden")
        check("tampered_pack_refused_without_mutation", "PACK_INTEGRITY" in page.locator("#error").inner_text() and len(state()["completed"]) == 4)
        corrupt = json.loads(original)
        corrupt["sourceHash"] = "0" * 64
        page.locator("#restore").set_input_files({"name": "wrong-source.json", "mimeType": "application/json", "buffer": json.dumps(corrupt).encode()})
        page.wait_for_function("document.getElementById('error').textContent.includes('differently bound')")
        check("wrong_source_workspace_refused", len(state()["completed"]) == 4)
        page.locator("#baseline-files").set_input_files([{"name": "a.txt", "mimeType": "text/plain", "buffer": b"old"}, {"name": "gone.txt", "mimeType": "text/plain", "buffer": b"old"}])
        page.locator("#candidate-files").set_input_files([{"name": "a.txt", "mimeType": "text/plain", "buffer": b"new"}, {"name": "new.txt", "mimeType": "text/plain", "buffer": b"new"}])
        page.locator("#rights").check()
        page.locator("#compare-own").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).completed.length===5")
        own = state()["completed"][-1]["result"]["evidence"]["output"]
        check("real_selected_file_comparison", own["changed"] == ["a.txt"] and own["missing"] == ["gone.txt"] and own["unexpected"] == ["new.txt"])
        page.locator("#baseline-files").set_input_files([{"name": "same.txt", "mimeType": "text/plain", "buffer": b"one"}, {"name": "same.txt", "mimeType": "text/plain", "buffer": b"two"}])
        page.locator("#compare-own").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).completed.length===6")
        check("duplicate_selected_names_refused", state()["completed"][-1]["result"]["decision"] == "REFUSED_OUT_OF_SCOPE")
        page.locator("#baseline-files").set_input_files({"name": "bad.bin", "mimeType": "application/octet-stream", "buffer": b"\xff\xfe\x80"})
        page.locator("#compare-own").click()
        page.wait_for_function("document.getElementById('error').textContent.includes('valid UTF-8')")
        check("non_UTF8_refused_before_mission", len(state()["completed"]) == 6)
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator('[data-stage="C"]').click()
        check("mobile_no_horizontal_overflow", page.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        check("mobile_C_evidence_visible", "DRIFT LOCALIZED" in page.locator("#status-tag").inner_text())
        if args.screenshots:
            page.screenshot(path=args.screenshots / "mobile-mission-c.png", full_page=True)
        page.goto(args.url)
        page.wait_for_function("document.documentElement.dataset.ready==='true'")
        page.keyboard.press("Tab")
        page.keyboard.press("Enter")
        check("keyboard_skip_link", page.url.endswith("#workspace"))
        check("no_external_network", all(url.startswith(args.url.split('/browser/')[0]) for url in requests))
        check("no_browser_exceptions", not errors)
        standalone = Path(__file__).resolve().parent / "Foundry_Lab.html"
        second = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
        single = second.new_page()
        standalone_requests = []
        single.on("request", lambda request: standalone_requests.append(request.url))
        single.goto(standalone.as_uri())
        single.wait_for_function("document.documentElement.dataset.ready !== undefined")
        check("single_file_initializes_without_server", single.locator("html").get_attribute("data-ready") == "true")
        single.locator("#try").click()
        single.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===1")
        for stage in [2, 3, 4]:
            single.locator("#continue").click()
            single.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage==={stage}")
        check("single_file_completes_all_four_missions", single.evaluate(f"JSON.parse(localStorage.getItem('{KEY}')).completed.length") == 4)
        check("single_file_zero_network_requests", all(url.startswith("file:") for url in standalone_requests))
        with single.expect_download() as download:
            single.locator('a[download][href="adapter.mjs"]').click()
        download.value.save_as(args.output / "downloaded-adapter.mjs")
        check("single_file_exact_instrument_download", (args.output / "downloaded-adapter.mjs").read_bytes() == (Path(__file__).resolve().parent / "adapter.mjs").read_bytes())
        version = browser.version
        browser.close()
    files = {path.name: {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in args.output.iterdir() if path.is_file() and path.name != "browser-qa.json"}
    record = {"schema": "foundry-browser-qa/v1", "browser": version, "sourceHash": json.loads((Path(__file__).resolve().parent / "source-manifest.json").read_text())["sourceHash"], "scope": "Actual local Chromium, localhost and file://; no public deployment or approved external executor.", "checks": checks, "passed": sum(row["passed"] for row in checks), "failed": sum(not row["passed"] for row in checks), "wall_seconds": time.time() - started, "downloaded_artifacts": files}
    (args.output / "browser-qa.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({key: value for key, value in record.items() if key not in ["checks", "downloaded_artifacts"]}, indent=2))


if __name__ == "__main__":
    main()
