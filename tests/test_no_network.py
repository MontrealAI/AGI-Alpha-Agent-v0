# SPDX-License-Identifier: Apache-2.0
import os
import shutil
import subprocess
from pathlib import Path

import pytest

if not shutil.which("docker"):
    pytest.skip("docker not available", allow_module_level=True)

try:
    subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
except subprocess.SubprocessError:
    pytest.skip("docker daemon not available", allow_module_level=True)

try:
    subprocess.run(["docker", "compose", "version"], check=True, capture_output=True, text=True)
except subprocess.SubprocessError:
    pytest.skip("docker compose not available", allow_module_level=True)

REPO_ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = REPO_ROOT / "infrastructure" / "docker-compose.yml"
ENV_FILE = REPO_ROOT / ".env"
MIN_DOCKER_DISK_GB = float(os.getenv("MIN_DOCKER_DISK_GB", "8"))


def _ensure_disk_space() -> None:
    usage = shutil.disk_usage(REPO_ROOT)
    free_gb = usage.free / (1024**3)
    if free_gb < MIN_DOCKER_DISK_GB:
        pytest.skip(f"Skipping Docker compose test due to low disk space ({free_gb:.1f} GiB free)")


def _ensure_env_file() -> bool:
    if ENV_FILE.exists():
        return False
    ENV_FILE.write_text("NEO4J_PASSWORD=test\nAPI_TOKEN=test-token\n", encoding="utf-8")
    return True


@pytest.fixture(scope="module")
def compose_stack() -> None:
    _ensure_disk_space()
    created_env = _ensure_env_file()
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "up",
            "-d",
            "agents",
        ],
        check=True,
    )
    try:
        yield
    finally:
        subprocess.run(
            [
                "docker",
                "compose",
                "-f",
                str(COMPOSE_FILE),
                "down",
                "-v",
            ],
            check=False,
        )
        if created_env:
            ENV_FILE.unlink(missing_ok=True)


def test_agents_no_outbound_network(compose_stack: None) -> None:
    result = subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "exec",
            "-T",
            "agents",
            "python",
            "-c",
            "import urllib.request,sys; urllib.request.urlopen('https://example.com')",
        ],
        capture_output=True,
    )
    assert result.returncode != 0
