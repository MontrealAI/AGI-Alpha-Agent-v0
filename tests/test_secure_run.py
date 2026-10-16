# SPDX-License-Identifier: Apache-2.0
import json
import os
import shutil
import subprocess
import sys

import pytest

from alpha_factory_v1.core.utils.secure_run import SandboxTimeout, secure_run


def test_secure_run_timeout(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda n: "/usr/bin/docker" if n == "docker" else None)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=120)

    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", fake_run)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, b"28.0.4\n"))

    with pytest.raises(SandboxTimeout):
        secure_run(["sleep", "130"])


@pytest.mark.parametrize("firejail", [None, "/usr/bin/firejail"])
def test_secure_run_refuses_host_fallback(monkeypatch, firejail) -> None:
    from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

    monkeypatch.setattr(shutil, "which", lambda name: firejail if name == "firejail" else None)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *args, **kwargs: pytest.fail("untrusted code reached host execution")
    )
    with pytest.raises(SandboxUnavailable):
        secure_run(["python", "-c", "print('must not execute')"])


@pytest.mark.parametrize(
    "failure",
    [
        "stopped",
        "timeout",
        "missing",
        "empty",
        "whitespace",
        "no-server",
        "client-only",
        "malformed",
        "extra-output",
        "extra-newline",
        "non-ascii",
        "too-long",
    ],
)
@pytest.mark.parametrize("firejail_available", [True, False])
def test_unusable_docker_is_checked_before_candidate_execution(monkeypatch, tmp_path, failure, firejail_available):
    from pathlib import Path

    from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: f"/usr/bin/{name}" if name == "docker" or firejail_available else None,
    )
    executions = []
    candidate = tmp_path / "candidate.py"
    candidate.write_text("print(42)\n")

    def probe(command, **kwargs):
        assert command == ["/usr/bin/docker", "version", "--format", "{{.Server.Version}}"]
        assert kwargs == {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.DEVNULL,
            "timeout": 5,
            "check": False,
        }
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 5)
        if failure == "missing":
            raise FileNotFoundError("Docker disappeared")
        if failure == "stopped":
            return subprocess.CompletedProcess(command, 1, b"28.0.4\n")
        output = {
            "empty": b"",
            "whitespace": b" \n",
            "no-server": b"<no value>\n",
            "client-only": b"Client: Docker Engine - Community\n Version: 28.0.4\n",
            "malformed": b"28.0.4+\n",
            "extra-output": b"28.0.4\nunexpected output\n",
            "extra-newline": b"28.0.4\n\n",
            "non-ascii": b"28.0.4-\xff\n",
            "too-long": b"28.0.4-" + b"a" * 128,
        }
        return subprocess.CompletedProcess(command, 0, output[failure])

    def execute(command, timeout, *, env):
        executions.append(command)
        assert command[0] == "/usr/bin/firejail"
        assert "--net=none" in command and "--nonewprivs" in command
        assert Path(command[-1]).read_text() == candidate.read_text()
        assert Path(command[-1]) != candidate
        assert env == {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": str(Path(command[-1]).parent)}
        return subprocess.CompletedProcess(command, 0, "42\n", "")

    monkeypatch.setattr(subprocess, "run", probe)
    monkeypatch.setattr(
        subprocess, "Popen", lambda *args, **kwargs: pytest.fail("untrusted code reached host execution")
    )
    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", execute)
    with pytest.raises(SandboxUnavailable):
        secure_run(["python", str(candidate)])
    assert not executions  # A present Firejail must never authorize untrusted code.
    if firejail_available:
        assert secure_run(["python", str(candidate)], allow_trusted_firejail=True).stdout == "42\n"
        assert len(executions) == 1
    else:
        with pytest.raises(SandboxUnavailable):
            secure_run(["python", str(candidate)], allow_trusted_firejail=True)
        assert not executions


@pytest.mark.parametrize(
    "version",
    [b"28.0.4\n", b"28.0.4\r\n", b"28.0.4", b"26.1.3+dfsg1-2\n", b"29.0.0-rc.1\n", b"28.2.2-0ubuntu1~24.04.1\n"],
)
def test_healthy_server_probe_preserves_docker_constraints(monkeypatch, tmp_path, version):
    from pathlib import Path

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.delenv("ALPHA_SANDBOX_IMAGE", raising=False)
    candidate = tmp_path / "candidate.py"
    candidate.write_text("print(42)\n")
    probes = []
    executions = []

    def probe(command, **kwargs):
        probes.append(command)
        if len(probes) == 1:
            assert command == ["/usr/bin/docker", "version", "--format", "{{.Server.Version}}"]
            assert kwargs == {
                "stdout": subprocess.PIPE,
                "stderr": subprocess.DEVNULL,
                "timeout": 5,
                "check": False,
            }
            return subprocess.CompletedProcess(command, 0, version)
        assert command == ["/usr/bin/docker", "rm", "-f", executions[0][4]]
        assert kwargs == {"capture_output": True, "timeout": 10, "check": False}
        return subprocess.CompletedProcess(command, 0)

    def execute(command, timeout, *, env):
        executions.append(command)
        assert timeout == 120 and env is None
        assert command[:4] == ["/usr/bin/docker", "run", "--rm", "--name"]
        assert command[5:15] == [
            "--network=none",
            "--cpus=2",
            "--memory=2g",
            "--pids-limit=64",
            "--read-only",
            "--cap-drop=ALL",
            "--user=65534:65534",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
            "--security-opt=no-new-privileges",
            "--mount",
        ]
        mount = command[15]
        assert mount.startswith("type=bind,src=") and mount.endswith(",dst=/work,readonly")
        stage = Path(mount.removeprefix("type=bind,src=").removesuffix(",dst=/work,readonly"))
        assert command[4] == stage.name
        assert stage != candidate.parent and list(stage.iterdir()) == [stage / "input-0"]
        assert (stage / "input-0").read_text() == candidate.read_text()
        assert (stage / "input-0").stat().st_mode & 0o777 == 0o444
        assert command[16:] == ["--workdir=/work", "python:3.12-slim", "python3", "/work/input-0"]
        return subprocess.CompletedProcess(command, 0, "42\n", "")

    monkeypatch.setattr(subprocess, "run", probe)
    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", execute)
    assert secure_run(["python", str(candidate)]).stdout == "42\n"
    assert len(executions) == 1 and len(probes) == 2


def test_candidate_failure_is_never_retried_in_another_backend(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0, b"28.0.4\n")
    )
    executions = []

    def execute(command, timeout, *, env):
        executions.append(command)
        assert env is None  # Docker client settings do not enter the container.
        return subprocess.CompletedProcess(command, 1, "", "candidate failed")

    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", execute)
    assert secure_run(["python", "-c", "raise ValueError('candidate failed')"]).returncode == 1
    assert len(executions) == 1 and executions[0][0] == "/usr/bin/docker"


def test_bounded_child_does_not_inherit_service_credentials(monkeypatch, tmp_path):
    from alpha_factory_v1.core.utils.secure_run import _bounded_run

    sensitive = ("OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "API_TOKEN", "PYTHONPATH", "PYTHONSTARTUP")
    for name in sensitive:
        monkeypatch.setenv(name, "synthetic-test-sentinel")
    environment = {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": str(tmp_path)}
    # This fixed, trusted test program observes the actual child environment;
    # no model-generated code or service credentials enter this test.
    result = _bounded_run(
        [sys.executable, "-c", "import json, os; print(json.dumps(dict(os.environ)))"],
        5,
        env=environment,
    )
    child = json.loads(result.stdout)
    assert result.returncode == 0
    assert all(name not in child for name in sensitive)
    assert all(child[name] == value for name, value in environment.items())
