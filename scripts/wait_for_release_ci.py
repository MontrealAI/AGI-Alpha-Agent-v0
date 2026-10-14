#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require historical main-branch CI on the exact release commit."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

WORKFLOWS = ("ci.yml", "pr-ci.yml", "smoke.yml")
REPOSITORY = "MontrealAI/AGI-Alpha-Agent-v0"
WAIT_SECONDS = 75 * 60
MAX_SNAPSHOT_BYTES = 8 * 1024 * 1024


def assess_runs(runs: list[dict[str, Any]], sha: str) -> bool:
    """Wait for the latest matching push, and reject every unsuccessful result."""
    matching = [
        run
        for run in runs
        if run.get("head_sha") == sha and run.get("head_branch") == "main" and run.get("event") == "push"
    ]
    if not matching:
        return False
    latest = max(matching, key=lambda run: int(run["id"]))
    if latest.get("status") != "completed":
        return False
    if latest.get("conclusion") != "success":
        raise RuntimeError(
            f"Required historical CI did not pass: {latest.get('html_url')} ({latest.get('conclusion')})"
        )
    return True


def validate_snapshot(snapshot: Any, sha: str, repository: str, ref: str) -> None:
    """Reject stale, incomplete or candidate evidence before making release assets."""
    if not isinstance(snapshot, dict) or (
        snapshot.get("commit") != sha or snapshot.get("repository") != repository or snapshot.get("ref") != ref
    ):
        raise ValueError("Historical CI evidence does not match the exact repository, commit and ref")
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or not ref.startswith("refs/heads/"):
        raise ValueError("Historical CI evidence requires a committed branch context")
    if ref != "refs/heads/main":
        if snapshot.get("required") is not False or snapshot.get("workflows") != {}:
            raise ValueError("Branch candidate evidence must explicitly record its non-publishing scope")
        return
    if repository != REPOSITORY or snapshot.get("required") is not True:
        raise ValueError("Main publication requires successful historical CI, not candidate evidence")
    workflows = snapshot.get("workflows")
    if not isinstance(workflows, dict) or set(workflows) != set(WORKFLOWS):
        raise ValueError("Historical CI evidence must contain all three required workflows")
    for workflow in WORKFLOWS:
        runs = workflows[workflow]
        if not isinstance(runs, list) or any(
            not isinstance(run, dict)
            or not isinstance(run.get("id"), int)
            or isinstance(run["id"], bool)
            or run["id"] <= 0
            for run in runs
        ):
            raise ValueError(f"Malformed historical CI workflow evidence: {workflow}")
        if any(run.get("path") != f".github/workflows/{workflow}" for run in runs):
            raise ValueError(f"Historical CI workflow identity mismatch: {workflow}")
        if not assess_runs(runs, sha):
            raise ValueError(f"Historical CI evidence is missing a completed successful main push: {workflow}")


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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="store_true", help="Record a branch-only, non-publishing snapshot")
    args = parser.parse_args()
    repo = os.environ["GITHUB_REPOSITORY"]
    sha = os.environ["GITHUB_SHA"]
    ref = os.environ["GITHUB_REF"]
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Historical release checks require an exact commit")
    output = Path("evidence/historical-ci.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    context = {"commit": sha, "repository": repo, "ref": ref, "required": not args.candidate}
    if args.candidate:
        candidate = {**context, "workflows": {}}
        validate_snapshot(candidate, sha, repo, ref)
        output.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        print("Branch candidate only; publication requires successful historical checks on main")
        return
    if repo != REPOSITORY or ref != "refs/heads/main":
        raise ValueError("Historical release checks require the authorized main commit")
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        snapshots = {}
        for workflow in WORKFLOWS:
            response = subprocess.check_output(
                ["gh", "api", f"repos/{repo}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=100"],
                text=True,
                timeout=30,
            )
            snapshots[workflow] = json.loads(response)["workflow_runs"]
        snapshot = {**context, "workflows": snapshots}
        output.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
        results = [assess_runs(runs, sha) for runs in snapshots.values()]
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
