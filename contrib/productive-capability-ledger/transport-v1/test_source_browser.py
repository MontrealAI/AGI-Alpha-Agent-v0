# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.metadata
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import shutil
import socket
import sys
import threading
import time
import zipfile
from typing import Any

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from playwright.sync_api import expect, sync_playwright
import uvicorn


def test_candidate_source_browser_approval_download_and_completed_reconnect(tmp_path: Path) -> None:
    root = Path(os.environ["SOURCE_ASSURANCE_CHECKOUT"]).resolve()
    commit = os.environ["SOURCE_ASSURANCE_COMMIT"]
    assert re.fullmatch(r"[0-9a-f]{40}", commit)
    assert importlib.metadata.version("alpha-factory-v1") == "1.42.0"
    from alpha_factory_v1.core.runtime.store import Journal

    candidate = root / "contrib/productive-capability-ledger/transport-v1"
    spec = importlib.util.spec_from_file_location("source_browser_candidate", candidate / "serve_candidate.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    registry = tmp_path / "public-source-scopes.json"
    registry.write_text(
        json.dumps(
            {
                "schema": "alpha-source-assurance-candidate-profile/v1",
                "maxSeconds": 20,
                "scopes": {"public-guide": {"manifestPath": "docs/try/sources.json", "sourceRef": commit}},
            }
        )
    )
    node, git = shutil.which("node"), shutil.which("git")
    assert node and git
    journal = Journal.initialize(tmp_path / "ephemeral-browser-fixture")
    token = (journal.root / "api.token").read_text().strip()
    app = module.create_candidate_app(journal, registry, node=Path(node), git=Path(git), python=Path(sys.executable))
    worker = app.state.source_assurance_worker
    now = datetime.now(timezone.utc)

    def iso(value: datetime) -> str:
        return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    payload = worker.prepare_input(
        "public-guide", "source-browser-fixture", created_at=iso(now), expires_at=iso(now + timedelta(minutes=10))
    )
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, access_log=False, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    evidence = Path(os.environ.get("SOURCE_ASSURANCE_EVIDENCE_DIR", tmp_path / "public-evidence"))
    evidence.mkdir(parents=True, exist_ok=True)
    page_errors: list[str] = []
    seen_urls: list[str] = []
    started = time.monotonic()
    try:
        with httpx.Client(
            base_url=origin, headers={"Authorization": "Bearer " + token}, timeout=90, trust_env=False
        ) as client:
            for _ in range(200):
                if server.started:
                    break
                time.sleep(0.025)
            assert server.started
            assert (
                client.get("/api/strategy-executor/status", headers={"Authorization": "Bearer invalid"}).status_code
                == 401
            )
            assert (
                client.post(
                    "/api/strategy-executor/prepare", json={}, headers={"Origin": "https://untrusted.example"}
                ).status_code
                == 403
            )
            with sync_playwright() as playwright:
                executable = os.environ.get("STRATEGY_CHROMIUM_EXECUTABLE")
                browser = playwright.chromium.launch(
                    headless=True, **({"executable_path": executable} if executable else {})
                )

                def open_page(language: str = "en") -> tuple[Any, Any]:
                    context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
                    context.route(
                        "**/*",
                        lambda route: (
                            route.continue_() if route.request.url.startswith(origin + "/") else route.abort()
                        ),
                    )
                    page = context.new_page()
                    page.on("pageerror", lambda error: page_errors.append(str(error)))
                    page.on("request", lambda request: seen_urls.append(request.url))
                    page.goto(origin + "/")
                    if language == "fr":
                        page.locator("#language").click()
                    expect(page.locator("html")).to_have_attribute("lang", language)
                    expect(page.locator("#approve")).to_be_disabled()
                    expect(page.locator("#run")).to_be_disabled()
                    page.locator("#token").fill(token)
                    page.locator("#connect").click()
                    expect(page.locator("#status")).to_have_text(
                        "Connecté à l’exécuteur local existant."
                        if language == "fr"
                        else "Connected to the existing local executor."
                    )
                    expect(page.locator("#token")).to_have_value("")
                    assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
                    return context, page

                context, page = open_page()
                expect(page.locator(".notice")).to_contain_text("operational adoption NOT APPROVED")
                before = client.get("/api/strategy-executor/status").json()
                page.locator("#request-id").fill("browser-source-request")
                page.locator("#input").fill("{}")
                page.locator("#prepare").click()
                expect(page.locator("#status")).to_have_text(
                    "Import the exact owner-prepared input and a valid request ID."
                )
                assert client.get("/api/strategy-executor/status").json()["request_count"] == before["request_count"]
                page.locator("#language").click()
                expect(page.locator("html")).to_have_attribute("lang", "fr")
                expect(page.locator("#prepare")).to_have_text("Préparer le plan exact")
                page.locator("#file").set_input_files(
                    {"name": "exact-source-input.json", "mimeType": "application/json", "buffer": payload_bytes}
                )
                expect(page.locator("#input")).to_have_value(payload_bytes.decode())
                page.locator("#prepare").click()
                expect(page.locator("#approve")).to_be_enabled()
                expect(page.locator("#plan-summary")).to_contain_text("Périmètre : public-guide")
                expect(page.locator("#plan-summary")).to_contain_text("Révision publique exacte : " + commit)
                expect(page.locator("#plan-summary")).to_contain_text("Une tentative source")
                page.get_by_text("Plan technique exact", exact=True).click()
                expect(page.locator("#plan")).to_be_visible()
                expect(page.locator("#plan")).to_contain_text('"plan_id"')
                prepared = json.loads(page.locator("#plan").inner_text())
                assert prepared["input"] == payload and prepared["state"] == "prepared"
                assert prepared["production_authority"] is False
                assert prepared["caps"] == {
                    "service_work": 1,
                    "improvement_work": 0,
                    "native_calls": 0,
                    "native_solve_seconds": 0,
                }
                binding = {key: prepared[key] for key in ("plan_id", "plan_digest")}
                assert client.post("/api/strategy-executor/run", json=binding).status_code == 409
                assert (
                    client.post("/api/strategy-executor/approve", json={**binding, "plan_digest": "0" * 64}).status_code
                    == 409
                )
                page.locator("#approve").click()
                expect(page.locator("#run")).to_be_enabled()
                expect(page.locator("#status")).to_have_text(
                    "Plan exact approuvé. Vous pouvez exécuter sa mission fixe."
                )
                page.locator("#run").click()
                expect(page.locator("#history article p")).to_contain_text("completed", timeout=90_000)
                expect(page.locator("#run")).to_be_disabled()
                completed_status = client.get("/api/strategy-executor/status").json()
                completed = completed_status["plans"][prepared["plan_id"]]
                outcome = completed["outcome"]
                assert completed["state"] == "completed" and outcome["verified"] is True
                result = outcome["result"]
                assert result["runId"] == payload["plan"]["runId"] and result["sourceRef"] == commit
                assert result["operationalAdoption"] == "NOT APPROVED" and result["customerAcceptance"] == "unknown"
                assert result["independentAcceptance"]["accepted"] is True
                with page.expect_download() as pending:
                    page.get_by_role("button", name="Télécharger le résultat ZIP vérifié", exact=True).click()
                archive_path = evidence / "source-customer-result.zip"
                pending.value.save_as(archive_path)
                raw = archive_path.read_bytes()
                download = result["download"]
                assert len(raw) == download["bytes"] and hashlib.sha256(raw).hexdigest() == download["sha256"]
                assert raw == base64.b64decode(download["base64"], validate=True)
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    assert archive.testzip() is None
                    assert set(archive.namelist()) == {*module.worker_module.PAYLOADS, "independent-acceptance.json"}
                    assert json.loads(archive.read("plan.json")) == payload["plan"]
                    assert json.loads(archive.read("independent-acceptance.json")) == result["independentAcceptance"]
                    assert "committed source identities checked" in archive.read("report.md").decode()
                    member_hashes = {
                        name: hashlib.sha256(archive.read(name)).hexdigest() for name in archive.namelist()
                    }
                with page.expect_download() as pending:
                    page.get_by_role("button", name="Exporter l’historique signé", exact=True).click()
                export_path = evidence / "source-signed-history.json"
                pending.value.save_as(export_path)
                exported = json.loads(export_path.read_bytes())
                assert exported["body"]["plan"] == completed
                assert exported["body"]["production_authority"] is False
                canonical = json.dumps(
                    exported["body"], sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode()
                assert hashlib.sha256(canonical).hexdigest() == exported["sha256"]
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(exported["public_key"])).verify(
                    base64.b64decode(exported["signature"], validate=True), bytes.fromhex(exported["sha256"])
                )
                assert token not in export_path.read_text() and str(journal.root) not in export_path.read_text()
                assert page.evaluate(
                    """async () => {
                        const {checkedDownload} = await import('/strategy.js');
                        try { await checkedDownload({filename:'bad.zip',mime:'application/zip',bytes:1,
                            sha256:'0'.repeat(64),base64:'eA=='}); return false; }
                        catch (error) { return error.message === 'DOWNLOAD_HASH'; }
                    }"""
                )
                source_directory = worker.output_root / payload["plan"]["runId"]
                reservations = {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in source_directory.glob("reservation-*.json")
                }
                assert len(reservations) == 1
                context.close()
                context, page = open_page()
                expect(page.locator("#history article p")).to_have_text(prepared["plan_id"] + " · completed")
                expect(page.get_by_role("button", name="Download verified result ZIP", exact=True)).to_be_enabled()
                page.get_by_role("button", name="Inspect plan", exact=True).click()
                expect(page.locator("#approve")).to_be_disabled()
                expect(page.locator("#run")).to_be_disabled()
                expect(page.locator("#plan-summary")).to_contain_text("Scope: public-guide")
                expect(page.locator("#plan-summary")).to_contain_text("Exact public commit: " + commit)
                page.get_by_text("Exact technical plan", exact=True).click()
                expect(page.locator("#plan")).to_be_visible()
                expect(page.locator("#plan")).to_contain_text('"outcome_hash"')
                assert json.loads(page.locator("#plan").inner_text())["outcome_hash"] == completed["outcome_hash"]
                duplicate = client.post("/api/strategy-executor/run", json=binding)
                assert duplicate.status_code == 200 and duplicate.json()["outcome_hash"] == completed["outcome_hash"]
                final = client.get("/api/strategy-executor/status").json()
                assert final["spent"] == completed_status["spent"] and final["request_count"] == 1
                assert final["spent"]["service_work"] == 1 and final["spent"]["improvement_work"] == 0
                assert reservations == {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in source_directory.glob("reservation-*.json")
                }
                page.locator("#language").click()
                expect(
                    page.get_by_role("button", name="Télécharger le résultat ZIP vérifié", exact=True)
                ).to_be_enabled()
                page.set_viewport_size({"width": 390, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert journal.verify()["valid"] is True and not page_errors
                assert all(url.startswith(origin + "/") and token not in url for url in seen_urls)
                record = {
                    "schema": "alpha-source-candidate-browser-acceptance/v1",
                    "passed": True,
                    "actualBrowser": "Chromium " + browser.version,
                    "runtime": "Public Alpha 1.42.0 in ephemeral isolated fixture",
                    "executedSource": commit,
                    "planId": prepared["plan_id"],
                    "sourceHash": prepared["source_hash"],
                    "outcomeHash": completed["outcome_hash"],
                    "customerZipSha256": hashlib.sha256(raw).hexdigest(),
                    "customerZipMembers": member_hashes,
                    "signedHistorySha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
                    "checks": {
                        "bilingual": True,
                        "exactApproval": True,
                        "realFixedWorker": True,
                        "independentAcceptance": True,
                        "browserHashCheck": True,
                        "signedExport": True,
                        "closureAfterCompletion": True,
                        "sameMissionReconnect": True,
                        "duplicateDispatchPrevented": True,
                        "singleSourceReservation": True,
                        "mobileLayout": True,
                    },
                    "approvedOperator": "NOT RUN",
                    "operationalAdoption": "NOT APPROVED",
                    "unattendedRecovery": "NOT QUALIFIED; completed-mission reconnect only",
                    "tabClosedDuringActiveWork": False,
                    "commercialAcceptance": "unknown",
                    "fullyLoadedCurrencyCost": None,
                    "wallSeconds": time.monotonic() - started,
                }
                (evidence / "source-browser-acceptance.json").write_text(json.dumps(record, indent=2) + "\n")
                context.close()
                browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
