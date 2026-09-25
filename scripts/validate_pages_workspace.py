# SPDX-License-Identifier: Apache-2.0
"""Require usable browser missions, native handoff, model inference and offline recovery."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
import json
import time
import tempfile
from pathlib import Path
from threading import Thread
from typing import Any

from playwright.sync_api import Page, sync_playwright, expect

from alpha_factory_v1.core.runtime.models import Mission
from alpha_factory_v1.core.runtime.engine import Engine
from alpha_factory_v1.core.runtime.store import Journal, digest
from scripts.validate_gallery_catalog import Handler


def inspect(page: Page, expression: str) -> Any:
    """Inspect through DevTools without weakening the page's actual CSP."""
    if expression.startswith("() =>"):
        expression = "(" + expression + ")()"
    session = page.context.new_cdp_session(page)
    try:
        response = session.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
                "allowUnsafeEvalBlockedByCSP": True,
            },
        )
        assert "exceptionDetails" not in response, response
        return response["result"].get("value")
    finally:
        session.detach()


def wait_for(page: Page, expression: str) -> None:
    deadline = time.monotonic() + 60
    while not inspect(page, expression):
        if time.monotonic() > deadline:
            raise TimeoutError(expression)
        page.wait_for_timeout(100)


def validate(site: Path, output: Path, model: bool = False, public_url: str | None = None) -> dict[str, Any]:
    """Exercise the real UI; provider mocks are not used for model acceptance."""
    output.mkdir(parents=True, exist_ok=True)
    server = None
    thread = None
    if public_url:
        if not public_url.startswith("https://"):
            raise ValueError("Public validation requires HTTPS")
        origin = public_url.rstrip("/") + "/"
    else:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(site.resolve())))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        origin = f"http://127.0.0.1:{server.server_port}/project/"
    report: dict[str, Any] = {
        "origin": public_url or "local project subpath",
        "missions": [],
        "model_required": model,
    }
    errors: list[str] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            context = browser.new_context(reduced_motion="reduce", viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(origin)
            wait_for(page, "document.getElementById('mission-goal').value.length > 0")
            page.screenshot(path=str(output / "workspace-desktop.png"))
            assert page.locator(".demo-card").count() == 26
            assert page.locator("a button").count() == 0
            for kind in ("allocation", "research", "schedule", "forecast"):
                page.locator(f'[data-kind="{kind}"]').click()
                page.locator("#run-mission").click()
                page.locator("#mission-result").wait_for(state="visible")
                data = json.loads(page.locator("#result-json").text_content())
                assert data["kind"] == kind and data["checks"]
                native = json.loads(page.locator("#mission-json").input_value())
                Mission.model_validate(native)
                report["missions"].append({"kind": kind, "method": data["method"], "metrics": data["metrics"]})
            page.locator('[data-kind="allocation"]').click()
            page.get_by_label("Budget", exact=True).fill("6")
            page.locator("#run-mission").click()
            page.locator("#mission-result").wait_for(state="visible")
            changed = json.loads(page.locator("#result-json").text_content())
            assert changed["evidence"]["totals"]["value"] == 12
            page.locator("#approve-result").click()
            page.locator("#mission-status").filter(has_text="Add a review note").wait_for()
            page.locator("#review-note").fill("Checked the budget and exact integer totals against my inputs.")
            page.locator("#remember-result").check()
            with page.expect_download() as download:
                page.locator("#approve-result").click()
            browser_artifact = output / "reviewed-browser-report.json"
            download.value.save_as(browser_artifact)
            saved = json.loads(browser_artifact.read_text())
            assert saved["payload"]["request"]["work"]["budget"] == 6
            Mission.model_validate(saved["payload"]["request"])
            page.reload()
            page.locator("#history-count").filter(has_text="1 saved").wait_for()
            page.locator(".history-panel summary").click()
            page.get_by_role("button", name="Load inputs", exact=True).click()
            expect(page.get_by_label("Budget", exact=True)).to_have_value("6")
            with page.expect_download() as download:
                page.locator("#export-mission").click()
            native_path = output / "native-mission.json"
            download.value.save_as(native_path)
            Mission.model_validate_json(native_path.read_text())
            page.locator("#mission-import").set_input_files(browser_artifact)
            page.locator("#mission-status").filter(has_text="Ready.").wait_for()
            saved["payload"]["request"]["work"]["budget"] = 7
            page.locator("#mission-import").set_input_files(
                {"name": "tampered.json", "mimeType": "application/json", "buffer": json.dumps(saved).encode()}
            )
            page.locator("#mission-status").filter(has_text="integrity check failed").wait_for()
            report["review_export_import_memory_and_tamper_detection"] = True

            # Untrusted source content must be rendered as text, not executable markup.
            request = {
                "goal": "Review source evidence",
                "work": {
                    "kind": "research",
                    "sources": [
                        {
                            "id": "one",
                            "title": "Untrusted source",
                            "text": "<img src=x onerror=alert(1)> Review source evidence carefully.",
                        }
                    ],
                },
            }
            page.locator("#mission-import").set_input_files(
                {"name": "source.json", "mimeType": "application/json", "buffer": json.dumps(request).encode()}
            )
            page.locator("#run-mission").click()
            page.locator("#mission-result").wait_for(state="visible")
            assert page.locator("#result-table img").count() == 0
            assert "<img" in page.locator("#result-table").inner_text()
            page.get_by_label("What would a useful result look like?").fill("Changed goal invalidates prior evidence")
            assert page.locator("#mission-result").is_hidden()
            report["source_html_is_text_and_input_changes_invalidate_review"] = True

            # Simulate a busy worker to deterministically verify termination controls.
            cancellation = browser.new_context(service_workers="block")
            busy = cancellation.new_page()
            busy.goto(origin)
            wait_for(busy, "document.getElementById('mission-goal').value.length > 0")
            busy.route(
                "**/mission-worker.mjs",
                lambda route: route.fulfill(
                    content_type="text/javascript", body="self.onmessage = () => { while (true) {} };"
                ),
            )
            busy.locator("#run-mission").click()
            busy.locator("#stop-mission").click()
            assert busy.locator("#run-mission").is_enabled()
            assert busy.locator("#mission-result").is_hidden()
            cancellation.close()
            report["worker_cancellation_control"] = True

            for width in (390, 320):
                page.set_viewport_size({"width": width, "height": 844})
                page.goto(origin)
                wait_for(page, "document.getElementById('mission-goal').value.length > 0")
                assert inspect(page, "document.documentElement.scrollWidth <= innerWidth + 1")
                page.screenshot(path=str(output / f"workspace-mobile-{width}.png"))
            page.locator('[data-stage="5"]').click()
            assert "Review and export" in page.locator("#wheel-caption").inner_text()
            page.get_by_role("searchbox", name="Search demos").fill("governance")
            assert page.locator(".demo-card:visible").count() == 1
            page.get_by_role("searchbox", name="Search demos").fill("does-not-exist-9481")
            assert page.locator("#no-results").is_visible()
            report["responsive_flywheel_and_search"] = True
            page.locator("#platform").select_option("windows")
            assert ".venv-agent\\Scripts\\alpha-agent.exe" in page.locator("#install-commands").inner_text()

            with tempfile.TemporaryDirectory(prefix="pages-signed-") as temporary:
                journal = Journal.initialize(Path(temporary) / "agent")
                engine = Engine(journal)
                page.locator("#signed-title").click()
                for kind in ("allocation", "forecast"):
                    request = json.loads(
                        (Path(__file__).resolve().parents[1] / f"examples/missions/{kind}.json").read_text()
                    )
                    if kind == "forecast":
                        request["work"]["observations"] = [value + 0.125 for value in request["work"]["observations"]]
                    mission = journal.submit(Mission.model_validate(request))
                    record = engine.execute(mission["id"])
                    assert record["state"] == "review", record
                    engine.review(
                        record["id"], record["revision"], digest(record["result"]), True, "Browser handoff acceptance"
                    )
                    artifact = engine.export(record["id"])
                    page.locator("#signed-file").set_input_files(
                        {"name": "signed.json", "mimeType": "application/json", "buffer": json.dumps(artifact).encode()}
                    )
                    page.locator("#trusted-key").fill(journal.public)
                    page.locator("#verify-signed").click()
                    page.locator("#signed-status").filter(
                        has_text="Ed25519 signature and approved result verified"
                    ).wait_for()
                    assert page.locator("#signed-output").text_content() == artifact["receipt"]["canonical_body"]
                artifact["receipt"]["body"]["document"]["state"] = "failed"
                page.locator("#signed-file").set_input_files(
                    {
                        "name": "tampered-signed.json",
                        "mimeType": "application/json",
                        "buffer": json.dumps(artifact).encode(),
                    }
                )
                page.locator("#verify-signed").click()
                page.locator("#signed-status").filter(has_text="Displayed data differs").wait_for()
                page.locator("#trusted-key").fill("0" * 64)
                page.locator("#verify-signed").click()
                page.locator("#signed-status").filter(has_text="does not match").wait_for()
                report["native_ed25519_exports_integer_float_and_tamper_rejection"] = True

            if model:
                page.locator("#ai-prompt").fill("The capital of France is")
                page.locator("#ai-generate").click()
                page.locator("#ai-status").filter(has_text="Generated locally").wait_for(timeout=240000)
                generated = page.locator("#ai-output").inner_text()
                assert generated.strip()
                report["actual_model_output"] = generated
                page.locator("#ai-stop").is_hidden()
                # A new worker must be able to load the actual cached weights offline.
            else:
                report["model"] = "Not run: minimal-assets acceptance. Full-assets job requires real generation."
            inspect(page, "() => navigator.serviceWorker.ready")
            wait_for(page, "navigator.serviceWorker.controller !== null")
            context.set_offline(True)
            response = page.goto(origin)
            assert response and response.ok and response.from_service_worker
            wait_for(page, "document.getElementById('mission-goal').value.length > 0")
            page.locator("#run-mission").click()
            page.locator("#mission-result").wait_for(state="visible")
            if model:
                page.locator("#ai-prompt").fill("The capital of France is")
                page.locator("#ai-generate").click()
                page.locator("#ai-status").filter(has_text="Generated locally").wait_for(timeout=240000)
                assert page.locator("#ai-output").inner_text() == report["actual_model_output"]
                report["actual_model_offline_after_reload"] = True
            report["offline_root_reload_and_mission"] = True
            assert not errors, errors
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if thread:
            thread.join(timeout=5)
    (output / "workspace.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=Path("site"))
    parser.add_argument("--output", type=Path, default=Path("evidence/pages-workspace"))
    parser.add_argument("--model", action="store_true")
    parser.add_argument("--url", help="Validate the deployed public HTTPS site instead of a local build")
    args = parser.parse_args()
    report = validate(args.site, args.output, args.model, args.url)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
