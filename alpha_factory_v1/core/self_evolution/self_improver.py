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

from alpha_factory_v1.core.utils.patch_guard import is_patch_valid
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


def _normalize_patch(patch: str, repo_root: Path) -> str:
    """Normalize a unified diff to include hunk ranges and a trailing newline."""
    patch = patch.replace("\r\n", "\n")
    if not patch.endswith("\n"):
        patch += "\n"

    lines = patch.splitlines()
    new_lines: list[str] = []
    current_file: str | None = None
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if line.startswith(("--- ", "+++ ")):
            current_file = line[4:].split("\t")[0]
            if current_file.startswith(("a/", "b/")):
                current_file = current_file[2:]
            new_lines.append(line)
            idx += 1
            continue
        if line.strip() == "@@":
            hunk_lines: list[str] = []
            j = idx + 1
            while j < len(lines) and not lines[j].startswith(("--- ", "+++ ", "@@")):
                hunk_lines.append(lines[j])
                j += 1
            orig_count = sum(1 for hl in hunk_lines if hl.startswith((" ", "-")))
            new_count = sum(1 for hl in hunk_lines if hl.startswith((" ", "+")))
            start = 1
            if current_file:
                file_path = repo_root / current_file
                if file_path.exists():
                    file_lines = file_path.read_text(encoding="utf-8").splitlines()
                    candidate = next((hl[1:] for hl in hunk_lines if hl.startswith((" ", "-"))), None)
                    if candidate in file_lines:
                        start = file_lines.index(candidate) + 1
            new_lines.append(f"@@ -{start},{orig_count} +{start},{new_count} @@")
            new_lines.extend(hunk_lines)
            idx = j
            continue
        new_lines.append(line)
        idx += 1
    return "\n".join(new_lines) + "\n"


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

    diff = Path(patch_file).read_text()
    diff = _normalize_patch(diff, repo_dir)
    if not is_patch_valid(diff):
        raise ValueError("Invalid or unsafe patch")

    with tempfile.NamedTemporaryFile("w+", delete=False) as tf:
        tf.write(diff)
        normalized = tf.name

    try:
        repo.git.apply(normalized)
        repo.index.add([metric_file])
        repo.index.commit("apply patch")
    finally:
        Path(normalized).unlink(missing_ok=True)
    # run basic checks before scoring
    run_preflight(repo_dir)
    new_score = _evaluate(repo_dir, metric_file)
    delta = new_score - baseline
    _log_delta(delta, Path(log_file))
    if cleanup:
        shutil.rmtree(repo_dir, ignore_errors=True)
    return delta, repo_dir
