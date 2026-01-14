# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from types import SimpleNamespace

from scripts.verify_demo_pages import DOCS_DIR, _build_demo_url, _extract_failure_text


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


def test_extract_failure_text_with_callable_object() -> None:
    class Failure:
        errorText = "network reset"

    def _call() -> Failure:
        return Failure()

    assert _extract_failure_text(_call) == "network reset"


def test_build_demo_url_uses_http() -> None:
    demo = DOCS_DIR / "alpha_agi_insight_v1"
    url = _build_demo_url("http://127.0.0.1:9999", demo)

    assert url.startswith("http://127.0.0.1:9999/")
    assert url.endswith("/alpha_agi_insight_v1/index.html")
    assert not url.startswith("file://")
