# SPDX-License-Identifier: Apache-2.0
"""Basic patch validation utilities."""

from __future__ import annotations

import contextlib
import re
from pathlib import Path


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


def normalize_patch_hunks(diff: str, repo_root: Path) -> str:
    """Normalize hunks missing line ranges so patch tooling can apply them."""
    lines = diff.splitlines()
    new_lines: list[str] = []
    current_file: str | None = None
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("+++ "):
            path = line[4:].split("\t")[0].strip()
            current_file = re.sub(r"^[ab]/", "", path)
            new_lines.append(line)
            i += 1
            continue
        if line.startswith("@@") and not re.match(r"^@@ -\d", line):
            hunk_lines: list[str] = []
            j = i + 1
            while (
                j < len(lines)
                and not lines[j].startswith("@@")
                and not lines[j].startswith(("--- ", "+++ "))
            ):
                hunk_lines.append(lines[j])
                j += 1
            old_count = 0
            new_count = 0
            first_removed: str | None = None
            for hunk_line in hunk_lines:
                if hunk_line.startswith("-"):
                    old_count += 1
                    if first_removed is None:
                        first_removed = hunk_line[1:]
                elif hunk_line.startswith("+"):
                    new_count += 1
                else:
                    old_count += 1
                    new_count += 1
            old_count = max(old_count, 1)
            new_count = max(new_count, 1)
            line_num = 1
            if current_file and first_removed is not None:
                file_path = repo_root / current_file
                if file_path.exists():
                    content = file_path.read_text().splitlines()
                    with contextlib.suppress(ValueError):
                        line_num = content.index(first_removed) + 1
            new_lines.append(f"@@ -{line_num},{old_count} +{line_num},{new_count} @@")
            i += 1
            continue
        new_lines.append(line)
        i += 1
    return "\n".join(new_lines) + ("\n" if diff.endswith("\n") else "")
