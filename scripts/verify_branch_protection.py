"""Verify GitHub branch protection and required checks are enforced.

This helper fails if the target branch is missing protection, lacks
required status checks, or is not configured to require branches to be
up to date. It reads the repository owner/name from the `GITHUB_REPOSITORY`
environment variable when not provided explicitly and expects an
authentication token from `GITHUB_TOKEN` or `GH_TOKEN`.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, Set

import requests

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"

DEFAULT_REQUIRED_CHECKS = [
    "✅ PR CI / Lint (ruff)",
    "✅ PR CI / Smoke tests",
    "🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.11)",
    "🚀 CI — Insight Demo / 🧹 Ruff + 🏷️ Mypy (3.12)",
    "🚀 CI — Insight Demo / ✅ Actionlint",
    "🚀 CI — Insight Demo / ✅ Pytest (3.11)",
    "🚀 CI — Insight Demo / ✅ Pytest (3.12)",
    "🚀 CI — Insight Demo / Windows Smoke",
    "🚀 CI — Insight Demo / macOS Smoke",
    "🚀 CI — Insight Demo / 📜 MkDocs",
    "🚀 CI — Insight Demo / 📚 Docs Build",
    "🚀 CI — Insight Demo / 🐳 Docker build",
]


def _build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }


def _required_contexts(protection: dict) -> Set[str]:
    contexts: set[str] = set()
    status_checks = protection.get("required_status_checks") or {}
    contexts.update(status_checks.get("contexts") or [])
    for check in status_checks.get("required_check_runs") or []:
        context = check.get("context")
        if context:
            contexts.add(context)
    return contexts


def _parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", help="GitHub repository owner (default: from GITHUB_REPOSITORY)")
    parser.add_argument("--repo", help="GitHub repository name (default: from GITHUB_REPOSITORY)")
    parser.add_argument("--branch", default="main", help="Branch to inspect (default: main)")
    parser.add_argument(
        "--required-check",
        action="append",
        default=None,
        help="Name of a required status check (may be passed multiple times).",
    )
    parser.add_argument(
        "--skip-strict",
        action="store_true",
        help="Allow branch protection without the 'Require branches to be up to date' setting.",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    repo_env = os.environ.get("GITHUB_REPOSITORY", ":").split("/", maxsplit=1)
    owner = args.owner or repo_env[0]
    repo = args.repo or (repo_env[1] if len(repo_env) > 1 else "")

    if not owner or not repo:
        sys.stderr.write("error: unable to determine repository owner/name; set --owner/--repo or GITHUB_REPOSITORY\n")
        return 1

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.stderr.write("error: set GITHUB_TOKEN or GH_TOKEN with access to read branch protection\n")
        return 1

    required_checks = args.required_check or DEFAULT_REQUIRED_CHECKS
    url = f"{API_URL}/repos/{owner}/{repo}/branches/{args.branch}/protection"
    response = requests.get(url, headers=_build_headers(token), timeout=30)
    if response.status_code == 404:
        sys.stderr.write(f"error: branch '{args.branch}' is not protected or not visible\n")
        return 1
    if not response.ok:
        sys.stderr.write(f"error: failed to read protection for {owner}/{repo}@{args.branch}: {response.text}\n")
        return 1

    protection = response.json()
    status_checks = protection.get("required_status_checks")
    if not status_checks:
        sys.stderr.write(f"error: {owner}/{repo}@{args.branch} is missing required status checks\n")
        return 1

    contexts = _required_contexts(protection)
    missing = sorted(set(required_checks) - contexts)
    if missing:
        sys.stderr.write("error: missing required checks:\n")
        for check in missing:
            sys.stderr.write(f"  - {check}\n")
        return 1

    if not args.skip_strict and not status_checks.get("strict", False):
        sys.stderr.write("error: 'Require branches to be up to date' is not enabled\n")
        return 1

    print(
        f"Branch protection verified for {owner}/{repo}@{args.branch}. "
        f"Checks enforced: {', '.join(sorted(contexts))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
