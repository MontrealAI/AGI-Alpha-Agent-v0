# SPDX-License-Identifier: Apache-2.0
"""Repo-Healer v1 bounded repair engine."""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile
from dataclasses import dataclass

from alpha_factory_v1.demos.self_healing_repo import patcher_core

from .github_integration import branch_name
from .models import FailureBundle, PatchCandidate, RepairReport, SupportMode, ValidatorClass
from .safety import is_patch_safe, touched_files_from_diff
from .triage import triage_bundle
from .validators import get_plan, run_validator


@dataclass(slots=True)
class EngineOptions:
    """Execution controls for repair loop."""

    dry_run: bool = False
    report_only: bool = False
    max_attempts: int = 2
    run_broader_validation: bool = True


class RepoHealerEngine:
    """Run triage, patch attempt, and validation in an isolated bounded loop."""

    def __init__(self, repo_root: pathlib.Path, options: EngineOptions | None = None):
        self.repo_root = repo_root
        self.options = options or EngineOptions()

    def run(self, bundle: FailureBundle, candidates: list[PatchCandidate]) -> RepairReport:
        triage = triage_bundle(bundle)
        if triage.support_mode != SupportMode.AUTOPATCH_SAFE or self.options.report_only:
            return RepairReport(
                False,
                triage.classification,
                triage.support_mode,
                triage.reason,
                [],
                0,
                replay_commands=[],
            )

        plan = get_plan(triage.validator_class)
        targeted = self._resolve_targeted_command(bundle, triage.validator_class, plan.targeted)
        commands = [targeted] + ([plan.broader] if self.options.run_broader_validation else [])
        attempts = 0

        for candidate in sorted(candidates, key=lambda c: c.score, reverse=True)[: self.options.max_attempts]:
            attempts += 1
            safe, reason = is_patch_safe(candidate.diff, self.repo_root)
            if not safe:
                continue
            if self.options.dry_run:
                return RepairReport(
                    True,
                    triage.classification,
                    triage.support_mode,
                    f"dry-run safe candidate ({reason})",
                    commands,
                    attempts,
                    candidate.summary,
                    branch_name=branch_name(bundle.run_id, bundle.sha),
                    replay_commands=commands,
                )

            with tempfile.TemporaryDirectory(prefix="repo-healer-attempt-") as tmpdir:
                isolated_repo = pathlib.Path(tmpdir) / "repo"
                self._copy_repo(self.repo_root, isolated_repo)
                try:
                    patcher_core.apply_patch(candidate.diff, repo_path=str(isolated_repo))
                except Exception:
                    continue

                try:
                    rc_target, _ = run_validator(targeted, cwd=str(isolated_repo))
                except Exception:
                    continue
                if rc_target != 0:
                    continue
                if self.options.run_broader_validation:
                    try:
                        rc_broader, _ = run_validator(plan.broader, cwd=str(isolated_repo))
                    except Exception:
                        continue
                    if rc_broader != 0:
                        continue
                    success_reason = "targeted and broader validators passed"
                else:
                    success_reason = "targeted validator passed (broader validation skipped by option)"

                self._promote_patch(candidate.diff, isolated_repo)
                return RepairReport(
                    True,
                    triage.classification,
                    triage.support_mode,
                    success_reason,
                    commands,
                    attempts,
                    candidate.summary,
                    branch_name=branch_name(bundle.run_id, bundle.sha),
                    replay_commands=commands,
                )

        return RepairReport(
            False,
            triage.classification,
            triage.support_mode,
            "no candidate passed validators",
            commands,
            attempts,
            replay_commands=commands,
        )

    @staticmethod
    def _resolve_targeted_command(
        bundle: FailureBundle, validator_class: ValidatorClass, default: list[str]
    ) -> list[str]:
        """Resolve a targeted replay command from structured bundle hints."""
        if bundle.reproduction_command:
            return list(bundle.reproduction_command)
        if validator_class != ValidatorClass.PYTEST:
            return default

        hinted_files = list(bundle.candidate_files) + [a.path for a in bundle.annotations if a.path]
        test_files = [path for path in hinted_files if path.startswith("tests/") and path.endswith(".py")]
        if test_files:
            return [sys.executable, "-m", "pytest", *test_files, "-q"]
        return default

    @staticmethod
    def _copy_repo(src: pathlib.Path, dst: pathlib.Path) -> None:
        """Copy repository into isolated scratch directory."""
        ignore = shutil.ignore_patterns(".git", ".pytest_cache", ".mypy_cache", "__pycache__")
        shutil.copytree(src, dst, ignore=ignore)

    def _promote_patch(self, diff: str, isolated_repo: pathlib.Path) -> None:
        """Copy touched files from validated isolated repo back to working tree."""
        for rel in touched_files_from_diff(diff):
            source = isolated_repo / rel
            destination = self.repo_root / rel
            if source.exists():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)


def write_report(report: RepairReport, out_path: pathlib.Path) -> None:
    """Write machine-readable report JSON."""
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
