# SPDX-License-Identifier: Apache-2.0
from functools import partial
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading

from playwright.sync_api import expect, sync_playwright
import test_successor_capability_browser as existing

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(os.environ.get("ENTERPRISE_BROWSER_EVIDENCE", "/tmp/autonomous-enterprises-browser"))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    existing.OUTPUT = OUTPUT
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(existing.QuietHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or shutil.which("chromium")
            )
            context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_port}/docs/successor/capabilities/#autonomous-enterprises")
            expect(page.locator("#enterprise-build")).to_be_enabled(timeout=30000)
            expect(page.locator("#enterprise-seed")).to_be_disabled()
            page.locator("#witness-enabled").check()
            page.locator("#public-confirmation").check()
            page.locator("#freeze").click()
            expect(page.locator("#development")).to_be_enabled()
            page.locator("#lab-public-confirmation").check()
            expect(page.locator("#lab-construct")).to_be_enabled()
            page.locator("#enterprise-build").click()
            expect(page.locator("#enterprise-status")).to_contain_text("Frozen", timeout=120000)
            expect(page.locator("#enterprise-seed")).to_be_enabled()
            expect(page.locator("#enterprise-facts")).to_contain_text("1,508,042")
            expect(page.locator("#brief-title")).to_be_disabled()
            expect(page.locator("#start-successor")).to_be_disabled()
            expect(page.locator("#freeze")).to_be_disabled()
            expect(page.locator("#development")).to_be_disabled()
            expect(page.locator("#heldout")).to_be_disabled()
            expect(page.locator("#lab-construct")).to_be_disabled()
            expect(page.locator("#lab-successor")).to_be_disabled()
            expect(page.locator("#run-gate")).to_contain_text("Finish or stop the active enterprise attempt")
            expect(page.locator("#lab-reservation")).to_contain_text("Finish or stop the active enterprise attempt")
            frozen = existing.history(page)
            constructed = dict(frozen)
            cutoff = next(
                index + 1 for index, event in enumerate(frozen["events"]) if event["kind"] == "enterprise-constructed"
            )
            constructed["events"] = frozen["events"][:cutoff]
            constructed["revision"] = cutoff - 1
            (OUTPUT / "accepted-construction-workspace.json").write_text(json.dumps(constructed, indent=2))
            # Restore the actual authenticated saved prefix at the interrupted boundary.
            # The fixture contains the same retained construction, not a second build.
            envelope = page.evaluate(
                """async value => {
                    const db = await new Promise((resolve, reject) => {
                        const request = indexedDB.open('agialpha.successor-capability.v1', 1);
                        request.onsuccess = () => resolve(request.result);
                        request.onerror = () => reject(request.error);
                    });
                    let envelope;
                    await new Promise((resolve, reject) => {
                        const tx = db.transaction('missions', 'readwrite');
                        const store = tx.objectStore('missions');
                        const request = store.get(value.missionId);
                        request.onsuccess = () => {
                            const prior = request.result;
                            envelope = {missionId:value.missionId,
                                revision:prior.revision - (prior.workspace.events.length - value.events.length),
                                workspace:value};
                            store.put(envelope);
                        };
                        tx.oncomplete = () => resolve();
                        tx.onerror = () => reject(tx.error);
                        tx.onabort = () => reject(tx.error);
                    });
                    db.close();
                    return envelope;
                }""",
                constructed,
            )
            (OUTPUT / "accepted-construction-storage-envelope.json").write_text(json.dumps(envelope, indent=2))
            page.reload()
            expect(page.locator("#enterprise-status")).to_contain_text("Construction accepted", timeout=120000)
            expect(page.locator("#enterprise-build")).to_be_disabled()
            expect(page.locator("#enterprise-seed")).to_be_disabled()
            expect(page.locator("#enterprise-continue")).to_be_enabled()
            page.locator("#enterprise-continue").click()
            expect(page.locator("#enterprise-status")).to_contain_text("Frozen", timeout=120000)
            expect(page.locator("#enterprise-seed")).to_be_enabled()
            recovered = existing.history(page)
            assert recovered["events"][:cutoff] == constructed["events"]
            assert [event["kind"] for event in recovered["events"]].count("enterprise-constructed") == 1
            assert recovered["events"][-1]["kind"] == "enterprise-frozen"
            assert not any(event["kind"] == "enterprise-tasks" for event in recovered["events"])
            (OUTPUT / "recovered-frozen-workspace.json").write_text(json.dumps(recovered, indent=2))
            page.locator("#enterprise-capital-run").click()
            expect(page.locator("#enterprise-capital-summary")).to_contain_text("13")
            page.locator("#enterprise-seed").fill("20261021")
            page.locator("#enterprise-continue").click()
            expect(page.locator("#enterprise-status")).to_contain_text("Successor accepted locally", timeout=120000)
            expect(page.locator("#brief-title")).to_be_enabled()
            expect(page.locator("#start-successor")).to_be_enabled()
            expect(page.locator("#development")).to_be_enabled()
            page.locator("#lab-public-confirmation").check()
            expect(page.locator("#lab-construct")).to_be_enabled()
            with page.expect_download(timeout=120000) as downloading:
                page.locator("#enterprise-export").click()
            docket_path = OUTPUT / "evidence-docket.json"
            downloading.value.save_as(docket_path)
            docket = json.loads(docket_path.read_text())
            assert len(docket["files"]) == 13
            run = json.loads(docket["files"]["05_agialpha_runs/run.json"])
            events = run["workspace"]["events"]
            assert events[0]["kind"] == "version"
            assert [event["kind"] for event in events].index("enterprise-frozen") < [
                event["kind"] for event in events
            ].index("enterprise-tasks")
            proof = subprocess.check_output(
                [
                    "node",
                    "--input-type=module",
                    "-e",
                    "import {readFileSync} from 'node:fs';"
                    "import {verifyDiscoveryDocket} from './examples/successor-capability/discovery-lab-docket.mjs';"
                    "console.log(JSON.stringify(await verifyDiscoveryDocket(readFileSync(process.argv[1],'utf8'))));",
                    str(docket_path),
                ],
                cwd=ROOT,
                text=True,
            )
            assert json.loads(proof)["verified"] is True
            (OUTPUT / "docket-verification.json").write_text(proof)
            existing.audit(page, "enterprise-desktop")
            page.locator("#autonomous-enterprises").screenshot(path=str(OUTPUT / "desktop.png"), animations="disabled")
            page.reload()
            expect(page.locator("#enterprise-status")).to_contain_text("Successor accepted locally", timeout=120000)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            existing.audit(page, "enterprise-mobile")
            page.locator("#autonomous-enterprises").screenshot(path=str(OUTPUT / "mobile.png"), animations="disabled")
            page.locator("#enterprise-capital-run").focus()
            expect(page.locator("#enterprise-capital-run")).to_be_focused()
            assert not errors, errors
            (OUTPUT / "summary.json").write_text(
                json.dumps(
                    {
                        "status": "PASSED",
                        "source": json.loads((ROOT / "docs/successor/capabilities/sources.json").read_text()),
                        "browser": browser.version,
                        "missionId": run["workspace"]["missionId"],
                        "eventCount": len(events),
                        "checks": [
                            "actual-construction",
                            "freeze-before-future-inputs",
                            "accepted-construction-reload",
                            "freeze-without-rebuilding-or-future-inputs",
                            "proposal-version-guard",
                            "active-unrelated-history-guards",
                            "terminal-related-controls-resume",
                            "five-treatments",
                            "changed-kernel-successor",
                            "actual-docket-download",
                            "independent-docket-replay",
                            "reload",
                            "mobile",
                            "keyboard",
                            "axe",
                            "no-page-errors",
                        ],
                    },
                    indent=2,
                )
                + "\n"
            )
            browser.close()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
