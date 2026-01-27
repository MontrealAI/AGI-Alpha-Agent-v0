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
import base64
import binascii
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping
from urllib.parse import quote

try:
    import yaml
except ImportError:  # pragma: no cover - optional dependency
    yaml = None

API_ROOT = "https://api.github.com"
DEFAULT_WORKFLOWS = (
    "ci.yml",
    "pr-ci.yml",
    "smoke.yml",
    "ci-health.yml",
)


def _github_request(
    url: str,
    token: str | None,
    *,
    retries: int = 2,
    backoff_seconds: float = 1.5,
) -> Mapping[str, object]:
    request = urllib.request.Request(url)
    request.add_header("Accept", "application/vnd.github+json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")

    attempt = 0
    while True:
        try:
            with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
                return json.load(response)
        except urllib.error.HTTPError as exc:
            should_retry = exc.code >= 500
            if attempt >= retries or not should_retry:
                raise
        except urllib.error.URLError:
            if attempt >= retries:
                raise
        attempt += 1
        sleep_for = backoff_seconds * (2 ** (attempt - 1))
        time.sleep(sleep_for)


def _error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="ignore")
    except Exception:  # pragma: no cover - defensive fallback
        return exc.reason
    return f"{exc.reason}: {body}" if body else exc.reason


def _latest_run(
    repo: str,
    workflow: str,
    token: str | None,
    *,
    branch: str | None = None,
) -> Mapping[str, object]:
    url = f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}/runs?per_page=1"
    if branch:
        url = f"{url}&branch={quote(branch)}"
    payload = _github_request(url, token)
    runs = payload.get("workflow_runs") or []
    if not runs:
        raise RuntimeError(f"No runs found for workflow '{workflow}' in repo {repo}")
    return runs[0]


def _can_rerun(run: Mapping[str, object]) -> bool:
    # GitHub omits the rerun URL when a workflow cannot be retried (e.g. pull
    # requests from forks with restricted permissions). Avoid issuing a rerun
    # request in that scenario to prevent noisy 403 responses that obscure the
    # underlying failure.
    return bool(run.get("rerun_url"))


def _rerun_workflow(repo: str, run: Mapping[str, object], token: str | None) -> str:
    if not token:
        return "GITHUB_TOKEN (or GH_TOKEN) is required to rerun workflows"

    if not _can_rerun(run):
        return "rerun not supported for this workflow run (missing rerun_url)"

    run_id = run.get("id")
    if not run_id:
        return "run is missing an id; cannot rerun"

    url = f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}/rerun"
    request = urllib.request.Request(url, method="POST")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(request, timeout=30):  # noqa: S310
            return "dispatched"
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        detail = _error_detail(exc)

        # GitHub returns 403 for runs that explicitly disallow retries (for
        # example, runs from forks without sufficient permissions). Treat this
        # as a terminal condition rather than attempting to rerun failed jobs,
        # which would trigger the same error and add noise to the logs.
        if exc.code == 403 and "cannot be retried" in detail:
            return f"rerun forbidden (HTTP 403): {detail}"

        fallback = _rerun_failed_jobs(repo, run_id, token)
        if fallback == "dispatched":
            return "dispatched failed jobs"
        return f"HTTP {exc.code}: {detail}; failed jobs rerun attempt → {fallback}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return f"network error: {exc.reason}"


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


def _workflow_filename_from_env(token: str | None = None) -> str | None:
    """Return the workflow filename for the current run if available.

    GitHub exposes ``GITHUB_WORKFLOW_REF`` for reusable workflows, but this
    variable is not always populated for standard runs. Fall back to scanning
    ``.github/workflows`` for a file whose ``name`` matches ``GITHUB_WORKFLOW``
    so the health check can reliably skip the workflow that invoked it.
    """
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if token and repo and run_id:
        try:
            payload = _github_request(f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}", token)
            path = payload.get("path")
            if isinstance(path, str):
                return Path(path).name
        except urllib.error.HTTPError:
            # Best effort only; fall back to scanning the workflow files.
            pass
        except urllib.error.URLError:
            pass

    workflow_ref = os.environ.get("GITHUB_WORKFLOW_REF")
    if workflow_ref:
        _, _, workflow_with_ref = workflow_ref.partition("/.github/workflows/")
        if workflow_with_ref:
            workflow, _, _ = workflow_with_ref.partition("@")
            if workflow:
                return workflow

    workflow_name = os.environ.get("GITHUB_WORKFLOW")
    if not workflow_name:
        return None

    workflow_dir = Path(".github/workflows")
    workflow_files = list(workflow_dir.glob("*.yml")) + list(workflow_dir.glob("*.yaml"))
    for workflow_file in workflow_files:
        try:
            raw = workflow_file.read_text(encoding="utf-8")
            if yaml is None:
                continue
            parsed = yaml.safe_load(raw) or {}
        except (OSError, yaml.YAMLError):  # pragma: no cover - best effort fallback
            continue

        if parsed.get("name") == workflow_name:
            return workflow_file.name

    return None


def _event_indicates_fork(repo: str) -> bool:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return False

    try:
        payload = json.loads(Path(event_path).read_text(encoding="utf-8"))
    except OSError:
        return False
    except json.JSONDecodeError:
        return False

    def _head_repo_full_name(data: Mapping[str, object]) -> str | None:
        head = data.get("head") if isinstance(data, dict) else None
        repo_data = head.get("repo") if isinstance(head, dict) else None
        full_name = repo_data.get("full_name") if isinstance(repo_data, dict) else None
        if isinstance(full_name, str):
            return full_name
        return None

    pull_request = payload.get("pull_request")
    if isinstance(pull_request, dict):
        head_full_name = _head_repo_full_name(pull_request)
        if head_full_name and head_full_name != repo:
            return True

    workflow_run = payload.get("workflow_run")
    if isinstance(workflow_run, dict):
        head_repo = workflow_run.get("head_repository")
        if isinstance(head_repo, dict):
            head_full_name = head_repo.get("full_name")
            if isinstance(head_full_name, str) and head_full_name != repo:
                return True
        pull_requests = workflow_run.get("pull_requests")
        if isinstance(pull_requests, list) and pull_requests:
            first_pr = pull_requests[0]
            if isinstance(first_pr, dict):
                head_full_name = _head_repo_full_name(first_pr)
                if head_full_name and head_full_name != repo:
                    return True

    return False


def _actions_write_capability(repo: str, token: str | None) -> tuple[bool, str]:
    if not token:
        return False, "missing token"
    if _event_indicates_fork(repo):
        return False, "fork pull request context"

    try:
        payload = _github_request(f"{API_ROOT}/repos/{repo}", token)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        return False, f"HTTP {exc.code}: {_error_detail(exc)}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return False, f"network error: {exc.reason}"

    permissions = payload.get("permissions")
    if isinstance(permissions, dict):
        can_write = any(permissions.get(key) for key in ("admin", "maintain", "push"))
        if not can_write:
            return False, "token has read-only repository permissions"

    return True, "token has repository write permissions"


def _workflow_events(repo: str, workflow: str, token: str | None) -> tuple[set[str] | None, str | None]:
    """Return the triggers configured for *workflow*.

    The workflow metadata endpoint omits the ``events`` list, so fall back to
    parsing the workflow file when the events cannot be read directly. A
    ``None`` return value indicates the events are unknown (not that there are
    no events).
    """

    url = f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}"
    try:
        payload = _github_request(url, token)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        return None, f"HTTP {exc.code}: {_error_detail(exc)}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return None, f"network error: {exc.reason}"

    events = payload.get("events")
    if events:
        return set(events), None

    path = payload.get("path")
    if not path:
        return None, "workflow metadata does not include a path"

    content_url = f"{API_ROOT}/repos/{repo}/contents/{path}"
    try:
        file_payload = _github_request(content_url, token)
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        return None, f"HTTP {exc.code} while reading workflow file: {_error_detail(exc)}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return None, f"network error while reading workflow file: {exc.reason}"

    content = file_payload.get("content")
    if not content or file_payload.get("encoding") != "base64":
        return None, "workflow content is missing or not base64 encoded"

    try:
        decoded = base64.b64decode(content).decode("utf-8")
    except (UnicodeDecodeError, ValueError, binascii.Error):
        return None, "unable to decode workflow content"

    if "workflow_dispatch" in decoded:
        return {"workflow_dispatch"}, None

    return set(), None


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
        return False, f"HTTP {exc.code}: {_error_detail(exc)}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return False, f"network error: {exc.reason}"


def _rerun_failed_jobs(repo: str, run_id: int, token: str | None) -> str:
    url = f"{API_ROOT}/repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs"
    request = urllib.request.Request(url, method="POST")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=30):  # noqa: S310
            return "dispatched"
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        return f"HTTP {exc.code}: {_error_detail(exc)}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return f"network error: {exc.reason}"


def _dispatch_workflow(repo: str, workflow: str, ref: str, token: str | None) -> tuple[bool, str]:
    if not token:
        return False, "GITHUB_TOKEN (or GH_TOKEN) is required to dispatch workflows"

    events, error = _workflow_events(repo, workflow, token)
    if error:
        return False, f"unable to read workflow events: {error}"
    if events is not None and "workflow_dispatch" not in events:
        return False, "workflow_dispatch trigger is not defined"

    url = f"{API_ROOT}/repos/{repo}/actions/workflows/{workflow}/dispatches"
    request = urllib.request.Request(url, method="POST")
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Accept", "application/vnd.github+json")
    request.add_header("Content-Type", "application/json")
    body = json.dumps({"ref": ref}).encode("utf-8")
    try:
        with urllib.request.urlopen(request, body, timeout=30):  # noqa: S310
            return True, f"dispatched on ref '{ref}'"
    except urllib.error.HTTPError as exc:  # pragma: no cover - network paths
        message = _error_detail(exc)
        if exc.code == 422 and "workflow_dispatch" in message:
            message = (
                "workflow is not dispatchable (missing workflow_dispatch); "
                "enable manual dispatch in the workflow triggers"
            )
        return False, f"HTTP {exc.code}: {message}"
    except urllib.error.URLError as exc:  # pragma: no cover - network paths
        return False, f"network error: {exc.reason}"


def _workflow_supports_dispatch(workflow: str) -> bool:
    path = Path(".github/workflows") / workflow
    if not path.exists():
        return False

    try:
        content = path.read_text()
    except OSError:
        return False

    if yaml is None:
        return "workflow_dispatch" in content

    config = yaml.safe_load(content) or {}

    triggers = config.get("on")
    if triggers is None:
        return False

    if isinstance(triggers, str):
        return triggers == "workflow_dispatch"

    if isinstance(triggers, list):
        return "workflow_dispatch" in triggers

    if isinstance(triggers, dict):
        return "workflow_dispatch" in triggers

    return False


def _format_failure(run: Mapping[str, object], workflow: str, *, age_seconds: float | None) -> str:
    conclusion = run.get("conclusion") or run.get("status")
    html_url = run.get("html_url", "<missing url>")
    branch = run.get("head_branch", "<unknown branch>")
    sha = run.get("head_sha", "<unknown sha>")
    age_hint = ""
    if age_seconds is not None:
        age_hint = f" age={age_seconds / 60:.1f}m"
    return f"{workflow}: {conclusion}{age_hint} (branch={branch} sha={sha})\n  {html_url}"


def verify_workflows(
    repo: str,
    workflows: Iterable[str],
    token: str | None,
    *,
    branch: str | None = None,
    wait_seconds: float = 0,
    poll_interval: float = 15,
    pending_grace_seconds: float = 0,
    rerun_failed: bool = False,
    skip_run_id: int | None = None,
) -> tuple[list[str], dict[str, Mapping[str, object]]]:
    failures: list[str] = []
    runs: dict[str, Mapping[str, object]] = {}
    remaining = wait_seconds

    rerun_attempts: dict[str, str] = {}

    while True:
        failures.clear()
        runs.clear()
        waiting = False
        now = datetime.now(timezone.utc)

        for workflow in workflows:
            try:
                run = _latest_run(repo, workflow, token, branch=branch)
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

            if rerun_failed and conclusion in {"failure", "timed_out", "cancelled"}:
                rerun_status = rerun_attempts.get(workflow)
                if not rerun_status:
                    if skip_run_id is not None and run.get("id") == skip_run_id:
                        rerun_status = "skipped current run"
                    elif _can_rerun(run):
                        rerun_status = _rerun_workflow(repo, run, token)
                    else:
                        rerun_status = "rerun not supported"
                    rerun_attempts[workflow] = rerun_status
                    dispatched = rerun_status == "dispatched"
                    outcome = "rerun requested" if dispatched else "rerun skipped"
                    icon = "🔁" if dispatched else "⚠️"
                    print(f"{icon} {workflow} → {outcome} ({rerun_status})")

                if rerun_status == "dispatched":
                    waiting = True
                    remaining = max(remaining, poll_interval)
                    continue

            is_pending = status in {"queued", "in_progress", "pending"}
            within_grace = age_seconds is None or age_seconds <= pending_grace_seconds

            if is_pending and (remaining > 0 or within_grace):
                waiting = True
                grace_hint = "within grace" if within_grace else f"waiting {remaining:.0f}s"
                age_hint = "age=?" if age_seconds is None else f"age={age_seconds / 60:.1f}m"
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
            "Treat queued/pending runs younger than this many minutes as acceptable even if they have not finished yet"
        ),
    )
    parser.add_argument(
        "--rerun-failed",
        action="store_true",
        help=(
            "Automatically rerun the most recent failed workflow run using GITHUB_TOKEN (or GH_TOKEN) when available."
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
        "--read-only",
        action="store_true",
        help="Disable mutation operations (rerun, cancel, dispatch) regardless of token permissions.",
    )
    parser.add_argument(
        "--ref",
        default=os.environ.get("GITHUB_REF_NAME", "main"),
        help="Git ref to use when dispatching workflows (default: main)",
    )
    parser.add_argument(
        "--branch",
        help=("Branch to evaluate workflow health for. Defaults to $GITHUB_REF_NAME when available, otherwise 'main'."),
    )
    args = parser.parse_args(argv)

    token = (
        args.token
        or os.environ.get("ADMIN_GITHUB_TOKEN")
        or os.environ.get("GITHUB_TOKEN")
        or os.environ.get("GH_TOKEN")
    )
    workflows = list(args.workflows or DEFAULT_WORKFLOWS)
    current_workflow = _workflow_filename_from_env(token)
    if not args.workflows and current_workflow:
        workflows = [wf for wf in workflows if wf != current_workflow]
    branch = args.branch or os.environ.get("GITHUB_REF_NAME") or "main"
    wait_seconds = max(0.0, args.wait_minutes * 60)
    if args.once:
        args.pending_grace_minutes = 0
        wait_seconds = 0
    poll_interval = max(1.0, args.poll_seconds)

    actions_write_allowed, actions_reason = _actions_write_capability(args.repo, token)
    if args.read_only:
        actions_write_allowed = False
        actions_reason = "forced read-only mode"

    if args.rerun_failed or args.cancel_stale or args.dispatch_missing:
        if not actions_write_allowed:
            print(
                f"⚠️ actions write operations disabled ({actions_reason}); running in read-only mode.",
                flush=True,
            )
            args.rerun_failed = False
            args.cancel_stale = False
            args.dispatch_missing = False

    failures, runs = verify_workflows(
        args.repo,
        workflows,
        token,
        branch=branch,
        wait_seconds=wait_seconds,
        poll_interval=poll_interval,
        pending_grace_seconds=max(0.0, args.pending_grace_minutes * 60),
        rerun_failed=args.rerun_failed,
        skip_run_id=int(os.environ.get("GITHUB_RUN_ID", "0") or 0) or None,
    )

    stale_cancelled: set[str] = set()
    current_run_id = int(os.environ.get("GITHUB_RUN_ID", "0") or 0) or None
    if args.cancel_stale and runs:
        stale_threshold = max(0.0, args.stale_minutes * 60)
        for workflow, run in runs.items():
            if current_run_id is not None and run.get("id") == current_run_id:
                print(f"⚠️ skip cancel for current run {current_run_id}")
                continue
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
            if not _workflow_supports_dispatch(workflow):
                print(f"⚠️ dispatch {workflow}: workflow_dispatch not configured; skipping")
                continue

            ok, message = _dispatch_workflow(args.repo, workflow, args.ref, token)
            outcome = "✅" if ok else "❌"
            print(f"{outcome} dispatch {workflow}: {message}")
            if ok:
                dispatched.add(workflow)

    if stale_cancelled or dispatched:
        # If remediation occurred, re-evaluate so we emit updated status for
        # newly dispatched runs or cancelled stale runs. Previous failures may
        # have been addressed by remediation, so refresh the state regardless of
        # whether the initial pass reported issues.
        failures, runs = verify_workflows(
            args.repo,
            workflows,
            token,
            branch=branch,
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
