# SPDX-License-Identifier: Apache-2.0
"""Local evaluation preparation, reported comparisons and safe historical recovery."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            executable = os.environ.get("CHROMIUM_EXECUTABLE")
            browser = p.chromium.launch(**({"executable_path": executable} if executable else {}))
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors: list[str] = []
            external: list[str] = []
            base = f"http://127.0.0.1:{server.server_port}"
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request", lambda request: external.append(request.url) if not request.url.startswith(base) else None
            )
            page.goto(base + "/successor/discover/")
            page.locator('a[href="../evaluate/"]').click()
            page.wait_for_url("**/successor/evaluate/")
            page.locator("#freeze").click()
            page.locator("#result").wait_for(state="visible")
            assert page.locator("#comparison").text_content() == "uncommissioned"
            assert "No authority" in page.locator(".states").text_content()
            assert '"designation": "not-earned"' in page.locator("#inspection").text_content()
            report = json.loads(page.locator("#report").input_value())
            report["state"] = "complete"
            report["finishedAt"] = page.evaluate("new Date().toISOString()")
            for row in report["rows"]:
                row["trialCount"] = 1
                for metric in row["metrics"]:
                    metric["lower"] = metric["upper"] = (
                        20 if row["role"] == "candidate" and metric["id"] == "quality" else 10
                    )
                    metric["evidenceDigest"] = "a" * 64
                for constraint in row["constraints"]:
                    constraint["status"] = "reported-pass"
                    constraint["evidenceDigest"] = "b" * 64
            page.locator("#report").fill(json.dumps(report))
            page.locator("#add").click()
            expect(page.locator("#comparison")).to_have_text("reported-comparison-ready-for-review")
            assert '"independentProof": false' in page.locator("#inspection").text_content()
            with page.expect_download() as download:
                page.locator("#save").click()
            record_bytes = Path(download.value.path()).read_bytes()
            # Invalid and forged imports preserve exact current record and enable recovery.
            forged = json.loads(record_bytes)
            forged["independent"] = True
            page.locator("#restore").set_input_files(
                {"name": "forged.json", "mimeType": "application/json", "buffer": json.dumps(forged).encode()}
            )
            page.locator("#error").wait_for(state="visible")
            assert page.locator("#comparison").text_content() == "reported-comparison-ready-for-review"
            with page.expect_download() as download:
                page.locator("#save").click()
            assert Path(download.value.path()).read_bytes() == record_bytes
            page.locator("#add").click()  # A repeated click must not duplicate the same attempt.
            expect(page.locator("#error")).to_contain_text("DUPLICATE")
            assert '"attempts": 1' in page.locator("#inspection").text_content()
            # Draft edits hide stale comparisons, retain prior valid bytes and require re-freezing.
            contract = json.loads(page.locator("#contract").input_value())
            contract["mission"] = "<script>alert('not executable')</script>"
            page.locator("#contract").fill(json.dumps(contract))
            assert page.locator("#result").is_hidden()
            assert page.locator("#save").is_disabled()
            with page.expect_download() as download:
                page.locator("#previous").click()
            assert Path(download.value.path()).read_bytes() == record_bytes
            page.locator("#freeze").click()
            expect(page.locator("#comparison")).to_have_text("uncommissioned")
            assert page.locator("#scope script").count() == 0
            assert "<script>" in page.locator("#scope").text_content()
            page.locator("#language").click()
            assert page.locator("html").get_attribute("lang") == "fr"
            assert "<script>" in page.locator("#contract").input_value()
            page.evaluate("document.documentElement.style.zoom = 2")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.evaluate("document.documentElement.style.zoom = 1")
            screenshots = Path(os.environ.get("EVALUATION_SCREENSHOTS", "/tmp/specialist-evaluation-screenshots"))
            screenshots.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshots / "desktop-fr.png"), full_page=True)
            context = browser.new_context(viewport={"width": 375, "height": 812})
            phone = context.new_page()
            phone.on("pageerror", lambda error: errors.append(str(error)))
            phone.goto(page.url)
            phone.locator("#restore").set_input_files(
                {"name": "record.json", "mimeType": "application/json", "buffer": record_bytes}
            )
            phone.locator("#result").wait_for(state="visible")
            assert "Historical reports" in phone.locator("#notice").text_content()
            assert '"authority": "none"' in phone.locator("#inspection").text_content()
            assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")
            phone.screenshot(path=str(screenshots / "mobile-en.png"), full_page=True)
            # Invalid UTF-8 must not be normalized silently.
            phone.locator("#restore").set_input_files(
                {"name": "bad.json", "mimeType": "application/json", "buffer": b'{"bad":"\xff"}'}
            )
            phone.locator("#error").wait_for(state="visible")
            assert phone.locator("#comparison").text_content() == "reported-comparison-ready-for-review"
            # Slow import cannot overwrite a newer contract edit.
            phone.evaluate(
                """() => { const original = File.prototype.arrayBuffer;
                File.prototype.arrayBuffer = function() { const file = this;
                    return new Promise(resolve => { window.finishImport = async () => resolve(await original.call(file));
                    document.documentElement.dataset.importReady = "true"; }); };
            }"""
            )
            phone.locator("#restore").set_input_files(
                {"name": "slow.json", "mimeType": "application/json", "buffer": record_bytes}
            )
            expect(phone.locator("html")).to_have_attribute("data-import-ready", "true")
            newer = phone.locator("#contract").input_value() + " "
            phone.locator("#contract").fill(newer)
            phone.evaluate("window.finishImport()")
            expect(phone.locator("#error")).to_contain_text("DRAFT_CHANGED")
            assert phone.locator("#contract").input_value() == newer
            assert phone.locator("#result").is_hidden()
            # Slow freeze cannot display evidence for stale edited bytes.
            phone.evaluate(
                """() => { const original = crypto.subtle.digest.bind(crypto.subtle);
                crypto.subtle.digest = (...args) => new Promise(resolve => {
                    window.finishFreeze = async () => { crypto.subtle.digest = original; resolve(await original(...args)); };
                    document.documentElement.dataset.freezeReady = "true";
                });
            }"""
            )
            phone.locator("#freeze").click()
            expect(phone.locator("html")).to_have_attribute("data-freeze-ready", "true")
            phone.locator("#contract").fill(newer + " ")
            phone.evaluate("window.finishFreeze()")
            expect(phone.locator("#freeze")).to_be_enabled()
            assert phone.locator("#result").is_hidden()
            assert "DRAFT_CHANGED" in phone.locator("#error").text_content()
            phone.locator("#freeze").focus()
            phone.keyboard.press("Enter")
            phone.locator("#result").wait_for(state="visible")
            phone.locator("#language").focus()
            phone.keyboard.press("Enter")
            assert phone.locator("html").get_attribute("lang") == "fr"
            phone.screenshot(path=str(screenshots / "mobile-fr.png"), full_page=True)
            axe = os.environ.get("AXE_SCRIPT")
            if os.environ.get("CI"):
                assert axe, "Exact-head CI requires Axe"
            if axe:
                phone.evaluate(Path(axe).read_text())
                violations = phone.evaluate("async () => (await axe.run()).violations")
                assert not violations, json.dumps(violations)
            # Actual browser clock: expiry changes the open decision without an edit.
            clock_page = context.new_page()
            clock_page.on("pageerror", lambda error: errors.append(str(error)))
            clock_page.clock.install()
            clock_page.goto(page.url)
            clock_contract = json.loads(clock_page.locator("#contract").input_value())
            clock_contract["expiresAt"] = clock_page.evaluate("new Date(Date.now() + 60000).toISOString()")
            clock_page.locator("#contract").fill(json.dumps(clock_contract))
            clock_page.locator("#freeze").click()
            clock_page.locator("#result").wait_for(state="visible")
            clock_report = json.loads(clock_page.locator("#report").input_value())
            clock_report["state"] = "complete"
            clock_report["finishedAt"] = clock_page.evaluate("new Date().toISOString()")
            for row in clock_report["rows"]:
                row["trialCount"] = 1
                for metric in row["metrics"]:
                    metric["lower"] = metric["upper"] = (
                        20 if row["role"] == "candidate" and metric["id"] == "quality" else 10
                    )
                    metric["evidenceDigest"] = "a" * 64
                for constraint in row["constraints"]:
                    constraint["status"] = "reported-pass"
                    constraint["evidenceDigest"] = "b" * 64
            clock_report["attemptId"] = "regressed-attempt"
            clock_report["rows"][0]["metrics"][3]["upper"] = 12
            clock_page.locator("#report").fill(json.dumps(clock_report))
            clock_page.locator("#add").click()
            expect(clock_page.locator("#comparison")).to_have_text("retain-incumbent")
            clock_report["attemptId"] = "passing-retry"
            clock_report["rows"][0]["metrics"][3]["upper"] = 10
            clock_page.locator("#report").fill(json.dumps(clock_report))
            clock_page.locator("#add").click()
            expect(clock_page.locator("#inspection")).to_contain_text("passing-retry")
            assert clock_page.locator("#comparison").text_content() == "retain-incumbent"
            assert "reported-metric-regression" in clock_page.locator("#inspection").text_content()
            clock_page.clock.fast_forward(60000)
            expect(clock_page.locator("#comparison")).to_have_text("expired")
            clock_page.evaluate(
                "window.dispatchEvent(new Event('focus')); document.dispatchEvent(new Event('visibilitychange'))"
            )
            assert clock_page.locator("#comparison").text_content() == "expired"
            clock_page.screenshot(path=str(screenshots / "expired-history.png"), full_page=True)
            assert not errors, errors
            assert not external, external
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
