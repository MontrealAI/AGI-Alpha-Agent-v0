# SPDX-License-Identifier: Apache-2.0
"""Real Chromium to fixed executor acceptance; never substitutes a simulated browser."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time

import httpx
from playwright.sync_api import expect, sync_playwright
import uvicorn

if os.environ.get("STRATEGY_INSTALLED_ACCEPTANCE") == "1":
    from strategy_succession_engineering.serve import ROOT, create
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serve import ROOT, create

from alpha_factory_v1.core.runtime.store import Journal


def fresh_mission():
    """A distinct graph matching the public preparer's seven-job synthetic request."""
    return {
        "initial": {
            "schema": "release-plan/v1",
            "id": "community-release-seven",
            "kind": "plan",
            "public_or_synthetic": "synthetic",
            "planning_only": True,
            "jobs": [
                {"id": "J1", "duration": 1, "crew": 1, "deps": []},
                {"id": "J2", "duration": 3, "crew": 2, "deps": ["J1"]},
                {"id": "J3", "duration": 2, "crew": 1, "deps": ["J1"]},
                {"id": "J4", "duration": 2, "crew": 1, "deps": ["J2", "J3"]},
                {"id": "J5", "duration": 2, "crew": 2, "deps": ["J4"]},
                {"id": "J6", "duration": 1, "crew": 1, "deps": ["J4"]},
                {"id": "J7", "duration": 1, "crew": 1, "deps": ["J5", "J6"]},
            ],
            "capacity": [2] * 32,
            "deadline": 30,
        },
        "changes": {"durations": {"J3": 4}, "deadline": 30},
        "repair": {"observed_at": 2, "capacity": [1 if 8 <= i < 13 else 2 for i in range(32)], "deadline": 30},
        "construction": {"enabled": True},
    }


def test_real_browser_approved_executor_reconnect_download_stop(tmp_path):
    """One approved journey keeps working after tab close; reconnect never reexecutes it."""
    journal = Journal.initialize(tmp_path / "private-test-home")
    token = (journal.root / "api.token").read_text().strip()
    app = create(journal.root, ROOT / "ENGINEERING_MANIFEST.json", native=True)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, access_log=False, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    headers = {"Authorization": "Bearer " + token}
    requests_seen, page_errors = [], []
    started = time.perf_counter()
    public = Path(os.environ.get("STRATEGY_EVIDENCE_DIR", Path(__file__).resolve().parents[1] / "acceptance-public"))
    public.mkdir(parents=True, exist_ok=True)
    try:
        with httpx.Client(base_url=origin, headers=headers, timeout=130, trust_env=False) as control:
            for _ in range(200):
                if server.started:
                    break
                time.sleep(0.025)
            assert server.started
            assert (
                control.get("/api/strategy-executor/status", headers={"Authorization": "Bearer wrong"}).status_code
                == 401
            )
            assert (
                control.post(
                    "/api/strategy-executor/prepare",
                    json={},
                    headers={**headers, "Origin": "https://untrusted.example"},
                ).status_code
                == 403
            )
            with sync_playwright() as p:
                executable = os.environ.get("STRATEGY_CHROMIUM_EXECUTABLE")
                browser = p.chromium.launch(headless=True, **({"executable_path": executable} if executable else {}))

                # The qualification driver supplies exact generated public bytes.
                # Use an isolated token-free page, then import its actual download.
                preparer_source = Path(__file__).absolute().with_name("public-planning-preparer.html")
                assert preparer_source.is_file() and not preparer_source.is_symlink()
                preparer_context = browser.new_context(accept_downloads=True)
                preparer_context.route(
                    "**/*",
                    lambda route: route.continue_() if route.request.url == preparer_source.as_uri() else route.abort(),
                )
                preparer = preparer_context.new_page()
                preparer_requests = []
                preparer.on("request", lambda request: preparer_requests.append(request.url))
                preparer.goto(preparer_source.as_uri())
                preparer.locator("#planning-preparer > summary").click()
                with preparer.expect_download() as pending:
                    preparer.locator("#planning-download").click()
                prepared_default = public / "browser-prepared-input-default.json"
                pending.value.save_as(prepared_default)
                expected_default = fresh_mission()
                expected_default["construction"]["enabled"] = False
                assert json.loads(prepared_default.read_text()) == expected_default
                assert preparer.locator('input[type="password"]').count() == 0
                preparer.locator("#planning-construction").check()
                with preparer.expect_download() as pending:
                    preparer.locator("#planning-download").click()
                prepared_optin = public / "browser-prepared-input-optin.json"
                pending.value.save_as(prepared_optin)
                payload_raw = prepared_optin.read_bytes()
                payload = json.loads(payload_raw)
                assert payload == fresh_mission()
                assert all(not url.startswith(("http:", "https:")) for url in preparer_requests)
                preparer_context.close()

                def fresh_page(width=1440, height=1000, language="en"):
                    context = browser.new_context(viewport={"width": width, "height": height}, accept_downloads=True)
                    context.route(
                        "**/*",
                        lambda route: (
                            route.continue_() if route.request.url.startswith(origin + "/") else route.abort()
                        ),
                    )
                    page = context.new_page()
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.on(
                        "request", lambda request: requests_seen.append({"method": request.method, "url": request.url})
                    )
                    page.goto(origin + ("/?lang=fr" if language == "fr" else "/"))
                    page.keyboard.press("Tab")
                    expect(page.locator(".skip")).to_be_focused()
                    page.keyboard.press("Enter")
                    expect(page.locator("#mission")).to_be_focused()
                    page.locator("#token").fill(token)
                    page.locator("#connect").click()
                    expect(page.locator("#connection")).to_have_text("Connecté" if language == "fr" else "Connected")
                    expect(page.locator("#token")).to_have_value("")
                    assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
                    return context, page

                context, page = fresh_page(language="fr")
                expect(page.locator("html")).to_have_attribute("lang", "fr")
                expect(page.locator(".consent")).to_contain_text("J’autorise cette mission")
                page.locator("details:has(#input) > summary").click()
                before_preflight = control.get("/api/strategy-executor/status").json()["request_count"]
                page.locator("#input").fill('{"initial": {}}')
                page.locator("#prepare").click()
                expect(page.locator("#error")).to_contain_text("objet JSON")
                assert control.get("/api/strategy-executor/status").json()["request_count"] == before_preflight
                page.locator("#input-file").set_input_files(
                    {
                        "name": "planning-mission-input.json",
                        "mimeType": "application/json",
                        "buffer": payload_raw,
                    }
                )
                expect(page.locator("#input-feedback")).to_contain_text("préliminaires du format réussies")
                page.locator("#prepare").click()
                expect(page.locator("#approved-input")).to_contain_text('"J7"')
                expect(page.locator("#scope")).to_contain_text("Plafond du travail d’amélioration")
                assert json.loads(page.locator("#approved-input").inner_text()) == payload
                page.locator("#language").click()
                expect(page.locator("#approve")).to_be_disabled()
                expect(page.locator("#mission-select")).not_to_have_value("")
                plan_id = page.locator("#mission-select").input_value()
                approved_input = page.locator("#approved-input").inner_text()
                # Editing future work must not alter the immutable approval snapshot.
                page.locator("#input").fill('{"different": "future input"}')
                assert page.locator("#approved-input").inner_text() == approved_input
                page.locator("#consent").check()
                page.locator("#approve").click()
                # Close while the request is active, then reconnect through a new browser context.
                for _ in range(200):
                    status = control.get("/api/strategy-executor/status").json()
                    if status["active_after_browser_close"]:
                        break
                    page.wait_for_timeout(25)
                assert status["active_after_browser_close"]
                context.close()
                context, page = fresh_page(language="fr")
                expect(page.locator("#mission-select")).to_have_value(plan_id)
                expect(page.locator("#approve")).to_be_disabled()
                for _ in range(500):
                    status = control.get("/api/strategy-executor/status").json()
                    plan = status["plans"][plan_id]
                    if plan["state"] != "running":
                        break
                    page.wait_for_timeout(100)
                assert plan["state"] == "completed", plan["state"]
                page.locator("#review").click()
                expect(page.locator(".schedule:not(.summary-table)")).to_have_count(3)
                expect(page.locator("#status")).to_contain_text("État de la mission")
                expect(page.locator("#results")).to_contain_text("Réparer le même projet")
                expect(page.locator("#background")).to_contain_text("aucune demande active")
                expect(page.locator("#keep")).to_be_enabled()
                assert status["spent"]["native_calls"] == 6
                phases = plan["outcome"]["result"]["phases"]
                assert plan["input"] == payload
                assert phases[0]["task"] == payload["initial"]
                assert len(phases[0]["task"]["jobs"]) == 7
                assert phases[1]["task"]["jobs"][2]["duration"] == 4
                assert phases[2]["baseline_source"]["receipt_hash"] == phases[1]["receipt_hash"]
                previous = {row["id"]: row for row in phases[1]["result"]["schedule"]}
                repair_task = phases[2]["task"]
                jobs = {row["id"]: row for row in repair_task["jobs"]}
                conflict_slots = [
                    slot
                    for slot, capacity in enumerate(repair_task["capacity"])
                    if sum(jobs[jid]["crew"] for jid, row in previous.items() if row["start"] <= slot < row["end"])
                    > capacity
                ]
                assert conflict_slots and phases[2]["result"]["movement"] > 0
                repaired = {row["id"]: row for row in phases[2]["result"]["schedule"]}
                assert all(repaired[jid]["start"] == start for jid, start in repair_task["locked"].items())
                assert phases[2]["result"]["movement"] == sum(
                    abs(repaired[jid]["start"] - previous[jid]["start"]) for jid in jobs
                )
                assert all(
                    sum(jobs[jid]["crew"] for jid, row in repaired.items() if row["start"] <= slot < row["end"])
                    <= capacity
                    for slot, capacity in enumerate(repair_task["capacity"])
                )
                assert len(plan["partial_receipts"]) == 3
                assert not status["active_after_browser_close"]
                assert [x["receipt_hash"] for x in plan["partial_receipts"]] == [
                    x["receipt_hash"] for x in plan["outcome"]["result"]["phases"]
                ]
                with page.expect_download() as event:
                    page.locator("#keep").click()
                download = event.value
                keep_path = public / "browser-kept-methods.json"
                download.save_as(keep_path)
                kept = json.loads(keep_path.read_text())
                assert kept["proof"] == kept["authority"] == []
                with page.expect_download() as event:
                    page.locator("#export").click()
                export_path = public / "browser-mission-export.json"
                event.value.save_as(export_path)
                exported = json.loads(export_path.read_text())
                assert exported["body"]["plan"]["outcome_hash"] == plan["outcome_hash"]
                assert exported["body"]["production_authority"] is False
                assert token not in export_path.read_text() and str(journal.root) not in export_path.read_text()
                with page.expect_download() as event:
                    page.locator("#report").click()
                report_path = public / "browser-readable-report-fr.txt"
                event.value.save_as(report_path)
                report_text = report_path.read_text()
                assert plan["source_hash"] in report_text and plan["outcome_hash"] in report_text
                assert all(phase["receipt_hash"] in report_text for phase in phases)
                assert "Rapport de mission" in report_text and "restent inconnus" in report_text
                assert "Vérification du résultat par l’exécuteur : réussie" in report_text
                assert "ALLOCATION" in report_text and "ce n’est pas une mesure CPU" in report_text
                assert '"service_work"' in report_text and '"improvement_work"' in report_text
                assert token not in report_text and str(journal.root) not in report_text
                page.locator("#language").click()
                expect(page.locator("#scope")).to_contain_text("Improvement work cap")
                page.screenshot(path=str(public / "browser-desktop.png"), full_page=True)
                page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute("lang", "fr")
                expect(page.locator("#prepare")).to_have_text("Démarrer")
                # A narrow screen retains navigable controls, output and history.
                page.set_viewport_size({"width": 390, "height": 844})
                page.screenshot(path=str(public / "browser-mobile.png"), full_page=True)
                # Keep geometry-only failure evidence before the blocking assertion.
                # Never serialize element text, input values, URLs or credentials.
                overflow = page.evaluate(
                    """() => {
                        const limit = 30;
                        const outside = [];
                        let count = 0;
                        for (const element of document.querySelectorAll('body *')) {
                            const box = element.getBoundingClientRect();
                            if (box.width <= 0 || box.height <= 0 ||
                                (box.right <= innerWidth + 0.5 && box.left >= -0.5)) continue;
                            count++;
                            if (outside.length >= limit) continue;
                            outside.push({
                                tag: element.tagName.slice(0, 40),
                                id: element.id.slice(0, 100),
                                class: typeof element.className === 'string' ? element.className.slice(0, 200) : '',
                                width: Math.round(box.width * 100) / 100,
                                left: Math.round(box.left * 100) / 100,
                                right: Math.round(box.right * 100) / 100,
                                scroll_width: element.scrollWidth,
                                client_width: element.clientWidth
                            });
                        }
                        return {
                            schema: 'strategy-browser-layout-observation/v1',
                            viewport_width: innerWidth,
                            viewport_height: innerHeight,
                            document_scroll_width: document.documentElement.scrollWidth,
                            document_client_width: document.documentElement.clientWidth,
                            overflow_element_count: count,
                            overflow_elements: outside
                        };
                    }"""
                )
                (public / "browser-mobile-layout.json").write_text(json.dumps(overflow, indent=2) + "\n")
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.locator("#language").click()
                page.locator("#pause").click()
                expect(page.locator("#pause")).to_have_text("Resume")
                expect(page.locator("#prepare")).to_be_disabled()
                page.locator("#pause").click()
                expect(page.locator("#pause")).to_have_text("Pause")
                page.locator("#stop").click()
                expect(page.locator("#stop")).to_be_disabled()
                expect(page.locator("#prepare")).to_be_disabled()
                assert control.post("/api/strategy-executor/control", json={"state": "ready"}).status_code == 409
                assert control.get("/api/strategy-executor/status").json()["spent"]["native_calls"] == 6
                assert journal.verify()["valid"] is True
                assert not page_errors, page_errors
                assert all(token not in x["url"] and x["url"].startswith(origin + "/") for x in requests_seen)
                result = {
                    "schema": "strategy-engineering-browser-acceptance/v1",
                    "actual_browser": True,
                    "browser_engine": "chromium",
                    "served_origin": origin,
                    "plan_id": plan_id,
                    "export_sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
                    "checks": {
                        "exact_browser_approval": True,
                        "real_fixed_executor": True,
                        "tab_closed_active": True,
                        "reconnect_same_mission": True,
                        "three_checked_partials": True,
                        "keep_export_downloads": True,
                        "no_token_storage_or_export": True,
                        "cross_origin_refused": True,
                        "pause_resume_stop": True,
                        "no_duplicate_native_calls": True,
                        "mobile_layout": True,
                        "real_calendar_repair": True,
                        "fresh_distinct_graph": True,
                        "bilingual_scope_and_recovery": True,
                        "readable_report_download": True,
                        "input_preflight_no_authority": True,
                        "public_preparer_input_identity": True,
                    },
                    "passed": True,
                    "browser": browser.version,
                    "source_hash": plan["source_hash"],
                    "outcome_hash": plan["outcome_hash"],
                    "actual_executor": "public Alpha1.42 Journal/ActionGateway plus fixed reviewed Node/Python/native methods",
                    "tab_closed_during_active_request": True,
                    "new_context_recovered_same_mission": True,
                    "native_calls": 6,
                    "public_preparer_source_sha256": hashlib.sha256(preparer_source.read_bytes()).hexdigest(),
                    "public_preparer_scope": "exact generated source HTML opened locally; public Pages is separately qualified",
                    "prepared_input_sha256": hashlib.sha256(payload_raw).hexdigest(),
                    "construction_opt_in": {
                        "public_default": False,
                        "explicit_browser_checkbox": True,
                        "only_changed_setting": "construction.enabled",
                        "approved_input_matches_actual_download": True,
                    },
                    "input_sha256": hashlib.sha256(
                        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
                    ).hexdigest(),
                    "input_task_id": payload["initial"]["id"],
                    "phase_makespans": [phase["result"]["makespan"] for phase in phases],
                    "costs": plan["outcome"]["costs"],
                    "repair_consequence": plan["outcome"]["result"]["repair_usefulness"]["consequence"],
                    "unchanged_baseline_invalid_calendar_slots": conflict_slots,
                    "committed_prefix_preserved": True,
                    "phase_receipts": [x["receipt_hash"] for x in plan["partial_receipts"]],
                    "source_changes_or_mock_browser": False,
                    "wall_seconds": time.perf_counter() - started,
                    "requests": requests_seen,
                    "human_and_monetary_cost": None,
                    "downloads": {
                        x.name: hashlib.sha256(x.read_bytes()).hexdigest()
                        for x in (keep_path, export_path, report_path, prepared_default, prepared_optin)
                    },
                }
                (public / "browser-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
                context.close()
                browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
