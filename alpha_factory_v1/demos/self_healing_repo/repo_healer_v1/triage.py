# SPDX-License-Identifier: Apache-2.0
"""Failure triage and support mode selection for Repo-Healer v1."""

from __future__ import annotations

from .models import FailureBundle, FailureClass, SupportMode, TriageResult, ValidatorClass

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
    "403",
    "fork",
)
UNSAFE_MARKERS = (
    "branch protection",
    "token",
    "secret",
    "signature",
    "publish",
    "disable test",
    "skip ci",
)
DRAFT_ONLY_MARKERS = ("actionlint", "docker build", "windows", "macos", "workflow yaml")


def triage_bundle(bundle: FailureBundle) -> TriageResult:
    """Classify a bundle into support mode and validator target."""
    if bundle.support_mode == SupportMode.REPORT_ONLY:
        return TriageResult(
            classification=FailureClass.DIAGNOSE_ONLY,
            support_mode=SupportMode.REPORT_ONLY,
            reason="bundle requested report-only mode",
            validator_class=ValidatorClass.NONE,
            candidate_files=_candidate_files(bundle),
        )
    if bundle.support_mode == SupportMode.DRAFT_PR_ONLY:
        return TriageResult(
            classification=FailureClass.DRAFT_PR_ONLY,
            support_mode=SupportMode.DRAFT_PR_ONLY,
            reason="bundle requested draft-pr-only mode",
            validator_class=bundle.validator_class,
            candidate_files=_candidate_files(bundle),
        )

    text = "\n".join([bundle.logs, *(a.message for a in bundle.annotations)]).lower()

    if bundle.platform.lower() in {"windows", "macos"}:
        return TriageResult(
            classification=FailureClass.UNSUPPORTED_PLATFORM,
            support_mode=SupportMode.DRAFT_PR_ONLY,
            reason=f"{bundle.platform} replay is Tier-2 diagnose-only in v1",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
        )
    if any(marker in text for marker in PERMISSION_MARKERS):
        return TriageResult(
            classification=FailureClass.PERMISSION_OR_FORK_CONTEXT,
            support_mode=SupportMode.REPORT_ONLY,
            reason="permission or fork context",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
        )
    if any(marker in text for marker in UNSAFE_MARKERS):
        return TriageResult(
            classification=FailureClass.UNSAFE_PROTECTED_SURFACE,
            support_mode=SupportMode.REPORT_ONLY,
            reason="protected or unsafe surface",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
        )
    if any(marker in text for marker in TRANSIENT_MARKERS):
        return TriageResult(
            classification=FailureClass.TRANSIENT_INFRA,
            support_mode=SupportMode.REPORT_ONLY,
            reason="likely transient infrastructure",
            validator_class=ValidatorClass.NONE,
            candidate_files=[],
        )
    if any(marker in text for marker in DRAFT_ONLY_MARKERS):
        return TriageResult(
            classification=FailureClass.DRAFT_PR_ONLY,
            support_mode=SupportMode.DRAFT_PR_ONLY,
            reason="tier-2 surface: draft patch or diagnosis only",
            validator_class=ValidatorClass.NONE,
            candidate_files=_candidate_files(bundle),
        )

    validator_class = (
        bundle.validator_class if bundle.validator_class != ValidatorClass.NONE else _validator_from_text(text)
    )
    return TriageResult(
        classification=FailureClass.SAFE_AUTOPATCH,
        support_mode=SupportMode.AUTOPATCH_SAFE,
        reason="linux reproducible code failure",
        validator_class=validator_class,
        candidate_files=_candidate_files(bundle),
    )


def _validator_from_text(text: str) -> ValidatorClass:
    if "ruff" in text:
        return ValidatorClass.RUFF
    if "mypy" in text:
        return ValidatorClass.MYPY
    if "mkdocs" in text:
        return ValidatorClass.MKDOCS
    if "importerror" in text or "modulenotfounderror" in text:
        return ValidatorClass.IMPORT
    if "smoke" in text:
        return ValidatorClass.SMOKE
    if "pytest" in text or "assert" in text:
        return ValidatorClass.PYTEST
    return ValidatorClass.SMOKE


def _candidate_files(bundle: FailureBundle) -> list[str]:
    by_annotation = [a.path for a in bundle.annotations if a.path]
    if by_annotation:
        return sorted(set(by_annotation))
    if bundle.candidate_files:
        return sorted(set(bundle.candidate_files))
    return []
