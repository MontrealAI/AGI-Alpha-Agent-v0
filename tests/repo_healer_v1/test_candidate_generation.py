# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.candidate_generation import generate_candidates
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, ValidatorClass


def test_generate_candidates_fixes_missing_import(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "tests" / "test_imports.py"
    target.parent.mkdir(parents=True)
    target.write_text("import unittest\nimport definitely_missing_module\n", encoding="utf-8")

    bundle = FailureBundle(
        workflow="wf",
        job="smoke",
        step="imports",
        run_id="1",
        sha="abc",
        validator_class=ValidatorClass.IMPORT,
        logs="ModuleNotFoundError: No module named 'definitely_missing_module'",
        candidate_files=["tests/test_imports.py"],
    )

    candidates = generate_candidates(repo, bundle)
    assert len(candidates) == 1
    assert "-import definitely_missing_module" in candidates[0].diff


def test_generate_candidates_noop_for_unsupported_class(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("ok\n", encoding="utf-8")

    bundle = FailureBundle("wf", "job", "step", "1", "abc", validator_class=ValidatorClass.PYTEST, logs="assert")
    assert generate_candidates(repo, bundle) == []
