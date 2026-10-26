# SPDX-License-Identifier: Apache-2.0
"""Actual Chromium over a finite disposable test journal, never an operator home."""

from __future__ import annotations

import base64
import io
import json
import os
import socket
import threading
import time
import zipfile
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from contrib.upgrade_decision.core import sha
from contrib.upgrade_decision.worker import create_app

pytest_plugins = ["contrib.upgrade_decision.test_transport"]


@pytest.mark.e2e
def test_actual_chromium_native_packet_download_reconnect_language_and_mobile(rig: Any, tmp_path: Path) -> None:
    worker, journal, policy, _, _ = rig
    app = create_app(journal, worker, policy)
    with socket.socket() as available:
        available.bind(("127.0.0.1", 0))
        port = available.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error", access_log=False))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    binary = os.environ.get("ALPHA_UPGRADE_CHROMIUM")
    token = (journal.root / "api.token").read_text().strip()
    checks = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=binary)
            page = browser.new_page(viewport={"width": 1280, "height": 960}, accept_downloads=True)
            page.goto(f"http://127.0.0.1:{port}/")
            page.locator("#case option").nth(1).wait_for(state="attached")
            assert page.locator("#case").input_value() == "native-component-refresh-development"
            assert page.locator("#prepare").is_disabled()
            checks.append("known public choice; no automatic execution")
            page.locator("#language").click()
            assert page.locator("h1").inner_text().startswith("Examinez")
            assert "Dépendances natives" in page.locator("#case option").first.inner_text()
            page.locator("#token").fill(token)
            page.locator("#connect").click()
            page.locator("#prepare").wait_for(state="visible")
            page.locator("#prepare").click()
            page.locator("#approve").wait_for(state="visible")
            assert "60" in page.locator("#plan-summary").inner_text()
            assert page.locator("#run").is_disabled()
            page.locator("#approve").click()
            page.locator("#run").click()
            download_button = page.get_by_role("button", name="Télécharger le résultat ZIP vérifié")
            download_button.wait_for(timeout=15000)
            with page.expect_download() as caught:
                download_button.click()
            download = caught.value
            raw = Path(download.path()).read_bytes()
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                record = json.loads(archive.read("decision-record.json"))
                assert record["nextAction"] == "ADVANCE_COMPONENT_KEEP_LOCK"
                assert len([n for n in archive.namelist() if n.startswith("research/")]) == 28
                original = json.loads(archive.read("research/artifact-manifest.json"))
                assert all(sha(archive.read("research/" + row["path"])) == row["sha256"] for row in original["files"])
                report = tmp_path / "report.html"
                report.write_bytes(archive.read("report.html"))
                hashes = json.loads(archive.read("checksums.json"))
                assert all(sha(archive.read(n)) == h for n, h in hashes.items())
            checks.append("actual verified ZIP; 28 unchanged writer files; useful native decision")
            with page.expect_download() as caught_export:
                page.get_by_role("button", name="Exporter l’historique signé").click()
            exported = json.loads(Path(caught_export.value.path()).read_text())
            assert token not in json.dumps(exported) and exported["body"]["production_authority"] is False
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

            Ed25519PublicKey.from_public_bytes(bytes.fromhex(exported["public_key"])).verify(
                base64.b64decode(exported["signature"]), bytes.fromhex(exported["sha256"])
            )
            checks.append("actual signed history export; no token in export")
            page.locator("#disconnect").click()
            page.locator("#token").fill(token)
            page.locator("#connect").click()
            download_button.wait_for()
            assert app.state.strategy_executor.status()["spent"]["service_work"] == 1
            checks.append("completed reconnect without repeated work")
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.screenshot(path=str(tmp_path / "offering-mobile.png"), full_page=True)
            report_page = browser.new_page(viewport={"width": 1280, "height": 960})
            report_page.goto(report.as_uri())
            assert "Keep the current lock" in report_page.locator("section[lang=en] .action").inner_text()
            report_page.screenshot(path=str(tmp_path / "report-desktop.png"), full_page=True)
            report_page.locator("#lang").click()
            assert "Conservez le verrou" in report_page.locator("section[lang=fr] .action").inner_text()
            report_page.set_viewport_size({"width": 390, "height": 844})
            assert report_page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            report_page.screenshot(path=str(tmp_path / "report-mobile-fr.png"), full_page=True)
            checks.append("EN/FR guidance and downloaded report; desktop/mobile no horizontal overflow")
            page.locator("#case").select_option("native-component-refresh-development")
            page.locator("#prepare").click()
            expect(page.locator("#approve")).to_be_disabled()
            assert app.state.strategy_executor.status()["spent"]["service_work"] == 1
            assert len(app.state.strategy_executor.status()["plans"]) == 1
            checks.append("same underlying selection reuses the completed plan and does not create another job")
            page.locator("#case").select_option("native-component-refresh-development")
            page.locator("details").first.evaluate("element => element.open = true")
            page.locator("#request-id").fill("browser-closure-repeat-evaluation")
            page.locator("#prepare").click()
            page.locator("#approve").click()
            expect(page.locator("#run")).to_be_enabled()
            page.evaluate("() => document.getElementById('run').click()")
            deadline = time.monotonic() + 2
            observed_running = False
            while time.monotonic() < deadline:
                active = app.state.strategy_executor.status()
                if any(plan["state"] == "running" for plan in active["plans"].values()):
                    observed_running = True
                    break
                time.sleep(0.002)
            assert observed_running
            page.close()
            page = browser.new_page(viewport={"width": 1280, "height": 960})
            page.goto(f"http://127.0.0.1:{port}/")
            page.locator("#token").fill(token)
            page.locator("#connect").click()
            page.get_by_role("button", name="Download verified result ZIP").nth(1).wait_for(timeout=15000)
            assert app.state.strategy_executor.status()["spent"]["service_work"] == 2
            checks.append(
                "actual active browser closure and completed reconnect; two repeated engineering evaluations, not two distinct customer jobs"
            )
            page.locator("#stop").click()
            expect(page.locator("#executor-state")).to_contain_text("stopped")
            assert page.locator("#resume").is_disabled()
            checks.append("permanent STOP in this finite test envelope")
            receipt = {
                "scope": "Finite disposable engineering fixture; not approved operator, source adoption, installed public wheel or live deployment.",
                "checks": checks,
                "chromium": browser.version,
                "downloadSha256": sha(raw),
                "downloadBytes": len(raw),
                "customerJobs": 0,
            }
            (tmp_path / "browser-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "receipt": str(tmp_path / "browser-receipt.json"),
                        "screenshots": str(tmp_path),
                        "checks": len(checks),
                    }
                )
            )
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        assert not thread.is_alive()
