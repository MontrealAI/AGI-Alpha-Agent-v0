# SPDX-License-Identifier: Apache-2.0
"""Test the alpha business v3 demo shell launcher."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

SCRIPT = Path("alpha_factory_v1/demos/alpha_agi_business_3_v1/run_business_3_demo.sh")


def test_run_business_3_demo_syntax() -> None:
    """Validate shell script syntax with ``bash -n``."""
    subprocess.run(["bash", "-n", str(SCRIPT)], check=True)


def test_run_business_3_demo_help(tmp_path: Path) -> None:
    """--help should exit successfully without a real Docker binary."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "docker.log"
    docker_stub = bin_dir / "docker"
    docker_stub.write_text(f"#!/usr/bin/env bash\necho $@ >> '{log_file}'\nexit 0\n")
    docker_stub.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"

    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert not log_file.exists(), "Help must not build or run a container"
