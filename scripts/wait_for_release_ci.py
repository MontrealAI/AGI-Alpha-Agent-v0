#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require historical main-branch CI on the exact release commit."""

from __future__ import annotations

# Exact builtin schema types reject numeric coercion and subclasses (E721 sites below).

import argparse
from collections.abc import Callable
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib.request import Request, urlopen

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

WORKFLOWS = ("ci.yml", "pr-ci.yml", "smoke.yml")
REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
# The integrated workflow has sequential dependency/build/test jobs. A successful
# main run on 2026-10-14 finished after the previous 75-minute polling deadline.
# Keep a finite wait without treating a slow successful run as failed evidence.
WAIT_SECONDS = 120 * 60
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024
QUALIFICATION_JOB = "Full software qualification"
MAX_JOBS = 10_000


def latest_main_run(runs: list[dict[str, Any]], sha: str) -> dict[str, Any] | None:
    """Keep the exact-SHA, main, push selection used by historical acceptance."""
    matching = [
        run
        for run in runs
        if run.get("head_sha") == sha and run.get("head_branch") == "main" and run.get("event") == "push"
    ]
    return max(matching, key=lambda run: int(run["id"])) if matching else None


def assess_runs(runs: list[dict[str, Any]], sha: str) -> bool:
    """Wait for the latest matching push, and reject every unsuccessful result."""
    latest = latest_main_run(runs, sha)
    if latest is None or latest.get("status") != "completed":
        return False
    if latest.get("conclusion") != "success":
        raise RuntimeError(
            f"Required historical CI did not pass: {latest.get('html_url')} ({latest.get('conclusion')})"
        )
    return True


def jobs_endpoint(repository: str, run: dict[str, Any]) -> str:
    """Bind job evidence to one run attempt, not the API's default mixed view."""
    keys = ("id", "run_attempt")
    if repository != REPOSITORY or any(type(run.get(key)) is not int or run[key] <= 0 for key in keys):  # noqa: E721
        raise ValueError("Qualification requires exact positive run and attempt IDs")
    return f"repos/{repository}/actions/runs/{run['id']}/attempts/{run['run_attempt']}/jobs"


def fetch_qualification_jobs(
    repository: str, run: dict[str, Any], read: Callable[[str], dict[str, Any]] | None = None
) -> dict[str, Any]:
    """Fetch every page of the exact attempt; never cherry-pick an older green job."""
    endpoint = jobs_endpoint(repository, run)
    jobs: list[dict[str, Any]] = []
    seen: set[int] = set()
    total: int | None = None
    for page in range(1, MAX_JOBS // 100 + 2):
        if read is None:
            response = subprocess.check_output(
                ["gh", "api", f"{endpoint}?per_page=100&page={page}"],
                text=True,
                timeout=30,
            )
            data = json.loads(response)
        else:
            data = read(f"{endpoint}?per_page=100&page={page}")
        count, rows = data.get("total_count"), data.get("jobs")
        if (
            type(count) is not int  # noqa: E721
            or not 0 <= count <= MAX_JOBS
            or not isinstance(rows, list)
            or len(rows) > 100
            or (total is not None and count != total)
        ):
            raise ValueError("Invalid or changing paginated qualification-job inventory")
        total = count
        for job in rows:
            if (
                not isinstance(job, dict)
                or type(job.get("id")) is not int  # noqa: E721
                or job["id"] <= 0
                or job["id"] in seen
                or type(job.get("run_id")) is not int  # noqa: E721
                or job.get("run_id") != run["id"]
                or job.get("head_sha") != run["head_sha"]
                or type(job.get("run_attempt", run["run_attempt"])) is not int  # noqa: E721
                or job.get("run_attempt", run["run_attempt"]) != run["run_attempt"]
            ):
                raise ValueError("Qualification job is not bound to the requested run, attempt and SHA")
            seen.add(job["id"])
            # The attempt-specific API documents run_id/head_sha, but not always
            # run_attempt. Its exact endpoint binds the latter explicitly here.
            jobs.append(
                {key: job.get(key) for key in ("id", "run_id", "head_sha", "name", "status", "conclusion")}
                | {"run_attempt": run["run_attempt"]}
            )
        if len(jobs) == total:
            return {
                "run_id": run["id"],
                "run_attempt": run["run_attempt"],
                "head_sha": run["head_sha"],
                "endpoint": endpoint,
                "total_count": total,
                "jobs": jobs,
            }
        if len(jobs) > total or not rows:
            raise ValueError("Incomplete paginated qualification-job inventory")
    raise ValueError("Qualification-job pagination exceeds supported bounds")


def validate_qualification(record: Any, run: dict[str, Any], repository: str) -> None:
    """A green paper-scope workflow is never a successful full-runtime gate."""
    if (
        not isinstance(record, dict)
        or type(record.get("run_id")) is not int  # noqa: E721
        or type(record.get("run_attempt")) is not int  # noqa: E721
        or any(
            record.get(key) != expected
            for key, expected in {
                "run_id": run["id"],
                "run_attempt": run["run_attempt"],
                "head_sha": run["head_sha"],
                "endpoint": jobs_endpoint(repository, run),
            }.items()
        )
    ):
        raise ValueError("Qualification evidence differs from the latest exact run, attempt or SHA")
    jobs = record.get("jobs")
    if (
        not isinstance(jobs, list)
        or type(record.get("total_count")) is not int  # noqa: E721
        or record["total_count"] != len(jobs)
        or not 0 <= len(jobs) <= MAX_JOBS
    ):
        raise ValueError("Qualification evidence must retain the complete job inventory")
    seen = set()
    for job in jobs:
        if (
            not isinstance(job, dict)
            or type(job.get("id")) is not int  # noqa: E721
            or job["id"] <= 0
            or job["id"] in seen
            or type(job.get("run_id")) is not int  # noqa: E721
            or job["run_id"] != run["id"]
            or type(job.get("run_attempt")) is not int  # noqa: E721
            or job["run_attempt"] != run["run_attempt"]
            or job.get("head_sha") != run["head_sha"]
        ):
            raise ValueError("Qualification job is not bound to the latest run, attempt and SHA")
        seen.add(job["id"])
    markers = [job for job in jobs if job.get("name") == QUALIFICATION_JOB]
    if len(markers) != 1 or markers[0].get("status") != "completed" or markers[0].get("conclusion") != "success":
        raise RuntimeError("Historical CI requires exactly one completed successful Full software qualification job")


def validate_snapshot(snapshot: Any, sha: str, repository: str, ref: str) -> None:
    """Reject stale, incomplete or candidate evidence before making release assets."""
    if not isinstance(snapshot, dict) or (
        snapshot.get("commit") != sha or snapshot.get("repository") != repository or snapshot.get("ref") != ref
    ):
        raise ValueError("Historical CI evidence does not match the exact repository, commit and ref")
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not ref.startswith("refs/heads/"):
        raise ValueError("Historical CI evidence requires a committed branch context")
    if ref != "refs/heads/main":
        if (
            snapshot.get("required") is not False
            or snapshot.get("workflows") != {}
            or snapshot.get("qualification_jobs", {}) != {}
        ):
            raise ValueError("Branch candidate evidence must explicitly record its non-publishing scope")
        return
    if repository != REPOSITORY or snapshot.get("required") is not True:
        raise ValueError("Main publication requires successful historical CI, not candidate evidence")
    workflows = snapshot.get("workflows")
    if not isinstance(workflows, dict) or set(workflows) != set(WORKFLOWS):
        raise ValueError("Historical CI evidence must contain all three required workflows")
    qualifications = snapshot.get("qualification_jobs")
    if not isinstance(qualifications, dict) or set(qualifications) != set(WORKFLOWS):
        raise ValueError("Historical CI requires full software qualification-job evidence for every workflow")
    for workflow in WORKFLOWS:
        runs = workflows[workflow]
        if not isinstance(runs, list) or any(
            not isinstance(run, dict)
            or not isinstance(run.get("id"), int)
            or isinstance(run["id"], bool)
            or run["id"] <= 0
            or type(run.get("run_attempt")) is not int  # noqa: E721
            or run["run_attempt"] <= 0
            for run in runs
        ):
            raise ValueError(f"Malformed historical CI workflow evidence: {workflow}")
        if any(run.get("path") != f".github/workflows/{workflow}" for run in runs):
            raise ValueError(f"Historical CI workflow identity mismatch: {workflow}")
        if not assess_runs(runs, sha):
            raise ValueError(f"Historical CI evidence is missing a completed successful main push: {workflow}")
        latest = latest_main_run(runs, sha)
        assert latest is not None
        validate_qualification(qualifications[workflow], latest, repository)


def require_historical_evidence(evidence: Path, sha: str) -> dict[str, Any]:
    """Validate the canonical snapshot, failing closed even for local packaging."""
    path = evidence / "historical-ci" / "historical-ci.json"
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError("A bounded historical-ci/historical-ci.json snapshot is required before packaging")
    with path.open("rb") as stream:
        raw = stream.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Historical CI snapshot exceeds the evidence size limit")
    try:
        snapshot = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError("Historical CI evidence is not a valid JSON snapshot") from exc
    if os.getenv("GITHUB_SHA", sha) != sha:
        raise ValueError("The package checkout differs from the historical CI commit")
    validate_snapshot(
        snapshot,
        sha,
        os.getenv("GITHUB_REPOSITORY", REPOSITORY),
        os.getenv("GITHUB_REF", "refs/heads/main"),
    )
    return {key: snapshot[key] for key in ("commit", "repository", "ref", "required")}


def _public_json(endpoint: str) -> dict[str, Any]:
    """Read only fixed public qualification endpoints, without credentials or retries."""
    allowed = (
        rf"repos/{REPOSITORY}/actions/(?:workflows/(?:ci\.yml|pr-ci\.yml|smoke\.yml)/runs"
        r"\?head_sha=[0-9a-f]{40}&per_page=100|runs/[1-9][0-9]*/attempts/[1-9][0-9]*/jobs"
        r"\?per_page=100&page=[1-9][0-9]*)"
    )
    if re.fullmatch(allowed, endpoint) is None:
        raise ValueError("Historical preflight permits only fixed public qualification endpoints")
    request = Request(
        "https://api.github.com/" + endpoint, headers={"User-Agent": "Alpha-historical-release-preflight"}
    )
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise RuntimeError("Historical preflight public API did not return HTTP 200")
        raw = response.read(MAX_SNAPSHOT_BYTES + 1)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError("Historical preflight public response exceeds its bound")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Historical preflight public response must be an object")
    return data


def preflight() -> bool:
    """Reject terminally impossible exact-main evidence once, without accepting pending work."""
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    ref = os.environ["GITHUB_REF"]
    if repo != REPOSITORY or ref != "refs/heads/main" or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Historical preflight requires the authorized exact main commit")
    complete = True
    for workflow in WORKFLOWS:
        data = _public_json(f"repos/{repo}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=100")
        runs = data.get("workflow_runs") if isinstance(data, dict) else None
        if not isinstance(runs, list) or any(
            not isinstance(run, dict)
            or type(run.get("id")) is not int  # noqa: E721
            or run["id"] <= 0
            or type(run.get("run_attempt")) is not int  # noqa: E721
            or run["run_attempt"] <= 0
            or run.get("path") != f".github/workflows/{workflow}"
            or not isinstance(run.get("head_sha"), str)
            or re.fullmatch(r"[0-9a-f]{40}", run["head_sha"]) is None
            or not isinstance(run.get("head_branch"), str)
            or not run["head_branch"]
            or not isinstance(run.get("event"), str)
            or not run["event"]
            for run in runs
        ):
            raise ValueError("Invalid historical preflight workflow inventory")
        if len({run["id"] for run in runs}) != len(runs):
            raise ValueError("Duplicate historical preflight workflow run")
        latest = latest_main_run(runs, sha)
        if latest is None:
            complete = False
            continue
        if latest.get("status") != "completed":
            if (
                latest.get("status") not in {"queued", "in_progress", "requested", "waiting", "pending"}
                or latest.get("conclusion") is not None
            ):
                raise ValueError("Invalid unfinished historical workflow state")
            complete = False
            continue
        assess_runs(runs, sha)
        record = fetch_qualification_jobs(repo, latest, read=_public_json)
        try:
            validate_qualification(record, latest, repo)
        except RuntimeError as error:
            raise RuntimeError(
                f"Historical preflight refuses {workflow} at {sha}: the exact main push has no successful full "
                "software qualification. A paper-only push cannot authorize a software release; qualify a "
                "substantive combined source through the normal main push path."
            ) from error
    if complete:
        print(
            f"Historical preflight found successful full markers for {sha}; final release acceptance is still required"
        )
    else:
        print(
            f"Historical preflight is PENDING for {sha}; no historical acceptance or release authorization is recorded"
        )
    return complete


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--candidate", action="store_true", help="Record a branch-only, non-publishing snapshot")
    mode.add_argument(
        "--preflight", action="store_true", help="Read-only, one-shot rejection of impossible main evidence"
    )
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    ref = os.environ["GITHUB_REF"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Historical release checks require an exact commit")
    if args.preflight:
        preflight()
        return
    output = Path("evidence/historical-ci.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    context = {"commit": sha, "repository": repo, "ref": ref, "required": not args.candidate}
    if args.candidate:
        candidate = {**context, "workflows": {}, "qualification_jobs": {}}
        validate_snapshot(candidate, sha, repo, ref)
        output.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        print("Branch candidate only; publication requires successful historical checks on main")
        return
    if repo != REPOSITORY or ref != "refs/heads/main":
        raise ValueError("Historical release checks require the authorized main commit")
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        snapshots = {}
        qualifications: dict[str, dict[str, Any] | None] = {}
        for workflow in WORKFLOWS:
            response = subprocess.check_output(
                ["gh", "api", f"repos/{repo}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=100"],
                text=True,
                timeout=30,
            )
            snapshots[workflow] = json.loads(response)["workflow_runs"]
            latest = latest_main_run(snapshots[workflow], sha)
            qualifications[workflow] = None
            if latest and latest.get("status") == "completed" and latest.get("conclusion") == "success":
                qualifications[workflow] = fetch_qualification_jobs(repo, latest)
        snapshot = {**context, "workflows": snapshots, "qualification_jobs": qualifications}
        output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        results = [assess_runs(runs, sha) for runs in snapshots.values()]
        for workflow, passed in zip(WORKFLOWS, results):
            if passed:
                latest = latest_main_run(snapshots[workflow], sha)
                assert latest is not None
                validate_qualification(qualifications[workflow], latest, repo)
        if all(results):
            validate_snapshot(snapshot, sha, repo, ref)
            print(f"Historical CI passed for {sha}")
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("Required historical CI did not complete before the release deadline")
        print(f"Waiting for historical CI on {sha}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
