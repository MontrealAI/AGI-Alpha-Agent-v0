# SPDX-License-Identifier: Apache-2.0
"""Exercise the bounded planner without provisioning any operating authority."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

from scripts.generate_alpha_flywheel import build
from scripts.validate_alpha_flywheel import CANONICAL_SOURCES, verify_packaged

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="flywheel-discovery-browser-") as directory:
        root = Path(directory)
        for name in CANONICAL_SOURCES:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            if (ROOT / name).exists():
                shutil.copyfile(ROOT / name, destination)
            else:
                raise FileNotFoundError(name)
        build(root)
        verify_packaged(root / "docs", root)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "docs")))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        errors: list[str] = []
        checks: list[str] = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or None)
                context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                url = f"http://127.0.0.1:{server.server_port}/flywheel/"
                page.goto(url)
                expect(page.locator("#discovery-provenance")).to_contain_text("planning assumptions")
                page.locator("#discovery-review").click()
                expect(page.locator("#discovery-error")).to_be_visible()
                checks.append("empty useful need refused")
                page.locator("#discovery-example").click()
                expect(page.locator("#discovery-provenance")).to_contain_text("supplied by its authors")
                expect(page.locator("#discovery-completeness")).to_contain_text("planning fields are populated")
                page.locator("#discovery-review").click()
                expect(page.locator("#discovery-status")).to_contain_text("remain unqualified")
                checks.append("supplied ingredients explicit; populated fields remain unqualified")
                original = page.locator("#discovery-purpose").input_value()
                page.locator("#lang-fr").click()
                expect(page.locator("#discovery-title")).to_contain_text("restriction")
                assert page.locator("#discovery-purpose").input_value() == original
                page.locator("#discovery-example").click()
                assert page.locator("#discovery-purpose").input_value().startswith("Préserver")
                page.locator("#lang-en").click()
                checks.append("EN/FR labels preserve user text; supplied examples localize explicitly")
                page.locator("#discovery-purpose").fill(
                    '<img src=x onerror="window.injected=true"> original requirements remain'
                )
                expect(page.locator("#discovery-witness")).to_contain_text("original requirements remain")
                assert page.locator("#discovery-witness img").count() == 0
                assert page.evaluate("window.injected===undefined")
                checks.append("untrusted user content rendered as text")
                planning_values = {
                    name: page.locator("#discovery-" + name).input_value() for name in ("existing", "gap", "why")
                }
                with page.expect_download() as first_download:
                    page.locator("#discovery-export").click()
                first_path = root / "first-project.json"
                first_download.value.save_as(first_path)
                first = json.loads(first_path.read_text())
                assert first["authority"] == "none" and first["opportunities"][0]["authority"] == "none"
                assert first["opportunities"][0]["state"] == "hypothesis"
                assert planning_values["existing"] in first["opportunities"][0]["currentApproach"]
                assert planning_values["gap"] in first["opportunities"][0]["target"]
                assert planning_values["why"] in first["opportunities"][0]["evidence"]
                with page.expect_download() as second_download:
                    page.locator("#discovery-export").click()
                second_path = root / "second-project.json"
                second_download.value.save_as(second_path)
                assert first_path.read_bytes() == second_path.read_bytes()
                checks.append("duplicate exports preserve one hypothesis and exact history")
                page.locator("#discovery .discovery-editor details").nth(1).locator("summary").click()
                page.locator("#discovery-decision").select_option("stop")
                with page.expect_download() as stopped_download:
                    page.locator("#discovery-export").click()
                stopped_path = root / "stopped-project.json"
                stopped_download.value.save_as(stopped_path)
                stopped = json.loads(stopped_path.read_text())
                assert len(stopped["opportunities"]) == 2
                assert stopped["opportunities"][0] == first["opportunities"][0]
                assert "Planning decision: stop" in stopped["opportunities"][1]["budget"]
                checks.append("stop appends decision without replacing earlier hypothesis")
                page.locator("#discovery-open").set_input_files(str(first_path))
                expect(page.locator("#discovery-status")).to_contain_text("Original project history restored")
                expect(page.locator("#discovery-witness")).to_contain_text("NONE")
                with page.expect_download() as restored_download:
                    page.locator("#discovery-export").click()
                restored_path = root / "restored-project.json"
                restored_download.value.save_as(restored_path)
                assert first_path.read_bytes() == restored_path.read_bytes()
                checks.append("existing project roundtrip retains history and no authority")
                malicious = dict(first, authority="live")
                malicious_path = root / "malicious-project.json"
                malicious_path.write_text(json.dumps(malicious))
                page.locator("#discovery-open").set_input_files(str(malicious_path))
                expect(page.locator("#discovery-error")).to_be_visible()
                expect(page.locator("#discovery-witness")).to_contain_text("NONE")
                checks.append("import cannot restore operating authority")
                page.locator("#start-example").click()
                expect(page.locator("#results")).to_be_visible()
                expect(page.locator("#run-status")).to_contain_text("No model or authorized operation")
                checks.append("preserved simulator remains usable")
                page.locator("#opportunity-investigation > summary").click()
                expect(page.locator("#opportunity-case")).to_contain_text("Temporal")
                expect(page.locator("#opportunity-result")).to_contain_text("applied")
                page.locator("#opportunity-episode").select_option("different_recipient_mission")
                expect(page.locator("#opportunity-result")).to_contain_text("partially-applied")
                page.locator("#opportunity-episode").select_option("audit_unavailable")
                expect(page.locator("#opportunity-result")).to_contain_text("no-affordable-distinguishing-observation")
                page.locator("#opportunity-episode").select_option("outside_declared_model")
                expect(page.locator("#opportunity-result")).to_contain_text("observation-outside-declared-model")
                page.locator("#opportunity-candidate").select_option("shared-resilience-planning")
                expect(page.locator("#opportunity-case")).to_contain_text("do not select as flagship")
                with page.expect_download() as investigation_download:
                    page.locator("#opportunity-evidence-export").click()
                investigation_path = root / "investigation.json"
                investigation_download.value.save_as(investigation_path)
                investigation = json.loads(investigation_path.read_bytes())
                assert investigation == json.loads(
                    (ROOT / "scripts/templates/alpha-flywheel/opportunity-evidence.json").read_bytes()
                )
                assert investigation["scope"]["authority_granted"] is False
                checks.append("source-backed candidate comparison, refusal cases and exact investigation download")
                page.locator("#discovery-recorded > summary").click()
                expect(page.locator("#discovery-recorded-scope")).to_contain_text("Complete actual cost is unknown")
                expect(page.locator("#discovery-recorded-witness")).to_contain_text("NONE")
                assert page.locator("#discovery-recorded-stages tbody tr").count() == 5
                with page.expect_download() as evidence_download:
                    page.locator("#discovery-evidence-export").click()
                evidence_path = root / "recorded-evidence.json"
                evidence_download.value.save_as(evidence_path)
                evidence = json.loads(evidence_path.read_text())
                assert evidence == json.loads(
                    (ROOT / "scripts/templates/alpha-flywheel/discovery-evidence.json").read_text()
                )
                assert evidence["summary"]["actual_frontier_calls"] == 0
                assert evidence["summary"]["authority_inherited"] is False
                assert evidence["connected"]["witness"]["spec"]["schema_name"] == "flywheel-transformation-witness/v1"
                selected = evidence["discovery_selected_prototype"]
                assert selected["bundle"]["status"] == "paused-uncertain"
                assert selected["decision"]["spec"]["disposition"] == "stop"
                checks.append("recorded lineage exports exact evidence and no inherited authority")
                for language in ("en", "fr"):
                    page.locator(f"#lang-{language}").click()
                    for width in (320, 390, 1440):
                        page.set_viewport_size({"width": width, "height": 900})
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (language, width)
                checks.append("EN/FR 320/390/1440 widths have no page overflow")
                page.locator("#lang-en").click()
                page.locator("#discovery-example").click()
                page.set_viewport_size({"width": 1440, "height": 1000})
                if os.environ.get("DISCOVERY_UI_SCREENSHOT"):
                    page.locator("#discovery").screenshot(path=os.environ["DISCOVERY_UI_SCREENSHOT"])
                assert not errors, errors
                checks.append("no browser script errors")
                browser.close()
        finally:
            server.shutdown()
        print(json.dumps({"status": "PASS", "checks": checks, "count": len(checks)}, indent=2))


if __name__ == "__main__":
    main()
