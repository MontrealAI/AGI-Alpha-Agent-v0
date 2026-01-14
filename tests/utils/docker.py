# SPDX-License-Identifier: Apache-2.0
"""Helpers for docker-dependent tests."""
from __future__ import annotations

import shutil
import subprocess


def docker_daemon_available() -> bool:
    """Return True when the Docker CLI and daemon are reachable."""
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(
            ["docker", "info"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True


def docker_compose_available() -> bool:
    """Return True when docker compose is available."""
    if not shutil.which("docker"):
        return False
    try:
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    return True
