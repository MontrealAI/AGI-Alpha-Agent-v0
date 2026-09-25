# SPDX-License-Identifier: Apache-2.0
"""Pinned model downloads cannot replace known bytes with corrupt responses."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from scripts import download_browser_model as downloader


def test_pinned_download_rejects_corruption_and_reuses_verified_cache(tmp_path: Path, monkeypatch) -> None:
    expected = b"verified model bytes"
    manifest = tmp_path / "browser_model_manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "repository": "example/model",
                "revision": "a" * 40,
                "files": {"onnx/model_int8.onnx": hashlib.sha256(expected).hexdigest()},
            }
        )
    )
    monkeypatch.setattr(downloader, "__file__", str(tmp_path / "download_browser_model.py"))
    target = tmp_path / "output" / "onnx" / "model_int8.onnx"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"old model")
    monkeypatch.setattr(downloader, "urlopen", lambda *a, **k: io.BytesIO(b"corrupt"))
    with pytest.raises(ValueError, match="checksum mismatch"):
        downloader.download(tmp_path / "output")
    assert target.read_bytes() == b"old model"
    assert list(target.parent.iterdir()) == [target]
    calls = []

    def response(url, **kwargs):
        calls.append(url)
        return io.BytesIO(expected)

    monkeypatch.setattr(downloader, "urlopen", response)
    downloader.download(tmp_path / "output")
    downloader.download(tmp_path / "output")
    assert len(calls) == 1 and "/resolve/" + "a" * 40 + "/" in calls[0]
    assert target.read_bytes() == expected
