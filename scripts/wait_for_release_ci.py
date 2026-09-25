#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Require historical main-branch CI on the exact release commit."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any

from alpha_factory_v1.utils.disclaimer import DISCLAIMER  # noqa: F401

WORKFLOWS = ("ci.yml", "pr-ci.yml", "smoke.yml")


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


def main() -> None:
    repo = "MontrealAI/AGI-Alpha-Agent-v0"
    sha = os.environ["GITHUB_SHA"]
    if (
        os.getenv("GITHUB_REPOSITORY") != repo
        or os.getenv("GITHUB_REF") != "refs/heads/main"
        or not re.fullmatch(r"[0-9a-f]{40}", sha)
    ):
        raise ValueError("Historical release checks require the authorized main commit")
    deadline = time.monotonic() + 3000
    output = Path("evidence/historical-ci.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    while True:
        snapshots = {}
        for workflow in WORKFLOWS:
            response = subprocess.check_output(
                ["gh", "api", f"repos/{repo}/actions/workflows/{workflow}/runs?head_sha={sha}&per_page=100"],
                text=True,
                timeout=30,
            )
            snapshots[workflow] = json.loads(response)["workflow_runs"]
        output.write_text(json.dumps({"commit": sha, "workflows": snapshots}, indent=2) + "\n")
        results = [assess_runs(runs, sha) for runs in snapshots.values()]
        if all(results):
            print(f"Historical CI passed for {sha}")
            return
        if time.monotonic() >= deadline:
            raise TimeoutError("Required historical CI did not complete before the release deadline")
        print(f"Waiting for historical CI on {sha}", flush=True)
        time.sleep(30)


if __name__ == "__main__":
    main()
