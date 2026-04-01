# SPDX-License-Identifier: Apache-2.0
"""Failure triage and risk policy selection for Repo-Healer v1."""

from __future__ import annotations

from .models import (
    FailureBundle,
    FailureClass,
    SupportMode,
    TriageDecision,
    TriageResult,
    ValidatorClass,
)

TRANSIENT_MARKERS = (
    "timed out",
    "connection reset",
    "temporary failure",
    "no route to host",
    "runner lost",
)
PERMISSION_MARKERS = (
    "permission denied",
    "resource not accessible by integration",
    "insufficient permission",
    "fork pull request",
    "forbidden",
)
UNSAFE_MARKERS = (
    "branch protection",
    "secret",
    "credential",
    "signing",
    "publish",
    "disable tests",
    "skip ci",
)


def triage_bundle(bundle: FailureBundle) -> TriageResult:
    """Classify failure bundle into repair decision and validator class."""
    text = "\n".join([bundle.logs, *(a.message for a in bundle.annotations)]).lower()

    if bundle.platform.lower() in {"windows", "macos"}:
        return TriageResult(
            failure_class=bundle.failure_class,
            decision=TriageDecision.DRAFT_PR_ONLY,
            reason=f"{bundle.platform} replay is Tier-2 diagnose-only in v1",
            validator_class=ValidatorClass.NONE,
            candidate_files=_candidate_files(bundle),
            support_mode=SupportMode.DRAFT_PR_ONLY,
        )
    if any(marker in text for marker in PERMISSION_MARKERS):
        return TriageResult(
            failure_class=bundle.failure_class,
            decision=TriageDecision.PERMISSION_OR_FORK_CONTEXT,
            reason="permission/fork context",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
            support_mode=SupportMode.REPORT_ONLY,
        )
    if any(marker in text for marker in UNSAFE_MARKERS):
        return TriageResult(
            failure_class=bundle.failure_class,
            decision=TriageDecision.UNSAFE_PROTECTED_SURFACE,
            reason="protected or unsafe surface",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
            support_mode=SupportMode.REPORT_ONLY,
        )
    if any(marker in text for marker in TRANSIENT_MARKERS):
        return TriageResult(
            failure_class=bundle.failure_class,
            decision=TriageDecision.TRANSIENT_INFRA,
            reason="likely transient infra",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
            support_mode=SupportMode.REPORT_ONLY,
        )

    failure_class, validator_class = _resolve_classes(bundle, text)
    return TriageResult(
        failure_class=failure_class,
        decision=TriageDecision.SAFE_AUTOPATCH,
        reason="linux reproducible code failure",
        validator_class=validator_class,
        candidate_files=_candidate_files(bundle),
        support_mode=SupportMode.AUTOPATCH_SAFE,
    )


def _resolve_classes(bundle: FailureBundle, text: str) -> tuple[FailureClass, ValidatorClass]:
    if bundle.failure_class != FailureClass.UNKNOWN:
        return bundle.failure_class, _validator_for_failure(bundle.failure_class)
    if "ruff" in text:
        return FailureClass.RUFF, ValidatorClass.RUFF
    if "mypy" in text:
        return FailureClass.MYPY, ValidatorClass.MYPY
    if "mkdocs" in text or "docs" in text:
        return FailureClass.DOCS, ValidatorClass.DOCS
    if "importerror" in text or "modulenotfounderror" in text:
        return FailureClass.IMPORT, ValidatorClass.PYTEST
    if "smoke" in bundle.workflow.lower() or "smoke" in text:
        return FailureClass.SMOKE, ValidatorClass.SMOKE
    return FailureClass.PYTEST, ValidatorClass.PYTEST


def _validator_for_failure(failure_class: FailureClass) -> ValidatorClass:
    return {
        FailureClass.RUFF: ValidatorClass.RUFF,
        FailureClass.MYPY: ValidatorClass.MYPY,
        FailureClass.DOCS: ValidatorClass.DOCS,
        FailureClass.SMOKE: ValidatorClass.SMOKE,
        FailureClass.IMPORT: ValidatorClass.PYTEST,
        FailureClass.PYTEST: ValidatorClass.PYTEST,
    }.get(failure_class, ValidatorClass.PYTEST)


def _candidate_files(bundle: FailureBundle) -> list[str]:
    explicit = sorted(set(bundle.candidate_files))
    if explicit:
        return explicit
    paths = sorted({a.path for a in bundle.annotations if a.path})
    return paths
