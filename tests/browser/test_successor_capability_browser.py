# SPDX-License-Identifier: Apache-2.0
"""Real browser acceptance for the isolated additive capability-development workspace."""

from __future__ import annotations

from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from typing import Any

from playwright.sync_api import Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("CAPABILITY_SCREENSHOTS", "/tmp/successor-capability-evidence"))
AXE = Path(os.environ.get("AXE_SCRIPT", str(ROOT / "tests/browser/node_modules/axe-core/axe.min.js")))


def audit(page: Page, label: str) -> None:
    """Fail closed on accessibility findings; retain the complete audit."""
    assert AXE.is_file(), "Install tests/browser dependencies or supply AXE_SCRIPT."
    page.evaluate(AXE.read_text())
    result = page.evaluate(
        "async () => await axe.run(document, {runOnly: {type: 'tag', "
        "values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'best-practice']}})"
    )
    (OUTPUT / f"accessibility-{label}.json").write_text(json.dumps(result, indent=2))
    assert not result["violations"], [(item["id"], item["nodes"]) for item in result["violations"]]


def capture(page: Page, label: str, selector: str | None = None) -> None:
    """Capture real browser pixels without changing the product layout."""
    expect(page.locator("#brief-form")).to_have_attribute("aria-busy", "false")
    page.evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")
    if selector:
        page.locator(selector).screenshot(path=str(OUTPUT / f"{label}.png"), animations="disabled")
    else:
        page.screenshot(path=str(OUTPUT / f"{label}.png"), full_page=True, animations="disabled")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *args: object) -> None:
        """Keep acceptance output concise."""


def history(page: Page) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(page.locator("#history-json").text_content() or "")
    return value


def ready(page: Page) -> None:
    expect(page.locator("#witness-enabled")).to_be_enabled()


def open_saved(page: Page, identity: str) -> None:
    page.locator("#saved").select_option(identity)
    page.locator("#open").click()
    expect(page.locator("#status")).to_contain_text("Saved history opened")


def freeze(page: Page) -> None:
    page.locator("#public-confirmation").check()
    page.locator("#freeze").click()
    expect(page.locator("#draft-badge")).to_contain_text("Frozen version")


def main() -> None:
    """Exercise construction, negative evidence, persistence and non-dispatch boundaries."""
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    url = base + "/docs/successor/capabilities/index.html"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "source.json").write_text(
        json.dumps(
            {
                "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                "source": json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text()),
                "trackedDiff": subprocess.check_output(["git", "diff", "HEAD", "--stat"], cwd=ROOT, text=True),
            },
            indent=2,
        )
    )
    try:
        with tempfile.TemporaryDirectory(prefix="capability-browser-") as temporary, sync_playwright() as playwright:
            executable = os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            browser = playwright.chromium.launch(executable_path=executable)
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            errors: list[str] = []
            requests: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            context.on("request", lambda request: requests.append(request.url))
            context.on("page", lambda tab: tab.on("pageerror", lambda error: errors.append(str(error))))
            page.on("dialog", lambda dialog: dialog.accept())
            page.goto(url)
            ready(page)
            page.keyboard.press("Tab")
            expect(page.locator(".skip")).to_be_focused()
            page.keyboard.press("Enter")
            assert page.url.endswith("#workspace")
            audit(page, "initial")
            capture(page, "desktop-introduction", ".hero")
            expect(page.locator("#development")).to_be_disabled()
            expect(page.locator("#heldout")).to_be_disabled()
            expect(page.locator("#freeze")).to_be_disabled()
            page.locator("#witness-enabled").check()
            freeze(page)
            initial = history(page)
            identity = initial["missionId"]
            assert initial["revision"] == 0
            page.locator("#development").click()
            expect(page.locator("#development-state")).to_contain_text("Computed PASS")
            page.locator("#heldout").click()
            expect(page.locator("#heldout-state")).to_contain_text("Computed PASS")
            original = history(page)
            assert len(original["events"]) == 3
            assert original["events"][2]["payload"]["exposure"]["status"] == "fresh-within-record-not-protected"
            page.locator("#development-report").locator("..").locator("summary").click()
            capture(page, "constructed-instrument-and-reuse", ".evidence-panel")
            audit(page, "computed-pass")
            (OUTPUT / "initial-passing-history.json").write_text(json.dumps(original, indent=2))
            with page.expect_download() as downloading:
                page.locator("#export").click()
            backup = Path(temporary) / "history.json"
            downloading.value.save_as(backup)
            assert json.loads(backup.read_text()) == original

            # Changed/invalid configuration cannot keep a current pass status or rerun old evidence.
            page.locator("#start-successor").click()
            page.locator("#experiment").fill("{bad json")
            expect(page.locator("#version-state")).to_contain_text("no current validation")
            expect(page.locator("#development")).to_be_disabled()
            page.locator("#successor-reason").fill("Exercise a deliberately invalid draft.")
            page.locator("#public-confirmation").check()
            page.locator("#freeze").click()
            expect(page.locator("#error")).to_be_visible()
            assert history(page) == original
            config = deepcopy(original["events"][0]["payload"]["specification"]["experiment"])
            config["world"]["degree"] = 3
            page.locator("#experiment").fill(json.dumps(config))
            page.locator("#brief-title").fill("A deliberately incompatible successor")
            page.locator("#successor-reason").fill(
                "Retain the failure when an unmodeled cubic interaction is introduced."
            )
            freeze(page)
            expect(page.locator("#development-state")).to_have_text("Not evaluated")
            expect(page.locator("#heldout-state")).to_have_text("Not evaluated")
            page.locator("#development").click()
            expect(page.locator("#status")).to_contain_text("Development report saved")
            page.locator("#heldout").click()
            expect(page.locator("#heldout-state")).to_contain_text("Computed FAIL")
            failed = history(page)
            assert failed["events"][:3] == original["events"]
            assert failed["events"][-1]["payload"]["report"]["verdict"] == "fail"
            assert failed["events"][-1]["payload"]["exposure"]["status"] == "previously-exposed-not-heldout"
            capture(page, "negative-successor", ".evidence-panel")
            (OUTPUT / "negative-history.json").write_text(json.dumps(failed, indent=2))
            page.reload()
            ready(page)
            open_saved(page, identity)
            assert history(page) == failed
            expect(page.locator("#heldout-state")).to_contain_text("Computed FAIL")
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 844})
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
                page.locator("#text-size").focus()
                page.keyboard.press("Space")
                expect(page.locator("#text-size")).to_have_attribute("aria-pressed", "true")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (width, "larger")
                if width == 390:
                    capture(page, "mobile-larger-text")
                    capture(page, "mobile-larger-introduction", ".hero")
                    capture(page, "mobile-larger-evidence", ".evidence-panel")
                    audit(page, "mobile-larger-text")
                page.locator("#text-size").click()
                page.evaluate("() => { document.documentElement.style.fontSize = '32px'; }")
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), (width, "200% text")
                if width == 390:
                    capture(page, "mobile-200-percent-text-evidence", ".evidence-panel")
                page.evaluate("() => { document.documentElement.style.fontSize = ''; }")
            page.set_viewport_size({"width": 1440, "height": 1000})

            # A later success retains the failed predecessor and never promotes the new draft.
            page.locator("#start-successor").click()
            page.locator("#brief-title").fill("Return to the qualified synthetic function class")
            page.locator("#experiment").fill(
                json.dumps(original["events"][0]["payload"]["specification"]["experiment"])
            )
            page.locator("#successor-reason").fill("Keep the cubic failure and explicitly restore the quadratic scope.")
            freeze(page)
            expect(page.locator("#version-state")).to_have_text("No validation yet.")
            page.locator("#development").click()
            page.locator("#heldout").click()
            expect(page.locator("#version-state")).to_contain_text("Computed PASS")
            recovered = history(page)
            assert recovered["events"][: len(failed["events"])] == failed["events"]
            expect(page.locator("#version-list > li").nth(1)).to_contain_text("Computed FAIL")
            expect(page.locator("#version-list > li").nth(2)).to_contain_text("Previously exposed")
            capture(page, "success-after-failure-history", ".history-panel")
            page.reload()
            ready(page)
            open_saved(page, identity)
            assert history(page) == recovered
            (OUTPUT / "recovered-complete-history.json").write_text(json.dumps(recovered, indent=2))

            # Fresh-origin import saves a full event history at independent storage revision zero.
            other_context = browser.new_context()
            other_context.on("request", lambda request: requests.append(request.url))
            other_context.on("page", lambda tab: tab.on("pageerror", lambda error: errors.append(str(error))))
            imported = other_context.new_page()
            imported.on("dialog", lambda dialog: dialog.accept())
            imported.goto(url)
            ready(imported)
            imported.locator("#public-confirmation").check()
            imported.locator("#import").set_input_files(backup)
            expect(imported.locator("#status")).to_contain_text("Whole history imported")
            assert history(imported) == original
            imported.reload()
            ready(imported)
            open_saved(imported, identity)
            assert history(imported) == original
            tampered = json.loads(backup.read_text())
            tampered["events"][2]["payload"]["report"]["verdict"] = "commercially-validated"
            bad_file = Path(temporary) / "tampered.json"
            bad_file.write_text(json.dumps(tampered))
            imported.locator("#public-confirmation").check()
            imported.locator("#import").set_input_files(bad_file)
            expect(imported.locator("#error")).to_be_visible()
            assert history(imported) == original

            # A passing reuse phase cannot overwrite a failed development verdict.
            mixed = other_context.new_page()
            mixed.on("dialog", lambda dialog: dialog.accept())
            mixed.goto(url)
            ready(mixed)
            mixed.locator("#witness-enabled").check()
            mixed_config = json.loads(mixed.locator("#experiment").input_value())
            mixed_config["input_count"] = 4
            mixed_config["world"]["degree"] = 3
            mixed_config["world"]["overrides"] = [
                {"mask": mask, "coefficient": 1 if mask == 11 else -1 if mask == 14 else 0} for mask in range(15)
            ]
            mixed.locator("#experiment").fill(json.dumps(mixed_config))
            freeze(mixed)
            mixed.locator("#development").click()
            expect(mixed.locator("#development-state")).to_contain_text("Computed FAIL")
            mixed.locator("#heldout").click()
            expect(mixed.locator("#heldout-state")).to_contain_text("Computed PASS")
            expect(mixed.locator("#version-state")).to_contain_text("Computed FAIL")
            capture(mixed, "development-fail-reuse-pass", ".evidence-panel")
            (OUTPUT / "mixed-development-fail.json").write_text(json.dumps(history(mixed), indent=2))
            mixed.locator("#start-successor").click()
            mixed_config["world"]["overrides"] = [
                {"mask": mask, "coefficient": 1 if mask == 7 else 0} for mask in range(15)
            ]
            mixed.locator("#experiment").fill(json.dumps(mixed_config))
            mixed.locator("#successor-reason").fill(
                "A complementary negative control fails reuse after development passes."
            )
            freeze(mixed)
            mixed.locator("#development").click()
            expect(mixed.locator("#development-state")).to_contain_text("Computed PASS")
            mixed.locator("#heldout").click()
            expect(mixed.locator("#heldout-state")).to_contain_text("Computed FAIL")
            expect(mixed.locator("#version-state")).to_contain_text("Computed FAIL")
            capture(mixed, "development-pass-reuse-fail", ".evidence-panel")
            (OUTPUT / "mixed-reuse-fail.json").write_text(json.dumps(history(mixed), indent=2))

            # Two-tab divergent successors preserve the losing candidate for recovery.
            peer = context.new_page()
            peer.on("dialog", lambda dialog: dialog.accept())
            peer.goto(url)
            ready(peer)
            open_saved(peer, identity)
            for tab, title in [(page, "First saved successor"), (peer, "Divergent successor retained for recovery")]:
                tab.locator("#start-successor").click()
                tab.locator("#brief-title").fill(title)
                tab.locator("#successor-reason").fill("Explicitly preserve this distinct development path.")
                tab.locator("#public-confirmation").check()
                tab.locator("#freeze").click()
                if tab is page:
                    expect(tab.locator("#draft-badge")).to_contain_text("Frozen version 4")
                else:
                    expect(tab.locator("#recovery")).to_be_visible()
            losing = history(peer)
            capture(peer, "conflicting-tab-recovery", "#recovery")
            expect(peer.locator("#development")).to_be_disabled()
            peer.locator("#new").click()
            expect(peer.locator("#error")).to_contain_text("protected recovery")
            assert history(peer) == losing
            with peer.expect_download() as downloading:
                peer.locator("#recovery-export").click()
            recovery = Path(temporary) / "recovery.json"
            downloading.value.save_as(recovery)
            assert json.loads(recovery.read_text()) == losing
            expect(peer.locator("#recovery")).to_be_visible()
            peer.locator("#recovery-retry").click()
            expect(peer.locator("#error")).to_contain_text("CONFLICT")
            peer.locator("#recovery-confirm").click()
            open_saved(peer, identity)
            assert history(peer) == history(page)

            # A recoverable storage outage preserves an initial frozen record and supports retry.
            offline = other_context.new_page()
            offline.on("dialog", lambda dialog: dialog.accept())
            offline.goto(url)
            ready(offline)
            offline.evaluate(
                """() => {
                window.originalTransaction = IDBDatabase.prototype.transaction;
                IDBDatabase.prototype.transaction = function(names, mode, ...rest) {
                    if (mode === 'readwrite') throw new Error('Synthetic storage outage');
                    return window.originalTransaction.call(this, names, mode, ...rest);
                };
            }"""
            )
            offline.locator("#public-confirmation").check()
            offline.locator("#freeze").click()
            expect(offline.locator("#recovery")).to_be_visible()
            preserved = history(offline)
            capture(offline, "storage-outage-recovery", "#recovery")
            offline.evaluate("() => { IDBDatabase.prototype.transaction = window.originalTransaction; }")
            offline.locator("#recovery-retry").click()
            expect(offline.locator("#status")).to_contain_text("confirmed saved")
            expect(offline.locator("#recovery")).to_be_hidden()
            assert history(offline) == preserved
            expect(offline.locator("#development")).to_be_disabled()  # proposal, not an executable invention
            audit(offline, "proposal-only")

            # A new browser process reopens IndexedDB from disk without replaying any experiment.
            profile = str(Path(temporary) / "durable-browser-profile")
            durable = playwright.chromium.launch_persistent_context(profile, executable_path=executable)
            durable.on("request", lambda request: requests.append(request.url))
            durable.on("page", lambda tab: tab.on("pageerror", lambda error: errors.append(str(error))))
            durable_page = durable.pages[0]
            durable_page.on("pageerror", lambda error: errors.append(str(error)))
            durable_page.on("dialog", lambda dialog: dialog.accept())
            durable_page.goto(url)
            ready(durable_page)
            durable_page.locator("#public-confirmation").check()
            durable_page.locator("#import").set_input_files(backup)
            expect(durable_page.locator("#status")).to_contain_text("Whole history imported")
            durable.close()
            durable = playwright.chromium.launch_persistent_context(profile, executable_path=executable)
            durable.on("request", lambda request: requests.append(request.url))
            durable.on("page", lambda tab: tab.on("pageerror", lambda error: errors.append(str(error))))
            durable_page = durable.pages[0]
            durable_page.on("pageerror", lambda error: errors.append(str(error)))
            durable_page.on("dialog", lambda dialog: dialog.accept())
            durable_page.goto(url)
            ready(durable_page)
            open_saved(durable_page, identity)
            assert history(durable_page) == original
            capture(durable_page, "browser-restart-history", ".history-panel")
            durable.close()

            assert not errors, errors
            assert all(request.startswith(base + "/") for request in requests), requests
            assert all(
                item["authority"] == [] and item["paymentRoute"] == "none"
                for item in [original, failed, losing, preserved]
            )
            context.close()
            other_context.close()
            browser.close()
        (OUTPUT / "journey-result.json").write_text(
            json.dumps(
                {
                    "result": "pass",
                    "journey": ["proposal", "construction", "computed-evidence", "reuse", "successor", "reload"],
                    "negativeAndMixedResults": "retained; either failed phase keeps aggregate FAIL",
                    "laterSuccess": "failed predecessor remains byte-identical in history",
                    "recovery": [
                        "fresh-context import",
                        "conflicting tabs",
                        "failed save and retry",
                        "browser-process restart",
                    ],
                    "viewports": [320, 390, 768, 1440],
                    "textScales": ["125% via product control", "200% via browser text sizing"],
                    "accessibility": "zero selected WCAG A/AA and best-practice violations",
                    "externalDispatches": 0,
                },
                indent=2,
            )
        )
        print(
            "PASS: constructed witness, held-out reuse, negative successor, reload/import, conflicting tabs, "
            "save recovery, mobile layout and no external dispatch"
        )
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
