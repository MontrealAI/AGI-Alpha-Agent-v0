# SPDX-License-Identifier: Apache-2.0
"""Installed dependencies must never enter repair copies or proposed file deletions."""
from __future__ import annotations

from pathlib import Path
import os

import pytest

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.candidate_generation import _diff_between_repos
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine import RepoHealerEngine
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.safety import is_patch_safe
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.workspace import (
    WorkspaceError,
    copy_workspace,
    project_path,
    workspace_files,
)
from alpha_factory_v1.demos.self_healing_repo import patcher_core
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, PatchCandidate, ValidatorClass


@pytest.mark.parametrize("folder", [".venv-agent", ".venv-audit", "labs/custom-python", "nested/node_modules"])
def test_copies_and_diffs_exclude_environments_at_every_depth(tmp_path: Path, folder: str) -> None:
    source = tmp_path / "project"
    environment = source / folder
    environment.mkdir(parents=True)
    (environment / "dependency.py").write_text("installed dependency must not enter the patch\n")
    if "custom-python" in folder:
        (environment / "pyvenv.cfg").write_text("home = /usr/bin\n")
    code = source / "app.py"
    code.write_text("value = 1\n")
    destination = tmp_path / "repair"
    copy_workspace(source, destination)
    assert not (destination / folder).exists()
    assert workspace_files(source) == workspace_files(destination) == {Path("app.py")}
    assert _diff_between_repos(source, destination) == ""
    (destination / "app.py").write_text("value = 2\n")
    patch = _diff_between_repos(source, destination)
    assert "-value = 1" in patch and "+value = 2" in patch
    assert "dependency" not in patch and "pyvenv.cfg" not in patch
    assert (environment / "dependency.py").is_file()
    assert is_patch_safe(patch, source)[0]
    dependency_patch = f"--- a/{folder}/dependency.py\n+++ b/{folder}/dependency.py\n@@ -1 +1 @@\n-old\n+new\n"
    assert not is_patch_safe(dependency_patch, source)[0]


def test_engine_retains_source_and_documentation_with_environment_like_names(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (source / ".venv-guide.md").write_text("Setup instructions\n")
    (source / "environment").mkdir()
    (source / "environment/config.py").write_text("source = True\n")
    destination = tmp_path / "repair"
    RepoHealerEngine._copy_repo(source, destination)
    assert workspace_files(source) == workspace_files(destination)
    assert (destination / ".venv-guide.md").read_text() == "Setup instructions\n"
    assert (destination / "environment/config.py").read_text() == "source = True\n"


@pytest.mark.parametrize("kind", ["file", "directory", "dangling", "hardlink", "fifo"])
def test_workspace_rejects_links_and_special_files_without_changing_outside_data(tmp_path: Path, kind: str) -> None:
    source = tmp_path / "repo"
    source.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "data.txt"
    target.write_text("outside data\n")
    entry = source / "linked"
    if kind == "hardlink":
        os.link(target, entry)
    elif kind == "fifo":
        if not hasattr(os, "mkfifo"):
            pytest.skip("FIFO creation requires POSIX")
        os.mkfifo(entry)
    else:
        entry.symlink_to(
            outside if kind == "directory" else outside / "missing" if kind == "dangling" else target,
            target_is_directory=kind == "directory",
        )
    with pytest.raises(WorkspaceError):
        workspace_files(source)
    with pytest.raises(WorkspaceError):
        copy_workspace(source, tmp_path / "copy")
    with pytest.raises(WorkspaceError):
        project_path(source, "linked")
    diff = "--- a/linked\n+++ b/linked\n@@ -1 +1 @@\n-outside data\n+changed\n"
    assert not is_patch_safe(diff, source)[0]
    with pytest.raises(WorkspaceError):
        patcher_core.apply_patch(diff, str(source))
    assert target.read_text() == "outside data\n"


@pytest.mark.parametrize(
    "name",
    [
        "/tmp/outside.py",
        "../outside.py",
        "nested/../../outside.py",
        "./file.py",
        "nested//file.py",
        "C:/outside.py",
        r"nested\file.py",
        "--config.py",
        "bad\nname.py",
    ],
)
def test_workspace_paths_must_be_canonical_and_relative(tmp_path: Path, name: str) -> None:
    with pytest.raises(WorkspaceError, match="canonical repository-relative"):
        project_path(tmp_path, name)


@pytest.mark.parametrize("link_in", ["source", "destination"])
def test_promotion_rechecks_files_after_validation(tmp_path: Path, monkeypatch, link_in: str) -> None:
    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import engine

    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "app.py"
    target.write_text("old\n")
    outside = tmp_path / "outside.py"
    outside.write_text("private\n")

    def validator(command, cwd):
        changed = Path(cwd) / "app.py" if link_in == "source" else target
        if not changed.is_symlink():
            changed.unlink()
            changed.symlink_to(outside)
        return 0, "passed"

    monkeypatch.setattr(engine, "run_validator", validator)
    bundle = FailureBundle(
        "wf", "job", "step", "1", "abc", validator_class=ValidatorClass.PYTEST, logs="AssertionError"
    )
    patch = PatchCandidate("--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-old\n+new\n", "fix", 1.0)
    report = RepoHealerEngine(repo).run(bundle, [patch])
    assert not report.success
    assert report.support_mode.value == "UNSAFE_PROTECTED_SURFACE"
    assert outside.read_text() == "private\n"
    if link_in == "source":
        assert target.read_text() == "old\n"
