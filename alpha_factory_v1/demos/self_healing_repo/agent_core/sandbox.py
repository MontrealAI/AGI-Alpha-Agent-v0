# SPDX-License-Identifier: Apache-2.0
"""Minimal Docker wrapper for sandboxed execution."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from typing import Iterable, Mapping

DEFAULT_IMAGE = os.getenv("SANDBOX_IMAGE", "python:3.11-slim")

_NAME_PART = r"[a-z0-9]+(?:(?:[._]|__|-+)[a-z0-9]+)*"
_HOST_LABEL = r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
_IMAGE_REFERENCE = re.compile(
    rf"(?:(?:{_HOST_LABEL})(?:\.{_HOST_LABEL})*(?::(?P<port>[0-9]{{1,5}}))?/)?"
    rf"{_NAME_PART}(?:/{_NAME_PART})*"
    r"(?::[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})?"
    r"(?:@sha256:[0-9a-f]{64})?"
)


def validate_image_reference(image: str) -> str:
    """Accept named image paths with optional registry port, tag and SHA-256 digest.

    This supported subset excludes option-shaped operands, whitespace/control
    characters, URLs and IPv6 registry literals before Docker is consulted.
    """
    match = _IMAGE_REFERENCE.fullmatch(image) if len(image) <= 512 else None
    if match is None or (match.group("port") is not None and not 1 <= int(match.group("port")) <= 65535):
        raise ValueError("A supported Docker image reference is required")
    return image


def run_in_docker(
    command: Iterable[str],
    repo_dir: str,
    *,
    image: str | None = None,
    mounts: Mapping[str, str] | None = None,
) -> tuple[int, str]:
    """Execute ``command`` inside ``image`` with ``repo_dir`` mounted.

    Additional ``mounts`` map host paths to container paths.
    Returns the exit code and combined stdout+stderr.
    """

    image = validate_image_reference(DEFAULT_IMAGE if image is None else image)
    if not shutil.which("docker"):
        raise RuntimeError("docker is required to run the sandbox")
    mounts = mounts or {}
    cmd = [
        "docker",
        "run",
        "--rm",
        "--network=none",
        "-v",
        f"{repo_dir}:/app",
    ]
    for host, target in mounts.items():
        cmd += ["-v", f"{host}:{target}"]
    cmd += ["-w", "/app", image, *command]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, (result.stdout or "") + (result.stderr or "")
