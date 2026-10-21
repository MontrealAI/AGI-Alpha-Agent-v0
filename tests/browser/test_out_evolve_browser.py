# SPDX-License-Identifier: Apache-2.0
"""Real-browser acceptance of generated Out-Evolve programs, lineage and recovery."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("OUT_EVOLVE_EVIDENCE", "/tmp/out-evolve-browser-evidence"))
AXE = Path(os.environ.get("AXE_SCRIPT", str(ROOT / "tests/browser/node_modules/axe-core/axe.min.js")))


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        """Suppress ordinary local fixture traffic."""


def idle(page: Page) -> None:
    """Wait for persisted evidence and unlocked founder controls."""
    expect(page.locator("#evolve-construct")).to_be_enabled(timeout=120000)
    expect(page.locator("#evolve-form")).to_have_attribute("aria-busy", "false")


def history(page: Page) -> dict[str, Any]:
    """Read the actual visible exported event record."""
    value: dict[str, Any] = json.loads(page.locator("#evolve-history-json").text_content() or "{}")
    return value


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
            manifest = json.loads(interrupted.locator("#evolve-apparatus").input_value())
            for suffix in ("a", "b", "c"):
                name = "dust-" + suffix
                channel = dict(manifest["channels"][0], id=name)
                manifest["channels"].append(channel)
                manifest["edges"].append({"id": name + "-readout", "from": name, "to": "readout", "gain": 1})
                for original in manifest["primitives"][:2]:
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
            interrupted.reload()
            idle(interrupted)
            assert history(interrupted) == cancelled
            interrupted.locator("#evolve-resume").click()
            idle(interrupted)
            resumed = history(interrupted)
            (OUTPUT / "cancel-resume.json").write_text(json.dumps(resumed, indent=2))
            assert resumed["events"][: len(cancelled["events"])] == cancelled["events"]
            assert any(
                event["payload"].get("status") in ("qualified", "exhausted", "infeasible")
                for event in resumed["events"]
            ), resumed["events"][-1]["payload"].get("message", "No terminal construction event")
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
