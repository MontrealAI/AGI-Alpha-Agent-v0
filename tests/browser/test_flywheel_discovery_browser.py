# SPDX-License-Identifier: Apache-2.0
"""Exercise the bounded planner without provisioning any operating authority."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
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
                assert page.locator("#discovery-needs").input_value() == ""
                assert page.locator("#discovery-existing").input_value() == ""
                assert page.locator("#discovery-gap").input_value() == ""
                assert page.locator("#discovery-why").input_value() == ""
                assert page.evaluate(
                    "document.querySelector('#discovery').compareDocumentPosition(document.querySelector('#explore')) & Node.DOCUMENT_POSITION_FOLLOWING"
                )
                page.locator("#explore-button").focus()
                page.keyboard.press("Enter")
                expect(page.locator("#discovery-needs")).to_be_focused()
                expect(page.locator("#results")).to_be_hidden()
                assert page.locator("#discovery-needs").input_value() == ""
                checks.append("discovery-first CTA opens a blank planner before optional simulation")
                page.locator("#discovery-review").click()
                expect(page.locator("#discovery-error")).to_be_visible()
                checks.append("empty useful need refused")
                page.locator("#discovery-candidate").click()
                expect(page.locator("#discovery-provenance")).to_contain_text("No new invention or observed demand")
                expect(page.locator("#discovery-candidate-sources")).to_be_visible()
                assert page.locator("#discovery-candidate-sources a").count() == 3
                expect(page.locator("#discovery-existing")).to_have_value(re.compile("pinned versions"))
                page.locator("#discovery-review").click()
                expect(page.locator("#discovery-status")).to_contain_text("remain unqualified")
                page.locator("#discovery-new").click()
                expect(page.locator("#discovery-candidate-sources")).to_be_hidden()
                assert page.locator("#discovery-needs").input_value() == ""
                checks.append("optional sourced candidate remains a hypothesis; blank exploration remains available")
                page.locator("#discovery-example").click()
                expect(page.locator("#discovery-provenance")).to_contain_text("supplied by its authors")
                expect(page.locator("#discovery-completeness")).to_contain_text("planning fields are populated")
                expect(page.locator("#discovery-gap")).to_have_value(re.compile("No unresolved advantage"))
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
                with page.expect_download() as first_download:
                    page.locator("#discovery-export").click()
                first_path = root / "first-project.json"
                first_download.value.save_as(first_path)
                first = json.loads(first_path.read_text())
                assert first["authority"] == "none" and first["opportunities"][0]["authority"] == "none"
                assert first["opportunities"][0]["state"] == "hypothesis"
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
                checks.append("recorded lineage exports exact evidence and no inherited authority")
                candidate = evidence["blue_sky_candidate"]
                experiment = candidate["experiment"]
                assert len(experiment["runs"]) == 76
                expect(page.locator("#discovery-candidate-recorded")).to_be_visible()
                expect(page.locator("#candidate-construction-count")).to_contain_text("8 additional recorded report-write actions")
                assert page.locator("#candidate-recorded-results tbody tr").count() == 4
                expected_writes = {"schema-only": 8, "full-fresh-contract": 63, "identity-reuse": 21, "ordinary-same-content-library": 21}
                for index, (arm, result) in enumerate(experiment["summary"].items()):
                    actual = page.locator("#candidate-recorded-results tbody tr").nth(index).locator("td").all_text_contents()
                    assert int(actual[2]) == expected_writes[arm]
                    assert actual[1] == f"{result['accepted']} / 19"
                expect(page.locator("#candidate-artifact-rows")).to_contain_text("ticket-0")
                expect(page.locator("#candidate-artifact-rows")).to_contain_text("6047")
                assert re.fullmatch(r"[a-f0-9]{64}", page.locator("#candidate-artifact-sha").text_content())
                emitted = json.loads(page.locator("#candidate-artifact-json").text_content())
                assert emitted == {"rows": [{"id": "ticket-0", "milliseconds": 1007}, {"id": "ticket-1", "milliseconds": 2029}, {"id": "ticket-2", "milliseconds": 3011}], "total_milliseconds": 6047}
                counter_index = next(index for index, run in enumerate(experiment["runs"]) if run["arm"] == "identity-reuse" and run["mission"] == "hidden-third-only")
                page.locator("#candidate-recorded-run").select_option(str(counter_index))
                expect(page.locator("#candidate-run-status")).to_contain_text("rejected")
                expect(page.locator("#candidate-artifact-title")).to_contain_text("rejected")
                expect(page.locator("#candidate-counterexample")).to_contain_text("Two probes do not establish a generic semantic guarantee")
                expect(page.locator("#candidate-recorded-decision")).to_contain_text("STOP")
                expect(page.locator("#candidate-recorded-witness")).to_contain_text("paused-uncertain")
                checks.append("actual 76-episode candidate comparison, report artifact, counterexample and justified stop are inspectable")
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
