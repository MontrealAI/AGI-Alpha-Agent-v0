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
from types import MappingProxyType

import pytest

from alpha_factory_v1.demos.era_of_experience.lab_cli import main
from alpha_factory_v1.demos.era_of_experience.lab_server import Handler, WEB
from scripts import experience_evidence as evidence

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "alpha_factory_v1/demos/era_of_experience"


def test_original_research_bytes_are_preserved() -> None:
    expected = {
        "RESEARCH_ARCHIVE.md": "c5ba20156a56270c49a0c1f9dfad6499949f845ede7c49fbde610160473fc4e8",
        "research_notebook_archive.ipynb": "e9147fdb5bb04e89b5a4ffc5db104fe24cf5254883b20b2d93f00e2c47324aa0",
        "legacy_run_experience_demo.sh": "02222c585e4ce9cc5c0b572422ff679e32f68bd0f532305ab3d8efff6efbfa83",
        "research_config.env.sample": "57f08e0917b7069c49a4bf53833bcd34d4f39e9a5d3b6333cc1aad39b5fffea7",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((DEMO / name).read_bytes()).hexdigest() == digest
    original = (ROOT / "scripts/templates/experience-original.html").read_bytes()
    assert hashlib.sha256(original).hexdigest() == "855deb463f0dfcdaab4914d2438bf9a238baa257af393ad711d3d093eeed22c4"
    assert (ROOT / "docs/era_of_experience/research.html").read_bytes() == original


def test_packaged_assets_are_current_and_complete() -> None:
    for path in (WEB / "assets").rglob("*"):
        if path.is_file():
            assert path.read_bytes() == (ROOT / "docs" / path.relative_to(WEB)).read_bytes(), path
    page = (WEB / "era_of_experience/index.html").read_text()
    assert 'data-packaged="true"' in page
    assert 'href="research.html"' not in page
    assert 'id="workspace"' in page and 'id="performance"' in page
    assert "{{VERSION}}" not in page


def test_server_serves_only_packaged_assets_with_loopback_host() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=server.serve_forever, daemon=True).start()
    try:
        connection = HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for path, status in [
            ("/", 200),
            ("/__live", 200),
            ("/assets/experience/engine.mjs?v=1.16.0", 200),
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
    assert "reward-trap" in capsys.readouterr().out
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
    assert "Recomputed every episode" in capsys.readouterr().out
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}


def test_notebook_executes_all_code_cells_without_network(tmp_path: Path) -> None:
    notebook = str(DEMO / "colab_era_of_experience.ipynb")
    code = f"""
import json,os,pathlib,sys
sys.path.insert(0,{str(ROOT)!r})
cells=json.loads(pathlib.Path({notebook!r}).read_text())['cells']
scope={{}}
first=True
for cell in cells:
 if cell['cell_type']=='code':
  exec(compile(''.join(cell['source']),'experience-notebook','exec'),scope)
  if first: os.chdir({str(tmp_path)!r});first=False
assert len(scope['folders'])==4
"""
    result = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, result.stderr
    assert len(list(tmp_path.glob("experience-notebook-runs/*/run.json"))) == 5


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, 1.1])
def test_legacy_reward_boundary_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch, value: float) -> None:
    from alpha_factory_v1.demos.era_of_experience import reward_backends

    monkeypatch.setattr(reward_backends, "_FROZEN", MappingProxyType({"bad": lambda s, a, r: value}))
    with pytest.raises(RuntimeError):
        reward_backends.reward_signal("bad", {}, None, {})
    with pytest.raises(ValueError):
        reward_backends.blend({"bad": value})
    with pytest.raises(ValueError):
        reward_backends.blend({"a": 0.5}, {"a": float("inf")})


@pytest.fixture(scope="module")
def accepted_receipt() -> dict:
    return {
        "schema": evidence.SCHEMA,
        "passed": True,
        "commit": "a" * 40,
        "version": "1.16.0",
        "origin": "https://montrealai.github.io/AGI-Alpha-Agent-v0/",
        "browser_errors": [],
        "http_failures": [],
        "checks": sorted(evidence.CHECKS),
        "assets": evidence.asset_hashes(),
        "cases": evidence.expected_cases(),
    }


def test_complete_receipt_is_bound_to_release(accepted_receipt: dict) -> None:
    evidence.verify_report(accepted_receipt, "a" * 40, "1.16.0", accepted_receipt["origin"])


@pytest.mark.parametrize(
    "change",
    ["commit", "version", "origin", "schema", "passed", "checks", "assets", "cases", "browser_errors", "http_failures"],
)
def test_incomplete_or_altered_receipt_is_rejected(accepted_receipt: dict, change: str) -> None:
    report = deepcopy(accepted_receipt)
    report[change] = "altered"
    with pytest.raises(ValueError):
        evidence.verify_report(report, "a" * 40, "1.16.0", accepted_receipt["origin"])
