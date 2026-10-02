# SPDX-License-Identifier: Apache-2.0
"""Installed dependencies must never enter repair copies or proposed file deletions."""
from __future__ import annotations

from pathlib import Path

import pytest

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.candidate_generation import _diff_between_repos
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine import RepoHealerEngine
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.safety import is_patch_safe
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.workspace import copy_workspace, workspace_files


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
