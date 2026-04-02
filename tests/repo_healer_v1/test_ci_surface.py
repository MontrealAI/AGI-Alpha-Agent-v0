# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from pathlib import Path

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.ci_surface import discover_ci_surface
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.engine import EngineOptions, RepoHealerEngine
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import PatchCandidate


def test_discover_ci_surface_from_pr_ci() -> None:
    surface = discover_ci_surface(Path("."))
    assert surface.pr_ruff_command == ["ruff", "check", "."]
    assert surface.pr_smoke_command[:3] == ["pytest", "-m", "smoke"]


def test_engine_ranks_minimal_candidate_first(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").write_text("hi\n", encoding="utf-8")
    (repo / "docs.md").write_text("one\ntwo\n", encoding="utf-8")
    engine = RepoHealerEngine(repo, EngineOptions(dry_run=True))

    heavy = PatchCandidate(
        diff=(
            "--- a/docs.md\n+++ b/docs.md\n@@ -1,2 +1,2 @@\n-one\n+ONE\n-two\n+TWO\n"
            "--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-hi\n+HI\n"
        ),
        summary="bulk",
        score=1.0,
    )
    minimal = PatchCandidate(
        diff="--- a/README.md\n+++ b/README.md\n@@ -1,1 +1,1 @@\n-hi\n+Hi\n",
        summary="narrow fix",
        score=0.9,
    )
    ranked = engine._rank_candidates([heavy, minimal])
    assert ranked[0].summary == "narrow fix"
