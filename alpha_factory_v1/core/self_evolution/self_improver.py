# SPDX-License-Identifier: Apache-2.0
"""Minimal self-improvement workflow using GitPython.

This module clones a repository, applies a unified diff patch, evaluates a
numeric score and logs the score delta. ``improve_repo`` optionally cleans up
the temporary clone via the ``cleanup`` flag.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from pathlib import Path
from typing import Tuple

from alpha_factory_v1.core.utils.patch_guard import is_patch_valid, normalize_patch_hunks
from alpha_factory_v1.core.eval.preflight import run_preflight

try:
    import git
except ModuleNotFoundError:  # pragma: no cover - optional
    git = None


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
    baseline = _evaluate(repo_dir, metric_file)

    diff = normalize_patch_hunks(Path(patch_file).read_text())
    if not diff.endswith("\n"):
        diff += "\n"
    if not is_patch_valid(diff):
        raise ValueError("Invalid or unsafe patch")

    tmp_patch = Path(tempfile.mkstemp(prefix="selfimprover-", suffix=".diff")[1])
    try:
        tmp_patch.write_text(diff)
        repo.git.apply(str(tmp_patch))
    finally:
        if tmp_patch.exists():
            tmp_patch.unlink()
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
