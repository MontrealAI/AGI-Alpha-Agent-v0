# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import pathlib

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.candidate_generation import generate_candidates
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, ValidatorClass


def test_generate_ruff_candidate(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "module.py"
    target.write_text("import pathlib\n\nprint('x')\n", encoding="utf-8")

    bundle = FailureBundle(
        workflow="wf",
        job="lint",
        step="ruff",
        run_id="1",
        sha="abc",
        logs="F401 'pathlib' imported but unused",
        validator_class=ValidatorClass.RUFF,
        candidate_files=["module.py"],
    )

    candidates = generate_candidates(bundle, repo)
    assert len(candidates) == 1
    assert "-import pathlib" in candidates[0].diff


def test_generate_import_candidate(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "tests.py"
    target.write_text("import definitely_missing_module\n", encoding="utf-8")

    bundle = FailureBundle(
        workflow="wf",
        job="tests",
        step="pytest",
        run_id="1",
        sha="abc",
        logs="ModuleNotFoundError: No module named 'definitely_missing_module'",
        validator_class=ValidatorClass.IMPORT,
        candidate_files=["tests.py"],
    )

    candidates = generate_candidates(bundle, repo)
    assert len(candidates) == 1
    assert "definitely_missing_module" in candidates[0].diff


def test_generate_ruff_semicolon_candidate(tmp_path: pathlib.Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    target = repo / "module.py"
    target.write_text("import os; import sys\n", encoding="utf-8")

    bundle = FailureBundle(
        workflow="wf",
        job="lint",
        step="ruff",
        run_id="1",
        sha="abc",
        logs="E702 Multiple statements on one line (semicolon)",
        validator_class=ValidatorClass.RUFF,
        candidate_files=["module.py"],
    )

    candidates = generate_candidates(bundle, repo)
    assert len(candidates) == 1
    assert "+import os" in candidates[0].diff
    assert "+import sys" in candidates[0].diff
