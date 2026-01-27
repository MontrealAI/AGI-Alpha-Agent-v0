"""Verify GitHub branch protection and required checks are enforced.

This helper fails if the target branch is missing protection, lacks
required status checks, or is not configured to require branches to be
up to date. It reads the repository owner/name from the `GITHUB_REPOSITORY`
environment variable when not provided explicitly and expects an
authentication token from `GITHUB_TOKEN` or `GH_TOKEN`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

import requests

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
GITHUB_ACTIONS_APP_ID = 15368

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
    "🚀 CI — Insight Demo / 📦 Deploy",
    "🚀 CI — Insight Demo / 🔒 Branch protection guardrails",
    "🩺 CI Health / CI watchdog",
]
DEFAULT_REQUIRED_CHECKS_PATH = Path("scripts/required_checks.json")


def _build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }


def _configure_required_checks(
    *,
    owner: str,
    repo: str,
    branch: str,
    token: str,
    required_checks: Iterable[str],
    strict: bool,
) -> None:
    url = f"{API_URL}/repos/{owner}/{repo}/branches/{branch}/protection/required_status_checks"
    payload = {
        "strict": strict,
        "checks": [
            {
                "context": context,
                # All required checks currently originate from GitHub Actions, which
                # must be identified by app_id when configuring required_check_runs.
                "app_id": GITHUB_ACTIONS_APP_ID,
            }
            for context in required_checks
        ],
    }
    response = requests.patch(url, headers=_build_headers(token), json=payload, timeout=30)
    if response.status_code == 404:
        # Branch protection may be disabled entirely; fall back to enabling it with
        # the expected required checks so future queries succeed.
        protection_url = f"{API_URL}/repos/{owner}/{repo}/branches/{branch}/protection"
        protection_payload = {
            "required_status_checks": payload,
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "dismiss_stale_reviews": True,
                "require_code_owner_reviews": False,
            },
            "restrictions": None,
            "allow_force_pushes": False,
            "allow_deletions": False,
            "block_creations": False,
            "required_linear_history": False,
            "allow_fork_syncing": True,
            "required_conversation_resolution": True,
            "lock_branch": False,
        }
        response = requests.put(
            protection_url,
            headers=_build_headers(token),
            json=protection_payload,
            timeout=30,
        )

    if not response.ok:
        raise RuntimeError("failed to enforce required status checks: " f"{response.status_code} {response.text}")


def _required_contexts(protection: dict) -> set[str]:
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
        "--required-checks-file",
        help=(
            "Path to a JSON file containing required check names. "
            "When omitted, scripts/required_checks.json is used if present."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Automatically enforce the expected branch protection status checks when"
            " they are missing or misconfigured."
        ),
    )
    parser.add_argument(
        "--skip-strict",
        action="store_true",
        help="Allow branch protection without the 'Require branches to be up to date' setting.",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Emit warnings instead of failing when branch protection is missing or incomplete.",
    )
    return parser.parse_args(argv)


def _warn_or_error(message: str, warn_only: bool) -> int:
    if warn_only:
        sys.stderr.write(f"::warning::{message}\n")
        return 0
    sys.stderr.write(f"error: {message}\n")
    return 1


def _load_required_checks(path: Path) -> list[str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise RuntimeError(f"unable to read required checks file: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid required checks JSON: {exc}") from exc

    if isinstance(payload, list) and all(isinstance(item, str) for item in payload):
        return payload
    raise RuntimeError("required checks JSON must be a list of strings")


def main(argv: Iterable[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    repo_env = os.environ.get("GITHUB_REPOSITORY", ":").split("/", maxsplit=1)
    owner = args.owner or repo_env[0]
    repo = args.repo or (repo_env[1] if len(repo_env) > 1 else "")

    if not owner or not repo:
        sys.stderr.write("error: unable to determine repository owner/name; set --owner/--repo or GITHUB_REPOSITORY\n")
        return 1

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.stderr.write("::warning::No GitHub token available; skipping branch protection verification.\n")
        return 0

    required_checks: list[str] = []
    if args.required_check:
        required_checks = list(args.required_check)
    else:
        checks_path = Path(args.required_checks_file) if args.required_checks_file else DEFAULT_REQUIRED_CHECKS_PATH
        if checks_path.exists():
            required_checks = _load_required_checks(checks_path)
        else:
            required_checks = list(DEFAULT_REQUIRED_CHECKS)

    if not required_checks:
        sys.stderr.write("error: required checks list is empty; provide --required-check or a checks file\n")
        return 1
    url = f"{API_URL}/repos/{owner}/{repo}/branches/{args.branch}/protection"
    response = requests.get(url, headers=_build_headers(token), timeout=30)
    if response.status_code == 403:
        sys.stderr.write("::warning::Missing permission to read branch protection; skipping verification.\n")
        return 0
    if response.status_code == 404:
        if not args.apply:
            return _warn_or_error(
                f"branch '{args.branch}' is not protected or not visible",
                args.warn_only,
            )
        _configure_required_checks(
            owner=owner,
            repo=repo,
            branch=args.branch,
            token=token,
            required_checks=required_checks,
            strict=not args.skip_strict,
        )
        response = requests.get(url, headers=_build_headers(token), timeout=30)
    if not response.ok:
        return _warn_or_error(
            f"failed to read protection for {owner}/{repo}@{args.branch}: {response.text}",
            args.warn_only,
        )

    protection = response.json()

    status_checks = protection.get("required_status_checks")
    if not status_checks:
        if not args.apply:
            return _warn_or_error(
                f"{owner}/{repo}@{args.branch} is missing required status checks",
                args.warn_only,
            )
        _configure_required_checks(
            owner=owner,
            repo=repo,
            branch=args.branch,
            token=token,
            required_checks=required_checks,
            strict=not args.skip_strict,
        )
        protection = requests.get(url, headers=_build_headers(token), timeout=30).json()
        status_checks = protection.get("required_status_checks") or {}

    contexts = _required_contexts(protection)
    missing = sorted(set(required_checks) - contexts)
    strict_enforced = status_checks.get("strict", False)

    if (missing or (not args.skip_strict and not strict_enforced)) and args.apply:
        _configure_required_checks(
            owner=owner,
            repo=repo,
            branch=args.branch,
            token=token,
            required_checks=required_checks,
            strict=not args.skip_strict,
        )
        protection = requests.get(url, headers=_build_headers(token), timeout=30).json()
        contexts = _required_contexts(protection)
        missing = sorted(set(required_checks) - contexts)
        strict_enforced = protection.get("required_status_checks", {}).get("strict", False)

    if missing:
        missing_message = "missing required checks:\n" + "\n".join(f"  - {check}" for check in missing)
        return _warn_or_error(missing_message, args.warn_only)

    if not args.skip_strict and not strict_enforced:
        return _warn_or_error("'Require branches to be up to date' is not enabled", args.warn_only)

    print(
        f"Branch protection verified for {owner}/{repo}@{args.branch}. "
        f"Checks enforced: {', '.join(sorted(contexts))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
