# SPDX-License-Identifier: Apache-2.0
"""Behavioral coverage for evidence, inference boundaries and actual planning outcomes."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from alpha_factory_v1.demos.muzeromctsllmagent_v0.lab import CORPUS, ollama_advice, retrieve, run, validate_advice

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/muzeromctsllmagent_v0"


def valid_advice():
    return {
        "action": 1,
        "rationale": "Take the delayed route.",
        "citations": [{"source_id": "finish", "quote": CORPUS[2].text}],
    }


def test_retrieval_ranks_and_hashes_real_sources():
    rows = retrieve("second state")
    assert len(rows) == 4
    assert rows[0]["overlap"] >= rows[-1]["overlap"]
    for row in rows:
        assert row["sha256"] == hashlib.sha256(row["text"].encode()).hexdigest()
        assert row["source"].startswith("muzero_planning/training.py:")
    assert all(row["overlap"] == 0 for row in retrieve("unmatchedword"))


@pytest.mark.parametrize("question", ["", "  ", "x" * 2001, " " * 2000 + "x", None])
def test_question_budget(question):
    with pytest.raises(ValueError):
        retrieve(question)


def test_exact_citation_required():
    assert validate_advice(valid_advice(), retrieve("reward"))["action"] == 1
    for field, value in [
        ("action", True),
        ("action", 2),
        ("action", "1"),
        ("rationale", ""),
        ("rationale", "x" * 2001),
        ("rationale", " " * 2000 + "x"),
        ("citations", []),
        ("citations", [{"source_id": "invented", "quote": "money"}]),
        ("citations", [{"source_id": "finish", "quote": "not a source quote"}]),
    ]:
        data = valid_advice()
        data[field] = value
        with pytest.raises(ValueError):
            validate_advice(data, retrieve("reward"))
    with pytest.raises(ValueError):
        validate_advice({**valid_advice(), "execute": "shell"}, retrieve("reward"))


def test_ollama_real_http_contract(monkeypatch):
    import httpx

    original = httpx.AsyncClient
    requests = []

    def respond(request):
        requests.append(request)
        body = json.loads(request.content)
        assert str(request.url) == "http://127.0.0.1:11434/api/chat"
        assert body["stream"] is False and body["format"]["additionalProperties"] is False
        assert body["options"]["num_predict"] == 512
        return httpx.Response(200, json={"done": True, "message": {"content": json.dumps(valid_advice())}})

    def client(**kwargs):
        assert kwargs["trust_env"] is False and kwargs["follow_redirects"] is False
        return original(transport=httpx.MockTransport(respond), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client)
    result = ollama_advice("reward?", retrieve("reward"), "test-model:local")
    assert result["mode"] == "ollama" and result["action"] == 1
    assert len(requests) == 1


@pytest.mark.parametrize("kind", ["http", "incomplete", "bad_json", "oversize", "invented", "timeout"])
def test_ollama_fails_without_synthetic_success(monkeypatch, kind):
    import httpx

    original = httpx.AsyncClient

    def respond(request):
        if kind == "timeout":
            raise httpx.ReadTimeout("timeout", request=request)
        if kind == "http":
            return httpx.Response(503)
        if kind == "oversize":
            return httpx.Response(200, content=b"x" * 65537)
        if kind == "bad_json":
            return httpx.Response(200, content=b"invalid")
        advice = valid_advice()
        advice["citations"][0]["quote"] = "fabricated"
        return httpx.Response(200, json={"done": kind != "incomplete", "message": {"content": json.dumps(advice)}})

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    with pytest.raises(ValueError):
        ollama_advice("reward?", retrieve("reward"), "test-model")


def test_model_name_cannot_be_a_command():
    with pytest.raises(ValueError):
        ollama_advice("reward?", retrieve("reward"), "model; rm -rf /")


def test_real_learning_and_counterfactuals():
    pytest.importorskip("torch")
    pytest.importorskip("gymnasium")
    report = list(run(episodes=32, seed=42))[-1]
    from alpha_factory_v1.demos.muzeromctsllmagent_v0 import __version__

    assert report["provenance"]["demo_version"] == __version__
    for path, digest in report["provenance"]["source_sha256"].items():
        assert digest == hashlib.sha256((DEMO.parent / path).read_bytes()).hexdigest()
    assert report["advice"]["mode"] == "disabled"
    assert report["agreement"] is None
    assert report["search_action"] == 1
    assert report["execution"] == "simulation_only" and report["decision"] == "review_required"
    assert [r["observed_return"] for r in report["counterfactuals"]] == [0.3, 1.0]
    assert sum(r["visits"] for r in report["experiment"]["search_after"]) == 32
    for row in report["experiment"]["search_after"]:
        if row["visits"] == 0:
            assert row["predicted_reward"] is None and row["value"] is None and row["q"] is None
    assert set(report["experiment"]["evaluation"]) == {"random", "untrained_search", "trained_policy", "trained_search"}
    json.dumps(report, allow_nan=False)


def test_advice_disagreement_is_retained(monkeypatch):
    pytest.importorskip("torch")
    pytest.importorskip("gymnasium")
    import alpha_factory_v1.demos.muzeromctsllmagent_v0.lab as lab

    monkeypatch.setattr(lab, "ollama_advice", lambda *a: {"mode": "test-double", "model": "test", **valid_advice()})
    report = list(run(episodes=0, simulations=4, model="test"))[-1]
    assert report["agreement"] == (report["search_action"] == 1)
    assert report["advice"]["mode"] == "test-double"
    assert report["experiment"]["history"] == []


def test_cli_help_and_overwrite_protection(tmp_path):
    command = [sys.executable, "-m", "alpha_factory_v1.demos.muzeromctsllmagent_v0"]
    result = subprocess.run(command + ["--help"], capture_output=True, text=True, timeout=15)
    assert result.returncode == 0 and "--headless" in result.stdout
    output = tmp_path / "existing.json"
    output.write_text("keep")
    result = subprocess.run(
        command + ["--headless", "--output", str(output)], capture_output=True, text=True, timeout=15
    )
    assert result.returncode == 2 and "already exists" in result.stderr
    assert output.read_text() == "keep"


def test_launcher_help_does_not_write_caller_files(tmp_path):
    result = subprocess.run(
        ["bash", str(DEMO / "install_and_launch.sh"), "--help"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0 and "7862" in result.stdout
    assert list(tmp_path.iterdir()) == []


def test_launcher_rejects_unsupported_platform_even_when_optimized(tmp_path):
    import shlex

    interpreter = tmp_path / "unsupported-python"
    code = 'import platform,sys; platform.system=lambda: "Darwin"; exec(sys.stdin.read())'
    interpreter.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} -c {shlex.quote(code)}\n")
    interpreter.chmod(0o700)
    result = subprocess.run(
        ["bash", str(DEMO / "install_and_launch.sh")],
        cwd=tmp_path,
        env={**os.environ, "PYTHON": str(interpreter), "PYTHONOPTIMIZE": "1"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode != 0 and "supports Linux x86_64" in result.stderr
    assert list(tmp_path.iterdir()) == [interpreter]


@pytest.mark.parametrize("seed", [float("inf"), float("nan"), 0.5])
def test_ui_invalid_input_clears_results_and_exposes_failure(seed):
    gr = pytest.importorskip("gradio")
    from alpha_factory_v1.demos.muzeromctsllmagent_v0.ui import build

    demo = build(SimpleNamespace(question="reward?", episodes=0, simulations=4, seed=42, model=""))
    execute = next(block.fn for block in demo.fns.values() if getattr(block.fn, "__name__", "") == "execute")
    events = execute("reward?", 0, 4, seed, "")
    assert "Preparing" in next(events)[0]
    failure = next(events)
    assert "Run failed" in failure[0]
    assert failure[3] is None and failure[7] == "" and failure[8]["interactive"] is False
    with pytest.raises(gr.Error, match="whole numbers"):
        next(events)


def test_macos_profile_tracks_shared_versions_without_linux_torch_suffix():
    from packaging.requirements import Requirement

    def requirements(path):
        return {
            requirement.name: str(requirement)
            for line in path.read_text().splitlines()
            if line.strip() and not line.startswith(("#", "--"))
            for requirement in [Requirement(line)]
        }

    shared = requirements(DEMO.parent / "muzero_planning/requirements.txt")
    macos = requirements(DEMO / "requirements-macos.txt")
    assert macos.pop("torch") == shared.pop("torch").replace("+cpu", "")
    assert macos == shared


def test_archived_originals_and_credential_redaction():
    archive = DEMO / "archive"
    manifest = json.loads((archive / "manifest.json").read_text())
    for entry in manifest["files"]:
        raw = (archive / entry["archive"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == entry["archive_sha256"]
    assert sum(r["credential_redactions"] for r in manifest["files"]) == 3


def test_ui_run_and_stop_controls_follow_actual_execution(monkeypatch):
    gr = pytest.importorskip("gradio")
    from alpha_factory_v1.demos.muzeromctsllmagent_v0 import ui

    def fake_run(*args, **kwargs):
        yield {"status": "training", "history": [{"episode": 1, "reward": 0.3}], "completed": 1, "total": 4}
        yield {
            "status": "complete",
            "search_action": 1,
            "agreement": None,
            "evidence": [],
            "advice": None,
            "counterfactuals": [],
            "experiment": {"history": [], "search_after": [], "evaluation": {"trained_search": [1.0]}},
        }

    monkeypatch.setattr(ui, "run", fake_run)
    demo = ui.build(SimpleNamespace(question="reward?", episodes=4, simulations=4, seed=42, model=""))
    stop_button = next(
        block for block in demo.blocks.values() if isinstance(block, gr.Button) and block.value == "Stop"
    )
    assert stop_button.interactive is False
    execute = next(block.fn for block in demo.fns.values() if getattr(block.fn, "__name__", "") == "execute")
    events = list(execute("reward?", 4, 4, 42, ""))
    for update in events[:-1]:
        assert update[8]["interactive"] is False
        assert update[9]["interactive"] is False and update[10]["interactive"] is True
    assert events[-1][8]["interactive"] is True
    assert events[-1][9]["interactive"] is True and events[-1][10]["interactive"] is False
    stop = next(block.fn for block in demo.fns.values() if getattr(block.fn, "__name__", "") == "request_stop")
    stopped = stop()
    assert stopped[0].startswith("Stop requested.")
    assert stopped[1]["interactive"] is True
    assert stopped[2]["interactive"] is False and stopped[3]["interactive"] is False and stopped[4] == ""
