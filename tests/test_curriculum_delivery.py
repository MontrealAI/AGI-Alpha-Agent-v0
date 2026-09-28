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

from alpha_factory_v1.demos.meta_agentic_agi_v3.lab_cli import main
from alpha_factory_v1.demos.meta_agentic_agi_v3.lab_server import Handler, WEB
from scripts import curriculum_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/meta_agentic_agi_v3"


def test_original_research_bytes_are_preserved() -> None:
    expected = {
        "RESEARCH_ARCHIVE.md": "86b8abae201d25abae6016f938262c7531bf583f78082fd66548c7c6dca3eb0c",
        "colab_meta_agentic_agi_v3_original.ipynb": "eb45f36391b0b108383e05fa44abf6b254371b04f164c384bc715a165509e24a",
        "configs/research_original.yml": "7d863f274674e5b55f3b8038ad230e9f4a2f7446887746e5219e0e9552170094",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == digest
    original = (ROOT / "scripts/templates/curriculum-original.html").read_bytes()
    assert hashlib.sha256(original).hexdigest() == "1728f43f04fcb2266e56b8869fd9f01e5b5135c5423b4a07cc30d7598fcdfb43"
    assert (ROOT / "docs/meta_agentic_agi_v3/research.html").read_bytes() == original


def test_packaged_assets_are_current_and_complete() -> None:
    for path in (WEB / "assets").rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (ROOT / "docs" / path.relative_to(WEB)).read_bytes(), path
    page = (WEB / "meta_agentic_agi_v3/index.html").read_text()
    assert 'data-packaged="true"' in page
    assert 'href="research.html"' not in page
    assert 'id="workspace"' in page and 'id="round"' in page
    assert "{{VERSION}}" not in page


def test_server_serves_only_packaged_assets_with_loopback_host() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for path, status in [
            ("/", 200),
            ("/__live", 200),
            ("/assets/curriculum/engine.mjs?v=1.18.0", 200),
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
    assert "coverage-trap" in capsys.readouterr().out
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
    assert "Recomputed every task" in capsys.readouterr().out
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_notebook_executes_all_code_cells_without_network(tmp_path: Path) -> None:
    notebook = str(DEMO / "colab_meta_agentic_agi_v3.ipynb")
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
assert len(scope['cases'])==4 and scope['verify'](scope['report'])==scope['report']
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert len(list(tmp_path.glob("curriculum-runs/*/run.json"))) == 1


@pytest.fixture(scope="module")
def accepted_receipt() -> dict:
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.18.0",
        "origin": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "browser_errors": [],
        "http_failures": [],
        "checks": sorted(evidence.CHECKS),
        "assets": evidence.asset_hashes(),
        "cases": evidence.expected_cases(),
    }


def test_complete_receipt_is_bound_to_release(accepted_receipt: dict) -> None:
    evidence.verify_report(accepted_receipt, "a" * 40, "1.18.0", accepted_receipt["origin"])


@pytest.mark.parametrize(
    "change",
    ["commit", "version", "origin", "schema", "passed", "checks", "assets", "cases", "browser_errors", "http_failures"],
)
def test_incomplete_or_altered_receipt_is_rejected(accepted_receipt: dict, change: str) -> None:
    report = deepcopy(accepted_receipt)
    report[change] = "altered"
    with pytest.raises(ValueError):
        evidence.verify_report(report, "a" * 40, "1.18.0", accepted_receipt["origin"])


def test_import_does_not_initialize_optional_sdks() -> None:
    code = f"""
import sys
sys.path.insert(0,{str(ROOT)!r})
import alpha_factory_v1.demos.meta_agentic_agi_v3
import alpha_factory_v1.demos.meta_agentic_agi_v3.curriculum_lab
assert not {{'agents','openai','anthropic'}}.intersection(sys.modules)
"""
    result = subprocess.run([sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
