# SPDX-License-Identifier: Apache-2.0
"""Exercise the original business evidence portfolio and strict evidence recovery."""
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
    route = os.environ.get("BUSINESS_ROUTE", "alpha_agi_business_2_v1/")
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
            assert first["plan"]["selectedIds"] == ["onboarding", "support"]
            assert first["plan"]["totalValuePoints"] == 21
            with page.expect_download() as download:
                page.locator("#download").click()
            data = Path(download.value.path()).read_bytes()
            canonical = json.dumps(json.loads(data), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
            assert hashlib.sha256(canonical).hexdigest() == first["inputDigest"]
            for selector in [
                "#policy [data-key=effortHours]",
                "#observations [data-key=baseline]",
                "#opportunities [data-key=valuePoints]",
            ]:
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
            page.locator("#policy [data-key=effortHours]").fill("0")
            assert run()["plan"]["selectedIds"] == []
            page.locator("#reset").click()
            wait("()=>document.querySelector('#policy [data-key=effortHours]').value==='12'")
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
                evidence = ROOT / "evidence/business2-browser"
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
                        "schema": "agialpha.business2.evidence.v1",
                        "input": json.loads(data),
                        "report": {"selected_id": "forged"},
                    }
                ).encode()
            )
            assert json.loads(page.locator("#raw").text_content()) == first
            notebook_path = (
                ROOT / "alpha_factory_v1/demos/alpha_agi_business_2_v1/colab_alpha_agi_business_2_demo.ipynb"
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
                    notebook_bytes = Path("business2-evidence.json").read_bytes()
                    notebook_input_bytes = Path("business2-input.json").read_bytes()
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
            assert json.loads(page.locator("#raw").text_content()) == first
            import_data(data.replace(b"Synthetic", b"\xffynthetic"))
            assert page.locator("#error").is_visible()
            import_data(b'{"schema_version":1,"schema_version":2}')
            assert page.locator("#error").is_visible()
            import_data(data + b" " * 128000)
            assert page.locator("#error").is_visible()
            import_data(b"\xef\xbb\xbf" + data)
            assert page.locator("#error").is_visible()
            import_data(data)
            large = json.loads(data)
            large["observations"] = [
                {
                    "id": f"o-{i}",
                    "source": str(i).ljust(200, "x"),
                    "metric": "m" * 200,
                    "unit": "u" * 200,
                    "baseline": 0,
                    "current": 1,
                    "direction": "increase",
                }
                for i in range(64)
            ]
            large["opportunities"] = [
                {
                    "id": f"p-{i}",
                    "title": "p" * 200,
                    "effortHours": 1,
                    "valuePoints": 1,
                    "evidenceIds": [f"o-{j}" for j in range(64)],
                }
                for i in range(16)
            ]
            import_data(json.dumps(large).encode())
            page.locator("#result").wait_for(state="visible")
            with page.expect_download() as exported:
                page.locator("#evidence").click()
            bundle = Path(exported.value.path()).read_bytes()
            assert len(bundle) > 128000
            import_data(bundle)
            assert page.locator("#result").is_visible()
            page.evaluate(
                """()=>{for(const el of document.querySelectorAll(
                '#observations [data-key=source],#observations [data-key=metric],'+
                '#observations [data-key=unit]'))el.value='🍁'.repeat(200);
                document.querySelector('#workspace').dispatchEvent(new Event('input',{bubbles:true}));}"""
            )
            page.locator("button[type=submit]").click()
            assert page.locator("#error").is_visible()
            assert not page.locator("#result").is_visible()
            import_data(data)
            page.locator("#addOpportunity").click()
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
            page.locator("#policy [data-key=effortHours]").fill("11")
            page.evaluate("()=>{window.restoreDigest();}")
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
            page.locator("#policy [data-key=effortHours]").fill("10")
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
            f"PASS: business2 EN/FR16layouts/{'Axe' if os.environ.get('AXE_SCRIPT') else 'Axe SKIPPED'}; "
            "exact portfolio/no-selection; exact canonical input/report hashes; "
            "strict numeric/UTF8/recovery; stale guards; keyboard and edits"
        )
    finally:
        server.shutdown()


if __name__ == "__main__":
    main()
