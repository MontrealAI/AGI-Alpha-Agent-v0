# SPDX-License-Identifier: Apache-2.0
"""Minimal self-improvement workflow using GitPython.

This module clones a repository, applies a unified diff patch, evaluates a
numeric score and logs the score delta. ``improve_repo`` optionally cleans up
the temporary clone via the ``cleanup`` flag.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Tuple

from alpha_factory_v1.core.utils.patch_guard import is_patch_valid
from alpha_factory_v1.core.eval.preflight import run_preflight

try:
    import git
except ModuleNotFoundError:  # pragma: no cover - optional
    git = None


def _ensure_git_identity(repo: "git.Repo") -> None:
    """Ensure the repo has user.name and user.email set for commits."""
    reader = repo.config_reader()
    needs_name = not reader.has_option("user", "name")
    needs_email = not reader.has_option("user", "email")
    if needs_name or needs_email:
        with repo.config_writer() as writer:
            if needs_name:
                writer.set_value("user", "name", "Alpha-Factory Bot")
            if needs_email:
                writer.set_value("user", "email", "alpha-factory@example.com")


def _evaluate(repo_path: Path, metric_file: str) -> float:
    """Return the numeric metric stored in ``metric_file`` inside ``repo_path``."""
    return float((repo_path / metric_file).read_text().strip())


def _log_delta(delta: float, log_file: Path) -> None:
    """Append ``delta`` with timestamp to ``log_file`` (JSON list)."""
    log: list[dict[str, float]]
    if log_file.exists():
        log = json.loads(log_file.read_text())
    else:
        log = []
    log.append({"ts": time.time(), "delta": delta})
    log_file.write_text(json.dumps(log))


def improve_repo(
    repo_url: str,
    patch_file: str,
    metric_file: str,
    log_file: str,
    cleanup: bool = True,
) -> Tuple[float, Path]:
    """Clone ``repo_url``, apply ``patch_file`` and log score delta.

    Parameters
    ----------
    repo_url:
        Repository to clone.
    patch_file:
        Unified diff to apply.
    metric_file:
        File containing the numeric metric used for scoring.
    log_file:
        JSON file updated with the score delta.
    cleanup:
        When ``True`` the temporary clone is removed before returning.

    Returns
    -------
    tuple[float, Path]
        Score delta and path to the cloned repository (if ``cleanup`` is
        ``False``).
    """
    if git is None:
        raise RuntimeError("GitPython is required")
    repo_dir = Path(tempfile.mkdtemp(prefix="selfimprover-"))
    repo = git.Repo.clone_from(repo_url, repo_dir)
    _ensure_git_identity(repo)
    baseline = _evaluate(repo_dir, metric_file)

    diff = Path(patch_file).read_text()
    if not is_patch_valid(diff):
        raise ValueError("Invalid or unsafe patch")

    result = subprocess.run(
        ["patch", "-p1", "-i", patch_file],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Patch apply failed:\n{result.stdout}{result.stderr}")
    repo.index.add([metric_file])
    repo.index.commit("apply patch")
    # run basic checks before scoring
    run_preflight(repo_dir)
    new_score = _evaluate(repo_dir, metric_file)
    delta = new_score - baseline
    _log_delta(delta, Path(log_file))
    if cleanup:
        shutil.rmtree(repo_dir, ignore_errors=True)
    return delta, repo_dir
