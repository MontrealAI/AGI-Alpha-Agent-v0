# SPDX-License-Identifier: Apache-2.0
import subprocess
from alpha_factory_v1.scripts import preflight


def test_check_patch_in_sandbox_ok(monkeypatch):
    def fake_run(cmd, capture_output=True, text=True, timeout=None):
        assert timeout == 30
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert preflight.check_patch_in_sandbox("img")


def test_check_patch_in_sandbox_missing(monkeypatch):
    def fake_run(*_a, **_k):
        return subprocess.CompletedProcess([], 1, "", "")

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert not preflight.check_patch_in_sandbox("img")
