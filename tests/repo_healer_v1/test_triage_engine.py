# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine import EngineOptions, RepoHealerEngine
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, PatchCandidate
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.triage import triage_bundle


def test_triage_permission_is_diagnose_only() -> None:
    bundle = FailureBundle("wf", "job", "step", "1", "abc", logs="403 Resource not accessible by integration")
    result = triage_bundle(bundle)
    assert result.policy.value == "diagnose_only"


def test_engine_dry_run_autofix(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    readme = repo / "README.md"
    readme.write_text("hello\n", encoding="utf-8")
    bundle = FailureBundle("wf", "job", "step", "1", "abc", logs="ruff F401")
    patch = PatchCandidate(
        diff="--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-hello\n+hello\n",
        summary="noop",
        score=0.9,
    )
    report = RepoHealerEngine(repo, EngineOptions(dry_run=True)).run(bundle, [patch])
    assert report.success is True
    assert report.selected_patch_summary == "noop"
