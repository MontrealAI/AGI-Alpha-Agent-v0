# SPDX-License-Identifier: Apache-2.0
"""Keep repair copies and comparisons scoped to the same project files."""
from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import shutil
import stat

_IGNORE_NAMES = {".git", ".mypy_cache", ".pytest_cache", "__pycache__", "node_modules", ".venv", "venv"}


class WorkspaceError(ValueError):
    """A repair input cannot be contained in an ordinary-file workspace."""


def project_path(root: Path, name: str) -> Path:
    """Resolve a canonical relative path without following project links."""
    relative = PurePosixPath(name)
    if (
        not name
        or name.startswith("-")
        or "\\" in name
        or PureWindowsPath(name).drive
        or relative.is_absolute()
        or relative.as_posix() != name
        or any(part in {".", "..", ""} for part in name.split("/"))
        or any(ord(char) < 32 for char in name)
    ):
        raise WorkspaceError(f"Expected a canonical repository-relative path: {name!r}")
    path = root.resolve(strict=True)
    for part in relative.parts:
        path = path / part
        if path.is_symlink() or path.resolve() != path:
            raise WorkspaceError(f"Linked workspace entry is not supported: {name}")
        if path.exists() and not (path.is_file() or path.is_dir()):
            raise WorkspaceError(f"Special workspace entry is not supported: {name}")
        if path.is_file() and path.stat().st_nlink != 1:
            raise WorkspaceError(f"Hard-linked workspace entry is not supported: {name}")
    return path


def ignored_entries(directory: str, names: list[str]) -> set[str]:
    """Prune dependency caches and Python environments before traversing them."""
    root = Path(directory)
    ignored = set(names) & _IGNORE_NAMES
    for name in names:
        if name in ignored:
            continue
        path = root / name
        metadata = path.lstat()
        mode = metadata.st_mode
        if name.startswith(".venv") and (stat.S_ISDIR(mode) or stat.S_ISLNK(mode)):
            ignored.add(name)
        elif stat.S_ISLNK(mode) or path.resolve() != path.absolute():
            raise WorkspaceError(f"Linked workspace entry is not supported: {path}")
        elif stat.S_ISDIR(mode) and (path / "pyvenv.cfg").is_file():
            ignored.add(name)
        elif not (stat.S_ISDIR(mode) or stat.S_ISREG(mode)):
            raise WorkspaceError(f"Special workspace entry is not supported: {path}")
        elif stat.S_ISREG(mode) and metadata.st_nlink != 1:
            raise WorkspaceError(f"Hard-linked workspace entry is not supported: {path}")
    return ignored


def copy_workspace(source: Path, destination: Path) -> None:
    """Copy project files without duplicating installed environments or caches."""
    # Preserve a link introduced during copying instead of dereferencing it;
    # the completed snapshot is checked again before any repair can run.
    shutil.copytree(source.resolve(strict=True), destination, ignore=ignored_entries, symlinks=True)
    workspace_files(destination)


def workspace_files(root: Path) -> set[Path]:
    """Enumerate the same files as copying, so excluded files never become deletions."""
    files: set[Path] = set()
    root = root.resolve(strict=True)

    def fail(error: OSError) -> None:
        raise error

    for directory, directories, filenames in os.walk(root, onerror=fail):
        ignored = ignored_entries(directory, directories + filenames)
        directories[:] = [name for name in directories if name not in ignored]
        files.update(
            (Path(directory) / name).relative_to(root)
            for name in filenames
            if name not in ignored and (Path(directory) / name).is_file()
        )
    return files
