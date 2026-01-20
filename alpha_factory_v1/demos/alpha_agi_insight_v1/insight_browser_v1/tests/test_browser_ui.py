# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

pw = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


def test_slider_updates_hash_and_restarts() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist" / "index.html"
    url = dist.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")

        initial_hash = page.evaluate("location.hash")
        seed_input = page.locator("#seed")
        seed_input.fill("999")
        seed_input.dispatch_event("change")

        page.wait_for_function("location.hash !== '%s'" % initial_hash)
        assert page.evaluate("location.hash") != initial_hash

        page.wait_for_selector("#toast.show")
        assert "restarted" in page.inner_text("#toast")
        browser.close()


def test_reload_restores_settings() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist" / "index.html"
    url = dist.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")

        seed_input = page.locator("#seed")
        seed_input.fill("321")
        seed_input.dispatch_event("change")
        page.wait_for_function("location.hash.includes('seed=321')")

        page.evaluate("location.hash = ''")
        page.reload()
        page.wait_for_selector("#controls")
        assert page.input_value("#seed") == "321"
        browser.close()


def test_llm_offline() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist" / "index.html"
    url = dist.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")

        out = page.evaluate("window.llmChat('hi')")
        assert out.startswith("[offline]")
        browser.close()


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "wasm_llm" / "pytorch_model.bin").exists(),
    reason="model file missing",
)  # type: ignore[misc]
def test_llm_offline_pipeline() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist" / "index.html"
    url = dist.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")

        out = page.evaluate("window.llmChat('hello')")
        assert not out.startswith("[offline]")
        browser.close()


def test_llm_openai_path() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist" / "index.html"
    url = dist.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.route(
            "https://api.openai.com/**",
            lambda route: route.fulfill(
                status=200,
                content_type="application/json",
                body='{"choices":[{"message":{"content":"pong"}}]}',
            ),
        )
        page.goto(url)
        page.evaluate("localStorage.setItem('OPENAI_API_KEY','sk')")

        out = page.evaluate("window.llmChat('hi')")
        assert out == "pong"
        browser.close()


@pytest.mark.skipif(shutil.which("npm") is None, reason="npm not installed")  # type: ignore[misc]
def test_env_value_injected(tmp_path: Path) -> None:
    browser_dir = Path(__file__).resolve().parents[1]
    target = tmp_path / "browser"
    shutil.copytree(browser_dir, target)
    (target / ".env").write_text("PINNER_TOKEN=test123\n")
    env = os.environ.copy()
    env.setdefault("FETCH_ASSETS_SKIP_LLM", "1")
    subprocess.check_call(["npm", "run", "build"], cwd=target, env=env)

    url = (target / "dist" / "index.html").as_uri()
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")
        assert page.evaluate("window.PINNER_TOKEN") == "test123"
        assert page.evaluate("typeof window.OPENAI_API_KEY === 'undefined' || !window.OPENAI_API_KEY")
        browser.close()


def test_runs_persist_after_reload() -> None:
    src = Path(__file__).resolve().parents[1] / "index.html"
    url = src.as_uri() + "#s=1&p=10&g=2"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")
        page.wait_for_function("window.archive !== undefined")
        page.wait_for_timeout(1000)
        count_before = page.evaluate("window.archive.list().then(r=>r.length)")
        page.reload()
        page.wait_for_selector("#controls")
        page.wait_for_function("window.archive !== undefined")
        count_after = page.evaluate("window.archive.list().then(r=>r.length)")
        assert count_before == count_after and count_before > 0
        browser.close()


def test_workers_in_sandbox_iframes() -> None:
    dist = Path(__file__).resolve().parents[1] / "dist" / "index.html"
    url = dist.as_uri()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector("#controls")
        page.wait_for_function("document.querySelectorAll('iframe[sandbox]').length >= 2")
        frames = page.query_selector_all("iframe[sandbox]")
        assert len(frames) >= 2
        for f in frames:
            assert f.get_attribute("sandbox") == "allow-scripts"
        browser.close()
