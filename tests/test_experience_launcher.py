# SPDX-License-Identifier: Apache-2.0
import os
import re
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(
    not Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh").exists(),
    reason="script missing",
)  # type: ignore[misc]
def test_experience_launcher(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh")
    config = script.parent / "config.env"
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
        'echo "OK"\n'
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SKIP_ENV_CHECK": "1",
            "SAMPLE_DATA_DIR": str(tmp_path / "samples"),
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
        }
    )
    env.pop("OPENAI_API_KEY", None)

    if config.exists():
        config.unlink()
    try:
        result = subprocess.run([f"./{script.name}"], cwd=script.parent, env=env, capture_output=True, text=True)
        created = config.exists()
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert "--profile offline" in log
    assert created


@pytest.mark.skipif(
    not Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh").exists(),
    reason="script missing",
)  # type: ignore[misc]
def test_experience_launcher_live(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh")
    config = script.parent / "config.env"
    docker_log = tmp_path / "docker.log"
    curl_log = tmp_path / "curl.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "LIVE_FEED=$LIVE_FEED" >> "$DOCKER_LOG"\n'
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
        'echo "OK"\n'
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SKIP_ENV_CHECK": "1",
            "SAMPLE_DATA_DIR": str(tmp_path / "samples"),
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
        }
    )
    env.pop("OPENAI_API_KEY", None)

    if config.exists():
        config.unlink()
    try:
        result = subprocess.run(
            [f"./{script.name}", "--live"], cwd=script.parent, env=env, capture_output=True, text=True
        )
        created = config.exists()
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert re.search(r"--profile [^\n]*live-feed", log)
    assert "LIVE_FEED=1" in log
    assert created


@pytest.mark.skipif(
    not Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh").exists(),
    reason="script missing",
)  # type: ignore[misc]
def test_experience_launcher_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh")
    config = script.parent / "config.env"
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
        'echo "OK"\n'
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SKIP_ENV_CHECK": "1",
            "SAMPLE_DATA_DIR": str(tmp_path / "samples"),
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
            "OPENAI_API_KEY": "dummy",
        }
    )

    if config.exists():
        config.unlink()
    try:
        result = subprocess.run([f"./{script.name}"], cwd=script.parent, env=env, capture_output=True, text=True)
        created = config.exists()
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert "--profile offline" not in log
    assert created


@pytest.mark.skipif(
    not Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh").exists(),
    reason="script missing",
)  # type: ignore[misc]
def test_experience_launcher_gpu(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh")
    config = script.parent / "config.env"
    docker_log = tmp_path / "docker.log"
    curl_log = tmp_path / "curl.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$@" >> "$DOCKER_LOG"\n'
        "if [ \"$1\" = \"info\" ]; then echo '{\"nvidia\":{}}'; fi\n"
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
        'echo "OK"\n'
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SKIP_ENV_CHECK": "1",
            "SAMPLE_DATA_DIR": str(tmp_path / "samples"),
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
            "OPENAI_API_KEY": "dummy",
        }
    )

    if config.exists():
        config.unlink()
    try:
        result = subprocess.run([f"./{script.name}"], cwd=script.parent, env=env, capture_output=True, text=True)
        created = config.exists()
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert re.search(r"--profile [^\n]*gpu", log)
    assert created


@pytest.mark.skipif(
    not Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh").exists(),
    reason="script missing",
)  # type: ignore[misc]
def test_experience_launcher_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = Path("alpha_factory_v1/demos/era_of_experience/run_experience_demo.sh")
    config = script.parent / "config.env"
    docker_log = tmp_path / "docker.log"
    curl_log = tmp_path / "curl.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    docker_stub = bin_dir / "docker"
    docker_stub.write_text(
        "#!/usr/bin/env bash\n"
        'echo "STREAM_RATE_HZ=$STREAM_RATE_HZ" >> "$DOCKER_LOG"\n'
        'echo "PORT=$PORT" >> "$DOCKER_LOG"\n'
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
        'echo "OK"\n'
    )
    curl_stub.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{bin_dir}:{env['PATH']}",
            "SKIP_ENV_CHECK": "1",
            "SAMPLE_DATA_DIR": str(tmp_path / "samples"),
            "STREAM_RATE_HZ": "7",
            "DOCKER_LOG": str(docker_log),
            "CURL_LOG": str(curl_log),
        }
    )
    env.pop("OPENAI_API_KEY", None)

    if config.exists():
        config.unlink()
    try:
        result = subprocess.run(
            [f"./{script.name}", "--port", "9999"],
            cwd=script.parent,
            env=env,
            capture_output=True,
            text=True,
        )
        created = config.exists()
    finally:
        if config.exists():
            config.unlink()

    assert result.returncode == 0, result.stderr
    assert docker_log.exists()
    log = docker_log.read_text()
    assert "STREAM_RATE_HZ=7" in log
    assert "PORT=9999" in log
    assert created
