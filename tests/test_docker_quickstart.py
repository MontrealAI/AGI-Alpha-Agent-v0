# SPDX-License-Identifier: Apache-2.0
"""Exercise the public Docker launcher from paths with spaces without starting services."""

from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout(tmp_path: Path):
    if os.name == "nt" or not shutil.which("bash"):
        pytest.skip("Bash launcher requires a POSIX host")
    root = tmp_path / "source checkout"
    (root / "docs").mkdir(parents=True)
    (root / "alpha_factory_v1").mkdir()
    shutil.copy2(ROOT / "run_quickstart.sh", root)
    (root / "docs/DISCLAIMER_SNIPPET.md").write_text("Project notice\n")
    (root / "alpha_factory_v1/.env.sample").write_text("API_TOKEN=REPLACE_ME_TOKEN\nNEO4J_PASSWORD=REPLACE_ME\n")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    log = tmp_path / "calls.jsonl"
    docker = binaries / "docker"
    docker.write_text(
        f"#!{sys.executable}\nimport os,sys,json\n"
        "with open(os.environ['QUICKSTART_TEST_LOG'],'a') as f:\n"
        " f.write(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:]})+'\\n')\n"
    )
    docker.chmod(0o755)
    env = {**os.environ, "PATH": str(binaries) + os.pathsep + os.environ["PATH"], "QUICKSTART_TEST_LOG": str(log)}
    return root, env, log


def launch(checkout, *args: str):
    root, env, _ = checkout
    return subprocess.run(
        ["bash", str(root / "run_quickstart.sh"), *args],
        cwd=root.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_first_launch_creates_private_configuration_and_stops(checkout) -> None:
    root, _, log = checkout
    result = launch(checkout)
    assert result.returncode == 1 and "Set API_TOKEN" in result.stderr
    assert (root / ".env").stat().st_mode & 0o777 == 0o600
    assert [json.loads(line)["args"] for line in log.read_text().splitlines()] == [["info"]]


def test_build_only_uses_repository_context_and_never_launches(checkout) -> None:
    root, _, log = checkout
    result = launch(checkout, "--build-only")
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    assert calls[-1] == {
        "cwd": str(root),
        "args": ["build", "-f", "docker/quickstart/Dockerfile", "-t", "alpha-factory-quickstart", "."],
    }
    assert not (root / ".env").exists()


def test_existing_configuration_is_preserved_and_api_is_loopback_only(checkout) -> None:
    root, _, log = checkout
    original = b"API_TOKEN=fixture-secret\nNEO4J_PASSWORD=fixture-secret\n"
    (root / ".env").write_bytes(original)
    result = launch(checkout)
    assert result.returncode == 0, result.stderr
    command = json.loads(log.read_text().splitlines()[-1])["args"]
    assert command[:3] == ["run", "--rm", "--init"]
    assert command[command.index("--env-file") + 1] == str(root / ".env")
    assert "127.0.0.1:8000:8000" in command
    assert "type=volume,source=alpha-factory-quickstart-data,target=/data" in command
    assert (root / ".env").read_bytes() == original
    assert "fixture-secret" not in result.stdout + result.stderr


@pytest.mark.parametrize("argument,code", [("--help", 0), ("--unknown", 2)])
def test_help_and_invalid_arguments_never_contact_docker(checkout, argument, code) -> None:
    root, _, log = checkout
    assert launch(checkout, argument).returncode == code
    assert not log.exists() and not (root / ".env").exists()


def test_container_normalizes_sample_comments_without_expanding_credentials(monkeypatch) -> None:
    module = runpy.run_path(str(ROOT / "docker/quickstart/start.py"))
    monkeypatch.setenv("API_TOKEN", "'local-token' # explanatory comment")
    monkeypatch.setenv("NEO4J_PASSWORD", "'${PRIVATE_VALUE}'")
    monkeypatch.setenv("PRIVATE_VALUE", "must-not-expand")
    monkeypatch.setenv("PORT", "9999 # old port")
    monkeypatch.setenv("AF_MEMORY_DIR", "/tmp/temporary # old memory")
    module["configure"](str(ROOT / "alpha_factory_v1/.env.sample"))
    assert os.environ["API_TOKEN"] == "local-token"
    assert os.environ["NEO4J_PASSWORD"] == "${PRIVATE_VALUE}"
    assert os.environ["PORT"] == "8000"
    assert os.environ["AF_MEMORY_DIR"] == "/data/memory"


@pytest.mark.parametrize("value", ["", "REPLACE_ME", "REPLACE_ME_TOKEN # sample"])
def test_container_rejects_unconfigured_secrets_before_importing_services(monkeypatch, value) -> None:
    module = runpy.run_path(str(ROOT / "docker/quickstart/start.py"))
    monkeypatch.setenv("API_TOKEN", value)
    with pytest.raises(SystemExit, match="Configure API_TOKEN"):
        module["configure"](str(ROOT / "alpha_factory_v1/.env.sample"))
