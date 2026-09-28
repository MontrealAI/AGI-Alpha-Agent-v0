# SPDX-License-Identifier: Apache-2.0
"""Protect preservation, installed assets, local serving and public release gates."""
from __future__ import annotations

from copy import deepcopy
import hashlib
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
from threading import Thread

import pytest

from alpha_factory_v1.demos.meta_agentic_tree_search_v0.lab_cli import main
from alpha_factory_v1.demos.meta_agentic_tree_search_v0.lab_server import Handler, WEB
from scripts import mats_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/meta_agentic_tree_search_v0"


def test_original_research_bytes_are_preserved() -> None:
    expected = {
        "RESEARCH_ARCHIVE.md": "9942faed0c8e585be220a4fef9ece36817867ae949262d8b84d083f0fce4bbfa",
        "research_notebook_archive.ipynb": "d1dd27c88eac6f76bfdf4a5b1976d4b33270c5d95cb87b997e16ddc48392a9e5",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == digest
    original = (ROOT / "scripts/templates/mats-original.html").read_bytes()
    assert hashlib.sha256(original).hexdigest() == "63639c40673a06e6f00770ba356aa0ec804a5612c8fb090a58c4a968883b2dd9"
    assert (ROOT / "docs/meta_agentic_tree_search_v0/research.html").read_bytes() == original


def test_packaged_assets_are_current_and_complete() -> None:
    for path in (WEB / "assets").rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (ROOT / "docs" / path.relative_to(WEB)).read_bytes(), path
    page = (WEB / "meta_agentic_tree_search_v0/index.html").read_text()
    assert 'data-packaged="true"' in page
    assert 'href="research.html"' not in page
    assert 'id="workspace"' in page and 'id="tree"' in page
    assert "{{VERSION}}" not in page


def test_server_serves_only_packaged_assets_with_loopback_host() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for path, status in [
            ("/", 200),
            ("/__live", 200),
            ("/assets/mats/engine.mjs?v=1.17.0", 200),
            ("/../lab.py", 404),
            ("/.env", 404),
            ("/assets/", 404),
            ("/%2e%2e/lab.py", 404),
        ]:
            connection.request("GET", path)
            response = connection.getresponse()
            assert response.status == status
            response.read()
            if status == 200:
                assert response.getheader("X-Content-Type-Options") == "nosniff"
                assert "frame-ancestors 'none'" in response.getheader("Content-Security-Policy")
        connection.request("GET", "/__live", headers={"Host": "untrusted.example"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        connection.request("HEAD", "/__live")
        response = connection.getresponse()
        assert response.status == 200 and response.read() == b""
        connection.request("POST", "/execute", body=b"{}")
        response = connection.getresponse()
        assert response.status == 501
        response.read()
        connection.close()
    finally:
        server.shutdown()
        server.server_close()


def test_cli_errors_and_read_only_verification(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--list"]) == 0
    assert "proxy-trap" in capsys.readouterr().out
    assert main(["--case", "missing", "--output", str(tmp_path)]) == 2
    assert not list(tmp_path.iterdir())
    assert "Unknown case" in capsys.readouterr().err
    assert main(["--serve", "--port", "0"]) == 2
    assert "Port" in capsys.readouterr().err
    assert main(["--output", str(tmp_path)]) == 0
    capsys.readouterr()
    run = next(tmp_path.glob("*/run.json"))
    before = {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert main(["--verify", str(run)]) == 0
    assert "Recomputed every selection" in capsys.readouterr().out
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_notebook_executes_all_code_cells_without_network(tmp_path: Path) -> None:
    notebook = str(DEMO / "colab_meta_agentic_tree_search.ipynb")
    code = f"""
import json,os,pathlib,sys
sys.path.insert(0,{str(ROOT)!r})
cells=json.loads(pathlib.Path({notebook!r}).read_text())['cells']
scope={{}}
first=True
for cell in cells:
 if cell['cell_type']=='code':
  exec(compile(''.join(cell['source']),'mats-notebook','exec'),scope)
  if first: os.chdir({str(tmp_path)!r});first=False
assert len(scope['cases'])==4 and scope['replayed']==scope['report']
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert len(list(tmp_path.glob("mats-notebook-runs/*/run.json"))) == 1


@pytest.fixture(scope="module")
def accepted_receipt() -> dict:
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.17.0",
        "origin": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "browser_errors": [],
        "http_failures": [],
        "checks": sorted(evidence.CHECKS),
        "assets": evidence.asset_hashes(),
        "cases": evidence.expected_cases(),
    }


def test_complete_receipt_is_bound_to_release(accepted_receipt: dict) -> None:
    evidence.verify_report(accepted_receipt, "a" * 40, "1.17.0", accepted_receipt["origin"])


@pytest.mark.parametrize(
    "change",
    ["commit", "version", "origin", "schema", "passed", "checks", "assets", "cases", "browser_errors", "http_failures"],
)
def test_incomplete_or_altered_receipt_is_rejected(accepted_receipt: dict, change: str) -> None:
    report = deepcopy(accepted_receipt)
    report[change] = "altered"
    with pytest.raises(ValueError):
        evidence.verify_report(report, "a" * 40, "1.17.0", accepted_receipt["origin"])


def test_import_does_not_initialize_optional_sdks() -> None:
    code = f"""
import sys
sys.path.insert(0,{str(ROOT)!r})
import alpha_factory_v1.demos.meta_agentic_tree_search_v0
import alpha_factory_v1.demos.meta_agentic_tree_search_v0.openai_agents_bridge
assert not {{'agents','openai','anthropic'}}.intersection(sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("failure", ["none", "after", "before"])
def test_sdk_coordinator_binds_parameters_and_never_repeats_completed_search(monkeypatch, failure):
    from types import SimpleNamespace
    from alpha_factory_v1.demos.meta_agentic_tree_search_v0 import openai_agents_bridge as bridge

    calls = []
    clients = []
    configs = []

    class Client:
        def __init__(self, **kwargs):
            assert kwargs == {"timeout": 15.0, "max_retries": 0}
            self.closed = False
            clients.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            self.closed = True

    class Runner:
        @staticmethod
        async def run(agent, prompt, **kwargs):
            assert kwargs["max_turns"] == 3 and kwargs["run_config"].tracing_disabled
            assert agent.model == "account-model" and len(agent.tools) == 1
            if failure == "before":
                raise RuntimeError("coordinator unavailable")
            first = await agent.tools[0]()
            second = await agent.tools[0]()
            assert first == second
            if failure == "after":
                raise RuntimeError("summary unavailable")

    monkeypatch.setitem(
        sys.modules,
        "agents",
        SimpleNamespace(
            Agent=lambda **kwargs: SimpleNamespace(**kwargs),
            Runner=Runner,
            RunConfig=lambda **kwargs: SimpleNamespace(**kwargs),
            function_tool=lambda **kwargs: lambda fn: fn,
            set_tracing_disabled=configs.append,
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "agents.models.openai_provider",
        SimpleNamespace(OpenAIProvider=lambda **kwargs: SimpleNamespace(**kwargs)),
    )
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=Client))
    monkeypatch.setattr(bridge, "run", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setenv("OPENAI_MODEL", "unchanged-parent-setting")
    if failure == "before":
        with pytest.raises(RuntimeError):
            bridge._run_runtime(7, 9, "account-model", "random", [1, 2])
        assert not calls
    else:
        bridge._run_runtime(7, 9, "account-model", "random", [1, 2])
        assert calls == [dict(episodes=7, target=9, model="account-model", rewriter="random", market_data=[1, 2])]
    assert all(client.closed for client in clients) and configs == [True]
    import os

    assert os.environ["OPENAI_MODEL"] == "unchanged-parent-setting"


def test_no_llm_overrides_provider_credentials(monkeypatch):
    import importlib

    meta_rewrite = importlib.import_module("alpha_factory_v1.demos.meta_agentic_tree_search_v0.mats.meta_rewrite")

    monkeypatch.setenv("NO_LLM", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "must-not-be-used")
    monkeypatch.setattr(meta_rewrite.importlib.util, "find_spec", lambda _: pytest.fail("provider was inspected"))
    for rewrite in (meta_rewrite.openai_rewrite, meta_rewrite.anthropic_rewrite):
        assert len(rewrite([1, 2, 3])) == 3


def test_legacy_cli_rejects_invalid_inputs_without_traceback(tmp_path, capsys):
    from alpha_factory_v1.demos.meta_agentic_tree_search_v0 import run_demo

    for args in (["--episodes", "0"], ["--target", "10001"], ["--market-data", str(tmp_path / "missing.csv")]):
        with pytest.raises(SystemExit) as error:
            run_demo.main(args)
        assert error.value.code == 2
        assert "Traceback" not in capsys.readouterr().err
