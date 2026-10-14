# SPDX-License-Identifier: Apache-2.0
"""Actual local operator browser journey; chain observations are explicit unit doubles."""

from __future__ import annotations

import json
import socket
import threading
import time
from copy import deepcopy
from pathlib import Path

import pytest
from test_successor_ascension import AWARD_TX, CLOSE_TX, POST_TX, WORKER
from test_successor_studio_operator import install_template, installed

from alpha_factory_v1.core.runtime.api import MAX_REQUEST_BYTES, create_app
from alpha_factory_v1.core.runtime.successor import studio_operator as operator
from alpha_factory_v1.core.runtime.successor import workbench

playwright = pytest.importorskip("playwright.sync_api")
uvicorn = pytest.importorskip("uvicorn")


def test_actual_local_ui_setup_pair_seal_separate_roles_run_review_and_export(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming, journal, _, keys, rpc = installed(tmp_path, monkeypatch)
    installation, tokens = install_template(journal, keys, rpc)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(journal), log_level="error", lifespan="off"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    try:
        with playwright.sync_playwright() as driver:
            if not Path(driver.chromium.executable_path).exists():
                pytest.skip("Chromium is not installed")
            browser = driver.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page(viewport={"width": 1280, "height": 960})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{port}/ascension-studio")
            page.fill("#token", (journal.root / "api.token").read_text())
            page.click("#login-form button")
            page.locator("#workspace").wait_for(state="visible")
            page.click("#first-install summary")
            template = installation["template"]
            context = template["market_context"]
            fields = {
                "template-id": template["template_id"],
                "valid-until": "2099-01-01T00:00",
                "max-calls": "7",
                "rpc-url": template["rpc_url"],
                "chain-id": context["chain_id"],
                "market": context["market"],
                "market-hash": context["market_code_hash"],
                "token-hash": context["token_code_hash"],
                "confirmations": "1",
                "mark": context["mark"],
                "mark-hash": context["mark_code_hash"],
                "seed": context["seed"],
                "seed-hash": context["seed_code_hash"],
                "controller-key": "local-controller.key",
                "reviewer-key": "local-verifier.key",
            }
            for name, value in fields.items():
                page.fill("#setup-" + name, value)
            for name, value in (
                ("controller", "local-controller"),
                ("producer", "local-producer"),
                ("reviewer", "local-verifier"),
                ("scope", "disposable-local-fixture"),
            ):
                page.select_option("#setup-" + name, value)
            page.check("#setup-confirm")
            page.click("#setup-form button")
            page.locator("#first-install").wait_for(state="hidden")
            playwright.expect(page.locator("#request-file")).to_be_enabled()
            page.set_input_files(
                "#request-file",
                {"name": "studio-work.json", "mimeType": "application/json", "buffer": json.dumps(incoming).encode()},
            )
            playwright.expect(page.locator("#file-summary")).to_contain_text("Selected request")
            page.fill("#pair-seed", "1")
            page.check("#pair-confirm")
            page.click("#pair-form button")
            page.locator("#seal-panel").wait_for(state="visible")
            page.check("#seal-confirm")
            page.click("#seal")
            page.locator("#bind-panel").wait_for(state="visible")
            with page.expect_download() as exported:
                page.click("#seal-download")
            seal_path = Path(exported.value.path())
            assert json.loads(seal_path.read_text())["domain"] == "ascension-terms"
            rpc.height = 3
            for name, value in (
                ("job-id", "1"),
                ("worker", WORKER),
                ("posting-tx", POST_TX),
                ("assignment-tx", AWARD_TX),
                ("expires", "2098-01-01T00:00"),
            ):
                page.fill("#" + name, value)
            page.click("#bind-form button")
            page.locator("#local-grant").wait_for(state="visible")
            page.fill("#controller-token", tokens["local-controller"])
            page.check("#controller-confirm")
            page.click("#controller-form button")
            page.locator("#local-run-form").wait_for(state="visible")
            assert operator.records(journal)[0]["state"] == "bound"
            page.check("#local-run-confirm")
            page.click("#local-run-form button")
            page.locator("#result-panel").wait_for(state="visible")
            assert "FAIL" in page.locator("#verdict").inner_text()
            with page.expect_download() as returned:
                page.click("#result-download")
            result = json.loads(Path(returned.value.path()).read_text())
            assert result["schema"] == "agialpha.ascension.studio-result.v1"
            page.fill("#review-token", tokens["local-verifier"])
            page.check("#review-confirm")
            page.click("#local-review-form button")
            page.locator("#acceptance-panel").wait_for(state="hidden")
            rpc.artifact_hash = result["artifact_keccak256"]
            rpc.close("paid")
            rpc.height = 4
            page.fill("#settlement-tx", CLOSE_TX)
            page.click("#settle-form button")
            page.locator("#settlement-panel").wait_for(state="visible")
            assert "paid" in page.locator("#settlement-summary").inner_text()
            page.screenshot(path=str(tmp_path / "operator-desktop.png"), full_page=True)
            page.select_option("#language", "fr")
            playwright.expect(page.locator("html")).to_have_attribute("lang", "fr")
            assert page.locator("#result-download").inner_text() == "Télécharger le résultat Studio signé"
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path=str(tmp_path / "operator-mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1280, "height": 960})
            page.select_option("#language", "en")
            playwright.expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
            first_digest = operator.records(journal)[0]["request_digest"]
            fresh = deepcopy(incoming)
            fresh["plan_index"] = 0
            fresh["work_spec"]["inputs"]["coefficients"][0] = 1
            page.set_input_files(
                "#request-file",
                {"name": "fresh-evaluation.json", "mimeType": "application/json", "buffer": json.dumps(fresh).encode()},
            )
            playwright.expect(page.locator("#file-summary")).to_contain_text("Selected request")
            playwright.expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
            page.fill("#pair-seed", "1")
            page.check("#pair-confirm")
            page.click("#pair-form button")
            page.locator("#seal-panel").wait_for(state="visible")
            page.select_option("#baseline", first_digest)
            page.click("#evaluation-form button")
            page.locator("#freeze-download").wait_for(state="visible")
            with page.expect_download() as frozen:
                page.click("#freeze-download")
            assert json.loads(Path(frozen.value.path()).read_text())["domain"] == "ascension-evaluation-freeze"
            assert len(operator.records(journal)) == 2
            page.click("#disconnect")
            page.locator("#workspace").wait_for(state="hidden")
            assert not page.locator("#result-preview").inner_text()
            assert not errors
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()


def test_actual_local_ui_bounds_utf8_request_body_before_post(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    incoming, journal, _, _, _ = installed(tmp_path, monkeypatch)
    incoming["work_spec"] = workbench.invoke({"operation": "example", "family": "documentation"})

    def encode(value: object) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))

    def body(raw: str) -> str:
        return encode({"request_json": raw})

    # A valid bounded documentation input tests bytes, not ASCII padding alone.
    source = incoming["work_spec"]["inputs"]["markdown"]
    characters = (280_000 - len(encode(incoming).encode())) // 3
    incoming["work_spec"]["inputs"]["markdown"] = "界" * characters + source
    raw = encode(incoming)
    raw += " " * (280_000 - len(raw.encode()))
    assert len(raw.encode()) == 280_000
    remaining = MAX_REQUEST_BYTES - len(body(raw).encode())
    exact = raw + "\n" * (remaining // 2) + " " * (remaining % 2)
    assert len(body(exact).encode()) == MAX_REQUEST_BYTES
    oversized = exact + " "
    assert len(oversized.encode()) <= MAX_REQUEST_BYTES
    assert len(body(oversized)) < MAX_REQUEST_BYTES < len(body(oversized).encode())

    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_app(journal), log_level="error", lifespan="off"))
    thread = threading.Thread(target=lambda: server.run(sockets=[listener]), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.02)
    try:
        with playwright.sync_playwright() as driver:
            if not Path(driver.chromium.executable_path).exists():
                pytest.skip("Chromium is not installed")
            browser = driver.chromium.launch(headless=True, args=["--no-sandbox"])
            page = browser.new_page()
            posts = []
            page.on("request", lambda request: posts.append(request) if request.method == "POST" else None)
            page.goto(f"http://127.0.0.1:{port}/ascension-studio")
            page.fill("#token", (journal.root / "api.token").read_text())
            page.click("#login-form button")
            page.locator("#workspace").wait_for(state="visible")

            def select_work(text: str) -> None:
                playwright.expect(page.locator("#request-file")).to_be_enabled()
                page.set_input_files(
                    "#request-file",
                    {"name": "bounded-work.json", "mimeType": "application/json", "buffer": text.encode()},
                )
                playwright.expect(page.locator("#file-summary")).to_contain_text("Selected request")
                playwright.expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")

            for accepted in (raw, exact):
                select_work(accepted)
                with page.expect_response(
                    lambda response: response.request.method == "POST"
                    and response.url.endswith("/api/ascension-studio/import")
                ) as submitted:
                    page.click("#prepare")
                assert submitted.value.status == 200
                playwright.expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
                assert len(posts[-1].post_data_buffer) == len(body(accepted).encode())
            assert len(posts) == 2
            assert len(operator.records(journal)) == 1

            select_work(oversized)
            page.click("#prepare")
            playwright.expect(page.locator("#message")).to_contain_text("encoded request exceeds the 512 KiB API limit")
            playwright.expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
            assert len(posts) == 2

            page.set_input_files(
                "#request-file",
                {"name": "too-large.json", "mimeType": "application/json", "buffer": b" " * (MAX_REQUEST_BYTES + 1)},
            )
            playwright.expect(page.locator("#message")).to_contain_text("file exceeds 512 KiB")
            playwright.expect(page.locator("#workspace")).to_have_attribute("aria-busy", "false")
            assert not page.locator("#file-summary").inner_text()
            assert len(posts) == 2
            browser.close()
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        listener.close()
