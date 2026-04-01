# SPDX-License-Identifier: Apache-2.0
"""Typed models for Repo-Healer v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FailureClass(str, Enum):
    """Normalized failure classes used by triage and policy."""

    AUTO_FIXABLE = "auto_fixable"
    TRANSIENT_INFRA = "transient_infra"
    PERMISSION = "permission"
    UNSAFE_SURFACE = "unsafe_surface"
    UNSUPPORTED_PLATFORM = "unsupported_platform"


class RiskPolicy(str, Enum):
    """Policy buckets for downstream execution."""

    SAFE_AUTOPATCH = "safe_autopatch"
    DRAFT_PR_ONLY = "draft_pr_only"
    DIAGNOSE_ONLY = "diagnose_only"


@dataclass(slots=True)
class FailureSignal:
    """Single structured CI signal."""

    source: str
    message: str
    path: str | None = None
    line: int | None = None
    code: str | None = None


@dataclass(slots=True)
class FailureBundle:
    """Minimal context pack consumed by Repo-Healer."""

    workflow: str
    job: str
    step: str
    run_id: str
    sha: str
    platform: str = "linux"
    exit_code: int = 1
    logs: str = ""
    junit_xml: str | None = None
    annotations: list[FailureSignal] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TriageResult:
    """Triage output used by the repair loop."""

    failure_class: FailureClass
    policy: RiskPolicy
    reason: str
    validator_key: str
    candidate_files: list[str]


@dataclass(slots=True)
class PatchCandidate:
    """Candidate patch and metadata."""

    diff: str
    summary: str
    score: float


@dataclass(slots=True)
class RepairReport:
    """Machine-readable report for CI artifacts and benchmarking."""

    success: bool
    policy: RiskPolicy
    reason: str
    validator_commands: list[list[str]]
    attempts: int
    selected_patch_summary: str | None = None
    branch_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["policy"] = self.policy.value
        return payload
