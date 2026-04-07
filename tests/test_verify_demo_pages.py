# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from types import SimpleNamespace

from scripts.verify_demo_pages import (
    DEMO_READINESS_SELECTORS,
    DOCS_DIR,
    SITE_DIR,
    _build_demo_url,
    _extract_failure_text,
    _is_ready,
    resolve_demo_pages_dir,
)


def test_extract_failure_text_with_none() -> None:
    assert _extract_failure_text(None) == "unknown"


def test_extract_failure_text_with_string() -> None:
    assert _extract_failure_text("net::ERR_FAILED") == "net::ERR_FAILED"


def test_extract_failure_text_with_dict() -> None:
    assert _extract_failure_text({"errorText": "timeout"}) == "timeout"


def test_extract_failure_text_with_object_attribute() -> None:
    failure = SimpleNamespace(error_text="connection reset")
    assert _extract_failure_text(failure) == "connection reset"


def test_extract_failure_text_with_object_camel_case_attribute() -> None:
    failure = SimpleNamespace(errorText="request aborted")
    assert _extract_failure_text(failure) == "request aborted"


def test_extract_failure_text_with_callable() -> None:
    assert _extract_failure_text(lambda: "broken pipe") == "broken pipe"


def test_extract_failure_text_with_callable_exception() -> None:
    def _boom() -> str:
        raise RuntimeError("nope")

    assert _extract_failure_text(_boom) == "unknown"


def test_build_demo_url_uses_http() -> None:
    demo = DOCS_DIR / "alpha_agi_insight_v1"
    url = _build_demo_url("http://127.0.0.1:9999", demo, DOCS_DIR)

    assert url.startswith("http://127.0.0.1:9999/")
    assert url.endswith("/alpha_agi_insight_v1/index.html")
    assert not url.startswith("file://")


def test_insight_page_uses_explicit_readiness_contract() -> None:
    assert DEMO_READINESS_SELECTORS["alpha_agi_insight_v1"] == ("html[data-insight-ready='1']", "#root")


def test_is_ready_requires_insight_marker_or_mounted_root() -> None:
    demo = DOCS_DIR / "alpha_agi_insight_v1"
    assert _is_ready(demo, {"match": "main h1", "hasMain": True, "bodyTextLen": 200}) == (False, "")
    assert _is_ready(demo, {"match": "#root", "rootChildCount": 0}) == (False, "")
    assert _is_ready(demo, {"match": "#root", "rootChildCount": 1}) == (True, "insight-root-mounted")


def test_resolve_demo_pages_dir_prefers_env_override(tmp_path, monkeypatch) -> None:
    custom = tmp_path / "custom-pages"
    custom.mkdir()
    monkeypatch.setenv("DEMO_PAGES_DIR", str(custom))
    assert resolve_demo_pages_dir() == custom


def test_resolve_demo_pages_dir_falls_back_to_docs_when_site_missing(monkeypatch) -> None:
    monkeypatch.delenv("DEMO_PAGES_DIR", raising=False)
    monkeypatch.setattr("scripts.verify_demo_pages.SITE_DIR", SITE_DIR / "__missing__")
    assert resolve_demo_pages_dir() == DOCS_DIR


def test_resolve_demo_pages_dir_prefers_built_site(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("DEMO_PAGES_DIR", raising=False)
    fake_site = tmp_path / "site"
    insight = fake_site / "alpha_agi_insight_v1"
    insight.mkdir(parents=True)
    (insight / "index.html").write_text("<!doctype html>", encoding="utf-8")
    monkeypatch.setattr("scripts.verify_demo_pages.SITE_DIR", fake_site)
    assert resolve_demo_pages_dir() == fake_site
