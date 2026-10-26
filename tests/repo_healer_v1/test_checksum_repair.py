# SPDX-License-Identifier: Apache-2.0
"""Checksum repair regression tests; historical versions share one defect pattern."""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.candidate_generation import generate_candidates
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.checksum_repair import transform_checksum_write_order
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine import RepoHealerEngine
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, ValidatorClass
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.workspace import WorkspaceError

FIXTURES = pathlib.Path(__file__).parent / "fixtures" / "checksum"


def bundle() -> FailureBundle:
    return FailureBundle(
        "integrity", "pytest", "validation", "local", "historical",
        candidate_files=["scripts/fetch_assets.py"],
        validator_class=ValidatorClass.PYTEST,
        logs="AssertionError: checksum mismatch must preserve destination bytes",
        reproduction_command=[sys.executable, "-m", "pytest", "tests/test_integrity.py", "-q"],
    )


def workspace(tmp_path: pathlib.Path, revision: str) -> pathlib.Path:
    root = tmp_path / "repo"
    (root / "scripts").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "scripts/fetch_assets.py").write_bytes((FIXTURES / f"{revision}.txt").read_bytes())
    (root / "tests/test_integrity.py").write_bytes((FIXTURES / "behavior_tests.txt").read_bytes())
    return root


@pytest.mark.parametrize("revision", ["b207647f", "762e6a43"])
def test_checksum_repair_runs_complete_engine_and_preserves_downloads(tmp_path: pathlib.Path, revision: str) -> None:
    root = workspace(tmp_path, revision)
    initial = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, capture_output=True)
    assert initial.returncode == 1
    before = (root / "scripts/fetch_assets.py").read_bytes()
    candidates = generate_candidates(root, bundle())
    assert len(candidates) == 1
    assert (root / "scripts/fetch_assets.py").read_bytes() == before
    report = RepoHealerEngine(root).run(bundle(), candidates)
    assert report.success
    assert report.reason == "targeted and broader validators passed"
    assert len(report.validator_commands) == 2
    final = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=root, capture_output=True)
    assert final.returncode == 0, final.stdout + final.stderr
    assert generate_candidates(root, bundle()) == []


def test_checksum_repair_never_skips_failing_broader_validation(tmp_path: pathlib.Path) -> None:
    root = workspace(tmp_path, "b207647f")
    (root / "tests/test_other.py").write_text("def test_other():\n    assert False\n")
    before = (root / "scripts/fetch_assets.py").read_bytes()
    report = RepoHealerEngine(root).run(bundle(), generate_candidates(root, bundle()))
    assert not report.success
    assert (root / "scripts/fetch_assets.py").read_bytes() == before


def test_checksum_repair_requires_checksum_evidence(tmp_path: pathlib.Path) -> None:
    root = workspace(tmp_path, "b207647f")
    request = bundle()
    request.logs = "AssertionError: unrelated regression"
    assert generate_candidates(root, request) == []


@pytest.mark.parametrize("name", ["../outside.py", "/tmp/outside.py"])
def test_checksum_repair_rejects_outside_paths(tmp_path: pathlib.Path, name: str) -> None:
    request = bundle()
    request.candidate_files = [name]
    with pytest.raises(WorkspaceError):
        generate_candidates(tmp_path, request)


@pytest.mark.parametrize("separator", ["\r", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"])
def test_checksum_repair_refuses_unsupported_separators(separator: str) -> None:
    source = (FIXTURES / "b207647f.txt").read_text()
    assert transform_checksum_write_order(source + "\n# " + separator) is None


@pytest.mark.parametrize(
    "old,new",
    [
        ("if expected:", "if expected:\n        data = b'changed'"),
        ("path.write_bytes(data)", "path.write_bytes(other)"),
        ("if ref == calc_b64 or ref.lower() == calc_hex:", "if True:"),
        ("return\n        raise RuntimeError", "return 1\n        raise RuntimeError"),
    ],
)
def test_checksum_repair_refuses_different_semantics(old: str, new: str) -> None:
    source = (FIXTURES / "b207647f.txt").read_text()
    assert old in source
    assert transform_checksum_write_order(source.replace(old, new)) is None


def test_checksum_repair_preserves_current_atomic_downloader() -> None:
    source = (FIXTURES / "current_main.txt").read_text()
    assert "os.replace(temp_file, path)" in source
    assert transform_checksum_write_order(source) is None
