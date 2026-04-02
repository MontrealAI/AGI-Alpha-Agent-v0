# SPDX-License-Identifier: Apache-2.0
"""Typed models for Repo-Healer v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class SupportMode(str, Enum):
    """Execution mode for the repair engine."""

    AUTOPATCH_SAFE = "AUTOPATCH_SAFE"
    DRAFT_PR_ONLY = "DRAFT_PR_ONLY"
    REPORT_ONLY = "REPORT_ONLY"


class FailureClass(str, Enum):
    """Normalized failure classifications."""

    SAFE_AUTOPATCH = "SAFE_AUTOPATCH"
    DRAFT_PR_ONLY = "DRAFT_PR_ONLY"
    DIAGNOSE_ONLY = "DIAGNOSE_ONLY"
    TRANSIENT_INFRA = "TRANSIENT_INFRA"
    PERMISSION_OR_FORK_CONTEXT = "PERMISSION_OR_FORK_CONTEXT"
    UNSAFE_PROTECTED_SURFACE = "UNSAFE_PROTECTED_SURFACE"
    UNSUPPORTED_PLATFORM = "UNSUPPORTED_PLATFORM"


class ValidatorClass(str, Enum):
    """Canonical validator classes currently used by this repository."""

    RUFF = "ruff"
    MYPY = "mypy"
    IMPORT = "import"
    PYTEST = "pytest"
    SMOKE = "smoke"
    MKDOCS = "mkdocs"
    NONE = "none"


@dataclass(slots=True)
class FailureSignal:
    """Single structured signal extracted from CI output."""

    source: str
    message: str
    path: str | None = None
    line: int | None = None
    code: str | None = None


@dataclass(slots=True)
class FailureBundle:
    """Structured failure bundle consumed by Repo-Healer."""

    workflow: str
    job: str
    step: str
    run_id: str
    sha: str
    failure_class: str = "unknown"
    platform: str = "linux"
    exit_code: int = 1
    candidate_files: list[str] = field(default_factory=list)
    reproduction_command: list[str] = field(default_factory=list)
    validator_class: ValidatorClass = ValidatorClass.NONE
    risk_tier: str = "tier1"
    support_mode: SupportMode = SupportMode.AUTOPATCH_SAFE
    logs: str = ""
    junit_xml: str | None = None
    annotations: list[FailureSignal] = field(default_factory=list)
    artifacts: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["validator_class"] = self.validator_class.value
        payload["support_mode"] = self.support_mode.value
        return payload


@dataclass(slots=True)
class TriageResult:
    """Triage output used by the bounded repair loop."""

    classification: FailureClass
    support_mode: SupportMode
    reason: str
    validator_class: ValidatorClass
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
    classification: FailureClass
    support_mode: SupportMode
    reason: str
    validator_commands: list[list[str]]
    attempts: int
    selected_patch_summary: str | None = None
    branch_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["classification"] = self.classification.value
        payload["support_mode"] = self.support_mode.value
        return payload
