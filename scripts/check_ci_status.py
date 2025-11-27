"""Quick status checker for GitHub Actions workflows.

Fetches the latest run for each workflow and exits non-zero when any
workflow is missing, pending or failed. Useful for keeping CI badges
and branch protections green.

Optional remediation flags cancel stale pending runs and re-dispatch workflows
using ``GITHUB_TOKEN`` so badges recover automatically. Provide a grace period
for in-flight runs to avoid failing while CI is still progressing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Iterable, Mapping

API_ROOT = "https://api.github.com"
DEFAULT_WORKFLOWS = (
    "ci.yml",
    "pr-ci.yml",
    "smoke.yml",
    "ci-health.yml",
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


def _iso_to_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _run_age_seconds(run: Mapping[str, object], *, now: datetime | None = None) -> float | None:
    current = now or datetime.now(timezone.utc)
    created_at = _iso_to_datetime(run.get("created_at"))
    if not created_at:
        return None
    age = (current - created_at).total_seconds()
    # Guard against clock skew or malformed timestamps in the future.
    return max(0.0, age)


def _cancel_run(repo: str, run_id: int, token: str | None) -> tuple[bool, str]:
    if not token:
        return False, "GITHUB_TOKEN (or GH_TOKEN) is required to cancel runs"
    url = f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}/cancel"
    request = urllib.request.Request(url, method="POST")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    try:
        with urllib.request.urlopen(request, timeout=30):  # noqa: S310
            return True, "cancelled"
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        return False, f"HTTP {exc.code}: {exc.reason}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return False, f"network error: {exc.reason}"


def _dispatch_workflow(repo: str, workflow: str, ref: str, token: str | None) -> tuple[bool, str]:
    if not token:
        return False, "GITHUB_TOKEN (or GH_TOKEN) is required to dispatch workflows"
    url = f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}/dispatches"
    request = urllib.request.Request(url, method="POST")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    body = json.dumps({"ref": ref}).encode("utf-8")
    try:
        with urllib.request.urlopen(request, body, timeout=30):  # noqa: S310
            return True, f"dispatched on ref '{ref}'"
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        return False, f"HTTP {exc.code}: {exc.reason}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return False, f"network error: {exc.reason}"


def _format_failure(run: Mapping[str, object], workflow: str, *, age_seconds: float | None) -> str:
    conclusion = run.get("conclusion") or run.get("status")
    html_url = run.get("html_url", "<missing url>")
    branch = run.get("head_branch", "<unknown branch>")
    sha = run.get("head_sha", "<unknown sha>")
    age_hint = ""
    if age_seconds is not None:
        age_hint = f" age={age_seconds/60:.1f}m"
    return f"{workflow}: {conclusion}{age_hint} (branch={branch} sha={sha})\n" f"  {html_url}"


def verify_workflows(
    repo: str,
    workflows: Iterable[str],
    token: str | None,
    *,
    wait_seconds: float = 0,
    poll_interval: float = 15,
    pending_grace_seconds: float = 0,
) -> tuple[list[str], dict[str, Mapping[str, object]]]:
    failures: list[str] = []
    runs: dict[str, Mapping[str, object]] = {}
    remaining = wait_seconds

    while True:
        failures.clear()
        runs.clear()
        waiting = False
        now = datetime.now(timezone.utc)

        for workflow in workflows:
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
                continue

            runs[workflow] = run
            conclusion = run.get("conclusion")
            status = run.get("status")
            age_seconds = _run_age_seconds(run, now=now)

            if conclusion == "success":
                print(f"✅ {workflow} → success ({status})")
                continue

            is_pending = status in {"queued", "in_progress", "pending"}
            within_grace = age_seconds is None or age_seconds <= pending_grace_seconds

            if is_pending and (remaining > 0 or within_grace):
                waiting = True
                grace_hint = "within grace" if within_grace else f"waiting {remaining:.0f}s"
                age_hint = "age=?" if age_seconds is None else f"age={age_seconds/60:.1f}m"
                print(f"⏳ {workflow} → {status} ({age_hint}, {grace_hint})", flush=True)
                continue

            failures.append(_format_failure(run, workflow, age_seconds=age_seconds))

        if waiting and remaining > 0:
            sleep_for = min(poll_interval, remaining)
            time.sleep(sleep_for)
            remaining = max(0.0, remaining - sleep_for)
            continue
        break

    return failures, runs


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
        "--token",
        help=(
            "Personal access token to raise rate limits and allow dispatch/cancel operations; "
            "falls back to GITHUB_TOKEN or GH_TOKEN when omitted"
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help=(
            "Check the latest runs once with zero grace period."
            " Equivalent to --wait-minutes 0 --pending-grace-minutes 0 so pending"
            " runs fail fast instead of waiting."
        ),
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=15,
        help="Polling interval when waiting for workflows to finish",
    )
    parser.add_argument(
        "--pending-grace-minutes",
        type=float,
        default=0,
        help=(
            "Treat queued/pending runs younger than this many minutes as acceptable even if "
            "they have not finished yet"
        ),
    )
    parser.add_argument(
        "--stale-minutes",
        type=float,
        default=120,
        help="Age threshold for cancelling pending runs when --cancel-stale is set",
    )
    parser.add_argument(
        "--cancel-stale",
        action="store_true",
        help="Cancel queued/pending runs older than --stale-minutes using GITHUB_TOKEN",
    )
    parser.add_argument(
        "--dispatch-missing",
        action="store_true",
        help="Dispatch workflows that are missing or not green using GITHUB_TOKEN",
    )
    parser.add_argument(
        "--ref",
        default=os.environ.get("GITHUB_REF_NAME", "main"),
        help="Git ref to use when dispatching workflows (default: main)",
    )
    args = parser.parse_args(argv)

    workflows = args.workflows or DEFAULT_WORKFLOWS
    token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    wait_seconds = max(0.0, args.wait_minutes * 60)
    if args.once:
        args.pending_grace_minutes = 0
        wait_seconds = 0
    poll_interval = max(1.0, args.poll_seconds)

    failures, runs = verify_workflows(
        args.repo,
        workflows,
        token,
        wait_seconds=wait_seconds,
        poll_interval=poll_interval,
        pending_grace_seconds=max(0.0, args.pending_grace_minutes * 60),
    )

    stale_cancelled: set[str] = set()
    if args.cancel_stale and runs:
        stale_threshold = max(0.0, args.stale_minutes * 60)
        for workflow, run in runs.items():
            age_seconds = _run_age_seconds(run)
            status = run.get("status")
            if status not in {"queued", "in_progress", "pending"}:
                continue
            if age_seconds is None or age_seconds < stale_threshold:
                continue
            ok, message = _cancel_run(args.repo, int(run["id"]), token)
            outcome = "✅" if ok else "❌"
            print(f"{outcome} cancel {workflow} run {run['id']}: {message}")
            if ok:
                stale_cancelled.add(workflow)

    failed_workflows = {wf for wf in workflows if wf not in runs or runs[wf].get("conclusion") != "success"}

    dispatched: set[str] = set()
    if args.dispatch_missing and failed_workflows:
        for workflow in failed_workflows:
            ok, message = _dispatch_workflow(args.repo, workflow, args.ref, token)
            outcome = "✅" if ok else "❌"
            print(f"{outcome} dispatch {workflow}: {message}")
            if ok:
                dispatched.add(workflow)

    if (stale_cancelled or dispatched) and not failures:
        # If remediation occurred and no prior failures, re-evaluate so we emit
        # updated status for newly dispatched runs.
        failures, runs = verify_workflows(
            args.repo,
            workflows,
            token,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
            pending_grace_seconds=max(0.0, args.pending_grace_minutes * 60),
        )

    if failures:
        print("\nFound non-green workflows:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
