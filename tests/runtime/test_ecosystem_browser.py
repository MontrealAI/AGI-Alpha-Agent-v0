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


@pytest.mark.parametrize(
    "route,script",
    [("/", "app.js"), ("/ascension-studio", "ascension-studio.js"), ("/ecosystem-studio", "ecosystem-studio.js")],
)
def test_native_login_is_inert_until_handlers_are_ready(tmp_path, monkeypatch, route, script):
    with native(tmp_path, monkeypatch) as (_, origin, token), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        held = []
        requests = []
        page.on(
            "request",
            lambda request: requests.append(request.url) if request.resource_type in {"fetch", "xhr"} else None,
        )
        page.route("**/" + script, lambda request: held.append(request))
        page.goto(origin + route, wait_until="commit")
        deadline = time.monotonic() + 5
        while not held and time.monotonic() < deadline:
            page.wait_for_timeout(10)
        assert held
        expect(page.locator("#token")).to_be_disabled()
        button = page.locator("#login-form button")
        expect(button).to_be_disabled()
        expect(page.locator("#initializing")).to_be_visible()
        button.click(force=True)
        page.keyboard.press("Enter")
        assert page.url == origin + route and not requests
        held[0].continue_()
        expect(page.locator("#token")).to_be_enabled()
        expect(button).to_be_enabled()
        expect(page.locator("#initializing")).to_be_hidden()
        page.locator("#token").fill(token)
        page.locator("#token").press("Enter")
        expect(page.locator("#workspace")).to_be_visible()
        assert page.url == origin + route
        browser.close()


@pytest.mark.parametrize("route", ["/", "/ascension-studio", "/ecosystem-studio"])
def test_native_login_without_javascript_explains_unavailable_controls(tmp_path, monkeypatch, route):
    with native(tmp_path, monkeypatch) as (_, origin, _), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(java_script_enabled=False)
        page.goto(origin + route)
        expect(page.locator("#token")).to_be_disabled()
        expect(page.locator("#login-form button")).to_be_disabled()
        expect(page.locator("noscript p")).to_contain_text("JavaScript is required")
        expect(page.locator("noscript p")).to_contain_text("JavaScript est requis")
        browser.close()


def test_unsigned_editor_exports_all_kinds_and_reimports_exact_bytes(tmp_path, monkeypatch):
    import hashlib
    from alpha_factory_v1.core.runtime.work_spec import read_spec

    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        connect(page, origin, token)
        for kind in ["research", "allocation", "schedule", "forecast"]:
            page.locator("#draft-kind").select_option(kind)
            page.locator("#draft-example").click()
            expect(page.locator("#draft-hash")).to_contain_text("specHash: 0x")
            page.locator("#draft-confirm").check()
            with page.expect_download() as received:
                page.locator("#draft-download").click()
            raw = Path(received.value.path()).read_bytes()
            specification, digest = read_spec(raw)
            assert specification.mission.work.kind == kind
            assert digest == "0x" + hashlib.sha256(raw).hexdigest()
            page.locator("#spec-file").set_input_files(
                {"name": "work.json", "mimeType": "application/json", "buffer": raw}
            )
            expect(page.locator("#spec-digest")).to_have_text("specHash: " + digest)
            assert journal.missions() == []
        page.locator("#language").select_option("fr")
        expect(page.locator("#draft-editor h2")).to_contain_text("non signé")
        page.locator("#draft-work").fill('{"kind":"research","kind":"allocation"}')
        expect(page.locator("#draft-download")).to_be_disabled()
        expect(page.locator("#draft-hash")).to_be_empty()
        expect(page.locator("#draft-status")).to_contain_text("invalide")
        browser.close()


def test_unsigned_editor_discards_late_validation_after_edit_and_disconnect(tmp_path, monkeypatch):
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        held = []

        def hold_first(route):
            if not held:
                held.append((route, route.fetch()))
            else:
                route.continue_()

        page.route("**/api/ecosystem/draft", hold_first)
        connect(page, origin, token)
        deadline = time.monotonic() + 5
        while not held and time.monotonic() < deadline:
            page.wait_for_timeout(10)
        assert held
        page.locator("#draft-goal").fill("A newer supplied-input goal")
        expect(page.locator("#draft-preview")).to_contain_text("A newer supplied-input goal")
        newer = page.locator("#draft-hash").inner_text()
        held[0][0].fulfill(response=held[0][1])
        page.wait_for_timeout(100)
        assert page.locator("#draft-hash").inner_text() == newer
        page.unroute("**/api/ecosystem/draft", hold_first)
        pending = []
        page.route("**/api/ecosystem/draft", lambda route: pending.append((route, route.fetch())))
        page.locator("#draft-goal").fill("Never restore this private draft after disconnect")
        deadline = time.monotonic() + 5
        while not pending and time.monotonic() < deadline:
            page.wait_for_timeout(10)
        assert pending
        page.locator("#disconnect").click()
        pending[0][0].fulfill(response=pending[0][1])
        page.wait_for_timeout(100)
        expect(page.locator("#draft-preview")).to_be_empty()
        expect(page.locator("#draft-goal")).to_have_value("")
        expect(page.locator("#draft-work")).to_have_value("")
        expect(page.locator("#draft-download")).to_be_disabled()
        assert journal.missions() == []
        browser.close()


def test_unsigned_editor_escaped_input_stays_within_transport_limit(tmp_path, monkeypatch):
    import json
    from alpha_factory_v1.core.runtime.work_spec import read_spec
    from test_work_spec_draft import escaped_work

    work = escaped_work()
    with native(tmp_path, monkeypatch) as (journal, origin, token), sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(accept_downloads=True)
        connect(page, origin, token)
        expect(page.locator("#draft-hash")).to_contain_text("specHash: 0x")
        with page.expect_request("**/api/ecosystem/draft") as request:
            page.locator("#draft-work").fill(json.dumps(work))
        body = request.value.post_data
        assert len(body.encode()) < 512 * 1024 and "mission_base64" in json.loads(body)
        expect(page.locator("#draft-hash")).to_contain_text("specHash: 0x")
        page.locator("#draft-confirm").check()
        with page.expect_download() as received:
            page.locator("#draft-download").click()
        raw = Path(received.value.path()).read_bytes()
        specification, _ = read_spec(raw)
        assert specification.mission.work.sources[0].text == work["sources"][0]["text"]
        assert journal.missions() == []
        browser.close()
