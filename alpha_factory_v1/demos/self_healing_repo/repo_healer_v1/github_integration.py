# SPDX-License-Identifier: Apache-2.0
"""GitHub metadata helpers for Repo-Healer v1."""

from __future__ import annotations

from dataclasses import dataclass

from .models import FailureBundle


@dataclass(slots=True)
class GitHubContext:
    """Context needed to decide push vs report-only mode."""

    can_push: bool
    reason: str


def branch_name(run_id: str, short_sha: str) -> str:
    """Return standardized auto-fix branch name."""
    return f"auto-fix/{run_id}-{short_sha[:8]}"


def commit_message(bundle: FailureBundle, summary: str) -> str:
    """Build commit message with CI metadata."""
    return f"fix(repo-healer): {summary} ({bundle.workflow}/{bundle.job})"


def pr_body(bundle: FailureBundle, summary: str, replay: list[list[str]]) -> str:
    """Build concise draft PR body."""
    lines = [
        "## Repo-Healer v1 repair",
        f"- Workflow: `{bundle.workflow}`",
        f"- Job: `{bundle.job}`",
        f"- Step: `{bundle.step}`",
        f"- Run: `{bundle.run_id}`",
        f"- Commit: `{bundle.sha}`",
        f"- Root cause: {summary}",
        "- Safety: existing-file-only policy + targeted/broader validators passed",
        "",
        "### Local replay",
    ]
    lines.extend([f"- `{' '.join(cmd)}`" for cmd in replay])
    return "\n".join(lines)


def resolve_permissions(is_fork: bool, token: str | None) -> GitHubContext:
    """Decide whether pushing is allowed."""
    if is_fork:
        return GitHubContext(False, "fork PR context; report-only mode")
    if not token:
        return GitHubContext(False, "missing token; report-only mode")
    return GitHubContext(True, "push allowed")
