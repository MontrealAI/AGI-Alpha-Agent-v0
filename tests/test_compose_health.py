# SPDX-License-Identifier: Apache-2.0
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from tests.utils.docker import docker_compose_available, docker_daemon_available

if not docker_compose_available() or not docker_daemon_available():
    pytest.skip("docker compose/daemon not available", allow_module_level=True)

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "infrastructure" / "docker-compose.yml"
ENV_FILE = Path(__file__).resolve().parents[1] / ".env"

if not ENV_FILE.exists():
    pytest.skip("dotenv file missing; create .env from .env.sample to run compose tests", allow_module_level=True)


def _wait(url: str, timeout: int = 60) -> bool:
    for _ in range(timeout):
        try:
            request = Request(url, headers={"User-Agent": "alpha-factory-tests/1.0"})
            with urlopen(request, timeout=2) as response:
                if response.status == 200:
                    return True
        except (HTTPError, URLError, TimeoutError):
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
