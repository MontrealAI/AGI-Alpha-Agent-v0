# SPDX-License-Identifier: Apache-2.0
import subprocess
import shutil
import pytest

from alpha_factory_v1.core.utils.secure_run import secure_run, SandboxTimeout


def test_secure_run_timeout(monkeypatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda n: "/usr/bin/docker" if n == "docker" else None)

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=120)

    monkeypatch.setattr("alpha_factory_v1.core.utils.secure_run._bounded_run", fake_run)
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)

    with pytest.raises(SandboxTimeout):
        secure_run(["sleep", "130"])


def test_secure_run_refuses_host_fallback(monkeypatch) -> None:
    from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

    monkeypatch.setattr(shutil, "which", lambda n: None)
    with pytest.raises(SandboxUnavailable):
        secure_run(["python", "-c", "print('must not execute')"])
