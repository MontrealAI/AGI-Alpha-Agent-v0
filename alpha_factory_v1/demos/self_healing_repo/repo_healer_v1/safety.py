# SPDX-License-Identifier: Apache-2.0
"""Patch safety policy for Repo-Healer v1."""

from __future__ import annotations

import pathlib
import re

from .workspace import WorkspaceError, project_path, workspace_files

FORBIDDEN_PATH_PATTERNS = (
    re.compile(r"^\.git(/|$)"),
    re.compile(r"^\.github/workflows/"),
    re.compile(r"^scripts/verify_branch_protection\.py$"),
)


def touched_files_from_diff(diff: str) -> set[str]:
    """Extract touched file paths from unified diff headers."""
    touched: set[str] = set()
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")):
            path = re.sub(r"^[ab]/", "", line[4:].split("\t")[0])
            touched.add(path)
    return touched


def is_patch_safe(diff: str, repo_root: pathlib.Path, allow_create: set[str] | None = None) -> tuple[bool, str]:
    """Check patch scope restrictions for Repo-Healer v1."""
    allow_create = allow_create or set()
    touched = touched_files_from_diff(diff)
    if not touched:
        return False, "patch has no file headers"
    try:
        for path in touched:
            project_path(repo_root, path)
        existing = {path.as_posix() for path in workspace_files(repo_root)}
    except (WorkspaceError, OSError) as exc:
        return False, str(exc)
    for path in touched:
        if any(p.search(path) for p in FORBIDDEN_PATH_PATTERNS):
            return False, f"touches protected surface: {path}"
        if path not in existing and path not in allow_create:
            return False, f"new files not allowed by default: {path}"
    if "[ci skip]" in diff.lower():
        return False, "forbidden ci bypass marker"
    return True, "safe"
