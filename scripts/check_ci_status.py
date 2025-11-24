"""Quick status checker for GitHub Actions workflows.

Fetches the latest run for each workflow and exits non-zero when any
workflow is missing, pending or failed. Useful for keeping CI badges
and branch protections green.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Iterable, Mapping

API_ROOT = "https://api.github.com"
DEFAULT_WORKFLOWS = (
    "ci.yml",
    "pr-ci.yml",
    "smoke.yml",
)


def _github_request(url: str, token: str | None) -> Mapping[str, object]:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        return json.load(response)


def _latest_run(repo: str, workflow: str, token: str | None) -> Mapping[str, object]:
    url = f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}/runs?per_page=1"
    payload = _github_request(url, token)
    runs = payload.get("workflow_runs") or []
    if not runs:
        raise RuntimeError(f"No runs found for workflow '{workflow}' in repo {repo}")
    return runs[0]


def _format_failure(run: Mapping[str, object], workflow: str) -> str:
    conclusion = run.get("conclusion") or run.get("status")
    html_url = run.get("html_url", "<missing url>")
    branch = run.get("head_branch", "<unknown branch>")
    sha = run.get("head_sha", "<unknown sha>")
    return (
        f"{workflow}: {conclusion} (branch={branch} sha={sha})\n"
        f"  {html_url}"
    )


def verify_workflows(
    repo: str,
    workflows: Iterable[str],
    token: str | None,
    *,
    wait_seconds: float = 0,
    poll_interval: float = 15,
) -> list[str]:
    failures: list[str] = []
    for workflow in workflows:
        start = time.monotonic()
        remaining = wait_seconds

        while True:
            try:
                run = _latest_run(repo, workflow, token)
            except (urllib.error.URLError, RuntimeError, json.JSONDecodeError) as exc:  # noqa: PERF203
                hint = ""
                if isinstance(exc, urllib.error.HTTPError):
                    status = exc.code
                    if status == 403:
                        hint = " (set GITHUB_TOKEN to raise the rate limit)"
                    elif status == 401:
                        hint = " (check that GITHUB_TOKEN is valid for the target repo)"
                failures.append(f"{workflow}: error fetching latest run: {exc}{hint}")
                break

            conclusion = run.get("conclusion")
            status = run.get("status")

            if conclusion == "success":
                print(f"✅ {workflow} → success ({status})")
                break

            if status in {"queued", "in_progress"} and remaining > 0:
                sleep_for = min(poll_interval, remaining)
                print(
                    f"⏳ {workflow} → {status} (waiting up to {remaining:.0f}s more)",
                    flush=True,
                )
                time.sleep(sleep_for)
                elapsed = time.monotonic() - start
                remaining = max(0.0, wait_seconds - elapsed)
                continue

            failures.append(_format_failure(run, workflow))
            break
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", "MontrealAI/AGI-Alpha-Agent-v0"),
        help="GitHub repository in <owner>/<repo> format",
    )
    parser.add_argument(
        "--workflow",
        "--workflows",
        action="append",
        dest="workflows",
        metavar="NAME",
        help="Workflow filename to validate (may be provided multiple times)",
    )
    parser.add_argument(
        "--wait-minutes",
        type=float,
        default=0,
        help="Wait for queued/in-progress runs to settle for up to N minutes before failing",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=15,
        help="Polling interval when waiting for workflows to finish",
    )
    args = parser.parse_args(argv)

    workflows = args.workflows or DEFAULT_WORKFLOWS
    token = os.environ.get("GITHUB_TOKEN")
    wait_seconds = max(0.0, args.wait_minutes * 60)
    poll_interval = max(1.0, args.poll_seconds)

    failures = verify_workflows(
        args.repo,
        workflows,
        token,
        wait_seconds=wait_seconds,
        poll_interval=poll_interval,
    )
    if failures:
        print("\nFound non-green workflows:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
