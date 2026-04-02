# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import cli
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.safety import is_patch_safe

import pytest


def test_cli_report_only_returns_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bundle = {
        "workflow": "wf",
        "job": "job",
        "step": "step",
        "run_id": "1",
        "sha": "abc",
        "logs": "permission denied",
        "annotations": [],
    }
    candidates = [{"diff": "--- a/README.md\n+++ b/README.md\n", "summary": "noop", "score": 0.1}]
    bundle_path = tmp_path / "bundle.json"
    candidates_path = tmp_path / "candidates.json"
    report_path = tmp_path / "report.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "repo-healer",
            "--repo",
            str(tmp_path),
            "--failure-bundle",
            str(bundle_path),
            "--candidates",
            str(candidates_path),
            "--report",
            str(report_path),
            "--report-only",
        ],
    )

    exit_code = cli.main()
    assert exit_code == 0
    assert report_path.exists()


def test_safety_rejects_dot_git_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    git_dir = repo / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")

    safe, reason = is_patch_safe(
        "--- a/.git/config\n+++ b/.git/config\n@@ -1,1 +1,1 @@\n-[core]\n+[core]\n",
        repo,
    )

    assert safe is False
    assert "protected surface" in reason
