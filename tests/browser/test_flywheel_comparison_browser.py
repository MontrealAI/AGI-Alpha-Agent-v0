# SPDX-License-Identifier: Apache-2.0
"""Rendered EN/FR comparison, denominator, export and missing-acceptance checks."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

from scripts.generate_alpha_flywheel import build
from scripts.validate_alpha_flywheel import CANONICAL_SOURCES, verify_packaged

ROOT = Path(__file__).resolve().parents[2]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass


def main() -> None:
    checks: list[str] = []
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="comparison-browser-") as temporary:
        root = Path(temporary)
        for name in CANONICAL_SOURCES:
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        build(root)
        verify_packaged(root / "docs", root)
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root / "docs")))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(executable_path=os.environ.get("CHROMIUM_EXECUTABLE") or None)
                context = browser.new_context(accept_downloads=True, viewport={"width": 1440, "height": 1000})
                page = context.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                url = f"http://127.0.0.1:{server.server_port}/flywheel/"
                page.goto(url + "#operational-results")
                expect(page.locator("#comparison-status")).to_contain_text("6/6")
                expect(page.locator("#comparison-outcomes tbody tr")).to_have_count(3)
                expect(page.locator("#comparison-contrasts")).to_contain_text("Real full cost unknown")
                checks.append("all six planned outcomes visible; cost qualification beside the result")
                for stage, expected in (
                    ("planned", "0/6"),
                    ("partially-executed", "3/6"),
                    ("additional-costs-unknown", "6/6"),
                ):
                    page.locator("#comparison-stage").select_option(stage)
                    expect(page.locator("#comparison-status")).to_contain_text(expected)
                expect(page.locator("#comparison-contrasts")).to_contain_text("withheld")
                page.locator("#comparison-stage").select_option("planned")
                expect(page.locator("#comparison-contrasts")).to_contain_text("[-2, 2]")
                checks.append("missing and partial trials preserve the denominator and unresolved range")
                for language in ("en", "fr"):
                    page.locator("#lang-" + language).click()
                    page.locator("#comparison-stage").select_option("reconciled-fixture")
                    expect(page.locator("#comparison-status")).to_contain_text("6/6")
                    for width in (320, 390, 1440):
                        page.set_viewport_size({"width": width, "height": 1000})
                        page.locator("#operational-results").scroll_into_view_if_needed()
                        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                        axe_path = os.environ.get("AXE_SCRIPT")
                        if axe_path:
                            page.evaluate(Path(axe_path).read_text() + ";void 0")
                            violations = page.evaluate(
                                "async(options)=>(await axe.run(document,options)).violations",
                                {
                                    "runOnly": {
                                        "type": "tag",
                                        "values": ["wcag2a", "wcag2aa", "wcag21aa", "best-practice"],
                                    }
                                },
                            )
                            assert not violations, violations
                        checks.append(f"{language} width {width}: no overflow; optional axe check")
                    with page.expect_download() as download:
                        page.locator("#comparison-export").click()
                    actual = json.loads(Path(download.value.path()).read_bytes())
                    expected_data = json.loads(
                        (root / "scripts/templates/alpha-flywheel/comparison-evidence.json").read_bytes()
                    )
                    assert actual == expected_data
                    assert len(actual["stages"]) == 4
                    checks.append(f"{language}: exact plan and all four stages exported")
                screenshot = os.environ.get("COMPARISON_UI_SCREENSHOT")
                if screenshot:
                    page.set_viewport_size({"width": 1440, "height": 1000})
                    page.locator("#operational-results").screenshot(path=screenshot)
                path = root / "scripts/templates/alpha-flywheel/comparison-evidence.json"
                value = json.loads(path.read_bytes())
                value["stages"]["reconciled-fixture"]["cells"][0]["acceptance_digest"] = None
                path.write_text(json.dumps(value))
                build(root)
                page.goto(url + "?missing-acceptance=1#operational-results")
                expect(page.locator("#comparison-status")).to_contain_text("5/6")
                expect(page.locator("#comparison-status")).to_contain_text("unassessed")
                checks.append("missing acceptance visibly reduces success and leaves an unassessed case")
                assert not errors, errors
                browser.close()
        finally:
            server.shutdown()
    report = {
        "status": "pass",
        "checks": checks,
        "page_errors": errors,
        "axe_enabled": bool(os.environ.get("AXE_SCRIPT")),
    }
    output = os.environ.get("COMPARISON_UI_REPORT")
    if output:
        Path(output).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
