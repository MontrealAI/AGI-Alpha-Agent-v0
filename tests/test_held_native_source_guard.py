# SPDX-License-Identifier: Apache-2.0
"""Pure temporary-file controls for the static identity guard, not native behavior tests."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/check_held_native_source.py"
GUARD_NAME = "Preserve held native source identities (no behavioral qualification)"


def guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location("owned_static_identity_guard", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(tmp_path: Path) -> dict[str, tuple[int, str]]:
    raw = b"inert owned identity fixture\n"
    (tmp_path / "fixture.txt").write_bytes(raw)
    return {"fixture.txt": (len(raw), hashlib.sha256(raw).hexdigest())}


def test_identity_guard_accepts_only_exact_temporary_bytes(tmp_path: Path) -> None:
    module = guard()
    pins = fixture(tmp_path)
    assert module.check_identities(tmp_path, pins)[0]["matched"] is True
    raw = (tmp_path / "fixture.txt").read_bytes()
    (tmp_path / "fixture.txt").write_bytes(b"I" + raw[1:])
    assert module.check_identities(tmp_path, pins)[0]["matched"] is False


def test_identity_guard_refuses_changed_size_and_missing_target(tmp_path: Path) -> None:
    module = guard()
    pins = fixture(tmp_path)
    (tmp_path / "fixture.txt").write_bytes(b"different length")
    assert module.check_identities(tmp_path, pins)[0]["matched"] is False
    (tmp_path / "fixture.txt").unlink()
    assert module.check_identities(tmp_path, pins)[0]["matched"] is False


def test_identity_guard_refuses_symlink_and_directory_targets(tmp_path: Path) -> None:
    module = guard()
    pins = fixture(tmp_path)
    original = tmp_path / "fixture.txt"
    original.rename(tmp_path / "actual.txt")
    original.symlink_to(tmp_path / "actual.txt")
    assert module.check_identities(tmp_path, pins)[0]["matched"] is False
    original.unlink()
    original.mkdir()
    assert module.check_identities(tmp_path, pins)[0]["matched"] is False


def test_fixed_cli_reports_only_static_identity_and_refuses_selectors() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT)], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "STATIC_SOURCE_IDENTITY_PRESERVED"
    assert report["omittedBehaviorQualified"] is False
    assert len(report["checks"]) == 5 and all(item["matched"] is True for item in report["checks"])
    refused = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", "/unselected"], check=False, capture_output=True, text=True
    )
    assert refused.returncode == 2


@pytest.mark.parametrize(
    ("filename", "job_name", "scope_name", "folder", "budget"),
    [
        (
            "agent-release.yml",
            "regression",
            "Offline regression including notebooks (four held native tests excluded)",
            "evidence",
            90,
        ),
        (
            "successor-capability.yml",
            "capability",
            "Computation, history and delivery gates",
            "capability-evidence",
            25,
        ),
    ],
)
def test_identity_guard_precedes_each_scoped_invocation_without_weakening_it(
    filename: str, job_name: str, scope_name: str, folder: str, budget: int
) -> None:
    workflow = yaml.safe_load((ROOT / ".github/workflows" / filename).read_text())
    job = workflow["jobs"][job_name]
    assert job["timeout-minutes"] == budget
    steps = job["steps"]
    index = next(i for i, step in enumerate(steps) if step.get("name") == scope_name)
    selected = steps[index - 1]
    assert selected == {
        "name": GUARD_NAME,
        "run": f"mkdir -p {folder}\npython scripts/check_held_native_source.py > "
        f"{folder}/held-native-source-preservation.json\n",
    }
    run = steps[index]["run"]
    assert run.count("--deselect=tests/test_successor_capability_delivery.py::") == 4
    assert "EXCLUSION_PLANNED" in run and "'qualified': False" in run
    if filename == "agent-release.yml":
        assert "--cov-fail-under=80" in run
    else:
        assert "--rootdir=." in run
        assert "tests/test_held_native_source_guard.py" in run
