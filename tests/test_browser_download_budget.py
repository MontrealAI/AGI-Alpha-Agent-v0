# SPDX-License-Identifier: Apache-2.0
"""Local application-byte/request limits; no wire or elapsed-time guarantees."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from scripts.download_browser_model import BoundedOpener, ResourceLimitExceeded
from scripts import download_browser_model as downloader


@pytest.mark.parametrize("value", [0, -1, True, 1.5, None])
@pytest.mark.parametrize("field", ["max_body_bytes", "max_requests"])
def test_invalid_limits_rejected_before_open(value, field: str) -> None:
    limits = {"max_body_bytes": 5, "max_requests": 2}
    limits[field] = value
    opener = Mock()
    with pytest.raises(ValueError):
        BoundedOpener(opener, **limits)
    opener.assert_not_called()


def test_exact_cap_eof_and_multiple_responses() -> None:
    first, second = io.BytesIO(b"ab"), io.BytesIO(b"cd")
    opener = Mock(side_effect=[first, second])
    bounded = BoundedOpener(opener, max_body_bytes=4, max_requests=2)
    for expected in (b"ab", b"cd"):
        with bounded("url") as stream:
            assert stream.read(0) == b""
            assert stream.read() == expected
            assert stream.read() == b""
    assert bounded.body_bytes == 4 and bounded.requests == 2
    assert first.closed and second.closed
    with pytest.raises(ResourceLimitExceeded):
        bounded("url")
    assert opener.call_count == 2


def test_context_manager_entered_stream_and_limit_cannot_be_suppressed() -> None:
    class Manager:
        def __init__(self):
            self.stream = io.BytesIO(b"abcdef")

        def __enter__(self):
            return self.stream

        def __exit__(self, *args):
            self.stream.close()
            return True

    manager = Manager()
    bounded = BoundedOpener(lambda: manager, max_body_bytes=2, max_requests=1)
    with pytest.raises(ResourceLimitExceeded):
        with bounded() as response:
            response.read()
    assert bounded.body_bytes == 3 and manager.stream.closed
    with pytest.raises(ResourceLimitExceeded):
        bounded()


def manifest(tmp_path: Path, monkeypatch, data: bytes = b"abcd") -> Path:
    (tmp_path / "browser_model_manifest.json").write_text(
        json.dumps({"repository": "example/model", "revision": "a" * 40,
                    "files": {"asset.bin": hashlib.sha256(data).hexdigest()}})
    )
    monkeypatch.setattr(downloader, "__file__", str(tmp_path / "download_browser_model.py"))
    output = tmp_path / "output"
    output.mkdir()
    return output


def test_nonterminating_response_stops_before_commit(tmp_path: Path, monkeypatch) -> None:
    output = manifest(tmp_path, monkeypatch)
    target = output / "asset.bin"
    target.write_bytes(b"prior bytes")

    class Stream(io.BytesIO):
        returned = 0

        def read(self, size=-1):
            assert 0 < size <= 5
            self.returned += size
            return b"x" * size

    stream = Stream()
    opener = Mock(return_value=stream)
    with patch.object(downloader.time, "sleep") as sleep, pytest.raises(ResourceLimitExceeded):
        downloader.download_with_retry(output, attempts=3, max_body_bytes=4, max_requests=3, opener=opener)
    assert opener.call_count == 1 and stream.returned == 5 and stream.closed
    assert target.read_bytes() == b"prior bytes"
    assert list(output.iterdir()) == [target]
    sleep.assert_not_called()


@pytest.mark.parametrize("body_limit,accepted", [(6, True), (5, False)])
def test_body_counter_persists_across_partial_read_retry(tmp_path: Path, monkeypatch, body_limit, accepted) -> None:
    output = manifest(tmp_path, monkeypatch)
    target = output / "asset.bin"
    target.write_bytes(b"prior bytes")

    class Partial(io.BytesIO):
        returned = False

        def read(self, size=-1):
            if self.returned:
                raise TimeoutError("partial response")
            self.returned = True
            return super().read(min(size, 2))

    partial, complete = Partial(b"abcd"), io.BytesIO(b"abcd")
    opener = Mock(side_effect=[partial, complete])
    with patch.object(downloader.time, "sleep") as sleep:
        if accepted:
            downloader.download_with_retry(
                output, attempts=3, max_body_bytes=body_limit, max_requests=3, opener=opener
            )
        else:
            with pytest.raises(ResourceLimitExceeded):
                downloader.download_with_retry(
                    output, attempts=3, max_body_bytes=body_limit, max_requests=3, opener=opener
                )
    assert opener.call_count == 2 and partial.closed and complete.closed
    assert target.read_bytes() == (b"abcd" if accepted else b"prior bytes")
    assert list(output.iterdir()) == [target]
    sleep.assert_called_once_with(0.25)


def test_failed_opens_count_and_budget_errors_do_not_retry(tmp_path: Path, monkeypatch) -> None:
    output = manifest(tmp_path, monkeypatch)
    opener = Mock(side_effect=TimeoutError("connection"))
    with patch.object(downloader.time, "sleep") as sleep, pytest.raises(ResourceLimitExceeded):
        downloader.download_with_retry(output, attempts=3, max_body_bytes=10, max_requests=1, opener=opener)
    assert opener.call_count == 1 and list(output.iterdir()) == []
    sleep.assert_called_once_with(0.25)


def test_valid_cache_does_not_consume_transport_budget(tmp_path: Path, monkeypatch) -> None:
    output = manifest(tmp_path, monkeypatch)
    (output / "asset.bin").write_bytes(b"abcd")
    opener = Mock()
    downloader.download_with_retry(output, attempts=3, max_body_bytes=1, max_requests=1, opener=opener)
    opener.assert_not_called()
    assert (output / "asset.bin").read_bytes() == b"abcd"


@pytest.mark.parametrize("limits", [{"max_body_bytes": 5}, {"max_requests": 2}])
def test_paired_limits_required_before_work(limits) -> None:
    with patch.object(downloader, "download") as work, pytest.raises(ValueError):
        downloader.download_with_retry(Path("unused"), **limits)
    work.assert_not_called()


def test_cli_budget_opt_in() -> None:
    argv = [
        "downloader", "--output", "requested", "--attempts", "3",
        "--max-body-bytes", "1000", "--max-requests", "5",
    ]
    with patch("sys.argv", argv), patch.object(downloader, "download_with_retry") as wrapper:
        downloader.main()
    wrapper.assert_called_once_with(Path("requested"), attempts=3, max_body_bytes=1000, max_requests=5)


def test_nonbyte_response_is_rejected_and_closed() -> None:
    class Response(io.BytesIO):
        def read(self, size=-1):
            return "not bytes"

    response = Response()
    bounded = BoundedOpener(lambda: response, max_body_bytes=3, max_requests=1)
    with pytest.raises(TypeError, match="must return bytes"):
        with bounded() as stream:
            stream.read()
    assert response.closed and bounded.exhausted


def test_underlying_read_contract_violation_is_recorded_and_rejected() -> None:
    class Response(io.BytesIO):
        def read(self, size=-1):
            return b"too many returned bytes"

    response = Response()
    bounded = BoundedOpener(lambda: response, max_body_bytes=3, max_requests=1)
    with pytest.raises(ResourceLimitExceeded, match="violated read bound"):
        with bounded() as stream:
            stream.read()
    assert response.closed and bounded.exhausted
    assert bounded.body_bytes == len(b"too many returned bytes")
