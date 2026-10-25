# SPDX-License-Identifier: Apache-2.0
"""Final recorded-result and unchanged local-flow check in actual Chromium."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
KEY = "agialpha.software-capability-foundry.workspace.v1"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", required=True)
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    started = time.time()
    checks = []
    output = ROOT / "evidence/final-record"
    output.mkdir(parents=True, exist_ok=True)
    record = json.loads((ROOT / "research.json").read_text())
    analysis = json.loads((ROOT.parent / "results/analysis.json").read_text())
    build = json.loads((ROOT / "standalone-build.json").read_text())

    def check(name: str, condition: bool) -> None:
        checks.append({"name": name, "passed": bool(condition)})
        if not condition:
            raise AssertionError(name)

    check("standalone_matches_build_identity", digest(ROOT / "Foundry_Lab.html") == build["standaloneSha256"])
    check("recorded_primary_is_exact_final_analysis", record["exact_values"]["primary_cpu_ratio"] == analysis["primary"]["geometric_cpu_ratio"] and record["exact_values"]["primary_ci95"] == analysis["primary"]["ci95"] and record["status"] == analysis["decision"])
    freeze = json.loads((ROOT.parent / "protocol/FREEZE.json").read_text())
    check("frozen_scientific_sources_unchanged", all(digest(ROOT.parent / path) == expected for path, expected in freeze["files"].items()))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=args.browser, args=["--no-sandbox"])
        context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
        page = context.new_page()
        requests, errors = [], []
        page.on("request", lambda request: requests.append(request.url))
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto((ROOT / "Foundry_Lab.html").as_uri())
        page.wait_for_function("document.documentElement.dataset.ready !== undefined")
        check("standalone_initializes_with_verified_source", page.locator("html").get_attribute("data-ready") == "true")
        check("final_status_and_no_pending_placeholder", page.locator("#research-status").inner_text() == "HOLD_FLYWHEEL_SUPERIORITY" and "PENDING_RESEARCH_RESULTS" not in page.locator("body").inner_text())
        check("six_recorded_findings_displayed", page.locator("#research-findings .finding").count() == 6)
        text = page.locator("#research").inner_text()
        check("primary_interval_and_negative_result_displayed", all(value in text for value in ["1.0574× CPU", "1.0246, 1.0899", "5.74% more CPU", "strongest direct specialist"]))
        check("counts_lineage_and_cost_limits_displayed", all(value in text for value in ["1,344 / 1,344", "96 parent calls", "24 scoped bindings", "Unknown", "payback", "not 24 natural repositories"]))
        check("recorded_and_live_execution_are_distinct", "RECORDED RESEARCH · NOT EXECUTING HERE" in text and page.locator("#result-mode").inner_text() == "LIVE LOCAL EXAMPLE" and "Not connected" in page.locator(".scopebar").inner_text())
        for name, identity in record["evidence"].items():
            with page.expect_download() as download:
                page.locator(f'#research-links a[href="./downloads/{name}"]').click()
            target = output / name
            download.value.save_as(target)
            check(f"offline_download_exact_{name}", digest(target) == identity["sha256"] == digest(ROOT.parent / identity["relative_source"]))
        with page.expect_download() as download:
            page.locator('#research-links a[href="./README.md"]').click()
        download.value.save_as(output / "browser-README.md")
        check("offline_download_reproduction_guide", (output / "browser-README.md").read_bytes() == (ROOT / "README.md").read_bytes())

        state = lambda: page.evaluate(f"JSON.parse(localStorage.getItem('{KEY}'))")
        page.locator("#try").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===1")
        check("local_A_exact_public_bytes", state()["completed"][0]["result"]["summary"] == {"stage": "A", "files": 8, "bytes": 31837, "differences": 0, "parentInvocations": 0})
        page.evaluate("document.getElementById('continue').click();document.getElementById('stop').click();")
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).status==='stopped'")
        check("STOP_preserves_completed_history", len(state()["completed"]) == 1 and state()["pending"]["stage"] == "B")
        page.reload()
        page.wait_for_function("document.documentElement.dataset.ready==='true'")
        check("reopen_inactive_with_interruption", len(state()["completed"]) == 1 and "Interrupted" in page.locator("#notice").inner_text())
        page.evaluate("document.getElementById('continue').click();document.getElementById('pause').click();")
        page.wait_for_timeout(100)
        check("pause_before_next_completion", len(state()["completed"]) == 1 and page.locator("#pause").inner_text() == "Resume")
        page.locator("#pause").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===2")
        check("fresh_B_uses_retained_instrument", state()["completed"][1]["result"]["summary"]["parentInvocations"] == 1)
        page.locator("#continue").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===3")
        result = state()["completed"][2]["result"]
        check("C_distinct_diagnostic_actual_parent_use", result["summary"]["parentInvocations"] == 2 and all(len(result["evidence"]["output"][name]) == 1 for name in ["changed", "missing", "unexpected", "modeChanged"]))
        page.locator("#continue").click()
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).nextStage===4")
        check("D_refusal_before_byte_processing", state()["completed"][3]["result"]["decision"] == "REFUSED_OUT_OF_SCOPE" and state()["completed"][3]["result"]["summary"]["bytes"] == 0)
        with page.expect_download() as download:
            page.locator("#export").click()
        download.value.save_as(output / "workspace.json")
        original = (output / "workspace.json").read_bytes()
        page.locator("#rollback").click()
        check("rollback_retires_preserves_four_results", state()["instrument"] is None and len(state()["completed"]) == 4)
        page.locator("#restore").set_input_files({"name": "workspace.json", "mimeType": "application/json", "buffer": original})
        page.wait_for_function(f"JSON.parse(localStorage.getItem('{KEY}')).instrument!==null")
        check("restore_final_source_bound_pack_inactive", len(state()["completed"]) == 4 and state()["pending"] is None and "restored inactive" in page.locator("#notice").inner_text())
        page.locator("#research").scroll_into_view_if_needed()
        page.wait_for_timeout(100)
        check("desktop_no_horizontal_overflow", page.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        if args.screenshots:
            args.screenshots.mkdir(parents=True, exist_ok=True)
            page.locator("#research").screenshot(path=args.screenshots / "final-research-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#research").scroll_into_view_if_needed()
        check("mobile_no_horizontal_overflow", page.evaluate("document.documentElement.scrollWidth<=innerWidth"))
        if args.screenshots:
            page.locator("#research").screenshot(path=args.screenshots / "final-research-mobile.png")
        check("no_network_or_external_execution", all(url.startswith("file:") for url in requests))
        check("no_browser_exceptions", not errors)
        version = browser.version
        browser.close()
    receipt = {"schema": "foundry-final-browser-qa/v1", "browser": version, "sourceHash": build["sourceHash"], "standaloneSha256": build["standaloneSha256"], "researchSha256": digest(ROOT / "research.json"), "checks": checks, "passed": sum(check["passed"] for check in checks), "failed": sum(not check["passed"] for check in checks), "wall_seconds": time.time()-started, "scope": "One final actual Chromium pass of the standalone recorded panel, exact offline downloads and retained local control logic; no experiment rerun or external executor.", "downloads": {path.name: {"bytes": path.stat().st_size, "sha256": digest(path)} for path in output.iterdir() if path.is_file()}}
    (ROOT / "evidence/final-browser-qa.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({name: receipt[name] for name in ["browser", "sourceHash", "standaloneSha256", "passed", "failed", "wall_seconds"]}, indent=2))


if __name__ == "__main__":
    main()
