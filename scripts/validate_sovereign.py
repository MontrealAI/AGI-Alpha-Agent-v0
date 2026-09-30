# SPDX-License-Identifier: Apache-2.0
"""Exercise native Sovereign execution, reviews, signed downloads and both public routes."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
import tempfile
from threading import Thread
import time
from typing import Any, Iterator

import uvicorn

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.service import create_app
from alpha_factory_v1.demos.sovereign_agentic_agialpha_agent_v0.workbench import STAGES, verify_packet
from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

DEMO = "sovereign_agentic_agialpha_agent_v0"
ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def serve(journal: Journal) -> Iterator[str]:
    """Reserve a loopback port before starting the real ASGI server."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        server = uvicorn.Server(uvicorn.Config(create_app(journal), log_level="error", access_log=False))
        thread = Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 10
            while not server.started:
                if not thread.is_alive() or time.monotonic() > deadline:
                    raise RuntimeError("Local Sovereign service did not start")
                time.sleep(0.02)
            yield f"http://127.0.0.1:{sock.getsockname()[1]}"
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                raise RuntimeError("Local Sovereign service did not stop")


def accessibility(page: Any, axe: Path | None) -> None:
    """Instrument through DevTools without weakening the application's CSP."""
    if axe is not None:
        page.evaluate(axe.read_text(encoding="utf-8"))
        violations = page.evaluate(
            "async () => (await axe.run(document, "
            "{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa']}})).violations"
        )
        if violations:
            raise AssertionError(json.dumps(violations, indent=2))


def gallery(page: Any, base: str, output: Path, axe: Path | None) -> list[dict[str, Any]]:
    """Verify exact raw downloads without reserializing signed numbers in JavaScript."""
    from playwright.sync_api import expect

    runs = []
    for prefix in ("", "alpha_factory_v1/demos/"):
        page.goto(f'{base.rstrip("/")}/{prefix}{DEMO}/', wait_until="networkidle")
        expect(page.locator("#mode-label")).to_have_text("RECORDED NATIVE EVIDENCE")
        expect(page.locator("#unlock")).to_be_hidden()
        expect(page.locator("#review-form")).to_be_hidden()
        expect(page.locator("#advance")).to_be_disabled()
        for case in ("balanced", "constrained", "expanded"):
            page.locator("#case").select_option(case)
            expect(page.locator("#workflow-state")).to_have_text("COMPLETED")
            for stage in STAGES:
                page.locator(f'[data-stage="{stage}"]').click()
                expect(page.locator("#stage-status")).to_have_text("COMPLETED")
            key = page.locator("#public-key").inner_text()
            with page.expect_download() as download:
                page.locator("#download").click()
            target = output / f'{"mirror" if prefix else "gallery"}-{case}.json'
            download.value.save_as(target)
            packet = json.loads(target.read_text())
            proof = verify_packet(packet, key)
            runs.append(
                {
                    "route": prefix + DEMO + "/",
                    "case": case,
                    "sha256": packet["sha256"],
                    "verified": proof["verified"],
                    "key_scope": "self-consistent public fixture",
                }
            )
        page.locator("#case").select_option("balanced")
        page.locator('[data-stage="portfolio"]').click()
        accessibility(page, axe)
        if not prefix:
            page.screenshot(path=str(output / "gallery-desktop.png"), full_page=True)
            page.locator('[data-stage="schedule"]').click()
            page.locator("#result").screenshot(path=str(output / "resource-schedule.png"))
            page.locator('[data-stage="portfolio"]').click()
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
            accessibility(page, axe)
            page.screenshot(path=str(output / "gallery-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1000})
    return runs


def native(page: Any, journal: Journal, output: Path, axe: Path | None) -> None:
    """Drive authority transitions through the browser and real authenticated API."""
    from playwright.sync_api import expect

    with serve(journal) as base:
        page.goto(base, wait_until="networkidle")
        expect(page.locator("#create")).to_be_disabled()
        page.locator("#access-code").fill("wrong-code")
        page.get_by_role("button", name="Unlock workspace").click()
        expect(page.locator("#error")).to_contain_text("Unlock")
        page.locator("#access-code").fill((journal.root / "api.token").read_text().strip())
        page.get_by_role("button", name="Unlock workspace").click()
        expect(page.locator("#unlock")).to_be_hidden()
        page.locator("#create").click()
        expect(page.locator("#workflow-state")).to_have_text("READY")
        ident = page.locator("#history").input_value()
        for stage in STAGES:
            page.locator("#advance").click()
            expect(page.locator("#workflow-state")).to_have_text("REVIEW")
            expect(page.locator("#advance")).to_be_disabled()
            expect(page.locator("#download")).to_be_hidden()
            expect(page.locator("#stage-kicker")).to_contain_text(stage.upper())
            if stage == "portfolio":
                expect(page.locator("#metric-value")).to_have_text("2,200")
                expect(page.locator("#stage-detail")).to_contain_text("1,850")
                assert page.locator("#stage-visual circle").count() == 5
                accessibility(page, axe)
                page.screenshot(path=str(output / "local-desktop.png"), full_page=True)
            else:
                page.locator('[data-stage="portfolio"]').click()
                expect(page.locator("#review-form")).to_be_hidden()
                page.locator(f'[data-stage="{stage}"]').click()
            page.locator("#review-note").fill(f"Automated browser fixture: checked {stage} and assumptions")
            page.locator("#approve").click()
            expect(page.locator("#workflow-state")).to_have_text("REVIEW")
            page.locator("#review-check").check()
            page.locator("#approve").click()
            expect(page.locator("#workflow-state")).to_have_text("COMPLETED" if stage == "brief" else "READY")
        with page.expect_download() as download:
            page.locator("#download").click()
        target = output / "local-packet.json"
        download.value.save_as(target)
        assert verify_packet(json.loads(target.read_text()), journal.public)["verified"]
        assert page.evaluate("localStorage.length === 0 && sessionStorage.length === 0")
        page.locator("#case").select_option("constrained")
        page.locator("#create").click()
        expect(page.locator("#workflow-state")).to_have_text("READY")
        page.locator("#advance").click()
        expect(page.locator("#workflow-state")).to_have_text("REVIEW")
        page.locator("#review-note").fill("Fixture rejection: assumptions are unmeasured")
        page.locator("#reject").click()
        expect(page.locator("#workflow-state")).to_have_text("REJECTED")
        expect(page.locator("#advance")).to_be_disabled()
        page.locator("#advanced summary").click()
        page.locator("#mandate-json").fill('{"budget":1,"budget":2}')
        page.locator("#apply-json").click()
        expect(page.locator("#error")).to_contain_text("Duplicate")
        page.locator("#case").select_option("balanced")
        page.locator("#pause").click()
        expect(page.locator("#pause")).to_have_text("Resume execution")
        expect(page.locator("#create")).to_be_disabled()
        page.locator("#lock").click()
        expect(page.locator("#result")).to_be_hidden()
        expect(page.locator("#unlock")).to_be_visible()
    with serve(Journal(journal.root)) as base:
        page.goto(base, wait_until="networkidle")
        page.locator("#access-code").fill((journal.root / "api.token").read_text().strip())
        page.get_by_role("button", name="Unlock workspace").click()
        expect(page.locator("#pause")).to_have_text("Resume execution")
        page.locator("#history").select_option(ident)
        expect(page.locator("#workflow-state")).to_have_text("PAUSED · COMPLETED")
        page.locator("#pause").click()
        expect(page.locator("#workflow-state")).to_have_text("COMPLETED")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
        accessibility(page, axe)
        page.screenshot(path=str(output / "local-mobile.png"), full_page=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        pending = []
        page.route("**/api/status", lambda route: pending.append(route))
        with page.expect_request(base + "/api/status"):
            page.locator("#refresh").click()
        page.locator("#lock").click()
        with page.expect_response(base + "/api/status"):
            pending[0].continue_()
        expect(page.locator("#result")).to_be_hidden()
        expect(page.locator("#unlock")).to_be_visible()
        expect(page.locator("#public-key")).to_contain_text("Unlock")
        page.unroute("**/api/status")


def validate(output: Path, url: str | None = None, axe: Path | None = None) -> dict[str, Any]:
    """Run native plus static acceptance, or verify both deployed gallery routes."""
    from playwright.sync_api import sync_playwright

    output.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    server = None
    thread = None
    with tempfile.TemporaryDirectory(prefix="sovereign-browser-") as temp, sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, service_workers="block")
        if url is None:
            context.route(
                "**/*",
                lambda route: route.continue_() if route.request.url.startswith("http://127.0.0.1:") else route.abort(),
            )
        page = context.new_page()
        page.on("pageerror", lambda exc: failures.append(str(exc)))
        try:
            if url is None:
                native(page, Journal.initialize(Path(temp) / "workspace"), output, axe)
                server = ThreadingHTTPServer(
                    ("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs"))
                )
                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()
                origin = f"http://127.0.0.1:{server.server_port}/"
            else:
                origin = url
            scenarios = gallery(page, origin, output, axe)
            release = context.request.get(url.rstrip("/") + "/release.json").json() if url else None
            assert not failures, failures
        finally:
            browser.close()
            if server is not None:
                server.shutdown()
                server.server_close()
                assert thread is not None
                thread.join(timeout=5)
    result = {
        "schema": "sovereign-browser-v1",
        "passed": True,
        "origin": url or "local",
        "native_workflow": url is None,
        "restart_pause_retained": url is None,
        "late_response_after_lock_rejected": url is None,
        "mobile_no_overflow": True,
        "axe_checked": axe is not None,
        "scenarios": scenarios,
        "browser_errors": failures,
        "release": release,
    }
    (output / "sovereign.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--url", help="Canonical site origin for public gallery acceptance")
    parser.add_argument("--axe-script", type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.output, args.url, args.axe_script), indent=2))
