# SPDX-License-Identifier: Apache-2.0
"""Keep repair copies and comparisons scoped to the same project files."""
from __future__ import annotations

import os
from pathlib import Path
import shutil

_IGNORE_NAMES = {".git", ".mypy_cache", ".pytest_cache", "__pycache__", "node_modules", ".venv", "venv"}


def ignored_entries(directory: str, names: list[str]) -> set[str]:
    """Prune dependency caches and Python environments before traversing them."""
    root = Path(directory)
    ignored = set(names) & _IGNORE_NAMES
    for name in names:
        path = root / name
        if path.is_dir() and (name.startswith(".venv") or (path / "pyvenv.cfg").is_file()):
            ignored.add(name)
    return ignored


def copy_workspace(source: Path, destination: Path) -> None:
    """Copy project files without duplicating installed environments or caches."""
    shutil.copytree(source, destination, ignore=ignored_entries)


def workspace_files(root: Path) -> set[Path]:
    """Enumerate the same files as copying, so excluded files never become deletions."""
    files: set[Path] = set()
    for directory, directories, filenames in os.walk(root):
        ignored = ignored_entries(directory, directories + filenames)
        directories[:] = [name for name in directories if name not in ignored]
        files.update(
            (Path(directory) / name).relative_to(root)
            for name in filenames
            if name not in ignored and (Path(directory) / name).is_file()
        )
    return files
