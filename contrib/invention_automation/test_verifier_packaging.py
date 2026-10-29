# SPDX-License-Identifier: Apache-2.0
"""Installed verifier boundaries and source binding, without candidate execution."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.invention_automation import critic_loop, specification_run
from alpha_factory_v1.core.runtime.invention_verification import critic_verify
from contrib.invention_automation.test_critic_verify import freeze_fixture

ROOT = Path(__file__).resolve().parents[2]
NAMESPACE = "alpha_factory_v1/core/runtime/invention_verification/"


def test_verifier_import_does_not_import_candidate_or_contrib() -> None:
    code = (
        "import importlib,json,sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "names=['critic_verify','qualify_verify','readonly','dynamic_oracle'];"
        "mods=[importlib.import_module('alpha_factory_v1.core.runtime.invention_verification.'+name) for name in names];"
        "assert not any(name.startswith(('contrib','alpha_factory_v1.core.runtime.invention_automation')) for name in sys.modules);"
        "print(json.dumps({'verifiers':[module.__name__ for module in mods],'candidate_imported':False}))"
    )
    result = subprocess.run([sys.executable, "-I", "-c", code, str(ROOT)], capture_output=True, text=True, check=True)
    assert json.loads(result.stdout)["candidate_imported"] is False


def test_compatibility_forwards_preserve_critic_api_without_defining_truth_gate() -> None:
    from contrib.invention_automation import critic_verify as compatibility

    assert compatibility.adjudicate is critic_verify.adjudicate
    assert compatibility.field_literal is critic_verify.field_literal
    assert critic_verify.adjudicate.__module__ == "alpha_factory_v1.core.runtime.invention_verification.critic_verify"


def test_source_identity_includes_actual_verifier_helpers_and_readonly_code() -> None:
    names = specification_run.source_hashes()
    assert {
        NAMESPACE + name
        for name in ["__init__.py", "critic_verify.py", "qualify_verify.py", "readonly.py", "dynamic_oracle.py"]
    } <= set(names)
    assert not any(name.startswith("contrib/") for name in names)


def test_missing_installed_verifier_fails_before_subprocess(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(critic_loop, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="installed verifier unavailable"):
        critic_loop.verify_role(tmp_path / "request.json", tmp_path / "context.json", tmp_path / "freeze.json")


def test_verifier_launch_excludes_site_and_working_directory_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert command[1:4] == ["-B", "-P", "-S"]
        assert command[4:6] == ["-m", "alpha_factory_v1.core.runtime.invention_verification.critic_verify"]
        assert isinstance(kwargs["env"], dict) and kwargs["env"]["PYTHONPATH"] == str(ROOT)
        receipt = {"freeze_verified": True, "candidate_write_denied_by_os": True, "new_socket_denied_by_os": True}
        return subprocess.CompletedProcess(command, 0, json.dumps(receipt), "")

    monkeypatch.setattr(subprocess, "run", run)
    critic_loop.verify_role(ROOT / "request.json", ROOT / "context.json", ROOT / "freeze.json")


@pytest.mark.parametrize("missing", ["__init__.py", "critic_verify.py", "qualify_verify.py", "readonly.py"])
def test_wrapper_pins_cannot_replace_missing_installed_verifier_code(tmp_path: Path, missing: str) -> None:
    request, context, _, _, freeze = freeze_fixture(tmp_path)
    value = json.loads(request.read_text())
    ctx = json.loads(context.read_text())
    del freeze["files"][NAMESPACE + missing]
    freeze["files"]["contrib/invention_automation/critic_verify.py"] = "0" * 64
    with pytest.raises(ValueError, match="source pins required"):
        critic_verify.verify_freeze(ROOT, freeze, value, ctx)
