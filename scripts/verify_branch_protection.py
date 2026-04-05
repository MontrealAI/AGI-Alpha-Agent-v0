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
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable, Sequence

API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
GITHUB_ACTIONS_APP_ID = 15368

DEFAULT_REQUIRED_CHECKS = [
    "✅ PR CI / Lint (ruff)",
    "✅ PR CI / Smoke tests",
]
DEFAULT_REQUIRED_CHECKS_PATH = Path("scripts/required_checks.json")


def _build_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
    }


def _api_request(
    method: str,
    url: str,
    token: str,
    *,
    payload: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | None, str]:
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    for key, value in _build_headers(token).items():
        request.add_header(key, value)
    if body is not None:
        request.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            response_body = response.read().decode("utf-8", errors="replace")
            parsed = json.loads(response_body) if response_body else None
            return response.status, parsed if isinstance(parsed, dict) else None, response_body
    except urllib.error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        parsed = None
        if response_body:
            try:
                decoded = json.loads(response_body)
            except json.JSONDecodeError:
                decoded = None
            if isinstance(decoded, dict):
                parsed = decoded
        return exc.code, parsed, response_body


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
    status, _, response_text = _api_request("PATCH", url, token, payload=payload)
    if status == 404:
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
        status, _, response_text = _api_request("PUT", protection_url, token, payload=protection_payload)

    if status < 200 or status >= 300:
        raise RuntimeError(f"failed to enforce required status checks: {status} {response_text}")


def _required_contexts(protection: dict[str, Any]) -> set[str]:
    contexts: set[str] = set()
    status_checks = protection.get("required_status_checks") or {}
    contexts.update(status_checks.get("contexts") or [])
    for check in status_checks.get("required_check_runs") or []:
        context = check.get("context")
        if context:
            contexts.add(context)
    return contexts


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
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
    return parser.parse_args(argv)


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
    args_source = sys.argv[1:] if argv is None else list(argv)
    args = _parse_args(args_source)
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
    status, protection, response_text = _api_request("GET", url, token)
    if status == 403:
        sys.stderr.write("::warning::Missing permission to read branch protection; skipping verification.\n")
        return 0
    if status == 404:
        if not args.apply:
            sys.stderr.write(f"error: branch '{args.branch}' is not protected or not visible\n")
            return 1
        _configure_required_checks(
            owner=owner,
            repo=repo,
            branch=args.branch,
            token=token,
            required_checks=required_checks,
            strict=not args.skip_strict,
        )
        status, protection, response_text = _api_request("GET", url, token)
    if status < 200 or status >= 300 or protection is None:
        sys.stderr.write(f"error: failed to read protection for {owner}/{repo}@{args.branch}: {response_text}\n")
        return 1

    status_checks = protection.get("required_status_checks")
    if not status_checks:
        if not args.apply:
            sys.stderr.write(f"error: {owner}/{repo}@{args.branch} is missing required status checks\n")
            return 1
        _configure_required_checks(
            owner=owner,
            repo=repo,
            branch=args.branch,
            token=token,
            required_checks=required_checks,
            strict=not args.skip_strict,
        )
        _, protection, _ = _api_request("GET", url, token)
        protection = protection or {}
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
        _, protection, _ = _api_request("GET", url, token)
        protection = protection or {}
        contexts = _required_contexts(protection)
        missing = sorted(set(required_checks) - contexts)
        strict_enforced = (protection.get("required_status_checks") or {}).get("strict", False)

    if missing:
        sys.stderr.write("error: missing required checks:\n")
        for check in missing:
            sys.stderr.write(f"  - {check}\n")
        return 1

    if not args.skip_strict and not strict_enforced:
        sys.stderr.write("error: 'Require branches to be up to date' is not enabled\n")
        return 1

    print(
        f"Branch protection verified for {owner}/{repo}@{args.branch}. "
        f"Checks enforced: {', '.join(sorted(contexts))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
