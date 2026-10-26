# SPDX-License-Identifier: Apache-2.0
"""A browser execution failure cannot masquerade as an unavailable browser."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests import test_workbox_integrity as subject


def harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "index.html").write_text("<html></html>")
    (source / "service-worker.js").write_text("const WORKBOX_SW_HASH = 'sha384-original';")
    destination = tmp_path / "run"
    destination.mkdir()
    engine, browser, page, element, expectation = (MagicMock() for _ in range(5))
    engine.__enter__.return_value = engine
    engine.chromium.launch.return_value = browser
    browser.new_context.return_value.new_page.return_value = page
    page.locator.return_value = element
    element.evaluate.return_value = True
    server, thread = MagicMock(), MagicMock()
    server.server_address = ("localhost", 8123)
    monkeypatch.setattr(subject, "sync_playwright", lambda: engine)
    monkeypatch.setattr(subject, "expect", lambda locator: expectation)
    monkeypatch.setattr(subject, "_start_server", lambda directory: (server, thread))
    return source, destination, engine, browser, page, element, expectation, server, thread


@pytest.mark.parametrize("stage", ["launch", "navigation", "controls", "toast", "controller"])
def test_browser_execution_error_is_never_an_optional_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stage: str):
    source, destination, engine, browser, page, element, expectation, server, thread = harness(tmp_path, monkeypatch)
    error = subject.PlaywrightError("CSP execution blocked or browser crashed")
    operation = {
        "launch": engine.chromium.launch,
        "navigation": page.goto,
        "controls": page.wait_for_selector,
        "toast": expectation.to_contain_text,
        "controller": element.evaluate,
    }[stage]
    operation.side_effect = error
    with pytest.raises(subject.PlaywrightError) as caught:
        subject.test_workbox_hash_mismatch(destination, source)
    assert caught.value is error
    assert browser.close.call_count == (0 if stage == "launch" else 1)
    server.shutdown.assert_called_once()
    thread.join.assert_called_once()


def test_only_genuinely_missing_browser_launch_is_optional(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, destination, engine, browser, _, _, _, server, thread = harness(tmp_path, monkeypatch)
    engine.chromium.launch.side_effect = subject.PlaywrightError("Executable doesn't exist at /missing/chromium")
    with pytest.raises(pytest.skip.Exception, match="browser not installed"):
        subject.test_workbox_hash_mismatch(destination, source)
    browser.close.assert_not_called()
    server.shutdown.assert_called_once()
    thread.join.assert_called_once()


def test_integrity_signal_and_uncontrolled_page_are_both_required(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, destination, _, browser, page, element, expectation, server, thread = harness(tmp_path, monkeypatch)
    subject.test_workbox_hash_mismatch(destination, source)
    expectation.to_contain_text.assert_called_once_with("offline mode disabled", timeout=30000)
    assert [call.args for call in page.locator.call_args_list] == [("#toast",), ("html",)]
    element.evaluate.assert_called_once_with("() => navigator.serviceWorker.controller === null")
    browser.close.assert_called_once()
    server.shutdown.assert_called_once()
    thread.join.assert_called_once()


def test_controlled_page_is_an_assertion_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, destination, _, browser, _, element, _, server, thread = harness(tmp_path, monkeypatch)
    element.evaluate.return_value = False
    with pytest.raises(AssertionError):
        subject.test_workbox_hash_mismatch(destination, source)
    browser.close.assert_called_once()
    server.shutdown.assert_called_once()
    thread.join.assert_called_once()
