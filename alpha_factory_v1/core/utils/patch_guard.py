# SPDX-License-Identifier: Apache-2.0
"""Basic patch validation utilities."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Optional


_BAD_PATTERNS = [
    r"rm\s+-rf",  # destructive removal
    r"https?://",  # network addresses
    r"\bcurl\b",
    r"\bwget\b",
    r"requests\.get",
    r"urllib\.request",
    r"socket\.",
]


def _changed_files(diff: str) -> list[str]:
    files: set[str] = set()
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            path = parts[1]
            if path.startswith("a/") or path.startswith("b/"):
                path = path[2:]
            files.add(path)
    return list(files)


def is_patch_valid(diff: str) -> bool:
    """Return ``True`` if ``diff`` does not appear dangerous or malformed."""

    if not diff.strip():
        return False

    lowered = diff.lower()
    for pat in _BAD_PATTERNS:
        if re.search(pat, lowered):
            return False

    files = _changed_files(diff)

    # Reject diffs that do not reference any files
    if not files:
        return False

    # Reject diffs touching only test files
    if all(f.startswith("tests/") or "/tests/" in f or f.split("/")[-1].startswith("test_") for f in files):
        return False

    return True


_HUNK_RE = re.compile(r"^@@\\s+-(\\d+)(?:,(\\d+))?\\s+\\+(\\d+)(?:,(\\d+))?\\s+@@")


def _find_hunk_start(lines: list[str], removed: list[str]) -> Optional[int]:
    if not removed:
        return len(lines) + 1
    for idx in range(len(lines) - len(removed) + 1):
        if lines[idx : idx + len(removed)] == removed:
            return idx + 1
    return None


def normalize_patch(diff: str, repo_root: Path) -> str:
    """Normalize unified diffs that omit hunk ranges.

    Args:
        diff: Original unified diff.
        repo_root: Repository root used to resolve file paths.

    Returns:
        Unified diff with explicit hunk ranges when possible.
    """
    lines = diff.splitlines()
    out: list[str] = []
    i = 0
    file_lines: list[str] = []
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- "):
            out.append(line)
            i += 1
            continue
        if line.startswith("+++ "):
            out.append(line)
            path = line[4:].split("\t")[0]
            path = re.sub(r"^[ab]/", "", path)
            file_path = repo_root / path
            file_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            i += 1
            continue
        if line.startswith("@@"):
            header = line
            if _HUNK_RE.match(header):
                out.append(header)
                i += 1
                continue
            if header.strip() == "@@":
                i += 1
                hunk_lines: list[str] = []
                while i < len(lines) and not lines[i].startswith(("@@", "--- ", "+++ ")):
                    hunk_lines.append(lines[i])
                    i += 1
                removed = [l[1:] for l in hunk_lines if l.startswith("-") and not l.startswith("---")]
                added = [l[1:] for l in hunk_lines if l.startswith("+") and not l.startswith("+++")]
                start = _find_hunk_start(file_lines, removed) or 1
                old_count = len(removed)
                new_count = len(added)
                out.append(f"@@ -{start},{old_count} +{start},{new_count} @@")
                out.extend(hunk_lines)
                continue
            out.append(line)
            i += 1
            continue
        out.append(line)
        i += 1
    text = "\n".join(out)
    if diff.endswith("\n"):
        text += "\n"
    return text
