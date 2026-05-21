# SPDX-License-Identifier: Apache-2.0
import contextlib
import os
import shutil
import subprocess
from pathlib import Path

import pytest

BASE_DIR = Path(__file__).resolve().parents[1] / "alpha_factory_v1" / "demos" / "macro_sentinel"
COMPOSE_FILE = BASE_DIR / "docker-compose.macro.yml"
RUN_SCRIPT = BASE_DIR / "run_macro_demo.sh"

if not shutil.which("docker"):
    pytest.skip("docker not available", allow_module_level=True)

compose_check = subprocess.run(
    ["docker", "compose", "version"],
    capture_output=True,
    text=True,
)
if compose_check.returncode != 0:
try:
    subprocess.run(["docker", "info"], check=True, capture_output=True, text=True)
except subprocess.SubprocessError:
    pytest.skip("docker daemon not available", allow_module_level=True)

try:
    subprocess.run(["docker", "compose", "version"], check=True, capture_output=True, text=True)
except subprocess.SubprocessError:
    pytest.skip("docker compose not available", allow_module_level=True)


def test_docker_compose_config() -> None:
    with _ensure_env_file():
        subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "config"], check=True, capture_output=True)


def test_run_macro_demo_help() -> None:
    """`run_macro_demo.sh --help` should exit successfully."""
    subprocess.run([str(RUN_SCRIPT), "--help"], check=True, capture_output=True)


def test_run_macro_demo_offline_not_selected(tmp_path: Path) -> None:
    """An API key in config.env should disable the offline profile."""
    config = RUN_SCRIPT.parent / "config.env"
    docker_log = tmp_path / "docker.log"
    curl_log = tmp_path / "curl.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$DOCKER_LOG"\n'
        'if [ "$1" = "info" ]; then echo "{}"; fi\n'
        'if [ "$1" = "version" ]; then echo "24.0.0"; fi\n'
        "exit 0\n"
    )
    docker_stub.chmod(0o755)

    curl_stub = bin_dir / "curl"
    curl_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$CURL_LOG"\n'
        'out=""\n'
        "for ((i=1;i<=$#;i++)); do\n"
        '  if [ "${!i}" = "-o" ]; then\n'
        "    j=$((i+1))\n"
        "    out=${!j}\n"
        "  fi\n"
        "done\n"
        'if [ -n "$out" ]; then echo sample > "$out"; fi\n'
        "echo OK\n"
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
        }
    )
    env.pop("OPENAI_API_KEY", None)

    config.write_text("OPENAI_API_KEY=test-key\n")
    try:
        result = subprocess.run(
            [f"./{RUN_SCRIPT.name}"], cwd=RUN_SCRIPT.parent, env=env, capture_output=True, text=True
        )
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert "--profile offline" not in log


def test_run_macro_demo_multiple_profiles(tmp_path: Path) -> None:
    """Offline and live profiles should be passed separately."""
    config = RUN_SCRIPT.parent / "config.env"
    docker_log = tmp_path / "docker.log"
    curl_log = tmp_path / "curl.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$DOCKER_LOG"\n'
        'if [ "$1" = "info" ]; then echo "{}"; fi\n'
        'if [ "$1" = "version" ]; then echo "24.0.0"; fi\n'
        "exit 0\n"
    )
    docker_stub.chmod(0o755)

    curl_stub = bin_dir / "curl"
    curl_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$CURL_LOG"\n'
        'out=""\n'
        "for ((i=1;i<=$#;i++)); do\n"
        '  if [ "${!i}" = "-o" ]; then\n'
        "    j=$((i+1))\n"
        "    out=${!j}\n"
        "  fi\n"
        "done\n"
        'if [ -n "$out" ]; then echo sample > "$out"; fi\n'
        "echo OK\n"
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
        }
    )
    env.pop("OPENAI_API_KEY", None)

    try:
        result = subprocess.run(
            [f"./{RUN_SCRIPT.name}", "--live"], cwd=RUN_SCRIPT.parent, env=env, capture_output=True, text=True
        )
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert "--profile offline" in log
    assert "--profile live-feed" in log


def test_compose_base_url_substitution() -> None:
    env = os.environ.copy()
    env["OLLAMA_BASE_URL"] = "http://example.com/v1"
    with _ensure_env_file():
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    assert "http://example.com/v1" in result.stdout


def test_compose_env_substitution() -> None:
    env = os.environ.copy()
    env["REDIS_PASSWORD"] = "secret"
    env["PROMETHEUS_SCRAPE_INTERVAL"] = "30s"
    with _ensure_env_file():
        result = subprocess.run(
            ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )
    assert "secret@redis" in result.stdout
    assert "30s" in result.stdout


@contextlib.contextmanager
def _ensure_env_file():
    config = RUN_SCRIPT.parent / "config.env"
    existed = config.exists()
    if not existed:
        config.write_text("OPENAI_API_KEY=\n")
    try:
        yield
    finally:
        if not existed and config.exists():
            config.unlink()
