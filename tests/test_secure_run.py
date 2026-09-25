# SPDX-License-Identifier: Apache-2.0
import subprocess
import shutil
import json
import os
import sys
import pytest

from alpha_factory_v1.core.utils.secure_run import secure_run, SandboxTimeout


def test_secure_run_timeout(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda n: "/usr/bin/docker" if n == "docker" else None)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=120)

    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", fake_run)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0))

    with pytest.raises(SandboxTimeout):
        secure_run(["sleep", "130"])


def test_secure_run_refuses_host_fallback(monkeypatch) -> None:
    from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

    monkeypatch.setattr(shutil, "which", lambda n: None)
    with pytest.raises(SandboxUnavailable):
        secure_run(["python", "-c", "print('must not execute')"])


@pytest.mark.parametrize("failure", ["stopped", "timeout", "missing"])
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
        assert command == ["/usr/bin/docker", "info"] and kwargs["timeout"] == 5
        if failure == "timeout":
            raise subprocess.TimeoutExpired(command, 5)
        if failure == "missing":
            raise FileNotFoundError("Docker disappeared")
        return subprocess.CompletedProcess(command, 1)

    def execute(command, timeout, *, env):
        executions.append(command)
        assert command[0] == "/usr/bin/firejail"
        assert "--net=none" in command and "--nonewprivs" in command
        assert Path(command[-1]).read_text() == candidate.read_text()
        assert Path(command[-1]) != candidate
        assert env == {"PATH": os.defpath, "LANG": "C.UTF-8", "HOME": str(Path(command[-1]).parent)}
        return subprocess.CompletedProcess(command, 0, "42\n", "")

    monkeypatch.setattr(subprocess, "run", probe)
    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", execute)
    if firejail_available:
        assert secure_run(["python", str(candidate)]).stdout == "42\n"
        assert len(executions) == 1
    else:
        with pytest.raises(SandboxUnavailable):
            secure_run(["python", str(candidate)])
        assert not executions


def test_candidate_failure_is_never_retried_in_another_backend(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 0))
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
