# SPDX-License-Identifier: Apache-2.0
"""Contract tests for explicit Ruff target selection."""

from __future__ import annotations

from pathlib import Path

from scripts.ruff_targets import tracked_python_targets


def test_tracked_python_targets_excludes_git_metadata() -> None:
    """Tracked targets never include Git metadata paths."""
    targets = tracked_python_targets(Path.cwd())
    assert targets
    assert all(not str(path).startswith(".git/") for path in targets)


def test_tracked_python_targets_only_python_sources() -> None:
    """Tracked target list is constrained to Python files."""
    targets = tracked_python_targets(Path.cwd())
    assert all(path.suffix in {".py", ".pyi"} for path in targets)
