# SPDX-License-Identifier: Apache-2.0
"""Repo-Healer v1 bounded repair engine."""

from __future__ import annotations

import json
import pathlib
import tempfile
from dataclasses import dataclass

from alpha_factory_v1.demos.self_healing_repo import patcher_core

from .models import FailureBundle, PatchCandidate, RepairReport, RiskPolicy
from .safety import is_patch_safe
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
        if triage.policy != RiskPolicy.SAFE_AUTOPATCH or self.options.report_only:
            return RepairReport(False, triage.policy, triage.reason, [], 0)

        plan = get_plan(triage.validator_key)
        commands = [plan.targeted, plan.broader]
        attempts = 0
        for candidate in sorted(candidates, key=lambda c: c.score, reverse=True)[: self.options.max_attempts]:
            attempts += 1
            safe, reason = is_patch_safe(candidate.diff, self.repo_root)
            if not safe:
                continue
            if self.options.dry_run:
                return RepairReport(True, triage.policy, "dry-run safe candidate", commands, attempts, candidate.summary)
            try:
                patcher_core.apply_patch(candidate.diff, repo_path=str(self.repo_root))
            except Exception:
                continue

            rc_target, _ = run_validator(plan.targeted, cwd=str(self.repo_root))
            if rc_target != 0:
                continue
            rc_broader, _ = run_validator(plan.broader, cwd=str(self.repo_root))
            if rc_broader == 0:
                return RepairReport(True, triage.policy, "validators passed", commands, attempts, candidate.summary)

        return RepairReport(False, triage.policy, "no candidate passed validators", commands, attempts)


def write_report(report: RepairReport, out_path: pathlib.Path) -> None:
    """Write machine-readable report JSON."""
    out_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
