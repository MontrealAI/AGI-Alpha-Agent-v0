#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Resolve tracked Python lint targets and optionally run Ruff."""

from __future__ import annotations

import argparse
import subprocess
import sys
from itertools import islice
from pathlib import Path

PYTHON_FILE_GLOBS: tuple[str, ...] = ("*.py", "*.pyi", "*.ipynb")
DEFAULT_BATCH_SIZE = 200
METADATA_PATH_PARTS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".cache",
        "__pycache__",
    }
)


def _repo_root() -> Path:
    """Return the current Git repository root path."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return Path.cwd()
    return Path(result.stdout.strip())


def list_tracked_python_files(repo_root: Path) -> list[str]:
    """Return tracked Python-related files for Ruff relative to ``repo_root``."""
    command = ["git", "-C", str(repo_root), "ls-files", "--cached", "-z", "--", *PYTHON_FILE_GLOBS]
    try:
        result = subprocess.run(command, check=True, capture_output=True)
    except subprocess.CalledProcessError:
        return _walk_python_files(repo_root)

    entries = [item for item in result.stdout.decode("utf-8").split("\x00") if item]
    filtered = sorted({entry for entry in entries if _is_lintable_path(entry)})
    return filtered


def _is_lintable_path(relative_path: str) -> bool:
    """Return whether ``relative_path`` should be included in Ruff scope."""
    path = Path(relative_path)
    return not any(part in METADATA_PATH_PARTS for part in path.parts)


def _walk_python_files(repo_root: Path) -> list[str]:
    """Return Python files from filesystem walk when Git metadata is unavailable."""
    discovered: set[str] = set()
    for pattern in PYTHON_FILE_GLOBS:
        for path in repo_root.rglob(pattern):
            try:
                rel = path.relative_to(repo_root).as_posix()
            except ValueError:
                continue
            if _is_lintable_path(rel):
                discovered.add(rel)
    return sorted(discovered)


def run_ruff(repo_root: Path, targets: list[str], batch_size: int) -> int:
    """Run Ruff over ``targets`` in deterministic batches to avoid long argv."""
    # Preserve these imported scientific artifacts before applying their finite
    # exact-file compatibility rules, including the empty-target case.
    if __package__:
        from .check_strategy_research_source import require_preserved
    else:
        from check_strategy_research_source import require_preserved
    require_preserved(repo_root)
    if not targets:
        print("No tracked Python files found; skipping Ruff.")
        return 0

    command_prefix = [sys.executable, "-m", "ruff", "check", "--force-exclude"]
    start = 0
    total = len(targets)
    while start < total:
        stop = start + batch_size
        batch = list(islice(targets, start, stop))
        command = command_prefix + batch
        result = subprocess.run(command, cwd=repo_root)
        if result.returncode != 0:
            return result.returncode
        start = stop
    return 0


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Execute Ruff with the resolved targets.")
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Max targets passed to each Ruff invocation when --run is enabled.",
    )
    return parser.parse_args()


def main() -> int:
    """Resolve tracked targets and optionally run Ruff."""
    args = parse_args()
    repo_root = _repo_root()
    targets = list_tracked_python_files(repo_root)

    if args.run:
        return run_ruff(repo_root, targets, batch_size=args.batch_size)

    for target in targets:
        print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
