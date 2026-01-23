# SPDX-License-Identifier: Apache-2.0
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

COMPOSE_FILE = Path(__file__).resolve().parents[1] / "infrastructure" / "docker-compose.yml"


@pytest.fixture(scope="module")
def compose_stack() -> None:
    env_path = COMPOSE_FILE.parents[1] / ".env"
    created_env = False
    if not env_path.exists():
        env_path.write_text("NEO4J_PASSWORD=test\nAPI_TOKEN=test-token\nAGI_INSIGHT_OFFLINE=1\n")
        created_env = True
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
            env_path.unlink(missing_ok=True)


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
