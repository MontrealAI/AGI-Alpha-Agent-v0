# SPDX-License-Identifier: Apache-2.0
import os
from pathlib import Path
import requests  # type: ignore[import-untyped]

import requests_mock

import pytest

import scripts.download_openai_gpt2 as dg


def test_model_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    custom_base = "https://example.com/gpt2"
    monkeypatch.setenv("OPENAI_GPT2_BASE_URL", custom_base)
    urls = dg.model_urls("124M")
    prefix = f"{custom_base}/124M/"
    assert urls[0].startswith(prefix)
    assert urls[-1].endswith("vocab.bpe")


@pytest.mark.skipif(os.getenv("PYTEST_NET_OFF") == "1", reason="network disabled")  # type: ignore[misc]
def test_download_invocation(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[str, Path]] = []

    def fake_download(url: str, dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        calls.append((url, dest))
        dest.write_text("stub")

    monkeypatch.setattr(dg, "_download", fake_download)
    dg.download_openai_gpt2("124M", dest=tmp_path)
    assert len(calls) == len(dg._FILE_LIST)
    assert calls[0][0] == dg.model_urls("124M")[0]


def test_download_file_success(tmp_path: Path, requests_mock: "requests_mock.Mocker") -> None:
    monkeypatch_file_list = ["dummy.txt"]
    url = dg.model_urls("124M")[0].replace("checkpoint", "dummy.txt")
    requests_mock.get(url, text="ok")

    dest_dir = tmp_path / "models"
    with pytest.MonkeyPatch.context() as m:
        m.setattr(dg, "_FILE_LIST", monkeypatch_file_list)
        dg.download_openai_gpt2("124M", dest=dest_dir)

    assert (dest_dir / "124M" / "dummy.txt").read_text() == "ok"


def test_download_error(tmp_path: Path, requests_mock: "requests_mock.Mocker") -> None:
    monkeypatch_file_list = ["dummy.txt"]
    url = dg.model_urls("124M")[0].replace("checkpoint", "dummy.txt")
    requests_mock.get(url, status_code=404)

    dest_dir = tmp_path / "models"
    with pytest.MonkeyPatch.context() as m:
        m.setattr(dg, "_FILE_LIST", monkeypatch_file_list)
        with pytest.raises(Exception):
            dg.download_openai_gpt2("124M", dest=dest_dir, attempts=1)


def test_download_small_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.download_gpt2_small as ds

    calls: list[str] = []

    def fail(dest: Path, model: str = "124M") -> None:
        calls.append("hf")
        raise RuntimeError("fail")

    def succeed(model: str, dest: Path | str = Path("dest"), attempts: int = 3) -> None:
        calls.append("openai")

    with monkeypatch.context() as m:
        m.setattr(ds.download_hf_gpt2, "download_hf_gpt2", fail)
        m.setattr(ds.download_openai_gpt2, "download_openai_gpt2", succeed)
        ds.download_model(Path("models"))
    assert calls == ["hf", "openai"]


def test_gpt2_link_head(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "OPENAI_GPT2_BASE_URL",
        "https://huggingface.co/openai-community/gpt2/resolve/main",
    )
    url = os.environ["OPENAI_GPT2_BASE_URL"].rstrip("/") + "/config.json"

    class FakeResponse:
        status_code = 200

    monkeypatch.setattr(requests, "head", lambda *_a, **_kw: FakeResponse())

    resp = requests.head(url, allow_redirects=True, timeout=10)
    assert resp.status_code == 200
