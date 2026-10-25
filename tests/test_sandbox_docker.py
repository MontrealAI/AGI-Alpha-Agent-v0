# SPDX-License-Identifier: Apache-2.0
"""Validate sandbox argv boundaries without invoking Docker or generated code."""

from typing import Any

import pytest
import shutil
import subprocess
from alpha_factory_v1.demos.self_healing_repo.agent_core import sandbox


def test_run_in_docker_requires_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(RuntimeError, match="docker is required"):
        sandbox.run_in_docker(["echo", "hi"], repo_dir="/tmp")


@pytest.mark.parametrize(
    "image",
    [
        "",
        "--privileged",
        "--network=host",
        "-v/host:/host",
        "python:3.11 --privileged",
        "python:3.11\n--privileged",
        "python:3.11\t",
        "python:3.11\x00",
        " python:3.11",
        "python:3.11\u00a0",
        "https://registry.example/image",
        "../image",
        "Team/image",
        "repo:",
        "repo@sha256:bad",
        "registry.example:0/image",
        "registry.example:65536/image",
    ],
)
def test_invalid_image_is_refused_before_availability_or_dispatch(image: str, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Invalid image reached Docker availability or subprocess dispatch")

    monkeypatch.setattr(shutil, "which", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="image reference"):
        sandbox.run_in_docker(["pytest", "-q"], repo_dir="/tmp", image=image)


def test_environment_default_is_validated_before_dispatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sandbox, "DEFAULT_IMAGE", "--privileged")

    def forbidden(*args: Any, **kwargs: Any) -> None:
        pytest.fail("Invalid configured image reached dispatch")

    monkeypatch.setattr(shutil, "which", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    with pytest.raises(ValueError, match="image reference"):
        sandbox.run_in_docker(["pytest", "-q"], repo_dir="/tmp")


@pytest.mark.parametrize(
    "image",
    [
        "python:3.11-slim",
        "ubuntu",
        "library/python",
        "ghcr.io/montrealai/worker:rc.1",
        "localhost:5000/team/my__image:V1",
        "registry.example:65535/a-b.c_d@sha256:" + "a" * 64,
        "team/image:tag@sha256:" + "f" * 64,
    ],
)
def test_valid_image_preserves_one_operand_and_existing_controls(image: str, monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/docker")

    def capture(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append(argv)
        assert kwargs == {"capture_output": True, "text": True}
        return subprocess.CompletedProcess(argv, 3, stdout="captured stdout", stderr="captured stderr")

    monkeypatch.setattr(subprocess, "run", capture)
    result = sandbox.run_in_docker(
        ["pytest", "-q", "literal;not-a-shell"],
        repo_dir="/tmp/repo",
        image=image,
        mounts={"/tmp/input": "/input"},
    )
    assert captured == [
        [
            "docker",
            "run",
            "--rm",
            "--network=none",
            "-v",
            "/tmp/repo:/app",
            "-v",
            "/tmp/input:/input",
            "-w",
            "/app",
            image,
            "pytest",
            "-q",
            "literal;not-a-shell",
        ]
    ]
    assert result == (3, "captured stdoutcaptured stderr")
