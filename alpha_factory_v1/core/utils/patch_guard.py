# SPDX-License-Identifier: Apache-2.0
"""Basic patch validation utilities."""

from __future__ import annotations

import re


_BAD_PATTERNS = [
    r"rm\s+-rf",  # destructive removal
    r"https?://",  # network addresses
    r"\bcurl\b",
    r"\bwget\b",
    r"requests\.get",
    r"urllib\.request",
    r"socket\.",
]


def normalize_patch_hunks(diff: str) -> str:
    """Ensure unified diff hunks include line ranges when omitted."""
    lines = diff.splitlines()
    normalized: list[str] = []
    for line in lines:
        if line.startswith("@@") and re.match(r"^@@\s*$", line):
            normalized.append("@@ -1,1 +1,1 @@")
        else:
            normalized.append(line)
    return "\n".join(normalized)


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
