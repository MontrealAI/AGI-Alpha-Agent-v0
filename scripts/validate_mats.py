# SPDX-License-Identifier: Apache-2.0
"""Exercise search, exact exports, hostile inputs, accessibility and offline recovery."""
from __future__ import annotations

import argparse
from copy import deepcopy
from functools import partial
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
from threading import Thread
from typing import Any
import zipfile

from playwright.sync_api import expect, sync_playwright
from alpha_factory_v1.demos.meta_agentic_tree_search_v0.search_lab import (
    artifacts,
    canonical,
    digest,
    evaluate,
    read_json,
    verify,
)
from alpha_factory_v1.core.runtime.ascension import compile_plan, verify_plan
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401
from scripts.validate_gallery_catalog import Handler
from scripts.mats_evidence import ASSETS, CHECKS, SCHEMA

ROOT = Path(__file__).resolve().parents[1]


def validate(site: Path, output: Path, public_url: str | None = None, axe_script: Path | None = None) -> dict[str, Any]:
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
    cases = read_json(ROOT / "alpha_factory_v1/demos/meta_agentic_tree_search_v0/scenarios.json")
    errors: list[str] = []
    failures: list[str] = []
    records: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
            context.route(
                "https://**", lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort()
            )
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("response", lambda response: failures.append(response.url) if response.status >= 400 else None)
            for relative in ASSETS:
                response = context.request.get(origin + relative, headers={"Cache-Control": "no-cache"})
                assert response.ok, relative
                value = hashlib.sha256(response.body()).hexdigest()
                assert value == hashlib.sha256((site / relative).read_bytes()).hexdigest(), relative
                hashes[relative] = value
            page.goto(origin + "meta_agentic_tree_search_v0/")
            expect(page.locator("#export")).to_be_enabled()
            for case in cases:
                page.locator("#case").select_option(case["id"])
                native = evaluate(case)
                expect(page.locator("#hash")).to_have_text("Run SHA-256 · " + native["sha256"])
                expect(page.locator("#export")).to_be_enabled()
                with page.expect_download() as download:
                    page.locator("#download").click()
                path = output / f"{case['id']}.json"
                download.value.save_as(path)
                report = verify(read_json(path))
                assert report == native
                with page.expect_download() as archive:
                    page.locator("#export").click()
                archive_path = output / f"{case['id']}.zip"
                archive.value.save_as(archive_path)
                with zipfile.ZipFile(archive_path) as bundle:
                    assert {name: bundle.read(name) for name in bundle.namelist()} == artifacts(report)
                assert verify_plan(compile_plan(report["result"]["jobs"]))["valid"]
                assert all(report["result"]["inputSha256"] in job["goal"] for job in report["result"]["jobs"])
                if case["id"] == "proxy-trap":
                    expect(page.locator("#status")).to_have_text("Keep the baseline")
                    expect(page.locator(".gate.hold")).to_contain_text("Escaped-defect ceiling")
                records.append({"id": case["id"], "sha256": report["sha256"], "status": report["result"]["status"]})
            page.locator("#import").set_input_files(output / "release-design.json")
            expect(page.locator("#export")).to_be_enabled()
            page.locator("#iterations").fill("200")
            expect(page.locator("#export")).to_be_disabled()
            page.locator("#run").click()
            changed = deepcopy(cases[0])
            changed["search"]["iterations"] = 200
            expect(page.locator("#hash")).to_have_text("Run SHA-256 · " + evaluate(changed)["sha256"])
            page.get_by_text("Inspect node statistics and the rollout", exact=True).click()
            page.locator("#iteration").fill("1")
            expect(page.locator("#iteration-label")).to_have_text("1 / 200")
            page.locator("#node").select_option("0")
            expect(page.locator("#node-detail")).to_contain_text("1 visits")
            assert page.locator("#tree circle").count() == 2
            page.locator("#next").click()
            expect(page.locator("#iteration-label")).to_have_text("2 / 200")
            page.locator("#iteration").fill("200")
            page.locator("#node").select_option("0")
            expect(page.locator("#node-detail")).to_contain_text("200 visits")
            page.get_by_text("Inspect a held-out workload and its schedule", exact=True).click()
            page.locator("#episode").fill("80")
            expect(page.locator("#episode-detail")).to_contain_text("Workload 80:")
            assert page.locator("#schedule tr").count() == len(cases[0]["stages"])
            page.locator("#auditOracle").uncheck()
            page.locator("#run").click()
            changed["search"]["auditOracle"] = False
            expect(page.locator("#hash")).to_have_text("Run SHA-256 · " + evaluate(changed)["sha256"])
            expect(page.locator("#gap")).to_have_text("Not audited")
            page.locator("#iterations").fill("241")
            page.locator("#run").click()
            expect(page.locator("#error")).to_be_visible()
            expect(page.locator("#export")).to_be_disabled()
            page.locator("#case").select_option("api-migration")
            expect(page.locator("#export")).to_be_enabled()
            page.locator(".editor summary").click()
            page.locator("#json").fill(canonical(cases[0]).decode())
            expect(page.locator("#export")).to_be_disabled()
            expect(page.locator("#run")).to_be_disabled()
            page.locator("#apply").click()
            expect(page.locator("#export")).to_be_enabled()
            page.locator(".editor summary").click()
            forged = read_json(output / "release-design.json")
            forged["result"]["trace"] = []
            forged["sha256"] = digest({k: v for k, v in forged.items() if k != "sha256"})
            for name, data, message in (
                ("forged", canonical(forged), "differs from recomputation"),
                ("duplicate", b'{"schema":1,"schema":2}', "Duplicate JSON key"),
                ("large", b" " * 1000001, "exceeds"),
                ("utf8", b"\xff", "encoded data"),
                ("nonfinite", b'{"x":1e999}', "Non-finite"),
                ("unknown-run-schema", canonical({**forged, "schema": "unknown-run"}), "Unsupported"),
            ):
                page.locator("#import").set_input_files(
                    {"name": f"{name}.json", "mimeType": "application/json", "buffer": data}
                )
                expect(page.locator("#error")).to_contain_text(message)
                expect(page.locator("#export")).to_be_disabled()
            page.locator("#case").select_option("data-pipeline")
            expect(page.locator("#export")).to_be_enabled()
            page.evaluate("localStorage.setItem('unrelated-workspace','retain')")
            page.locator("#save").click()
            page.locator("#iterations").fill("200")
            page.locator("#restore").click()
            expect(page.locator("#iterations")).to_have_value("120")
            page.locator("#clear").click()
            assert page.evaluate("localStorage.getItem('unrelated-workspace')") == "retain"
            page.locator("#restore").click()
            expect(page.locator("#error")).to_contain_text("No saved MATS settings")
            hostile = deepcopy(cases[0])
            hostile["note"] = '<img src="invalid" onerror="window.matsAttack=1">'
            page.locator("#import").set_input_files(
                {"name": "text.json", "mimeType": "application/json", "buffer": canonical(hostile)}
            )
            expect(page.locator("#case-note")).to_have_text(hostile["note"])
            assert page.evaluate("window.matsAttack === undefined")
            page.goto(origin + "alpha_factory_v1/demos/meta_agentic_tree_search_v0/")
            expect(page.locator("#export")).to_be_enabled()
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                page.screenshot(path=str(output / f"mats-{width}.png"), full_page=True)
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    violations = page.evaluate(
                        "async () => (await axe.run(document, {runOnly:['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
                    assert not violations, violations
            page.locator("#iterations").focus()
            page.keyboard.press("Tab")
            assert page.locator("#depth").evaluate("element => element === document.activeElement")
            page.goto(origin + "meta_agentic_tree_search_v0/research.html")
            page.locator("#offline-mode").click()
            original = read_json(ROOT / "docs/meta_agentic_tree_search_v0/assets/logs.json")
            expect(page.locator("#logs-panel")).to_contain_text(original["logs"][0])
            assert page.locator("#logs-panel").inner_text().splitlines() == original["logs"]
            expect(page.get_by_role("link", name="Open editable workspace ↗")).to_be_visible()
            page.goto(origin + "meta_agentic_tree_search_v0/")
            expect(page.locator("#export")).to_be_enabled()
            page.evaluate("() => navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            expect(page.locator("#export")).to_be_enabled()
            page.locator("#case").select_option("proxy-trap")
            expect(page.locator("#status")).to_have_text("Keep the baseline")
            assert not errors and not failures, {"browser_errors": errors, "http_failures": failures}
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
    report = {
        "schema": SCHEMA,
        "passed": True,
        "origin": origin,
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "version": json.loads((ROOT / "alpha_factory_v1/demos/catalog.json").read_text())["release"],
        "cases": records,
        "checks": sorted(CHECKS - (set() if axe_script else {"axe-wcag-a-aa-no-violations"})),
        "assets": hashes,
        "browser_errors": errors,
        "http_failures": failures,
    }
    (output / "mats.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/mats-browser"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    validate(args.site, args.output, args.url, args.axe_script)
    print(
        "Verified MATS tree search, exact exports, hostile imports, "
        "accessibility, offline recovery and original replay"
    )
