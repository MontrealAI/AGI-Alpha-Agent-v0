# SPDX-License-Identifier: Apache-2.0
"""Exercise the dedicated bounded planner; accepts AXE_SCRIPT for accessibility."""
import json
import os
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    route = os.environ.get("PLANNER_ROUTE", "alpha_super_planner_v1/")
    url = f"http://127.0.0.1:{server.server_port}/{route}"
    errors = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(url)
            page.locator("button[type=submit]").click()
            assert page.locator("#result").is_visible()
            result = json.loads(page.locator("#artifact").text_content())
            assert result["result"]["selected_ids"] == ["draft", "publish", "research", "review"]
            with page.expect_download() as download:
                page.locator("#export").click()
            assert download.value.suggested_filename == "bounded-plan-evidence.json"
            assert json.loads(Path(download.value.path()).read_text()) == result
            for language in ["en", "fr"]:
                if language == "fr":
                    page.locator("#language").click()
                assert page.locator("html").get_attribute("lang") == language
                for width in [320, 390, 768, 1440]:
                    page.set_viewport_size({"width": width, "height": 1000})
                    for scale in [100, 200]:
                        page.evaluate('(scale) => document.documentElement.style.fontSize = scale + "%"', scale)
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (
                            language,
                            width,
                            scale,
                        )
                page.evaluate('document.documentElement.style.fontSize = "100%"')
                axe = os.environ.get("AXE_SCRIPT")
                if axe:
                    page.evaluate(Path(axe).read_text())
                    violations = page.evaluate(
                        'async () => (await axe.run(document, {runOnly:{type:"tag",'
                        'values:["wcag2a","wcag2aa","wcag21aa"]}})).violations'
                    )
                    assert not violations, [(v["id"], v["nodes"]) for v in violations]
                evidence = ROOT / "evidence" / "planner-browser"
                evidence.mkdir(parents=True, exist_ok=True)
                page.set_viewport_size({"width": 1440 if language == "en" else 390, "height": 1000})
                page.evaluate("document.activeElement.blur()")
                page.screenshot(path=str(evidence / f"{language}.png"), full_page=True)
            page.locator("#budget").fill("0")
            assert not page.locator("#result").is_visible()
            page.locator("button[type=submit]").click()
            assert json.loads(page.locator("#artifact").text_content())["result"]["selected_ids"] == []
            page.locator("#import").set_input_files(
                {"name": "bad.json", "mimeType": "application/json", "buffer": b'{"schema":"bad"}'}
            )
            page.locator("#error").wait_for(state="visible")
            assert not page.locator("#result").is_visible()
            page.locator("#import").set_input_files(
                {
                    "name": "good.json",
                    "mimeType": "application/json",
                    "buffer": json.dumps({**result, "result": {"forged": True}}).encode(),
                }
            )
            page.wait_for_function("document.getElementById('budget').value === '12'")
            page.locator("button[type=submit]").click()
            assert json.loads(page.locator("#artifact").text_content()) == result
            page.locator("#goal").fill("")
            page.locator("#language").click()
            assert not page.locator("#result").is_visible()
            assert page.locator("#goal").input_value() == ""
            page.locator("#example").click()
            page.locator("#add-task").click()
            assert page.locator(".task").count() == 6
            page.locator(".remove").last.click()
            assert page.locator(".task").count() == 5
            page.reload()
            page.keyboard.press("Tab")
            assert page.locator(".skip").evaluate("(el)=>el===document.activeElement")
            assert not errors, errors
            browser.close()
        print(
            "PASS: EN/FR, eight layouts at100/200%, Axe, export/import, invalid input, "
            "stale result, keyboard, task edits"
        )
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
