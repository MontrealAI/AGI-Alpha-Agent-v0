# SPDX-License-Identifier: Apache-2.0
"""Failure triage and risk policy selection for Repo-Healer v1."""

from __future__ import annotations

from .models import FailureBundle, FailureClass, RiskPolicy, TriageResult

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
)
UNSAFE_MARKERS = ("branch protection", "token", "secret", "signature", "publish")


def triage_bundle(bundle: FailureBundle) -> TriageResult:
    """Classify failure bundle into repair policy and validator path."""
    text = "\n".join([bundle.logs, *(a.message for a in bundle.annotations)]).lower()

    if bundle.platform.lower() in {"windows", "macos"}:
        return TriageResult(
            failure_class=FailureClass.UNSUPPORTED_PLATFORM,
            policy=RiskPolicy.DRAFT_PR_ONLY,
            reason=f"{bundle.platform} replay is Tier-2 diagnose-only in v1",
            validator_key="none",
            candidate_files=[],
        )
    if any(marker in text for marker in PERMISSION_MARKERS):
        return TriageResult(
            FailureClass.PERMISSION,
            RiskPolicy.DIAGNOSE_ONLY,
            "permission/token context",
            "none",
            [],
        )
    if any(marker in text for marker in UNSAFE_MARKERS):
        return TriageResult(
            FailureClass.UNSAFE_SURFACE,
            RiskPolicy.DIAGNOSE_ONLY,
            "protected or unsafe surface",
            "none",
            [],
        )
    if any(marker in text for marker in TRANSIENT_MARKERS):
        return TriageResult(
            FailureClass.TRANSIENT_INFRA,
            RiskPolicy.DIAGNOSE_ONLY,
            "likely transient infra",
            "none",
            [],
        )

    validator_key = _validator_from_text(text)
    files = _candidate_files(bundle)
    return TriageResult(
        FailureClass.AUTO_FIXABLE,
        RiskPolicy.SAFE_AUTOPATCH,
        "linux reproducible code failure",
        validator_key,
        files,
    )


def _validator_from_text(text: str) -> str:
    if "ruff" in text:
        return "ruff"
    if "mypy" in text:
        return "mypy"
    if "mkdocs" in text or "docs" in text:
        return "mkdocs"
    if "importerror" in text or "modulenotfounderror" in text:
        return "import"
    if "pytest" in text or "assert" in text:
        return "pytest"
    return "smoke"


def _candidate_files(bundle: FailureBundle) -> list[str]:
    paths = [a.path for a in bundle.annotations if a.path]
    if paths:
        return sorted(set(paths))
    return []
