# SPDX-License-Identifier: Apache-2.0
"""Bounded retry policy and unchanged atomic downloader regression coverage."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import ssl
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from scripts import download_browser_model as downloader


@pytest.mark.parametrize("attempts", [False, True, 0, 4, -1, 1.5, "3", None])
def test_invalid_budget_rejected_without_work(attempts) -> None:
    with patch.object(downloader, "download") as work, pytest.raises(ValueError):
        downloader.download_with_retry(Path("unused"), attempts=attempts)
    work.assert_not_called()


@pytest.mark.parametrize("backoff", [False, -1, 3, float("nan"), float("inf"), "1", None])
def test_invalid_delay_rejected_without_work(backoff) -> None:
    with patch.object(downloader, "download") as work, pytest.raises(ValueError):
        downloader.download_with_retry(Path("unused"), backoff=backoff)
    work.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        ValueError("checksum mismatch"),
        PermissionError("write denied"),
        URLError("unknown"),
        URLError(ssl.SSLCertVerificationError("untrusted")),
        ssl.SSLCertVerificationError("untrusted"),
        HTTPError("x", 404, "missing", None, None),
        HTTPError("x", 401, "auth", None, None),
        HTTPError("x", 403, "forbidden", None, None),
        HTTPError("x", 501, "not implemented", None, None),
    ],
)
def test_permanent_failure_not_retried(error) -> None:
    with patch.object(downloader, "download", side_effect=error) as work:
        with patch.object(downloader.time, "sleep") as sleep, pytest.raises(type(error)):
            downloader.download_with_retry(Path("unused"), attempts=3)
    assert work.call_count == 1
    sleep.assert_not_called()


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("read"),
        ConnectionError("connection"),
        URLError(TimeoutError("url")),
        HTTPError("x", 429, "busy", None, None),
        HTTPError("x", 500, "server", None, None),
        HTTPError("x", 502, "gateway", None, None),
        HTTPError("x", 503, "busy", None, None),
        HTTPError("x", 504, "timeout", None, None),
    ],
)
def test_exhaustion_retains_exact_error_and_budget(error) -> None:
    with patch.object(downloader, "download", side_effect=error) as work:
        with patch.object(downloader.time, "sleep") as sleep, pytest.raises(type(error)) as raised:
            downloader.download_with_retry(Path("unused"), attempts=3)
    assert raised.value is error
    assert work.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [0.25, 0.5]


@pytest.mark.parametrize("attempts", [1, 2, 3])
def test_requested_budget_and_maximum_backoff(attempts: int) -> None:
    error = TimeoutError("read")
    with patch.object(downloader, "download", side_effect=error) as work:
        with patch.object(downloader.time, "sleep") as sleep, pytest.raises(TimeoutError):
            downloader.download_with_retry(Path("unused"), attempts=attempts, backoff=2)
    assert work.call_count == attempts
    assert [call.args[0] for call in sleep.call_args_list] == [2, 4][: attempts - 1]


def test_early_success_stops_without_additional_sleep() -> None:
    with patch.object(downloader, "download", side_effect=[TimeoutError("read"), None]) as work:
        with patch.object(downloader.time, "sleep") as sleep:
            downloader.download_with_retry(Path("unused"), attempts=3)
    assert work.call_count == 2
    sleep.assert_called_once_with(0.25)


def test_cli_routes_to_bounded_wrapper() -> None:
    with patch("sys.argv", ["download_browser_model.py", "--output", "requested"]):
        with patch.object(downloader, "download_with_retry") as wrapper:
            downloader.main()
    wrapper.assert_called_once_with(Path("requested"), attempts=1)


def test_retry_reuses_prior_verified_files_and_warm_queue(tmp_path: Path, monkeypatch) -> None:
    payloads = {"first.json": b"first verified bytes", "second.json": b"second verified bytes"}
    manifest = {
        "repository": "example/model",
        "revision": "a" * 40,
        "files": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
    }
    (tmp_path / "browser_model_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr(downloader, "__file__", str(tmp_path / "download_browser_model.py"))
    requests = []
    failed = False

    def response(url, **kwargs):
        nonlocal failed
        name = url.rsplit("/", 1)[-1]
        requests.append(name)
        assert kwargs == {"timeout": 120}
        if name == "second.json" and not failed:
            failed = True
            raise TimeoutError("interrupted transport")
        return io.BytesIO(payloads[name])

    monkeypatch.setattr(downloader, "urlopen", response)
    with patch.object(downloader.time, "sleep") as sleep:
        downloader.download_with_retry(tmp_path / "output", attempts=3)
        downloader.download_with_retry(tmp_path / "output", attempts=3)
    assert requests == ["first.json", "second.json", "second.json"]
    sleep.assert_called_once_with(0.25)
    assert sorted(path.name for path in (tmp_path / "output").iterdir()) == sorted(payloads)
    for name, expected in payloads.items():
        assert (tmp_path / "output" / name).read_bytes() == expected


def test_default_preserves_single_attempt() -> None:
    error = TimeoutError("read")
    with patch.object(downloader, "download", side_effect=error) as work:
        with patch.object(downloader.time, "sleep") as sleep, pytest.raises(TimeoutError):
            downloader.download_with_retry(Path("unused"))
    work.assert_called_once_with(Path("unused"))
    sleep.assert_not_called()


def test_cli_explicitly_opts_into_retries() -> None:
    with patch("sys.argv", ["download_browser_model.py", "--output", "requested", "--attempts", "3"]):
        with patch.object(downloader, "download_with_retry") as wrapper:
            downloader.main()
    wrapper.assert_called_once_with(Path("requested"), attempts=3)
