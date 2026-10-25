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

                def fresh_page(width=1440, height=1000):
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
                    page.goto(origin)
                    page.locator("#token").fill(token)
                    page.locator("#connect").click()
                    expect(page.locator("#connection")).to_have_text("Connected")
                    expect(page.locator("#token")).to_have_value("")
                    assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
                    return context, page

                context, page = fresh_page()
                page.locator("#prepare").click()
                expect(page.locator("#approved-input")).to_contain_text('"J2"')
                expect(page.locator("#approve")).to_be_disabled()
                expect(page.locator("#mission-select")).not_to_have_value("")
                plan_id = page.locator("#mission-select").input_value()
                approved_input = page.locator("#approved-input").inner_text()
                # Editing future work must not alter the immutable approval snapshot.
                page.locator("details:has(#input) > summary").click()
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
                context, page = fresh_page()
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
                expect(page.locator(".schedule")).to_have_count(3)
                expect(page.locator("#keep")).to_be_enabled()
                assert status["spent"]["native_calls"] == 6
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
                page.screenshot(path=str(public / "browser-desktop.png"), full_page=True)
                page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute("lang", "fr")
                expect(page.locator("#prepare")).to_have_text("Démarrer")
                # A narrow screen retains navigable controls, output and history.
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                page.screenshot(path=str(public / "browser-mobile.png"), full_page=True)
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
                    },
                    "passed": True,
                    "browser": browser.version,
                    "source_hash": plan["source_hash"],
                    "outcome_hash": plan["outcome_hash"],
                    "actual_executor": "public Alpha1.42 Journal/ActionGateway plus fixed reviewed Node/Python/native methods",
                    "tab_closed_during_active_request": True,
                    "new_context_recovered_same_mission": True,
                    "native_calls": 6,
                    "phase_receipts": [x["receipt_hash"] for x in plan["partial_receipts"]],
                    "source_changes_or_mock_browser": False,
                    "wall_seconds": time.perf_counter() - started,
                    "requests": requests_seen,
                    "human_and_monetary_cost": None,
                    "downloads": {x.name: hashlib.sha256(x.read_bytes()).hexdigest() for x in (keep_path, export_path)},
                }
                (public / "browser-acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
                context.close()
                browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
