# SPDX-License-Identifier: Apache-2.0
"""Exercise persistent public-data missions, review, imports and conflict recovery."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            context = browser.new_context()
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def wait(predicate):
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    if page.evaluate(predicate):
                        return
                    page.wait_for_timeout(25)
                raise AssertionError((predicate, page.locator("#error").text_content()))

            page.goto(f"http://127.0.0.1:{server.server_port}/successor/mission/")
            page.locator("#new").click()
            wait("()=>!document.querySelector('#run').disabled")
            page.locator("#run").click()
            wait("()=>document.querySelector('#result-summary').textContent.includes('295')")
            assert page.locator("#files button").count() == 3
            page.locator('[data-view="checks"]').click()
            page.locator("#note").fill("I checked the totals against the supplied rows.")
            page.locator("#accept").click()
            wait("()=>document.querySelector('#check-data').textContent.includes('LOCAL_SELF_REPORTED_REVIEW')")
            page.reload()
            page.locator("#open").click()
            wait("()=>document.querySelector('#check-data').textContent.includes('LOCAL_SELF_REPORTED_REVIEW')")
            page.locator('[data-view="result"]').click()
            with page.expect_download() as download:
                page.locator("#export").click()
            record_bytes = Path(download.value.path()).read_bytes()
            record = json.loads(record_bytes)
            assert record["state"] == "reviewed"
            # Recover in a genuinely fresh origin storage context.
            url = page.url
            context.close()
            context = browser.new_context()
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            wait("()=>!document.querySelector('#import').disabled")
            assert page.locator("#saved option").count() == 0
            # External recovery is historical; acceptance cannot silently carry forward.
            page.locator("#import").set_input_files(
                {"name": "mission.json", "mimeType": "application/json", "buffer": record_bytes}
            )
            wait("()=>!document.querySelector('#fork').disabled")
            assert page.locator("#run").is_disabled()
            assert '"currentReview": null' in page.locator("#check-data").text_content()
            assert '"persisted": false' in page.locator("#check-data").text_content()
            page.locator("#fork").click()
            wait("()=>!document.querySelector('#run').disabled")
            assert '"state": "draft"' in page.locator("#check-data").text_content()
            # A different real dataset produces a different result after recovery.
            page.locator("#csv").fill("group,amount\nNew,12\nNew,-2\nOther,40\n")
            page.locator("#save").click()
            wait("()=>!document.querySelector('#run').disabled")
            page.locator("#run").click()
            wait("()=>document.querySelector('#result-summary').textContent.includes('50')")
            assert '"review": null' in page.locator("#check-data").text_content()
            with page.expect_download() as second_download:
                page.locator("#export").click()
            second_record = json.loads(Path(second_download.value.path()).read_bytes())
            assert second_record["missionId"] != record["missionId"]
            assert second_record["specDigest"] != record["specDigest"]
            assert second_record["result"]["runId"] != record["result"]["runId"]
            assert second_record["result"]["bindingDigest"] != record["result"]["bindingDigest"]
            assert second_record["review"] is None
            assert second_record["history"][-1]["trust"] == "historical-untrusted"
            # Preserve raw invalid integer text across language changes.
            page.locator('[data-view="mission"]').click()
            page.locator("#minutes").fill("1.00000000000000001")
            page.locator("#language").click()
            assert page.locator("#minutes").input_value() == "1.00000000000000001"
            page.locator("#save").click()
            wait("()=>!document.querySelector('#error').hidden")
            assert "INTEGER_TEXT" in page.locator("#error").text_content()
            page.locator("#minutes").fill("10")
            page.locator("#save").click()
            wait("()=>!document.querySelector('#run').disabled")
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 1000})
                for scale in (100, 200):
                    page.evaluate("scale=>document.documentElement.style.fontSize=scale+'%'", scale)
                    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (width, scale)
            page.evaluate("()=>document.documentElement.style.fontSize='100%'")
            # Another page changes the same revision. This page must become read-only.
            second = context.new_page()
            second.goto(page.url)
            second.locator("#saved").select_option(page.locator("#saved").input_value())
            second.locator("#open").click()
            second.locator("#name").fill("Other tab saved first")
            second.locator("#save").click()
            second.wait_for_timeout(200)
            page.locator("#name").fill("Stale tab edit")
            page.locator("#save").click()
            wait("()=>document.querySelector('#error').textContent.includes('LOCAL_REVISION_CONFLICT')")
            assert page.locator("#run").is_disabled()
            assert page.locator("#name").is_disabled()
            page.locator("#open").click()
            wait("()=>document.querySelector('#name').value==='Other tab saved first'")
            # Malformed UTF-8 is rejected instead of silently replaced.
            page.locator("#import").set_input_files(
                {"name": "bad.json", "mimeType": "application/json", "buffer": b"\xff"}
            )
            wait("()=>!document.querySelector('#error').hidden")
            # STOP is issued as soon as the persisted running state is exposed.
            page.locator('[data-view="mission"]').click()
            page.evaluate(
                """async()=>{
              document.querySelector('#run').click();
              const deadline=performance.now()+5000;
              while(document.querySelector('#stop').disabled){
                if(performance.now()>deadline)throw Error('STOP not available');
                await new Promise(resolve=>setTimeout(resolve,0));
              }
              document.querySelector('#stop').click();
            }"""
            )
            wait("()=>JSON.parse(document.querySelector('#check-data').textContent).state==='stopped'")
            assert '"resultDigest": null' in page.locator("#check-data").text_content()
            assert errors == [], errors
            axe = os.environ.get("AXE_SCRIPT")
            if axe:
                # Inline CSP deliberately disallows arbitrary script injection; route exact audit bytes.
                script = Path(axe).read_text()
                result = page.evaluate(
                    script
                    + "; async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})"
                )
                assert result["violations"] == [], result["violations"]
            # No-script and unavailable-storage modes keep actions closed.
            no_script = browser.new_context(java_script_enabled=False)
            no_page = no_script.new_page()
            no_page.goto(page.url)
            assert no_page.locator("noscript").is_visible()
            assert no_page.locator("#new").is_disabled()
            assert no_page.locator("#run").is_disabled()
            unavailable = browser.new_context()
            unavailable.add_init_script("Object.defineProperty(window,'indexedDB',{value:undefined})")
            unavailable_page = unavailable.new_page()
            unavailable_page.goto(page.url)
            unavailable_page.locator("#error").wait_for(state="visible")
            assert "LOCAL_STORAGE_UNAVAILABLE" in unavailable_page.locator("#error").text_content()
            assert unavailable_page.locator("#new").is_disabled()
            assert unavailable_page.locator("#run").is_disabled()
            assert unavailable_page.locator("#import").is_enabled()
            browser.close()
        print(
            "PASS: persistent mission, real second dataset, explicit review, import history, "
            "conflict, strict input, EN/FR layouts"
        )
        print("Accessibility audit: " + ("passed" if os.environ.get("AXE_SCRIPT") else "not run (AXE_SCRIPT absent)"))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
