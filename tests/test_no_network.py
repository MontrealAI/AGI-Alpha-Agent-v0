# SPDX-License-Identifier: Apache-2.0
import subprocess
from pathlib import Path

import pytest

from tests.utils.docker import docker_compose_available, docker_daemon_available

if not docker_compose_available() or not docker_daemon_available():
    pytest.skip("docker compose/daemon not available", allow_module_level=True)

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "infrastructure" / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose_stack() -> None:
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
