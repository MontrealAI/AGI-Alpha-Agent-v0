# SPDX-License-Identifier: Apache-2.0
"""Actual browser-only guided work; Fleet requests remain unexecuted in this suite."""

import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import Dialog, Error, Page, expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]
expect.set_options(timeout=30_000)


def upload(page: Page, selector: str, raw: bytes, name: str) -> None:
    page.locator(selector).set_input_files({"name": name, "mimeType": "application/json", "buffer": raw})


def downloaded(page: Page, selector: str) -> bytes:
    with page.expect_download() as item:
        page.locator(selector).click()
    return Path(item.value.path()).read_bytes()


def watch(page: Page, origin: str, errors: list[str], external: list[str]) -> None:
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("request", lambda request: external.append(request.url) if not request.url.startswith(origin) else None)


def leave_warning(page: Page, destination: str) -> None:
    dialogs: list[str] = []
    previous = page.url

    def dismiss(dialog: Dialog) -> None:
        dialogs.append(dialog.type)
        dialog.dismiss()

    page.once("dialog", dismiss)
    try:
        page.goto(destination, timeout=3000)
    except Error:
        pass
    assert dialogs == ["beforeunload"], dialogs
    assert page.url == previous


def force_guided_quota(page: Page) -> None:
    page.evaluate("""() => {
        globalThis.originalGuidedPut = IDBObjectStore.prototype.put;
        IDBObjectStore.prototype.put = function(...args) {
            if (this.name === 'journeys') {
                throw new DOMException('Forced guided quota failure', 'QuotaExceededError');
            }
            return globalThis.originalGuidedPut.apply(this, args);
        };
    }""")


def stored_guided_history(page: Page, project_id: str) -> bytes:
    raw = page.evaluate(
        """async projectId => {
        const db = await new Promise(resolve => {
            const r=indexedDB.open('agialpha.guided-project.v1');r.onsuccess=()=>resolve(r.result);
        });
        const raw=await new Promise(resolve=>{
            const r=db.transaction('journeys').objectStore('journeys').get(projectId);
            r.onsuccess=()=>resolve(r.result.raw);
        });
        db.close();return raw;
    }""",
        project_id,
    )
    assert isinstance(raw, str)
    return raw.encode()


def rejected_project(page: Page) -> bytes:
    page.locator("#new").click()
    expect(page.locator("#run")).to_be_enabled()
    page.locator("#project-choice").focus()
    page.keyboard.press("Space")
    page.locator("#project-start").focus()
    page.keyboard.press("Enter")
    expect(page.locator("#project-summary")).to_contain_text("revision 0")
    page.locator("#run").click()
    expect(page.locator("#result-summary")).to_contain_text("295")
    page.locator('[data-view="checks"]').click()
    page.locator("#note").fill("Retain rejected comparison; independent economic advantage has not been measured.")
    page.locator("#reject").click()
    expect(page.locator("#project-summary")).to_contain_text("revision 3")
    original = downloaded(page, "#route-export")
    assert json.loads(json.loads(original)["cycles"][0]["records"][-1]["bytes"])["review"]["decision"] == "rejected"
    return original


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    url = origin + "/docs/successor/mission/"
    screenshots = Path(os.environ.get("GUIDED_SCREENSHOTS", "guided-successor-screenshots"))
    screenshots.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    external: list[str] = []
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            for language in ("en", "fr"):
                context = browser.new_context(viewport={"width": 1440, "height": 1100}, accept_downloads=True)
                page = context.new_page()
                watch(page, origin, errors, external)
                page.goto(url + "?lang=" + language)
                expect(page.locator("#new")).to_be_enabled()
                assert page.locator("html").get_attribute("lang") == language
                original = rejected_project(page)
                native = json.loads(original)
                initial = downloaded(page, "#journey-export")
                assert json.loads(initial)["history"][0]["raw"].encode() == original
                page.locator("#journey-route").select_option("agijobsv0-jobregistry-v2")
                assert page.locator("#jobs-amount").input_value() == ""
                page.locator("#jobs-amount").fill("0.000000000000000001")
                page.locator("#route-export").click()
                expect(page.locator("#error")).to_contain_text("AGIALPHA_AMOUNT_BOUNDS")
                page.locator("#jobs-amount").fill("2.000000000000000007")
                proposal = downloaded(page, "#route-export")
                proposed = json.loads(proposal)
                assert proposed["planning"]["amountBaseUnits"] == "2000000000000000007"
                assert proposed["planning"]["status"] == "unfunded-proposal"
                assert proposed["route"] == {"backend": "agijobsv0-jobregistry-v2", "asset": "AGIALPHA"}
                assert proposed["original"]["raw"].encode() == original
                result = downloaded(page, "#jobs-run")
                assert json.loads(result)["history"][-1]["kind"] == "local-result"
                request = json.loads(downloaded(page, "#fleet-export"))
                assert request["route"]["asset"] == "AGIALPHA"
                assert request["upstream"]["raw"].encode() == result
                assert request["authority"] == "none" and request["productionQualified"] is False
                complete = downloaded(page, "#journey-export")
                whole = json.loads(complete)
                assert len(whole["history"]) == 3
                assert whole["history"][0]["raw"].encode() == original
                assert whole["history"][1]["raw"].encode() == proposal
                assert whole["history"][2]["raw"].encode() == result
                assert whole["authority"] == "none" and whole["settlement"] == "not-connected"
                page.locator("#journey-route").select_option("manager-usdc")
                page.locator("#fleet-export").click()
                expect(page.locator("#error")).to_contain_text("SELECTED_ROUTE_DIFFERS_FROM_RETURN")
                assert downloaded(page, "#journey-export") == complete
                page.locator("#journey-route").select_option("agijobsv0-jobregistry-v2")
                upload(page, "#return-import", result, "duplicate.json")
                expect(page.locator("#error")).to_contain_text("DUPLICATE_EVENT")
                assert downloaded(page, "#journey-export") == complete
                for width in (320, 390, 1440):
                    page.set_viewport_size({"width": width, "height": 1000})
                    for scale in (1, 2):
                        page.evaluate("scale => document.documentElement.style.fontSize = (17 * scale) + 'px'", scale)
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        page.screenshot(path=str(screenshots / f"{language}-{width}-{scale}x.png"), full_page=True)
                context.close()
                context = browser.new_context(viewport={"width": 390, "height": 844}, accept_downloads=True)
                page = context.new_page()
                watch(page, origin, errors, external)
                page.goto(url + "?lang=" + language)
                expect(page.locator("#journey-import")).to_be_enabled()
                upload(page, "#journey-import", complete, "complete.json")
                expect(page.locator("#project-summary")).to_contain_text("historical")
                assert page.locator("#run").is_disabled() and page.locator("#project-resume").is_disabled()
                assert '"currentReview": null' in page.locator("#project-history").text_content()
                assert downloaded(page, "#journey-export") == complete
                page.locator("#project-choice").check()
                page.locator("#project-resume").click()
                expect(page.locator("#run")).to_be_enabled()
                page.locator("#csv").fill("group,amount\nNew,12\nNew,-2\nOther,40\n")
                assert page.locator("#save").is_disabled()
                page.locator("#project-choice").check()
                page.locator("#save").click()
                expect(page.locator("#run")).to_be_enabled()
                page.locator("#run").click()
                expect(page.locator("#result-summary")).to_contain_text("50")
                updated = downloaded(page, "#journey-export")
                changed = json.loads(updated)
                assert changed["history"][:3] == whole["history"] and len(changed["history"]) == 4
                changed_native = json.loads(changed["native"]["raw"])
                assert changed_native["cycles"][0] == native["cycles"][0]
                assert json.loads(changed_native["cycles"][-1]["records"][-1]["bytes"])["review"] is None
                upload(page, "#journey-import", complete, "stale.json")
                expect(page.locator("#error")).to_contain_text("JOURNEY_IMPORT_CONFLICT")
                assert downloaded(page, "#journey-export") == updated
                context.close()
                nojs = browser.new_context(java_script_enabled=False, viewport={"width": 320, "height": 900})
                page = nojs.new_page()
                page.goto(url)
                assert page.locator("noscript").is_visible()
                for selector in ("#new", "#journey-import", "#route-export", "#journey-route"):
                    assert page.locator(selector).is_disabled()
                page.screenshot(path=str(screenshots / f"{language}-nojs.png"), full_page=True)
                nojs.close()
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            watch(page, origin, errors, external)
            page.goto(url)
            expect(page.locator("#new")).to_be_enabled()
            rejected_project(page)
            saved = downloaded(page, "#journey-export")
            project_id = json.loads(saved)["projectId"]
            force_guided_quota(page)
            page.locator("#journey-route").select_option("agijobsv0-jobregistry-v2")
            page.locator("#jobs-amount").fill("10")
            page.locator("#route-export").click()
            expect(page.locator("#error")).to_be_visible()
            expect(page.locator("#journey-summary")).to_contain_text("export before leaving")
            unsaved = downloaded(page, "#journey-export")
            assert len(json.loads(unsaved)["history"]) == 2
            expect(page.locator("#journey-recovery")).to_be_visible()
            assert downloaded(page, "#recovery-export") == unsaved
            with page.expect_download() as cancelled:
                page.locator("#recovery-export").click()
            cancelled.value.cancel()
            leave_warning(page, origin + "/docs/successor/discover/")
            page.evaluate("""() => {
                globalThis.originalDownloadClick = HTMLAnchorElement.prototype.click;
                globalThis.blockedRecoveryDownloads = 0;
                HTMLAnchorElement.prototype.click = function() {
                    if (this.download) {globalThis.blockedRecoveryDownloads++;return;}
                    return globalThis.originalDownloadClick.call(this);
                };
            }""")
            page.evaluate("() => {document.getElementById('status').textContent = '';}")
            page.locator("#recovery-export").click()
            expect(page.locator("#status")).to_contain_text("Recovery download prepared")
            assert page.evaluate("globalThis.blockedRecoveryDownloads") == 1
            leave_warning(page, origin + "/docs/successor/discover/")
            page.evaluate("() => {HTMLAnchorElement.prototype.click = globalThis.originalDownloadClick;}")
            upload(page, "#journey-import", complete, "another-project.json")
            expect(page.locator("#error")).to_contain_text("RECOVERY")
            assert downloaded(page, "#recovery-export") == unsaved
            other_native = json.loads(complete)["native"]["raw"].encode()
            upload(page, "#project-import", other_native, "other-native-project.json")
            expect(page.locator("#project-summary")).to_contain_text(json.loads(complete)["projectId"])
            page.locator("#journey-export").click()
            expect(page.locator("#error")).to_contain_text("RECOVERY")
            assert downloaded(page, "#recovery-export") == unsaved
            leave_warning(page, origin + "/docs/successor/discover/")
            page.evaluate("() => {IDBObjectStore.prototype.put = globalThis.originalGuidedPut;}")
            assert stored_guided_history(page, project_id) == saved
            page.screenshot(path=str(screenshots / "guided-save-failure-exportable.png"), full_page=True)
            page.locator("#recovery-confirm").click()
            expect(page.locator("#journey-recovery")).to_be_hidden()
            assert page.evaluate("""() => {
                const event = new Event('beforeunload', {cancelable:true});
                window.dispatchEvent(event);return event.defaultPrevented;
            }""") is False
            page.goto(origin + "/docs/successor/discover/")
            assert page.url.endswith("/docs/successor/discover/")
            context.close()
            context = browser.new_context(accept_downloads=True)
            page = context.new_page()
            watch(page, origin, errors, external)
            page.goto(url)
            expect(page.locator("#new")).to_be_enabled()
            rejected_project(page)
            before_failure = downloaded(page, "#journey-export")
            retry_project_id = json.loads(before_failure)["projectId"]
            force_guided_quota(page)
            page.locator("#journey-route").select_option("agijobsv0-jobregistry-v2")
            page.locator("#jobs-amount").fill("10")
            page.locator("#route-export").click()
            expect(page.locator("#journey-recovery")).to_be_visible()
            protected = downloaded(page, "#recovery-export")
            assert len(json.loads(protected)["history"]) == 2
            assert stored_guided_history(page, retry_project_id) == before_failure
            page.evaluate("() => {IDBObjectStore.prototype.put = globalThis.originalGuidedPut;}")
            page.locator("#recovery-save").click()
            expect(page.locator("#journey-recovery")).to_be_hidden()
            assert stored_guided_history(page, retry_project_id) == protected
            assert page.evaluate("""() => {
                const event = new Event('beforeunload', {cancelable:true});
                window.dispatchEvent(event);return event.defaultPrevented;
            }""") is False
            continued = downloaded(page, "#jobs-run")
            assert json.loads(continued)["history"][-1]["kind"] == "local-result"
            continued_history = downloaded(page, "#journey-export")
            assert json.loads(continued_history)["history"][:2] == json.loads(protected)["history"]
            assert len(json.loads(continued_history)["history"]) == 3
            assert stored_guided_history(page, retry_project_id) == continued_history
            page.reload()
            expect(page.locator("#journey-import")).to_be_enabled()
            upload(page, "#journey-import", continued_history, "continued.json")
            expect(page.locator("#project-summary")).to_contain_text("historical")
            assert page.locator("#run").is_disabled()
            assert downloaded(page, "#journey-export") == continued_history
            page.screenshot(path=str(screenshots / "guided-save-retry-continued.png"), full_page=True)
            context.close()
            assert errors == [], errors
            assert external == [], external
            browser.close()
            assert len(list(screenshots.glob("*.png"))) == 16
            print(
                "Guided browser PASS: EN/FR, exact token units, native Jobs work, retained history, "
                "historical recovery, changed work, stale import, 320/390/1440, 200% text, no-JS "
                "and failed save export."
            )
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
