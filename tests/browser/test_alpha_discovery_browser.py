# SPDX-License-Identifier: Apache-2.0
"""Exercise local-only discovery, evidence boundaries, recovery and EN/FR continuity."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            executable = os.environ.get("CHROMIUM_EXECUTABLE")
            browser = p.chromium.launch(**({"executable_path": executable} if executable else {}))
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors, external = [], []
            screenshots = Path(os.environ.get("DISCOVERY_SCREENSHOTS", "/tmp/alpha-discovery-screenshots"))
            screenshots.mkdir(parents=True, exist_ok=True)
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: (
                    external.append(request.url)
                    if not request.url.startswith(f"http://127.0.0.1:{server.server_port}/")
                    else None
                ),
            )
            page.goto(f"http://127.0.0.1:{server.server_port}/successor/discover/")
            page.locator("#example").click()
            page.locator("#analyze").click()
            page.locator("#result").wait_for(state="visible")
            assert "not yet" in page.locator("#decision").text_content()
            assert "qualified reviewer" in page.locator("#experiment").text_content()
            assert page.locator("#hypotheses article").count() == 3
            page.screenshot(path=str(screenshots / "desktop-en.png"), full_page=True)
            with page.expect_download() as download:
                page.locator("#export").click()
            original = Path(download.value.path()).read_bytes()
            brief = json.loads(original)
            assert brief["analysis"]["independentProof"] is False
            assert brief["handoff"]["authority"] == "none"
            assert "not physical validation" in brief["handoff"]["gym"]["simulationLimits"]
            page.locator("#changed").fill("Changed input <script>alert(1)</script>")
            assert page.locator("#result").is_hidden()
            assert page.locator("#export").is_disabled()
            page.locator("#language").click()
            assert page.locator("#changed").input_value() == "Changed input <script>alert(1)</script>"
            assert page.locator("html").get_attribute("lang") == "fr"
            page.locator("#analyze").click()
            page.locator("#result").wait_for(state="visible")
            assert "pas encore" in page.locator("#decision").text_content()
            page.screenshot(path=str(screenshots / "desktop-fr.png"), full_page=True)
            page.evaluate("document.documentElement.style.zoom = 2")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(screenshots / "desktop-fr-200-percent.png"), full_page=True)
            page.evaluate("document.documentElement.style.zoom = 1")
            assert page.locator("#hypotheses script").count() == 0
            # Fresh context imports only inputs, never a claimed result or authority.
            brief["analysis"]["decision"] = "certified"
            brief["handoff"]["authority"] = "execute"
            context = browser.new_context(viewport={"width": 375, "height": 812})
            phone = context.new_page()
            phone.on("pageerror", lambda error: errors.append(str(error)))
            phone.goto(page.url)
            phone.locator("#restore").set_input_files(
                {"name": "brief.json", "mimeType": "application/json", "buffer": json.dumps(brief).encode()}
            )
            phone.wait_for_function("document.querySelector('#mission').value.includes('battery')")
            assert phone.locator("#result").is_hidden()
            phone.locator("#analyze").click()
            phone.locator("#result").wait_for(state="visible")
            assert '"authority": "none"' in phone.locator("#inspection").text_content()
            assert phone.evaluate("document.documentElement.scrollWidth <= innerWidth")
            phone.screenshot(path=str(screenshots / "mobile-en.png"), full_page=True)
            phone.locator("#metrics details").first.locator("summary").click()
            phone.locator("#m-0-candidate-value").fill("1.5")
            phone.locator("#analyze").click()
            assert phone.locator("#error").is_visible()
            assert phone.locator("#result").is_hidden()
            phone.locator("#example").click()
            phone.locator("#c-0-status").select_option("reported-fail")
            phone.locator("#analyze").click()
            phone.locator("#result").wait_for(state="visible")
            assert "Keep the incumbent" in phone.locator("#decision").text_content()
            # Invalid UTF-8 is rejected rather than silently rewritten into replacement characters.
            malformed = original.replace(b"A longer-lasting", b"A \xffonger-lasting", 1)
            assert malformed != original
            preserved = phone.locator("#mission").input_value()
            phone.locator("#restore").set_input_files(
                {"name": "malformed.json", "mimeType": "application/json", "buffer": malformed}
            )
            phone.wait_for_function("!document.querySelector('#error').hidden")
            assert phone.locator("#mission").input_value() == preserved
            # Interrupted file reading cannot overwrite newer user input.
            phone.evaluate(
                """() => { const original = File.prototype.arrayBuffer;
              File.prototype.arrayBuffer = function() { const file = this;
                return new Promise(resolve => { window.finishImport = async () => resolve(await original.call(file)); }); };
            }"""
            )
            phone.locator("#restore").set_input_files(
                {"name": "slow.json", "mimeType": "application/json", "buffer": original}
            )
            phone.wait_for_function("typeof window.finishImport === 'function'")
            phone.locator("#changed").fill("Newer edit must survive")
            phone.evaluate("window.finishImport()")
            phone.wait_for_function("!document.querySelector('#error').hidden")
            assert phone.locator("#changed").input_value() == "Newer edit must survive"
            assert phone.locator("#result").is_hidden()
            phone.locator("#example").click()
            phone.locator("#language").click()
            phone.locator("#analyze").click()
            phone.locator("#result").wait_for(state="visible")
            phone.screenshot(path=str(screenshots / "mobile-fr.png"), full_page=True)
            axe = os.environ.get("AXE_SCRIPT")
            if axe:
                # Inject via evaluate because the production page deliberately has a hash-only CSP.
                phone.evaluate(Path(axe).read_text())
                result = phone.evaluate(
                    "async () => (await axe.run(document, {runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations"
                )
                assert not result, json.dumps(result)
            screenshot = os.environ.get("DISCOVERY_SCREENSHOT")
            if screenshot:
                page.locator("#language").click()
                page.screenshot(path=screenshot, full_page=True)
            assert errors == [], errors
            assert external == [], external
            browser.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
