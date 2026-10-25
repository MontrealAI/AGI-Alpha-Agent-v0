# SPDX-License-Identifier: Apache-2.0
"""Qdrant target and redirect boundaries, without live network access."""

from __future__ import annotations

import hashlib
import json
import sys
from types import ModuleType
from typing import Any
from unittest.mock import Mock
from urllib import request as urllib_request

import pytest

from alpha_factory_v1.demos.macro_sentinel import data_feeds


@pytest.fixture
def event() -> dict[str, Any]:
    return {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "fed_speech": "Authored public development example",
        "yield_10y": 4.0,
        "yield_3m": 4.5,
        "stable_flow": 1.0,
        "es_settle": 5000.0,
    }


@pytest.fixture
def put(monkeypatch: pytest.MonkeyPatch) -> Mock:
    transport = ModuleType("af_requests")
    request = Mock(return_value=Mock(status_code=200))
    transport.put = request  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "af_requests", transport)
    return request


@pytest.mark.parametrize(
    ("target", "origin"),
    [
        ("qdrant.example:6333", "https://qdrant.example:6333"),
        ("https://QDRANT.example:6333", "https://qdrant.example:6333"),
        ("qdrant", "https://qdrant"),
        ("https://[2001:db8::1]:6333", "https://[2001:db8::1]:6333"),
        ("127.0.0.1:6333", "http://127.0.0.1:6333"),
        ("127.23.45.67:6333", "http://127.23.45.67:6333"),
        ("localhost:6333", "http://localhost:6333"),
        ("[::1]:6333", "http://[::1]:6333"),
        ("http://localhost:6333", "http://localhost:6333"),
        ("http://127.0.0.1:6333", "http://127.0.0.1:6333"),
        ("http://[::1]:6333", "http://[::1]:6333"),
        ("https://localhost:6333", "https://localhost:6333"),
    ],
)
def test_qdrant_uses_exact_validated_origin(
    monkeypatch: pytest.MonkeyPatch, event: dict[str, Any], put: Mock, target: str, origin: str
) -> None:
    monkeypatch.setattr(data_feeds, "VEC_URL", target)
    data_feeds._push_qdrant(event)
    put.assert_called_once()
    args, kwargs = put.call_args
    assert args == (origin + "/collections/macro/points",)
    assert kwargs["allow_redirects"] is False
    assert kwargs["timeout"] == 5
    assert kwargs["headers"] == {"Content-Type": "application/json"}
    assert json.loads(kwargs["data"]) == {
        "points": [
            {
                "id": event["timestamp"],
                "vector": list(hashlib.sha256(event["fed_speech"].encode()).digest()[:8]),
                "payload": event,
            }
        ]
    }
    put.return_value.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize(
    "target",
    [
        "http://qdrant.example:6333",
        "http://qdrant:6333",
        "http://127.0.0.1.evil.example:6333",
        "http://localhost.evil.example:6333",
        "http://[::ffff:127.0.0.1]:6333",
        "http://0.0.0.0:6333",
        "https://user:password@qdrant.example:6333",
        "qdrant.example@other.example:6333",
        "https://qdrant.example:6333/",
        "qdrant.example:6333/collections/other/points",
        "https://qdrant.example:6333?token=synthetic",
        "https://qdrant.example:6333?",
        "https://qdrant.example:6333#fragment",
        "https://qdrant.example:6333#",
        "https://qdrant.example\\@127.0.0.1:6333",
        "qdrant.example\n",
        "https://qdrant.example\t:6333",
        " qdrant.example:6333",
        "qdrant.example:6333 ",
        "https://qdrant.example\x00:6333",
        "https://qdrant.example\x7f:6333",
        "https://qdrant.example%2fother.example:6333",
        "http://[::1%25lo]:6333",
        "https://[v1.fe]:6333",
        "http://[::1]other.example:6333",
        "http://prefix[::1]:6333",
        "//qdrant.example:6333",
        "ftp://qdrant.example:6333",
        "https:////qdrant.example:6333",
        "https://",
        "qdrant.example:",
        "qdrant.example:0",
        "qdrant.example:65536",
        "qdrant.example:abc",
        "qdrant.example:-1",
        "qdrant.example:6333:6444",
        "127.0.0.999:6333",
        "2130706433:6333",
        "localhost.:6333",
        "qdrant..example:6333",
        "-qdrant.example:6333",
        "qdrant.example;other:6333",
        "https://qdrant\N{FULLWIDTH FULL STOP}example:6333",
    ],
)
def test_qdrant_refuses_unsafe_target_before_transport(
    monkeypatch: pytest.MonkeyPatch, event: dict[str, Any], put: Mock, target: str
) -> None:
    monkeypatch.setattr(data_feeds, "VEC_URL", target)
    with pytest.raises(ValueError, match="Qdrant"):
        data_feeds._push_qdrant(event)
    put.assert_not_called()


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_qdrant_refuses_redirect_response(
    monkeypatch: pytest.MonkeyPatch, event: dict[str, Any], put: Mock, status: int
) -> None:
    monkeypatch.setattr(data_feeds, "VEC_URL", "https://qdrant.example:6333")
    put.return_value.status_code = status
    put.return_value.headers = {"Location": "http://other.example/collect"}
    with pytest.raises(ValueError, match="Qdrant redirects"):
        data_feeds._push_qdrant(event)
    put.assert_called_once()
    assert put.call_args.kwargs["allow_redirects"] is False
    put.return_value.raise_for_status.assert_not_called()


def test_qdrant_real_requests_does_not_send_redirected_request(
    monkeypatch: pytest.MonkeyPatch, event: dict[str, Any]
) -> None:
    """Exercise installed requests redirect handling with its adapter mocked."""
    pytest.importorskip("requests.adapters", reason="real requests is optional")
    import requests

    attempts: list[str] = []

    def send(_adapter: Any, request: Any, **kwargs: Any) -> Any:
        attempts.append(request.url)
        assert kwargs["verify"] is True
        assert kwargs["timeout"] == 5
        response = requests.Response()
        response.url = request.url
        response.request = request
        response._content = b""
        response.status_code = 307 if len(attempts) == 1 else 200
        response.headers["Location"] = "http://other.example/collect"
        return response

    with requests.Session() as session:
        session.trust_env = False
        monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
        transport = ModuleType("af_requests")
        transport.put = session.put  # type: ignore[attr-defined]
        monkeypatch.setitem(sys.modules, "af_requests", transport)
        monkeypatch.setattr(data_feeds, "VEC_URL", "https://qdrant.example:6333")
        with pytest.raises(ValueError, match="Qdrant redirects"):
            data_feeds._push_qdrant(event)
    assert attempts == ["https://qdrant.example:6333/collections/macro/points"]


def test_qdrant_unconfigured_does_not_send(monkeypatch: pytest.MonkeyPatch, event: dict[str, Any], put: Mock) -> None:
    monkeypatch.setattr(data_feeds, "VEC_URL", None)
    data_feeds._push_qdrant(event)
    put.assert_not_called()


def test_qdrant_transport_without_redirect_control_fails_closed(
    monkeypatch: pytest.MonkeyPatch, event: dict[str, Any]
) -> None:
    from alpha_factory_v1 import af_requests as fallback

    network = Mock(side_effect=AssertionError("No network is permitted in this test"))
    monkeypatch.setitem(sys.modules, "af_requests", fallback)
    monkeypatch.setattr(urllib_request, "urlopen", network)
    monkeypatch.setattr(data_feeds, "VEC_URL", "https://qdrant.example:6333")
    with pytest.raises(TypeError, match="allow_redirects"):
        data_feeds._push_qdrant(event)
    network.assert_not_called()


def test_qdrant_refusal_preserves_other_fanout_sinks(
    monkeypatch: pytest.MonkeyPatch, event: dict[str, Any], put: Mock
) -> None:
    database, redis = Mock(), Mock()
    monkeypatch.setattr(data_feeds, "_push_db", database)
    monkeypatch.setattr(data_feeds, "_push_redis", redis)
    monkeypatch.setattr(data_feeds, "VEC_URL", "http://qdrant.example:6333")
    data_feeds._fanout(event)
    database.assert_called_once_with(event)
    redis.assert_called_once_with(event)
    put.assert_not_called()
