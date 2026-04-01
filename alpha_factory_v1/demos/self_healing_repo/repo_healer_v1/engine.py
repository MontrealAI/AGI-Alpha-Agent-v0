# SPDX-License-Identifier: Apache-2.0
"""Repo-Healer v1 bounded repair engine."""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

from alpha_factory_v1.demos.self_healing_repo import patcher_core

from .models import FailureBundle, PatchCandidate, RepairReport, SupportMode, TriageDecision
from .safety import is_patch_safe, touched_files_from_diff
from .triage import triage_bundle
from .validators import get_plan, run_validator


@dataclass(slots=True)
class EngineOptions:
    """Execution controls for repair loop."""

    dry_run: bool = False
    report_only: bool = False
    max_attempts: int = 2


class RepoHealerEngine:
    """Run triage, patch attempt, and validation in a bounded loop."""

    def __init__(self, repo_root: pathlib.Path, options: EngineOptions | None = None):
        self.repo_root = repo_root
        self.options = options or EngineOptions()

    def run(self, bundle: FailureBundle, candidates: list[PatchCandidate]) -> RepairReport:
        triage = triage_bundle(bundle)
        if self.options.report_only:
            triage = triage.__class__(
                failure_class=triage.failure_class,
                decision=triage.decision,
                reason=f"report-only mode: {triage.reason}",
                validator_class=triage.validator_class,
                candidate_files=triage.candidate_files,
                support_mode=SupportMode.REPORT_ONLY,
            )
        if triage.support_mode != SupportMode.AUTOPATCH_SAFE:
            return RepairReport(False, triage.decision, triage.support_mode, triage.reason, [], 0)

        plan = get_plan(triage.validator_class)
        targeted_cmd = bundle.reproduction_command or plan.targeted
        broader_cmd = plan.broader if not bundle.reproduction_command else targeted_cmd
        commands = [targeted_cmd, broader_cmd]
        attempts = 0
        for candidate in sorted(candidates, key=lambda c: c.score, reverse=True)[: self.options.max_attempts]:
            attempts += 1
            safe, _ = is_patch_safe(candidate.diff, self.repo_root)
            if not safe:
                continue
            if self.options.dry_run:
                return RepairReport(
                    True,
                    TriageDecision.SAFE_AUTOPATCH,
                    triage.support_mode,
                    "dry-run safe candidate",
                    commands,
                    attempts,
                    candidate.summary,
                )
            snapshot = self._snapshot_files(candidate.diff)
            try:
                patcher_core.apply_patch(candidate.diff, repo_path=str(self.repo_root))
                rc_target, _ = run_validator(targeted_cmd, cwd=str(self.repo_root))
                if rc_target != 0:
                    self._restore_snapshot(snapshot)
                    continue
                rc_broader, _ = run_validator(broader_cmd, cwd=str(self.repo_root))
                if rc_broader == 0:
                    return RepairReport(
                        True,
                        TriageDecision.SAFE_AUTOPATCH,
                        triage.support_mode,
                        "validators passed",
                        commands,
                        attempts,
                        candidate.summary,
                    )
                self._restore_snapshot(snapshot)
            except Exception:
                self._restore_snapshot(snapshot)
                continue

        return RepairReport(
            False,
            TriageDecision.DIAGNOSE_ONLY,
            SupportMode.REPORT_ONLY,
            "no candidate passed validators",
            commands,
            attempts,
        )

    def _snapshot_files(self, diff: str) -> dict[pathlib.Path, str]:
        """Capture pre-apply contents so failed candidates can roll back safely."""
        snapshot: dict[pathlib.Path, str] = {}
        for rel in touched_files_from_diff(diff):
            file_path = self.repo_root / rel
            if file_path.exists():
                snapshot[file_path] = file_path.read_text(encoding="utf-8")
        return snapshot

    def _restore_snapshot(self, snapshot: dict[pathlib.Path, str]) -> None:
        """Restore repository contents after failed candidate validation."""
        for path, text in snapshot.items():
            path.write_text(text, encoding="utf-8")


def write_report(report: RepairReport, out_path: pathlib.Path) -> None:
    """Write machine-readable report JSON."""
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
