# SPDX-License-Identifier: Apache-2.0
import shutil
import subprocess
import time
from pathlib import Path

import pytest
import requests

def _docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
    except Exception:
        return False
    return True


if not _docker_ready():
    pytest.skip("docker daemon not available", allow_module_level=True)

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "infrastructure" / "docker-compose.yml"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

if not ENV_FILE.exists():
    pytest.skip("dotenv file missing; create .env from .env.sample to run compose tests", allow_module_level=True)


def _wait(url: str, timeout: int = 60) -> bool:
    for _ in range(timeout):
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


@pytest.fixture(scope="module")
def compose_stack() -> None:
    subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d"], check=True)
    try:
        yield
    finally:
        subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "down", "-v"], check=False)


def test_compose_health(compose_stack: None) -> None:
    assert _wait("http://localhost:8000/healthz"), "/healthz endpoint not healthy"
    assert _wait("http://localhost:8000/readiness"), "/readiness endpoint not healthy"
