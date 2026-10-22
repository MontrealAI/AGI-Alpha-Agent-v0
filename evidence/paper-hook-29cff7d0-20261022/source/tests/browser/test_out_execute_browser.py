# SPDX-License-Identifier: Apache-2.0
"""Hosted real-browser acceptance for additive finite completion and shared history."""
from __future__ import annotations

import json
import os
import shutil
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("OUT_EXECUTE_EVIDENCE", str(ROOT / "capability-evidence/out-execute-browser")))
AXE = Path(os.environ.get("AXE_SCRIPT", str(ROOT / "tests/browser/node_modules/axe-core/axe.min.js")))


def idle(page: Page) -> None:
    expect(page.locator("#evolve-form")).to_have_attribute("aria-busy", "false", timeout=120000)
    expect(page.locator("#evolve-import")).to_be_enabled(timeout=120000)
    expect(page.locator("#evolve-error")).to_be_hidden()


def history(page: Page) -> dict[str, Any]:
    return dict(json.loads(page.locator("#evolve-history-json").text_content() or "{}"))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors: list[str] = []
    requests: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            )
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            context.on("request", lambda request: requests.append(request.url))
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/docs/successor/capabilities/")
            idle(page)
            page.locator("#execute-start").click()
            idle(page)
            expect(page.locator("#execute-acceptance")).to_contain_text("Unfinished")
            page.locator("#execute-step").click()
            idle(page)
            assert history(page)["events"][-1]["payload"]["checkpoint"]["next"] == 1
            page.locator("#execute-pause").click()
            idle(page)
            paused = history(page)
            assert paused["events"][-1]["payload"]["checkpoint"]["status"] == "CANCELLED"
            page.reload()
            idle(page)
            expect(page.locator("#execute-status")).to_contain_text("CANCELLED")
            page.locator("#execute-finish").click()
            idle(page)
            expect(page.locator("#execute-acceptance")).to_contain_text("optimum accepted: 1")
            first = history(page)
            unsaved_path = OUTPUT / "unsaved-checkpoint.json"
            unsaved_path.write_text(
                json.dumps(
                    {
                        "schema": "out-execute-unsaved-recovery/v1",
                        "history": paused,
                        "checkpoint": first["events"][-1]["payload"]["checkpoint"],
                    }
                )
            )
            assert first["id"] == paused["id"]
            assert first["events"][: len(paused["events"])] == paused["events"]
            page.locator("#execute-change").click()
            page.locator("#execute-start").click()
            idle(page)
            page.locator("#execute-finish").click()
            idle(page)
            expect(page.locator("#execute-changes")).to_contain_text("outside optimization stopped")
            changed = history(page)
            result = changed["events"][-1]["payload"]["checkpoint"]["completion"]
            assert result["artifact"] == {"b": 0, "x": 1, "y": 0}
            assert result["work"]["boundaryAssignments"] == 0
            assert result["work"]["acceptanceBoundaryAssignments"] > 0
            for button in ("outside", "extend"):
                page.locator(f"#execute-{button}").click()
                page.locator("#execute-start").click()
                idle(page)
                page.locator("#execute-finish").click()
                idle(page)
            for button, asset in (("manager", "USDC"), ("jobs", "AGIALPHA"), ("fleet", None)):
                with page.expect_download() as download:
                    page.locator(f"#execute-{button}").click()
                download.value.save_as(OUTPUT / f"{button}-unsubmitted-draft.json")
                idle(page)
                draft = json.loads(page.locator("#execute-draft").text_content() or "{}")
                assert draft["targetInterface"]["asset"] == asset
                assert draft["limits"]["executionApproved"] is False
                assert draft["limits"]["spendBaseUnits"] == "0"
            with page.expect_download() as download:
                page.locator("#evolve-export-history").click()
            download.value.save_as(OUTPUT / "complete-history.json")
            with page.expect_download() as checkpoint_download:
                page.locator("#execute-export").click()
            checkpoint_download.value.save_as(OUTPUT / "saved-checkpoint.json")
            saved = history(page)
            page.reload()
            idle(page)
            expect(page.locator("#execute-acceptance")).to_contain_text("Historical")
            assert history(page) == saved
            fresh_context = browser.new_context(accept_downloads=True)
            imported = fresh_context.new_page()
            imported.on("pageerror", lambda error: errors.append(str(error)))
            imported.goto(f"http://127.0.0.1:{server.server_port}/docs/successor/capabilities/")
            idle(imported)
            imported.locator("#evolve-import").set_input_files(OUTPUT / "complete-history.json")
            idle(imported)
            expect(imported.locator("#execute-acceptance")).to_contain_text("Historical")
            assert history(imported) == saved
            imported.locator("#evolve-import").set_input_files(OUTPUT / "saved-checkpoint.json")
            idle(imported)
            assert history(imported) == saved
            fresh_context.close()
            unsaved_context = browser.new_context(accept_downloads=True)
            recovery_page = unsaved_context.new_page()
            recovery_page.on("pageerror", lambda error: errors.append(str(error)))
            recovery_page.goto(f"http://127.0.0.1:{server.server_port}/docs/successor/capabilities/")
            idle(recovery_page)
            recovery_page.locator("#evolve-import").set_input_files(unsaved_path)
            idle(recovery_page)
            expect(recovery_page.locator("#execute-acceptance")).to_contain_text("Historical")
            restored = history(recovery_page)
            assert restored["events"][: len(paused["events"])] == paused["events"]
            assert restored["events"][-1]["payload"]["checkpoint"] == first["events"][-1]["payload"]["checkpoint"]
            assert len(restored["events"]) == len(paused["events"]) + 1
            unsaved_context.close()
            page.evaluate(AXE.read_text())
            audit = page.evaluate(
                "async () => await axe.run(document, {runOnly: {type: 'tag', values: "
                "['wcag2a','wcag2aa','wcag21aa','best-practice']}})"
            )
            (OUTPUT / "accessibility.json").write_text(json.dumps(audit, indent=2))
            assert not audit["violations"]
            page.locator("#out-execute").screenshot(path=str(OUTPUT / "desktop-completion.png"))
            page.set_viewport_size({"width": 390, "height": 844})
            page.locator("#out-execute").screenshot(path=str(OUTPUT / "mobile-completion.png"))
            page.set_viewport_size({"width": 320, "height": 740})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert not errors, errors
            assert all(
                url.startswith(f"http://127.0.0.1:{server.server_port}/") or url.startswith("blob:") for url in requests
            )
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
