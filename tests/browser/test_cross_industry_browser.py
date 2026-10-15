# SPDX-License-Identifier: Apache-2.0
"""Exercise the original cross-industry comparison and strict evidence recovery."""
import hashlib
import contextlib
import io
import tempfile
import sys
import json
import os
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    route = os.environ.get("CROSS_ROUTE", "cross_industry_alpha_factory/")
    errors = []
    external = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 1000})
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "request",
                lambda request: (
                    external.append(request.url)
                    if not request.url.startswith(f"http://127.0.0.1:{server.server_port}/")
                    else None
                ),
            )

            def wait(predicate):
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    if page.evaluate(predicate):
                        return
                    page.wait_for_timeout(50)
                raise AssertionError(f"Timed out: {predicate}")

            page.goto(f"http://127.0.0.1:{server.server_port}/{route}")
            wait("()=>document.querySelectorAll('#opportunities fieldset').length===3")

            def run():
                page.locator("button[type=submit]").click()
                page.locator("#result").wait_for(state="visible")
                return json.loads(page.locator("#raw").text_content())

            assert page.locator("nav a").first.get_attribute("href") in ["../index.html", "../../../index.html"]
            first = run()
            assert first["selected_id"] == "routing"
            assert first["ranking"][0]["score"] == 74.5
            with page.expect_download() as download:
                page.locator("#download").click()
            data = Path(download.value.path()).read_bytes()
            assert hashlib.sha256(data).hexdigest() in page.locator("#digest").text_content()
            canonical = json.dumps(json.loads(data), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
            assert hashlib.sha256(canonical).hexdigest() == first["input_sha256"]
            for selector in ["#weights-benefit", "#constraints-max_risk", "#opportunities [data-field=effort]"]:
                field = page.locator(selector).first
                previous = field.input_value()
                for value in ["1.00000000000000001", "1e1"]:
                    field.fill(value)
                    page.locator("#language").click()
                    assert page.locator(selector).first.input_value() == value
                    page.locator("#language").click()
                    page.locator("button[type=submit]").click()
                    page.locator("#error").wait_for(state="visible")
                    assert not page.locator("#result").is_visible()
                field.fill(previous)
            page.locator("#constraints-max_risk").fill("0")
            assert run()["selected_id"] is None
            page.locator("#reset").click()
            wait("()=>document.getElementById('constraints-max_risk').value==='60'")
            run()
            for language in ["en", "fr"]:
                if language == "fr":
                    page.locator("#language").click()
                assert page.locator("html").get_attribute("lang") == language
                for width in [320, 390, 768, 1440]:
                    page.set_viewport_size({"width": width, "height": 1000})
                    for scale in [100, 200]:
                        page.evaluate('(scale)=>document.documentElement.style.fontSize=scale+"%"', scale)
                        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), (
                            language,
                            width,
                            scale,
                        )
                page.evaluate('document.documentElement.style.fontSize="100%"')
                axe = os.environ.get("AXE_SCRIPT")
                if axe:
                    page.evaluate(Path(axe).read_text())
                    violations = page.evaluate(
                        'async()=> (await axe.run(document,{runOnly:{type:"tag",'
                        'values:["wcag2a","wcag2aa","wcag21aa"]}})).violations'
                    )
                    assert not violations, [(v["id"], v["nodes"]) for v in violations]
                evidence = ROOT / "evidence/cross-industry-browser"
                evidence.mkdir(parents=True, exist_ok=True)
                for width, name in [(1440, "desktop"), (390, "mobile")]:
                    page.set_viewport_size({"width": width, "height": 1000})
                    page.screenshot(path=str(evidence / f"{language}-{name}.png"), full_page=True)

            def import_data(raw):
                page.locator("#import").set_input_files(
                    {"name": "input.json", "mimeType": "application/json", "buffer": raw}
                )
                wait("()=>document.getElementById('import').value===''")

            import_data(
                json.dumps(
                    {
                        "schema_version": "cross-industry-browser-evidence-v1",
                        "input": json.loads(data),
                        "report": {"selected_id": "forged"},
                        "downloadedInputSha256": "forged",
                        "hashScope": "forged",
                    }
                ).encode()
            )
            assert json.loads(page.locator("#raw").text_content()) == first
            with page.expect_download() as saved_report:
                page.locator("#evidence").click()
            own_report = Path(saved_report.value.path()).read_bytes()
            import_data(own_report)
            assert page.locator("#result").is_visible()
            assert not page.locator("#error").is_visible()
            assert json.loads(page.locator("#raw").text_content()) == first
            notebook_path = (
                ROOT
                / "alpha_factory_v1/demos/cross_industry_alpha_factory"
                / "colab_deploy_alpha_factory_cross_industry_demo.ipynb"
            )
            cells = json.loads(notebook_path.read_text())["cells"]
            previous = Path.cwd()
            with tempfile.TemporaryDirectory() as temporary:
                try:
                    os.chdir(temporary)
                    namespace = {}
                    with contextlib.redirect_stdout(io.StringIO()):
                        for cell in cells:
                            if cell["cell_type"] == "code":
                                exec(compile("".join(cell["source"]), str(notebook_path), "exec"), namespace)
                    notebook_bytes = Path("cross-industry-evidence.json").read_bytes()
                    notebook_input_bytes = Path("cross-industry-input.json").read_bytes()
                finally:
                    os.chdir(previous)
            import_data(notebook_input_bytes)
            assert page.locator("#result").is_visible()
            assert json.loads(page.locator("#raw").text_content()) == first
            import_data(notebook_bytes)
            assert page.locator("#result").is_visible()
            assert not page.locator("#error").is_visible()
            assert json.loads(page.locator("#raw").text_content()) == first
            notebook_evidence = json.loads(notebook_bytes)
            notebook_evidence["report"] = {"forged": True}
            import_data(json.dumps(notebook_evidence).encode())
            assert page.locator("#result").is_visible()
            assert json.loads(page.locator("#raw").text_content()) == first
            import_data(data.replace(b"Manufacturing", b"\xffanufacturing"))
            assert page.locator("#error").is_visible()
            import_data(b"\xef\xbb\xbf" + data)
            assert page.locator("#error").is_visible()
            import_data(b'{"schema_version":1,"schema_version":2}')
            assert page.locator("#error").is_visible()
            import_data(data)
            page.locator("#add").click()
            assert page.locator("#opportunities fieldset").count() == 4
            page.locator("#opportunities fieldset").last.locator("button").click()
            assert page.locator("#opportunities fieldset").count() == 3
            page.evaluate(
                """()=>{const original=crypto.subtle.digest.bind(crypto.subtle);
                window.restoreDigest=()=>crypto.subtle.digest=original;
                crypto.subtle.digest=(...args)=>new Promise(resolve=>
                window.releaseDigest=async()=>resolve(await original(...args)));}"""
            )
            page.locator("button[type=submit]").click()
            wait("()=>!!window.releaseDigest")
            assert not page.locator("#result").is_visible()
            page.locator("#weights-benefit").fill("41")
            page.evaluate("()=>window.releaseDigest()")
            page.wait_for_timeout(100)
            assert not page.locator("#result").is_visible()
            page.evaluate("()=>{window.restoreDigest();}")
            page.evaluate(
                """()=>{const original=File.prototype.arrayBuffer;
                window.restoreFile=()=>File.prototype.arrayBuffer=original;
                File.prototype.arrayBuffer=function(){const file=this;return new Promise(resolve=>
                window.releaseFile=async()=>resolve(await original.call(file)));};}"""
            )
            page.locator("#import").set_input_files(
                {"name": "input.json", "mimeType": "application/json", "buffer": data}
            )
            wait("()=>!!window.releaseFile")
            page.locator("#reset").click()
            page.evaluate("()=>window.releaseFile()")
            page.wait_for_timeout(100)
            assert not page.locator("#result").is_visible()
            page.evaluate("()=>{window.restoreFile();}")
            page.reload()
            page.keyboard.press("Tab")
            assert page.locator(".skip").evaluate("(e)=>e===document.activeElement")
            assert not errors, errors
            assert not external, external
            browser.close()
        print(
            f"PASS: cross-industry EN/FR16layouts/{'Axe' if os.environ.get('AXE_SCRIPT') else 'Axe SKIPPED'}; "
            "ranking/noeligible; exact canonical and export hashes; strict numeric/UTF8/recovery; "
            "stale guards; keyboard and edits"
        )
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
