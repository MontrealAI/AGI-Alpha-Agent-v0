# SPDX-License-Identifier: Apache-2.0
"""Apply minimal unified diff patches."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


class PatchApplyError(ValueError):
    """Raised when a patch cannot be applied."""


def _strip_prefix(path: str) -> str:
    for prefix in ("a/", "b/"):
        if path.startswith(prefix):
            return path[len(prefix) :]
    return path


def _parse_hunks(lines: Iterable[str]) -> dict[str, list[list[str]]]:
    files: dict[str, list[list[str]]] = {}
    current_path: str | None = None
    current_hunk: list[str] | None = None
    for raw in lines:
        line = raw.rstrip("\n")
        if line.startswith("--- "):
            current_path = None
            current_hunk = None
            continue
        if line.startswith("+++ "):
            current_path = _strip_prefix(line[4:].split("\t")[0])
            files.setdefault(current_path, [])
            current_hunk = None
            continue
        if line.startswith("@@"):
            if current_path is None:
                continue
            current_hunk = []
            files[current_path].append(current_hunk)
            continue
        if line.startswith("\\ No newline"):
            continue
        if current_hunk is not None and line and line[0] in {" ", "-", "+"}:
            current_hunk.append(line)
    return files


def _apply_hunk(lines: list[str], hunk: list[str]) -> list[str]:
    needle = [line[1:] for line in hunk if line[0] in {" ", "-"}]
    replacement = [line[1:] for line in hunk if line[0] in {" ", "+"}]
    if not needle:
        raise PatchApplyError("Patch hunk has no context or removals")
    for idx in range(len(lines) - len(needle) + 1):
        if lines[idx : idx + len(needle)] == needle:
            return lines[:idx] + replacement + lines[idx + len(needle) :]
    raise PatchApplyError("Patch hunk does not match target file")


def apply_unified_patch(repo_root: Path, patch: str) -> None:
    """Apply a unified diff patch to files under ``repo_root``."""
    files = _parse_hunks(patch.splitlines())
    if not files:
        raise PatchApplyError("No file hunks found in patch")
    for rel_path, hunks in files.items():
        target = repo_root / rel_path
        if not target.exists():
            raise PatchApplyError(f"Target file not found: {rel_path}")
        original_text = target.read_text()
        lines = original_text.splitlines()
        for hunk in hunks:
            lines = _apply_hunk(lines, hunk)
        updated = "\n".join(lines)
        if original_text.endswith("\n"):
            updated += "\n"
        target.write_text(updated)


__all__ = ["PatchApplyError", "apply_unified_patch"]
