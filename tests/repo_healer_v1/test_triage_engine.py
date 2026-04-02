# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib
from unittest import mock

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine import EngineOptions, RepoHealerEngine
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, PatchCandidate
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.cli import _load_bundle
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.triage import triage_bundle


def test_triage_permission_is_report_only() -> None:
    bundle = FailureBundle("wf", "job", "step", "1", "abc", logs="403 Resource not accessible by integration")
    result = triage_bundle(bundle)
    assert result.support_mode.value == "REPORT_ONLY"


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


def test_cli_deserializes_annotations(tmp_path: pathlib.Path) -> None:
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(
        (
            '{"workflow":"w","job":"j","step":"s","run_id":"1","sha":"abc",'
            '"annotations":[{"source":"gha","message":"mypy error"}]}'
        ),
        encoding="utf-8",
    )
    bundle = _load_bundle(bundle_path)
    assert bundle.annotations[0].message == "mypy error"


def test_triage_does_not_flag_assignment_as_unsafe() -> None:
    bundle = FailureBundle("wf", "job", "step", "1", "abc", logs="mypy: Incompatible types in assignment")
    result = triage_bundle(bundle)
    assert result.support_mode.value == "AUTOPATCH_SAFE"


def test_engine_isolated_validation_promotes_patch(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    readme = repo / "README.md"
    readme.write_text("hello\n", encoding="utf-8")
    bundle = FailureBundle("wf", "job", "step", "1", "abc", logs="pytest assert")
    patch = PatchCandidate(
        diff="--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-hello\n+good\n",
        summary="good",
        score=1.0,
    )

    with (
        mock.patch("alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine.run_validator") as run_validator,
        mock.patch("alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine.get_plan") as get_plan,
    ):
        get_plan.return_value = mock.Mock(targeted=["target"], broader=["broad"])
        run_validator.side_effect = [(0, "ok"), (0, "ok")]
        report = RepoHealerEngine(repo, EngineOptions(dry_run=False, max_attempts=1)).run(bundle, [patch])

    assert report.success is True
    assert readme.read_text(encoding="utf-8") == "good\n"
