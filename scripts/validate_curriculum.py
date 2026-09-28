# SPDX-License-Identifier: Apache-2.0
"""Exercise the curriculum, exact exports, hostile inputs, accessibility and offline replay."""
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
from alpha_factory_v1.demos.meta_agentic_agi_v3.curriculum_lab import (
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
from scripts.curriculum_evidence import ASSETS, CHECKS, SCHEMA

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
    cases = read_json(ROOT / "alpha_factory_v1/demos/meta_agentic_agi_v3/scenarios.json")
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
            page.goto(origin + "meta_agentic_agi_v3/")
            expect(page.locator("#download")).to_be_enabled()
            for case in cases:
                page.locator("#case").select_option(case["id"])
                native = evaluate(case)
                expect(page.locator("#run-hash")).to_have_text("Run SHA-256: " + native["sha256"])
                with page.expect_download() as download:
                    page.locator("#download-run").click()
                path = output / f"{case['id']}.json"
                download.value.save_as(path)
                report = verify(read_json(path))
                assert report == native
                with page.expect_download() as archive:
                    page.locator("#download").click()
                archive_path = output / f"{case['id']}.zip"
                archive.value.save_as(archive_path)
                with zipfile.ZipFile(archive_path) as bundle:
                    assert {name: bundle.read(name) for name in bundle.namelist()} == artifacts(report)
                assert verify_plan(compile_plan(report["result"]["jobs"]))["valid"]
                assert all(report["inputSha256"] in job["goal"] for job in report["result"]["jobs"])
                if case["id"] in {"coverage-trap", "resource-limit"}:
                    expect(page.locator("#review-state")).to_have_text("Hold · baseline retained")
                    assert page.locator(".gate.hold").count() > 0
                records.append({"id": case["id"], "sha256": report["sha256"], "status": report["result"]["status"]})
            page.get_by_text("Inputs & reproducibility", exact=True).click()
            page.locator("#import").set_input_files(output / "balanced.json")
            expect(page.locator("#status")).to_contain_text("independently recomputed")
            page.locator("#rounds").fill("8")
            expect(page.locator("#download")).to_be_disabled()
            page.locator("#run").click()
            changed = deepcopy(cases[0])
            changed["rounds"] = 8
            expect(page.locator("#run-hash")).to_have_text("Run SHA-256: " + evaluate(changed)["sha256"])
            page.locator("#round").fill("1")
            expect(page.locator("#round-label")).to_have_text("1")
            current = evaluate(changed)["result"]["history"][0]
            assert page.locator("#task option").count() == len(current["tasks"])
            expect(page.locator("#examples")).to_contain_text(str(current["tasks"][0]["examples"][0][1]))
            expect(page.locator("#solution")).to_contain_text("hypotheses")
            assert page.locator("#candidates tr").count() == len(current["candidates"])
            page.get_by_text("Inspect complete parent → child lineage", exact=True).click()
            expect(page.locator("#lineage")).to_contain_text("baseline seed")
            page.locator("#heldout-task").select_option("3")
            expect(page.locator("#heldout-detail")).to_contain_text("Reference:")
            page.locator("#rounds").fill("13")
            page.locator("#run").click()
            expect(page.locator("#status")).to_contain_text("integer")
            expect(page.locator("#download")).to_be_disabled()
            page.locator("#source").fill(canonical(cases[0]).decode())
            page.locator("#run").click()
            expect(page.locator("#status")).to_contain_text("Apply the edited JSON")
            page.locator("#apply").click()
            expect(page.locator("#download")).to_be_disabled()
            page.locator("#run").click()
            expect(page.locator("#download")).to_be_enabled()
            forged = read_json(output / "balanced.json")
            forged["result"]["history"] = []
            forged["sha256"] = digest({k: v for k, v in forged.items() if k != "sha256"})
            for name, data in [
                ("forged", canonical(forged)),
                ("duplicate", b'{"schema":1,"schema":2}'),
                ("large", b" " * 1000001),
                ("utf8", b"\xff"),
                ("nonfinite", b'{"x":1e999}'),
                ("unknown", canonical({**cases[0], "schema": "unknown"})),
            ]:
                page.locator("#import").set_input_files(
                    {"name": f"{name}.json", "mimeType": "application/json", "buffer": data}
                )
                expect(page.locator("#status")).to_contain_text("Import rejected")
                expect(page.locator("#download")).to_be_disabled()
            page.locator("#case").select_option("balanced")
            expect(page.locator("#download")).to_be_enabled()
            page.evaluate("localStorage.setItem('unrelated-workspace','retain')")
            page.locator("#save").click()
            page.locator("#rounds").fill("3")
            page.locator("#restore").click()
            expect(page.locator("#rounds")).to_have_value("10")
            expect(page.locator("#download")).to_be_disabled()
            page.locator("#forget").click()
            assert page.evaluate("localStorage.getItem('unrelated-workspace')") == "retain"
            page.locator("#restore").click()
            expect(page.locator("#storage-status")).to_contain_text("No saved settings")
            hostile = deepcopy(cases[0])
            hostile["note"] = '<img src="invalid" onerror="window.curriculumAttack=1">'
            page.locator("#import").set_input_files(
                {"name": "text.json", "mimeType": "application/json", "buffer": canonical(hostile)}
            )
            expect(page.locator("#case-note")).to_have_text(hostile["note"])
            assert page.evaluate("window.curriculumAttack === undefined")
            page.goto(origin + "alpha_factory_v1/demos/meta_agentic_agi_v3/")
            expect(page.locator("#download")).to_be_enabled()
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1000 if width == 1440 else 844})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), width
                page.screenshot(path=str(output / f"curriculum-{width}.png"), full_page=True)
                if axe_script:
                    page.add_script_tag(path=str(axe_script.resolve()))
                    violations = page.evaluate(
                        "async () => (await axe.run(document, {runOnly:['wcag2a','wcag2aa','wcag21aa']})).violations"
                    )
                    assert not violations, violations
            page.locator("#seed").focus()
            page.keyboard.press("Tab")
            assert page.locator("#rounds").evaluate("element => element === document.activeElement")
            page.goto(origin + "meta_agentic_agi_v3/research.html")
            page.locator("#offline-mode").click()
            original = read_json(ROOT / "docs/meta_agentic_agi_v3/assets/logs.json")
            expect(page.locator("#logs-panel")).to_contain_text(original["logs"][0])
            assert page.locator("#logs-panel").inner_text().splitlines() == original["logs"]
            page.goto(origin + "meta_agentic_agi_v3/")
            expect(page.locator("#download")).to_be_enabled()
            page.evaluate("() => navigator.serviceWorker.ready")
            page.reload()
            page.wait_for_function("navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            page.reload()
            expect(page.locator("#download")).to_be_enabled()
            page.locator("#case").select_option("coverage-trap")
            expect(page.locator("#review-state")).to_have_text("Hold · baseline retained")
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
    (output / "curriculum.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("docs"))
    parser.add_argument("--output", type=Path, default=Path("evidence/curriculum-browser"))
    parser.add_argument("--url")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    validate(args.site, args.output, args.url, args.axe_script)
    print("Verified curriculum, exact exports, hostile imports, accessibility, offline recovery and original replay")
