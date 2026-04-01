# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.cli import main
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.safety import is_patch_safe


def test_cli_report_only_returns_zero(tmp_path: Path, monkeypatch) -> None:
    bundle = {
        "workflow": "wf",
        "job": "job",
        "step": "step",
        "run_id": "1",
        "sha": "abc",
        "logs": "permission denied",
        "annotations": [],
    }
    candidates = [
        {
            "diff": "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-a\n+a\n",
            "summary": "noop",
            "score": 0.1,
        }
    ]
    (tmp_path / "README.md").write_text("a\n", encoding="utf-8")
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
    candidates_path = tmp_path / "candidates.json"
    candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
    report_path = tmp_path / "report.json"

    monkeypatch.chdir(tmp_path)
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

    assert main() == 0
    assert report_path.exists()


def test_patch_safety_blocks_git_internal_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("x\n", encoding="utf-8")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]\n", encoding="utf-8")

    diff = "--- a/.git/config\n+++ b/.git/config\n@@ -1,1 +1,1 @@\n-[core]\n+[evil]\n"
    safe, reason = is_patch_safe(diff, tmp_path)
    assert safe is False
    assert "protected surface" in reason
