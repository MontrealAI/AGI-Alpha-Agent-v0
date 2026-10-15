# SPDX-License-Identifier: Apache-2.0
"""Actual native Jobs browser journey with synthetic read-only chain observations."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import socket
import threading
import time
from typing import Any

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright, expect
import uvicorn

from alpha_factory_v1.core.runtime import ecosystem as eco
from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime.store import Journal
from test_ecosystem_jobs import fixture, reader, SPEC, WORKER, TX

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def native(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Journal, str, str]]:
    journal = Journal.initialize(tmp_path / "agent")
    profile, state = fixture()
    (journal.root / "jobs-v0-profile.json").write_text(profile.model_dump_json())
    monkeypatch.setattr(eco, "ReadOnlyRPC", lambda _url: reader(state))
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = f"http://127.0.0.1:{listener.getsockname()[1]}"
    server = uvicorn.Server(uvicorn.Config(create_app(journal), log_level="error", lifespan="off"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    try:
        yield journal, origin, (journal.root / "api.token").read_text().strip()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def connect(page: Any, origin: str, token: str) -> None:
    page.goto(origin + "/ecosystem-studio")
    page.locator("#token").fill(token)
    page.locator("#token").press("Enter")
    expect(page.locator("#workspace")).to_be_visible()
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")


def admit(page: Any) -> None:
    page.locator("#spec-file").set_input_files({"name": "work.json", "mimeType": "application/json", "buffer": SPEC})
    expect(page.locator("#spec-digest")).to_contain_text("1cb2ef99")
    page.locator("#job-id").fill("1")
    page.locator("#worker").fill(WORKER)
    page.locator("#assignment").fill(TX)
    page.locator("#admit-confirm").check()
    page.locator("#admit").press("Enter")
    expect(page.locator("#selected-summary")).to_contain_text("queued")
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")


def test_complete_native_journey_and_retained_reload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        connect(page, origin, token)
        admit(page)
        page.locator("#run-confirm").check()
        page.locator("#execute").press("Enter")
        expect(page.locator("#selected-summary")).to_contain_text("review")
        expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
        page.locator("#note").fill("Fixture local operator inspected exact result; no independent market approval")
        page.locator("#review-confirm").check()
        page.locator("#review").press("Enter")
        expect(page.locator("#selected-summary")).to_contain_text("completed")
        expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
        with page.expect_download() as download:
            page.locator("#export").press("Enter")
        download.value.save_as(tmp_path / "delivery.json")
        assert (tmp_path / "delivery.json").stat().st_size > 100
        expect(page.locator("#result-hash")).to_contain_text("resultHash: 0x")
        before = journal.verify()
        connect(page, origin, token)
        page.locator("#history button").press("Enter")
        expect(page.locator("#selected-summary")).to_contain_text("completed")
        assert journal.verify() == before
        page.route(
            "**/axe-fixture.js",
            lambda route: route.fulfill(
                path=str(ROOT / "tests/browser/node_modules/axe-core/axe.min.js"), content_type="application/javascript"
            ),
        )
        page.add_script_tag(url=origin + "/axe-fixture.js")
        for language in ("en", "fr"):
            page.locator("#language").select_option(language)
            for width in (1440, 390, 320):
                page.set_viewport_size({"width": width, "height": 1080})
                audit = page.evaluate(
                    "async()=>await axe.run(document,{runOnly:{type:'tag',"
                    "values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})"
                )
                assert not audit["violations"], audit["violations"]
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth+1")
                page.screenshot(path=str(tmp_path / f"jobs-{language}-{width}.png"), full_page=True)
        page.locator("#disconnect").press("Enter")
        expect(page.locator("#workspace")).to_be_hidden()
        assert page.locator("#record").inner_text() == ""
        assert not errors
        browser.close()


def test_lost_admission_response_reopens_one_mission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page()
        connect(page, origin, token)

        def lose(route: Any) -> None:
            response = route.fetch()
            assert response.ok
            route.abort()

        page.route("**/api/ecosystem/admit", lose)
        page.locator("#spec-file").set_input_files(
            {"name": "work.json", "mimeType": "application/json", "buffer": SPEC}
        )
        expect(page.locator("#spec-digest")).to_contain_text("1cb2ef99")
        page.locator("#job-id").fill("1")
        page.locator("#worker").fill(WORKER)
        page.locator("#assignment").fill(TX)
        page.locator("#admit-confirm").check()
        page.locator("#admit").press("Enter")
        expect(page.locator("#message")).to_contain_text("uncertain")
        assert len(journal.missions()) == 1
        page.unroute("**/api/ecosystem/admit", lose)
        connect(page, origin, token)
        page.locator("#history button").press("Enter")
        expect(page.locator("#selected-summary")).to_contain_text("queued")
        admit(page)
        assert len(journal.missions()) == 1
        browser.close()


def test_lost_execution_reopens_review_without_replay(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page()
        connect(page, origin, token)
        admit(page)

        def lose(route: Any) -> None:
            response = route.fetch()
            assert response.ok
            route.abort()

        page.route("**/api/ecosystem/execute", lose)
        page.locator("#run-confirm").check()
        page.locator("#execute").click()
        expect(page.locator("#message")).to_contain_text("uncertain")
        page.locator("#language").select_option("fr")
        expect(page.locator("#message")).to_contain_text("incertaine")
        before = journal.verify()
        connect(page, origin, token)
        page.locator("#history button").click()
        expect(page.locator("#selected-summary")).to_contain_text("review")
        expect(page.locator("#execute")).to_be_disabled()
        assert journal.verify() == before
        browser.close()


def test_disconnect_suppresses_late_history_and_clears_confirmations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page()
        connect(page, origin, token)
        page.locator("#admit-confirm").check()
        page.locator("#job-id").fill("2")
        expect(page.locator("#admit-confirm")).not_to_be_checked()
        admit(page)
        held = []
        page.route("**/api/ecosystem/status", lambda route: held.append(route))
        page.locator("#refresh").click()
        expect(page.locator("#workspace")).to_have_attribute("aria-busy", "true")
        assert held
        page.locator("#disconnect").click()
        held[0].fulfill(json={"identity": "late", "records": [{"goal": "PRIVATE-LATE"}], "profile": None})
        page.wait_for_timeout(100)
        expect(page.locator("#workspace")).to_be_hidden()
        assert "PRIVATE-LATE" not in page.locator("body").inner_text()
        assert page.locator("#record").inner_text() == ""
        assert page.locator("#token").input_value() == ""
        browser.close()


def test_changed_journal_disconnects_without_mutation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as driver:
        browser = driver.chromium.launch()
        page = browser.new_page()
        connect(page, origin, token)
        before = journal.verify()
        page.route(
            "**/api/ecosystem/status", lambda route: route.fulfill(json={"identity": "different", "records": []})
        )
        page.locator("#refresh").click()
        expect(page.locator("#workspace")).to_be_hidden()
        assert journal.verify() == before
        browser.close()


def test_public_chooser_uses_existing_paths_without_native_or_wallet_requests(tmp_path: Path) -> None:
    from functools import partial
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(SimpleHTTPRequestHandler, directory=str(ROOT / "docs")))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as driver:
            browser = driver.chromium.launch()
            page = browser.new_page(viewport={"width": 390, "height": 1080})
            requests = []
            errors = []
            page.on("request", lambda request: requests.append(request.url))
            page.on("pageerror", lambda error: errors.append(str(error)))
            origin = f"http://127.0.0.1:{server.server_port}"
            page.goto(origin + "/ascension/mainnet/")
            expect(page.locator("#ecosystem-continue")).to_be_visible()
            page.locator("#ecosystem-continue").click()
            expect(page.locator('[data-step="project"]')).to_have_attribute("aria-current", "step")
            for market in ["ascension", "jobs-v0", "manager"]:
                page.locator("#ecosystem-market").select_option(market)
                for executor in ["native", "fleet"]:
                    page.locator("#ecosystem-executor").select_option(executor)
                    expect(page.locator("#ecosystem-token")).to_have_text("USDC" if market == "manager" else "AGIALPHA")
                    if executor == "fleet" or market == "manager":
                        expect(page.locator("#ecosystem-continue")).to_be_hidden()
                        expect(page.locator("#ecosystem-native")).to_be_hidden()
                    elif market == "jobs-v0":
                        expect(page.locator("#ecosystem-native")).to_have_attribute(
                            "href", "http://127.0.0.1:8765/ecosystem-studio"
                        )
            assert not any("/api/ecosystem/" in url or ":8765/" in url for url in requests)
            assert not errors
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
