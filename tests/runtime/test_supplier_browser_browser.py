# SPDX-License-Identifier: Apache-2.0
"""Real native UI with explicit synthetic chain/advisor/actuator test doubles."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import socket
import threading
import time

import pytest
import uvicorn
from playwright.sync_api import sync_playwright, expect
from alpha_factory_v1.core.runtime.api import create_app
from alpha_factory_v1.core.runtime import supplier_browser as adapter
from test_supplier_browser_jobs import configured as supplier_configured, FixtureComputer, DoneAdvisor
from test_ecosystem_jobs import WORKER, TX

configured = supplier_configured


@contextmanager
def native(journal):
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    origin = "http://127.0.0.1:" + str(listener.getsockname()[1])
    server = uvicorn.Server(uvicorn.Config(create_app(journal), log_level="error", lifespan="off"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    assert server.started
    try:
        yield origin, (journal.root / "api.token").read_text().strip()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def connect(page, origin, token):
    page.goto(origin + "/supplier-studio")
    page.locator("#token").fill(token)
    page.locator("#connect").click()
    expect(page.locator("#workspace")).to_be_visible()
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")


def admission(page, raw):
    page.locator("#spec-file").set_input_files({"name": "spec.json", "mimeType": "application/json", "buffer": raw})
    expect(page.locator("#spec-hash")).to_contain_text("specHash: 0x")
    page.locator("#job-id").fill("1")
    page.locator("#worker").fill(WORKER)
    page.locator("#assignment").fill(TX)
    page.locator("#admit-confirm").check()
    page.locator("#admit").click()
    expect(page.locator("#selected")).to_be_visible()
    expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")


def test_bilingual_native_supplier_review_export_and_disconnect(configured, monkeypatch, tmp_path):
    journal, raw, _ = configured
    original = adapter.execute
    monkeypatch.setattr(adapter, "execute", lambda *args: original(*args, _factory=FixtureComputer))
    with native(journal) as (origin, token), sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        connect(page, origin, token)
        admission(page, raw)
        expect(page.locator("#stop")).to_be_disabled()
        page.locator("#prepare").click()
        expect(page.locator("#permission")).to_contain_text("computer_commitment")
        assert journal.latest(json.loads(page.locator("#record").inner_text())["id"])["state"] == "admitted"
        page.locator("#run-confirm").check()
        page.locator("#job-id").fill("2")
        expect(page.locator("#execute")).to_be_disabled()
        expect(page.locator("#run-confirm")).not_to_be_checked()
        page.locator("#job-id").fill("1")
        page.locator("#prepare").click()
        expect(page.locator("#execute")).to_be_enabled()
        page.locator("#run-confirm").check()
        page.locator("#execute").click()
        expect(page.locator("#record")).to_contain_text('"state": "review"')
        expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
        page.locator("#note").fill("Inspected synthetic output and retained comparison")
        page.locator("#review-confirm").check()
        page.locator("#review").click()
        expect(page.locator("#export")).to_be_enabled()
        expect(page.locator("#stop")).to_be_disabled()
        with page.expect_download() as download:
            page.locator("#export").click()
        path = tmp_path / "delivery.json"
        download.value.save_as(path)
        record = json.loads(page.locator("#record").inner_text())
        assert adapter.verify_delivery(path.read_bytes(), journal.public, record["observation"])["valid"]
        for language in ("en", "fr"):
            page.locator("#language").select_option(language)
            for width in (320, 390, 768, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                for scale in ("100%", "200%"):
                    page.evaluate("scale => document.documentElement.style.fontSize = scale", scale)
                    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1"), page.evaluate(
                        "() => [...document.querySelectorAll('body *')]"
                        ".filter(e => e.getBoundingClientRect().right > innerWidth + 1)"
                        ".map(e => [e.tagName,e.id,e.getBoundingClientRect().right]).slice(0,20)"
                    )
                page.evaluate("document.documentElement.style.fontSize = '100%'")
            if os.environ.get("AXE_SCRIPT"):
                page.evaluate(Path(os.environ["AXE_SCRIPT"]).read_text())
                assert not page.evaluate("async()=> (await axe.run()).violations")
        page.locator("#disconnect").click()
        expect(page.locator("#workspace")).to_be_hidden()
        assert page.locator("#record").inner_text() == ""
        assert not errors
        browser.close()


def test_stop_stays_available_during_provider_wait(configured, monkeypatch):
    journal, raw, _ = configured
    entered, release = threading.Event(), threading.Event()

    class WaitingAdvisor(DoneAdvisor):
        def next(self, task, observation):
            entered.set()
            assert release.wait(10)
            return super().next(task, observation)

    original = adapter.execute
    monkeypatch.setattr(adapter, "_advisor", WaitingAdvisor)
    monkeypatch.setattr(adapter, "execute", lambda *args: original(*args, _factory=FixtureComputer))
    with native(journal) as (origin, token), sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        connect(page, origin, token)
        admission(page, raw)
        expect(page.locator("#stop")).to_be_disabled()
        page.locator("#prepare").click()
        expect(page.locator("#execute")).to_be_enabled()
        page.locator("#run-confirm").check()
        page.locator("#execute").click()
        assert entered.wait(5)
        expect(page.locator("#stop")).to_be_enabled()
        page.locator("#stop").click()
        expect(page.locator("#record")).to_contain_text('"state": "stopped"')
        release.set()
        expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
        page.locator("#refresh").click()
        expect(page.locator("#record")).to_contain_text('"state": "stopped"')
        browser.close()


def test_controls_fail_closed_without_script_and_during_initialization(configured):
    journal, _, _ = configured
    with native(journal) as (origin, _), sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(java_script_enabled=False)
        page.goto(origin + "/supplier-studio")
        expect(page.locator("noscript p")).to_contain_text("No work has started")
        expect(page.locator("#token")).to_be_disabled()
        expect(page.locator("#connect")).to_be_disabled()
        page.close()
        page = browser.new_page()
        held, requests = [], []
        page.on("request", lambda request: requests.append(request.url))
        page.route("**/supplier-studio.js", lambda route: held.append(route))
        with page.expect_request("**/supplier-studio.js"):
            page.goto(origin + "/supplier-studio", wait_until="commit")
        expect(page.locator("#connect")).to_be_disabled()
        expect(page.locator("#token")).to_be_disabled()
        assert held
        assert not any("/api/" in url for url in requests)
        held[0].continue_()
        expect(page.locator("#connect")).to_be_enabled()
        browser.close()


def test_missing_profiles_and_invalid_utf8_never_start_provider(configured, monkeypatch):
    journal, _, _ = configured
    (journal.root / "supplier-browser-profile.json").unlink()
    monkeypatch.setattr(adapter, "_advisor", lambda *args: pytest.fail("unexpected provider initialization"))
    with native(journal) as (origin, token), sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        connect(page, origin, token)
        expect(page.locator("#readiness")).to_contain_text("Setup required")
        expect(page.locator("#admit")).to_be_disabled()
        page.locator("#spec-file").set_input_files(
            {"name": "bad.json", "mimeType": "application/json", "buffer": b'{"goal":"\xff"}'}
        )
        expect(page.locator("#message")).to_contain_text("UTF-8")
        assert page.locator("#spec-preview").inner_text() == ""
        expect(page.locator("#admit")).to_be_disabled()
        browser.close()


def test_changed_intent_invalidates_inflight_prepare(configured):
    journal, raw, _ = configured
    with native(journal) as (origin, token), sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        connect(page, origin, token)
        admission(page, raw)
        held = []
        page.route("**/api/supplier-browser/prepare", lambda route: held.append(route))
        with page.expect_request("**/api/supplier-browser/prepare"):
            page.locator("#prepare").click()
        page.evaluate(
            "() => {const input=document.querySelector('#job-id');input.value='2';"
            "input.dispatchEvent(new Event('input',{bubbles:true}));}"
        )
        assert held
        held[0].continue_()
        expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
        assert page.locator("#permission").inner_text() == ""
        expect(page.locator("#execute")).to_be_disabled()
        expect(page.locator("#run-confirm")).not_to_be_checked()
        browser.close()


def test_real_chromium_observation_matches_independent_reviewer():
    from test_supplier_browser_spec import specification
    from alpha_factory_v1.core.runtime.supplier_browser_spec import computer_task, extract_artifacts

    spec = specification()
    with sync_playwright() as driver:
        browser = driver.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(computer_task(spec).html)
        with pytest.raises(ValueError):
            extract_artifacts(spec, page.locator("body").inner_text())
        page.locator("#delivery").select_option("7")
        page.locator("#compare").click()
        result = extract_artifacts(spec, page.locator("body").inner_text())
        assert result["acceptance"]["accepted"]
        page.locator("#delivery").select_option("1")
        page.locator("#compare").click()
        with pytest.raises(ValueError):
            extract_artifacts(spec, page.locator("body").inner_text())
        browser.close()
