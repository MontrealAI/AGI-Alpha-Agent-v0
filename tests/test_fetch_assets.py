# SPDX-License-Identifier: Apache-2.0
import base64
import hashlib
from pathlib import Path
import sys
import pytest
import requests_mock

import scripts.fetch_assets as fa


def test_fetch_assets_failure(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(fa, "ASSETS", {"dummy.txt": "cid"})

    def boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("boom")

    monkeypatch.setattr(fa, "download_with_retry", boom)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(sys, "argv", ["fetch_assets.py"])
        with pytest.raises(SystemExit) as exc:
            fa.main()

    _ = capsys.readouterr()
    assert exc.value.code == 1


def test_download_with_retry_fallback(tmp_path: Path, requests_mock: requests_mock.Mocker) -> None:
    path = tmp_path / "out"
    url = "https://example.com/file"
    requests_mock.get(url, [{"status_code": 500}, {"text": "data"}])
    fa.download_with_retry(url, path, attempts=2, label="file")
    assert path.read_text() == "data"
    assert len(requests_mock.request_history) == 2


def test_download_with_retry_auth_message(
    tmp_path: Path, requests_mock: requests_mock.Mocker, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "out"
    url = "https://example.com/CID"
    requests_mock.get(url, status_code=401)
    with pytest.raises(RuntimeError) as exc:
        fa.download_with_retry(url, path, attempts=1, label="wasm_llm/pytorch_model.bin")
    out = capsys.readouterr().out
    assert "HF_GPT2_BASE_URL" in out
    msg = str(exc.value)
    assert "CID" in msg and "http" in msg
    assert "authentication" in msg.lower()


def test_verify_assets(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    content = b"data"
    asset_path = tmp_path / "file.txt"
    asset_path.write_bytes(content)
    digest = base64.b64encode(hashlib.sha384(content).digest()).decode()
    monkeypatch.setattr(fa, "ASSETS", {"file.txt": "cid"})
    monkeypatch.setattr(fa, "CHECKSUMS", {"file.txt": f"sha384-{digest}"})
    assert fa.verify_assets(tmp_path) == []
    asset_path.write_text("bad")
    assert fa.verify_assets(tmp_path) == ["file.txt"]
