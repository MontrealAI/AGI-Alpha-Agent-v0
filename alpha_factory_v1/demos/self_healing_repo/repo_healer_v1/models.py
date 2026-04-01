# SPDX-License-Identifier: Apache-2.0
"""Typed models for Repo-Healer v1."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class FailureClass(str, Enum):
    """Normalized failure classes used by triage and policy."""

    RUFF = "ruff"
    MYPY = "mypy"
    PYTEST = "pytest"
    SMOKE = "smoke"
    DOCS = "docs"
    IMPORT = "import"
    ACTIONLINT = "actionlint"
    DOCKER = "docker"
    UNKNOWN = "unknown"


class TriageDecision(str, Enum):
    """Policy decision for a bundle."""

    SAFE_AUTOPATCH = "SAFE_AUTOPATCH"
    DRAFT_PR_ONLY = "DRAFT_PR_ONLY"
    DIAGNOSE_ONLY = "DIAGNOSE_ONLY"
    TRANSIENT_INFRA = "TRANSIENT_INFRA"
    PERMISSION_OR_FORK_CONTEXT = "PERMISSION_OR_FORK_CONTEXT"
    UNSAFE_PROTECTED_SURFACE = "UNSAFE_PROTECTED_SURFACE"


class SupportMode(str, Enum):
    """Execution modes for repo healer."""

    AUTOPATCH_SAFE = "AUTOPATCH_SAFE"
    DRAFT_PR_ONLY = "DRAFT_PR_ONLY"
    REPORT_ONLY = "REPORT_ONLY"


class ValidatorClass(str, Enum):
    """Validator classes mapped to canonical replay commands."""

    RUFF = "ruff"
    MYPY = "mypy"
    PYTEST = "pytest"
    SMOKE = "smoke"
    DOCS = "docs"
    NONE = "none"


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
    """Structured failure bundle consumed by Repo-Healer."""

    workflow: str
    job: str
    step: str
    run_id: str
    sha: str
    failure_class: FailureClass = FailureClass.UNKNOWN
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
        payload["failure_class"] = self.failure_class.value
        payload["validator_class"] = self.validator_class.value
        payload["support_mode"] = self.support_mode.value
        return payload


@dataclass(slots=True)
class TriageResult:
    """Triage output used by the repair loop."""

    failure_class: FailureClass
    decision: TriageDecision
    reason: str
    validator_class: ValidatorClass
    candidate_files: list[str]
    support_mode: SupportMode


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
    decision: TriageDecision
    support_mode: SupportMode
    reason: str
    validator_commands: list[list[str]]
    attempts: int
    selected_patch_summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["decision"] = self.decision.value
        payload["support_mode"] = self.support_mode.value
        return payload
