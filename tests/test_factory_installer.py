# SPDX-License-Identifier: Apache-2.0
"""Exercise shell launch wiring without building or deploying real services."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def checkout(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    if not shutil.which("bash") or os.name == "nt":
        pytest.skip("Bash fixture requires a POSIX host")
    repo = tmp_path / "factory source"
    scripts = repo / "alpha_factory_v1/scripts"
    scripts.mkdir(parents=True)
    for name in ("install_alpha_factory_pro.sh",):
        shutil.copy2(ROOT / "alpha_factory_v1/scripts" / name, scripts / name)
    (repo / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    (repo / "alpha_factory_v1/Dockerfile").write_text("FROM fixture\n")
    (repo / "alpha_factory_v1/.env.sample").write_text("API_TOKEN=REPLACE_ME_TOKEN\nNEO4J_PASSWORD=REPLACE_ME\n")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    log = tmp_path / "calls.jsonl"
    docker = binaries / "docker"
    docker.write_text(
        f"#!{sys.executable}\nimport json,os,sys\n"
        "with open(os.environ['FACTORY_TEST_LOG'],'a') as f:\n"
        " f.write(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:]})+'\\n')\n"
        "if sys.argv[1:3]==['compose','version']: print('2.39.0')\n"
    )
    docker.chmod(0o755)
    environment = {
        **os.environ,
        "PATH": str(binaries) + os.pathsep + os.environ["PATH"],
        "FACTORY_TEST_LOG": str(log),
        "PYTHONPATH": str(ROOT),
    }
    return repo, environment, log


def launch(checkout: tuple[Path, dict[str, str], Path], *args: str) -> subprocess.CompletedProcess[str]:
    repo, environment, _ = checkout
    return subprocess.run(
        ["bash", str(repo / "alpha_factory_v1/scripts/install_alpha_factory_pro.sh"), *args],
        cwd=repo.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_build_uses_complete_repo_real_argument_and_never_deploys(checkout: tuple[Path, dict[str, str], Path]) -> None:
    repo, _, log = checkout
    result = launch(checkout, "--no-ui", "--no-cache", "--tests")
    assert result.returncode == 0, result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    build = next(call for call in calls if call["args"][0] == "build")
    assert build["cwd"] == str(repo)
    assert build["args"][-1] == "." and "alpha_factory_v1/Dockerfile" in build["args"]
    assert "INSTALL_UI=0" in build["args"] and "--no-cache" in build["args"]
    assert all("compose" not in call["args"] and "pull" not in call["args"] for call in calls)
    assert not (repo / "alpha_factory_v1/.env").exists()


def test_first_deploy_creates_private_template_then_stops_without_a_build(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    repo, _, log = checkout
    result = launch(checkout, "--deploy")
    assert result.returncode == 1 and "Configure API_TOKEN" in result.stderr
    env_file = repo / "alpha_factory_v1/.env"
    assert env_file.read_bytes() == (repo / "alpha_factory_v1/.env.sample").read_bytes()
    assert env_file.stat().st_mode & 0o777 == 0o600
    calls = [json.loads(line)["args"] for line in log.read_text().splitlines()]
    assert calls == [["info"], ["compose", "version"]]


def test_unimplemented_strategy_fails_before_any_mutation(checkout: tuple[Path, dict[str, str], Path]) -> None:
    repo, _, log = checkout
    result = launch(checkout, "--alpha", "btc_gld", "--deploy")
    assert result.returncode == 2 and "no configurable strategy registry" in result.stderr
    assert not log.exists() and not (repo / "alpha_factory_v1/.env").exists()


def test_existing_config_is_preserved_and_missing_secrets_do_not_deploy(
    checkout: tuple[Path, dict[str, str], Path],
) -> None:
    repo, environment, log = checkout
    environment.pop("API_TOKEN", None)
    environment.pop("NEO4J_PASSWORD", None)
    env_file = repo / "alpha_factory_v1/.env"
    original = b"API_TOKEN=REPLACE_ME_TOKEN\nNEO4J_PASSWORD=REPLACE_ME\n# preserve my notes\n"
    env_file.write_bytes(original)
    result = launch(checkout, "--deploy")
    assert result.returncode != 0
    assert env_file.read_bytes() == original
    assert all("up" not in json.loads(line)["args"] for line in log.read_text().splitlines())
