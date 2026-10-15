# SPDX-License-Identifier: Apache-2.0
"""Actual local project cycle, fresh-context restore, failure preservation and CAS."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import re
import threading
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    screenshots = Path(os.environ.get("PROJECT_SCREENSHOTS", "project-screenshots"))
    screenshots.mkdir(parents=True, exist_ok=True)
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            url = f"http://127.0.0.1:{server.server_port}/docs/successor/mission/"

            def export_project():
                with page.expect_download() as d:
                    page.locator("#project-export").click()
                return Path(d.value.path()).read_bytes()

            # Produce the actual discovery brief through the existing discovery UI.
            page.goto(f"http://127.0.0.1:{server.server_port}/docs/successor/discover/")
            page.locator("#restore").set_input_files(
                str(ROOT / "examples/successor-project/public-data-opportunity.json")
            )
            expect(page.locator("#mission")).to_have_value(re.compile("Reconcile"), timeout=30000)
            page.locator("#analyze").click()
            expect(page.locator("#export")).to_be_enabled(timeout=30000)
            with page.expect_download() as discovery_download:
                page.locator("#export").click()
            discovery_bytes = Path(discovery_download.value.path()).read_bytes()
            page.goto(url)
            expect(page.locator("#discovery-import")).to_be_enabled(timeout=30000)
            page.locator("#discovery-import").set_input_files(
                {"name": "brief.json", "mimeType": "application/json", "buffer": discovery_bytes}
            )
            expect(page.locator("#discovery-selected")).to_contain_text("Reconcile", timeout=30000)
            page.locator("#new").click()
            expect(page.locator("#run")).to_be_enabled(timeout=30000)
            page.locator("#project-choice").check()
            page.locator("#project-start").click()
            expect(page.locator("#project-summary")).to_contain_text("revision 0", timeout=30000)
            page.locator("#run").click()
            expect(page.locator("#result-summary")).to_contain_text("295", timeout=30000)
            page.locator('[data-view="checks"]').click()
            page.locator("#note").fill("Retain incumbent: comparative burden is not yet measured.")
            page.locator("#reject").click()
            expect(page.locator("#project-summary")).to_contain_text("revision 3", timeout=30000)
            first_bytes = export_project()
            first = json.loads(first_bytes)
            assert first["authority"] == "none"
            assert first["cycles"][0]["discovery"]["bytes"].encode() == discovery_bytes
            assert len(first["cycles"][0]["stageWork"]) == 21
            assert first["cycles"][0]["evaluationDraft"]["commitments"] is None
            page.screenshot(path=str(screenshots / "01-real-result-rejected.png"), full_page=True)
            context.close()

            # A fresh browser context has no grants, review, or storage from the first.
            context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)
            expect(page.locator("#project-import")).to_be_enabled(timeout=30000)
            page.locator("#project-import").set_input_files(
                {"name": "project.json", "mimeType": "application/json", "buffer": first_bytes}
            )
            expect(page.locator("#project-summary")).to_contain_text("historical", timeout=30000)
            assert page.locator("#run").is_disabled()
            assert '"currentReview": null' in page.locator("#project-history").text_content()
            assert page.locator("#project-resume").is_disabled()
            page.screenshot(path=str(screenshots / "02-fresh-context-history.png"), full_page=True)
            page.locator("#project-choice").check()
            page.locator("#project-resume").click()
            expect(page.locator("#run")).to_be_enabled(timeout=30000)
            page.locator("#csv").fill("group,amount\nNew,12\nNew,-2\nOther,40\n")
            assert page.locator("#save").is_disabled(), "Changed input requires fresh explicit mapping selection"
            page.locator("#project-choice").check()
            page.locator("#save").click()
            expect(page.locator("#run")).to_be_enabled(timeout=30000)
            page.locator("#run").click()
            expect(page.locator("#result-summary")).to_contain_text("50", timeout=30000)
            second = json.loads(export_project())
            assert second["projectId"] == first["projectId"]
            assert second["cycles"][0] == first["cycles"][0], "Keep exact failed/rejected historical cycle"
            assert second["cycles"][-1]["cycleId"] != first["cycles"][0]["cycleId"]
            old = json.loads(first["cycles"][0]["records"][-1]["bytes"])
            new = json.loads(second["cycles"][-1]["records"][-1]["bytes"])
            assert old["review"]["decision"] == "rejected"
            assert new["review"] is None and old["missionId"] != new["missionId"]
            assert new["specDigest"] != old["specDigest"]
            assert "stale-dependent-evaluation" in page.locator("#project-history").text_content()
            page.screenshot(path=str(screenshots / "03-different-dataset-result.png"), full_page=True)

            # A stale same-ID import cannot replace the newer saved local project.
            page.locator("#project-import").set_input_files(
                {"name": "old.json", "mimeType": "application/json", "buffer": first_bytes}
            )
            expect(page.locator("#project-summary")).to_contain_text("revision 3", timeout=30000)
            page.locator("#project-choice").check()
            page.locator("#project-resume").click()
            expect(page.locator("#error")).to_contain_text("PROJECT_IMPORT_CONFLICT", timeout=30000)
            assert page.locator("#run").is_disabled()
            assert json.loads(export_project())["projectDigest"] == first["projectDigest"]
            page.locator("#project-open").click()
            expect(page.locator("#project-summary")).to_contain_text(f"revision {second['revision']}", timeout=30000)
            page.locator("#project-choice").check()
            page.locator("#project-resume").click()
            expect(page.locator("#run")).to_be_enabled(timeout=30000)

            # Actual IndexedDB put failure: no run, export survives, old save stays intact.
            page.evaluate(
                """() => { globalThis.originalPut = IDBObjectStore.prototype.put;
              IDBObjectStore.prototype.put = function() { throw new DOMException('Forced quota failure',
                'QuotaExceededError'); }; }"""
            )
            page.locator("#run").click()
            expect(page.locator("#project-summary")).to_contain_text("historical", timeout=30000)
            assert page.locator("#run").is_disabled()
            failed = json.loads(export_project())
            assert json.loads(failed["cycles"][-1]["records"][-1]["bytes"])["state"] == "running"
            page.evaluate("() => { IDBObjectStore.prototype.put = globalThis.originalPut; }")
            page.screenshot(path=str(screenshots / "04-failed-save-exportable.png"), full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            page.screenshot(path=str(screenshots / "05-mobile-history.png"), full_page=True)
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            assert errors == [], errors
            context.close()

            # Separate real-origin module test: transactional concurrent tabs and corruption.
            context = browser.new_context()
            page = context.new_page()
            page.goto(f"http://127.0.0.1:{server.server_port}/")
            result = page.evaluate(
                """async (project) => {
              const {openProjectStore} = await import('/examples/successor-project/store.mjs');
              const {appendRecord,projectView,validateProject} = await import('/examples/successor-project/engine.mjs');
              const {startRun} = await import('/examples/successor-workbench/mission-record.mjs');
              const a = await openProjectStore({name:'project-cas'}), b = await openProjectStore({name:'project-cas'});
              await a.save(project);
              const last = project.cycles.at(-1), native = JSON.parse(last.records.at(-1).bytes);
              const sources={mission:last.records.at(-1).source,discovery:last.discovery.source};
              // Retained source identity is only consistency data, not a signer identity.
              const view=await projectView(project,{sourceHash:'f'.repeat(64),sources});
              if(view.sourceCurrent || view.currentReview !== null)throw Error('source drift');
              const c=await import('/examples/successor-project/engine.mjs');
              const n=await import('/examples/successor-workbench/mission-record.mjs');
              const fresh=await n.createRecord({missionId:'concurrent',sourceHash:project.sourceHash,spec:native.spec});
              const base=await c.nextCycle(project,{cycleId:'concurrent-cycle',record:fresh,
                choices:last.mapping.choices,sourceHash:project.sourceHash,sources,expectedRevision:project.revision});
              await a.save(base,{revision:project.revision,digest:project.projectDigest});
              const make=async id=>appendRecord(base,await startRun(fresh,{expectedRevision:0,runId:id}),{
                expectedRevision:base.revision,sourceHash:base.sourceHash,sources});
              const candidates=await Promise.all([make('a'),make('b')]);
              const outcomes=await Promise.allSettled(candidates.map((v,i)=>(i?a:b).save(v,{
                revision:base.revision,digest:base.projectDigest})));
              if(outcomes.filter(x=>x.status==='fulfilled').length!==1)throw Error('CAS winner');
              const winner=await a.get(project.projectId);if(winner.revision!==base.revision+1)
                throw Error('CAS revision');
              const loser=outcomes.findIndex(x=>x.status==='rejected');await validateProject(candidates[loser]);
              a.close();b.close();const reopen=await openProjectStore({name:'project-cas'});
              if((await reopen.get(project.projectId)).projectDigest!==winner.projectDigest)
                throw Error('reopen changed');
              const raw=await new Promise(resolve=>{const r=indexedDB.open('project-cas');
                r.onsuccess=()=>resolve(r.result);});
              await new Promise(resolve=>{const tx=raw.transaction('projects','readwrite');
                tx.objectStore('projects').put({...winner,authority:'grant'});tx.oncomplete=resolve;});
              let denied=false;try{await reopen.get(project.projectId);}catch{denied=true;}if(!denied)
                throw Error('corruption accepted');
              raw.close();reopen.close();return 'atomic conflict, drift, corruption and reopen passed';
            }""",
                first,
            )
            print(result)
            browser.close()
            assert len(list(screenshots.glob("*.png"))) == 5
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
