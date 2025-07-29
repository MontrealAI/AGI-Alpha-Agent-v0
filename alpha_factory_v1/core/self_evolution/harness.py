# SPDX-License-Identifier: Apache-2.0
"""Patch evaluation harness using Docker-in-Docker."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Tuple

from alpha_factory_v1.core.eval.preflight import run_preflight
from alpha_factory_v1.core.governance.stake_registry import StakeRegistry
from alpha_factory_v1.demos.self_healing_repo import patcher_core

IMAGE = os.getenv("SELF_EVOLUTION_IMAGE", "python:3.11-slim")

__all__ = [
    "apply_patch",
    "vote_and_merge",
    "patcher_core",
    "_run_tests",
    "run_preflight",
]


def _run_tests(repo: Path) -> int:
    """Run the repository's test suite in a Docker container.

    Args:
        repo: Path to the repository to test.

    Returns:
        The pytest return code.
    """
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{repo}:/work",
    ]
    wheelhouse = os.getenv("WHEELHOUSE")
    if wheelhouse:
        cmd.extend(["-e", f"WHEELHOUSE={wheelhouse}", "-v", f"{wheelhouse}:{wheelhouse}"])
    cmd.extend(
        [
            "-w",
            "/work",
            IMAGE,
            "bash",
            "-c",
            'python check_env.py --auto-install${WHEELHOUSE:+ --wheelhouse "$WHEELHOUSE"} && pytest -q',
        ]
    )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode


def apply_patch(repo: str | Path, diff: str) -> Tuple[bool, Path]:
    """Apply `diff` to `repo` in isolation and run the tests.

    Args:
        repo: Repository path to patch.
        diff: Unified diff to apply.

    Returns:
        Tuple containing the test result and sandbox path.
    """
    src = Path(repo).resolve()
    tmp = Path(tempfile.mkdtemp(prefix="self-evo-"))
    shutil.copytree(src, tmp, dirs_exist_ok=True)
    patcher_core.apply_patch(diff, repo_path=str(tmp))
    run_preflight(tmp)
    rc = _run_tests(tmp)
    return rc == 0, tmp


def vote_and_merge(repo: str | Path, diff: str, registry: StakeRegistry, agent_id: str = "orch") -> bool:
    """Apply patch and merge into `repo` when tests pass and the metric improves.

    Args:
        repo: Repository path to modify.
        diff: Unified diff to apply.
        registry: Vote registry used for consensus.
        agent_id: Identifier for the voting agent.

    Returns:
        ``True`` if the patch was merged into the repository.
    """
    repo_path = Path(repo).resolve()
    proposal = hashlib.sha1(diff.encode()).hexdigest()
    baseline = float((repo_path / "metric.txt").read_text().strip())
    ok, patched = apply_patch(repo_path, diff)
    if not ok:
        registry.vote(proposal, agent_id, False)
        shutil.rmtree(patched)
        return False
    try:
        new_score = float((patched / "metric.txt").read_text().strip())
    except Exception:
        new_score = baseline
    improved = new_score < baseline
    registry.vote(proposal, agent_id, improved)
    accepted = improved and registry.accepted(proposal)
    if accepted:
        for src_file in patched.rglob("*"):
            if src_file.is_file():
                rel = src_file.relative_to(patched)
                dest = repo_path / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dest)
        registry.archive_accept(agent_id)
    shutil.rmtree(patched)
    return accepted
