# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import pytest

requests_mock = pytest.importorskip("requests_mock")

from alpha_factory_v1.demos.gpt2_small_cli import model_download as dg


def test_base_url_env(monkeypatch: pytest.MonkeyPatch) -> None:
    custom = "https://example.com/gpt2"
    monkeypatch.setenv("HF_GPT2_BASE_URL", custom)
    assert dg._base_url() == custom


@pytest.mark.skipif(os.getenv("PYTEST_NET_OFF") == "1", reason="network disabled")  # type: ignore[misc]
def test_download_invocation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path]] = []

    def fake_download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text("ok")
        calls.append((url, dest))

    monkeypatch.setattr(dg, "_download", fake_download)
    monkeypatch.setattr(dg, "_verify", lambda *_: None)
    dg.download_hf_gpt2(dest=tmp_path)
    assert len(calls) == len(dg._FILES)
    assert calls[0][0].startswith(dg._base_url())


def test_download_file_success(tmp_path: Path, requests_mock: "requests_mock.Mocker") -> None:
    monkeypatch_files = ["dummy.txt"]
    url = f"{dg._base_url()}/dummy.txt"
    requests_mock.get(url, text="ok")

    with pytest.MonkeyPatch.context() as m:
        m.setattr(dg, "_FILES", monkeypatch_files)
        dg.download_hf_gpt2(dest=tmp_path)

    assert (tmp_path / "dummy.txt").read_text() == "ok"


def test_download_error(tmp_path: Path, requests_mock: "requests_mock.Mocker") -> None:
    monkeypatch_files = ["dummy.txt"]
    url = f"{dg._base_url()}/dummy.txt"
    requests_mock.get(url, status_code=404)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(dg, "_FILES", monkeypatch_files)
        with pytest.raises(Exception):
            dg.download_hf_gpt2(dest=tmp_path, attempts=1)
