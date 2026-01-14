# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from types import SimpleNamespace

from scripts.verify_demo_pages import _extract_failure_text, _format_request_failure, _resolve_request_failure


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


def test_resolve_request_failure_with_callable() -> None:
    class DummyRequest:
        def __init__(self) -> None:
            self.url = "file://example"

        def failure(self) -> dict[str, str]:
            return {"errorText": "timeout"}

    assert _resolve_request_failure(DummyRequest()) == {"errorText": "timeout"}


def test_format_request_failure_with_string_payload() -> None:
    class DummyRequest:
        def __init__(self) -> None:
            self.url = "file://example"
            self.failure = "net::ERR_FAILED"

    assert _format_request_failure(DummyRequest()) == "file://example -> net::ERR_FAILED"


def test_format_request_failure_with_callable_exception() -> None:
    class DummyRequest:
        def __init__(self) -> None:
            self.url = "file://example"

        def failure(self) -> str:
            raise RuntimeError("boom")

    assert _format_request_failure(DummyRequest()) == "file://example -> unknown"
