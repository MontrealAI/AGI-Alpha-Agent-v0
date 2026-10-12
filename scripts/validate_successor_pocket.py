# SPDX-License-Identifier: Apache-2.0
"""Verify the personal SUCCESSOR lab and its downloaded offline round trip."""

from __future__ import annotations

import argparse
import hashlib
import json
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from typing import Any

from playwright.sync_api import expect, sync_playwright

from scripts.validate_ascension import Handler, inspect
from scripts.validate_successor_build import validate_workshop


def validate(site: Path, output: Path, public_url: str | None = None) -> None:
    """Exercise real computations, portable copies, accessibility and failure recovery."""
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public acceptance requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        Thread(target=server.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    report: dict[str, Any] = {"passed": False, "checks": [], "errors": [], "accessibility": []}
    axe = Path("tests/browser/node_modules/axe-core/axe.min.js").read_text()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            page = context.new_page()
            page.on("pageerror", lambda error: report["errors"].append(str(error)))
            page.goto(origin + "successor/play/", wait_until="networkidle")
            expect(page.locator("#app")).to_be_visible()
            expect(page.locator("#loading")).to_be_hidden()
            request_urls: list[str] = []
            page.on("request", lambda request: request_urls.append(request.url))
            name = '</script><img src=x onerror="alert(1)">'
            page.locator("#lab-name").fill(name)
            page.locator("#run").focus()
            page.keyboard.press("Enter")
            expect(page.locator("#checks")).to_have_text("6 / 6")
            expect(page.locator("#programs")).to_have_text("4")
            expect(page.locator("#result-title")).to_be_focused()
            expect(page.locator("#result-title")).to_have_text(name)
            expect(page.locator("#result-title img")).to_have_count(0)
            with page.expect_download() as saved:
                page.locator("#save").click()
            portable = output.resolve() / "My-SUCCESSOR-Omega.html"
            saved.value.save_as(portable)
            assert portable.stat().st_size < 150_000
            report["download_sha256"] = hashlib.sha256(portable.read_bytes()).hexdigest()
            assert "Apache License" in portable.read_text()
            report["checks"] += ["real-engine-four-candidates-six-checks", "keyboard-focus", "escaped-personal-name"]
            with page.expect_download() as data:
                page.locator("#outcome details").last.locator("summary").click()
                page.locator("#export-evidence").click()
            evidence_path = output / "experiment.json"
            data.value.save_as(evidence_path)
            evidence = json.loads(evidence_path.read_text())
            assert evidence["evaluation"]["correctness"] is True
            assert evidence["evaluation"]["authority"] == []
            assert evidence["request"]["seed"] == 42
            assert len(evidence["discovery"]["attempts"]) == 4
            assert not request_urls, request_urls
            assert inspect(page, "localStorage.length === 0 && sessionStorage.length === 0")
            report["checks"] += ["complete-evidence-download", "no-network-or-storage"]
            offline = browser.new_context(offline=True, viewport={"width": 1440, "height": 1000})
            local = offline.new_page()
            local.on("pageerror", lambda error: report["errors"].append(str(error)))
            local.goto(portable.as_uri())
            expect(local.locator("#app")).to_be_visible()
            expect(local.locator("#lab-name")).to_have_value(name)
            expect(local.locator("#count")).to_have_text("1")
            expect(local.locator("#status")).to_contain_text("historical")
            local.locator("#language").click()
            local.locator("#lab-name").fill("Mon univers Ω")
            local.locator("#challenge").select_option("1000")
            local.locator("#again").click()
            expect(local.locator("#count")).to_have_text("2")
            expect(local.locator("#checks")).to_have_text("6 / 6")
            expect(local.locator("#status")).to_contain_text("prête")
            fresh = json.loads(local.locator("#evidence").text_content() or "{}")
            assert fresh["request"]["seed"] != evidence["request"]["seed"]
            assert fresh["frozen"]["release_hash"] != evidence["frozen"]["release_hash"]
            assert fresh["evaluation"]["institutional_verdict"] == "HOLD"
            with local.expect_download() as resaved:
                local.locator("#save").click()
            again_file = output.resolve() / "saved-again.html"
            resaved.value.save_as(again_file)
            restored = offline.new_page()
            restored.goto(again_file.as_uri())
            expect(restored.locator("html")).to_have_attribute("lang", "fr")
            expect(restored.locator("#lab-name")).to_have_value("Mon univers Ω")
            expect(restored.locator("#count")).to_have_text("2")
            report["checks"] += ["offline-file-runs", "new-inputs-new-proof", "second-download-restores", "french"]
            for width, language, large in ((1440, "fr", False), (390, "en", False), (320, "fr", True)):
                if local.locator("html").get_attribute("lang") != language:
                    local.locator("#language").click()
                if (local.locator("#large").get_attribute("aria-pressed") == "true") != large:
                    local.locator("#large").click()
                local.set_viewport_size({"width": width, "height": 1000})
                assert inspect(local, "document.documentElement.scrollWidth <= innerWidth + 1")
                assert inspect(local, "parseFloat(getComputedStyle(document.body).fontSize) >= 18")
                inspect(local, axe + "; void 0")
                audit = inspect(
                    local,
                    "axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','best-practice']}})",
                )
                report["accessibility"].append(
                    {"width": width, "language": language, "large": large, "violations": audit["violations"]}
                )
                assert not audit["violations"], audit["violations"]
                local.screenshot(path=str(output / f"lab-{width}-{language}.png"), full_page=True)
            report["checks"] += ["mobile-and-large-text", "axe-no-violations"]
            local.locator("#lab-name").fill(" ")
            local.locator("#run").click()
            expect(local.locator("#lab-name")).to_have_attribute("aria-invalid", "true")
            expect(local.locator("#status")).to_be_focused()
            expect(local.locator("#count")).to_have_text("2")
            local.locator("#lab-name").fill("Recovered Ω")
            local.locator("#run").click()
            expect(local.locator("#count")).to_have_text("3")
            report["checks"].append("invalid-input-preserves-experiments")
            nojs = browser.new_context(java_script_enabled=False)
            fallback = nojs.new_page()
            fallback.goto(origin + "successor/play/")
            expect(fallback.locator("noscript")).to_be_visible()
            expect(fallback.locator("#app")).to_be_hidden()
            report["checks"].append("no-javascript-guidance")
            assert not report["errors"], report["errors"]
            report["builder"] = validate_workshop(browser, origin, output, axe)
            report["passed"] = True
            browser.close()
    finally:
        (output / "pocket.json").write_text(json.dumps(report, indent=2) + "\n")
        if server:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/successor-pocket"))
    parser.add_argument("--url")
    args = parser.parse_args()
    validate(args.site, args.output, args.url)
