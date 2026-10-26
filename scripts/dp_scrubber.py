#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Apply a local private/pay-walled text heuristic to staged files or a release delta.

This keyword heuristic does not call a model and is not a secret scanner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable, List, Sequence

# Basic corpus representing proprietary content. Real implementation would load
# a hashed corpus or database.
PROPRIETARY_CORPUS = {
    "exclusive",
    "dataset",
    "paywalled",
    "examplecorp",
}

TOKEN_LIMIT = 64

# Release-only source-data admission: intentional Apache-2.0 classifier fixtures.
# Changing any fixture byte, its committed mode, or its path requires a new review.
# The original positive finding remains visible in the release report.
REVIEWED_SYNTHETIC_FIXTURE_PATH = "tests/test_dp_scrubber.py"
REVIEWED_SYNTHETIC_FIXTURE_SHA256 = "4f37a40592f89c3cac877364a7b60f66778f4bf66e2a911069dae69eb2031b07"
REVIEWED_SYNTHETIC_FIXTURE_GIT_BLOB = "9ed7236c0fbba004feb0467848cbef8bf6cc5f26"
REVIEWED_SYNTHETIC_FIXTURE_MODE = "100644"


def classify_with_llm(text: str) -> bool:
    """Apply the legacy local keyword heuristic without calling a model."""
    lower = text.lower()
    return "paywalled" in lower or "proprietary" in lower


def tokenize(text: str) -> List[str]:
    return re.findall(r"\b\w+\b", text.lower())


def is_proprietary_content(text: str) -> bool:
    tokens = tokenize(text)
    count = 0
    for tok in tokens:
        if tok in PROPRIETARY_CORPUS:
            count += 1
            if count >= TOKEN_LIMIT:
                return True
        else:
            if 0 < count < TOKEN_LIMIT and classify_with_llm(" ".join(tokens)):
                return True
            count = 0
    if 0 < count < TOKEN_LIMIT and classify_with_llm(text):
        return True
    return False


def scan_file(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False
    return is_proprietary_content(text)


def staged_files() -> Iterable[Path]:
    result = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    for line in result.stdout.splitlines():
        p = Path(line)
        if p.is_file():
            yield p


def _git(arguments: Sequence[str], *, root: Path | None = None) -> bytes:
    """Run a read-only Git query, refusing incomplete coverage on failure."""
    result = subprocess.run(
        ["git", "-c", "core.fsmonitor=false", "--no-pager", "--literal-pathspecs", *arguments],
        capture_output=True,
        cwd=root,
    )
    if result.returncode != 0:
        raise RuntimeError("Git query failed; release-delta coverage is incomplete")
    return result.stdout


def _safe_path(root: Path, name: bytes, *, deleted: bool) -> str:
    """Validate a repository-relative tracked name without following symlinks."""
    path = os.fsdecode(name)
    parts = PurePosixPath(path).parts
    if (
        not parts
        or path.startswith("/")
        or re.match(r"^[A-Za-z]:", path)
        or "\\" in path
        or any(part in {".", ".."} for part in parts)
    ):
        raise RuntimeError("Unsafe tracked path in release delta")
    if deleted:
        return path
    current = root
    for index, part in enumerate(parts):
        current /= part
        mode = current.lstat().st_mode
        if stat.S_ISLNK(mode) or (index < len(parts) - 1 and not stat.S_ISDIR(mode)):
            raise RuntimeError(f"Nonregular tracked path in release delta: {json.dumps(path)}")
        if index == len(parts) - 1 and not stat.S_ISREG(mode):
            raise RuntimeError(f"Nonregular tracked path in release delta: {json.dumps(path)}")
    return path


def _require_clean_head(root: Path, head: str, options: Sequence[str]) -> None:
    """Refuse tracked overlays and index flags that can hide local differences."""
    if any(
        record and not record.startswith(b"H ") for record in _git(["ls-files", "-v", "-z"], root=root).split(b"\0")
    ):
        raise RuntimeError("Tracked index flags require separate review before release coverage")
    if _git(["diff", "--name-only", "-z", *options, head, "--"], root=root) or _git(
        ["diff", "--cached", "--name-only", "-z", *options, head, "--"], root=root
    ):
        raise RuntimeError("Tracked worktree and index must match committed HEAD for release coverage")


def release_delta(base: str) -> dict[str, object]:
    """Scan committed HEAD additions against an exact ancestor with no tracked overlay.

    Git supplies the delta without external diff or text-conversion commands.
    Deleted files and Git-classified binaries are counted, not classified as text.
    Untracked files are outside this tracked release-delta scope.
    """
    if re.fullmatch(r"[0-9a-fA-F]{40}", base) is None:
        raise RuntimeError("--base requires an exact 40-character commit SHA")
    _git(["cat-file", "-e", f"{base}^{{commit}}"])
    _git(["merge-base", "--is-ancestor", base, "HEAD"])
    root = Path(os.fsdecode(_git(["rev-parse", "--show-toplevel"]).rstrip(b"\n"))).resolve(strict=True)
    options = ["--no-ext-diff", "--no-textconv", "--no-renames"]
    head = _git(["rev-parse", "--verify", "HEAD"], root=root).strip().decode("ascii")
    _require_clean_head(root, head, options)
    raw = _git(["diff", "--raw", "--no-abbrev", "-z", *options, base, head, "--"], root=root).split(b"\0")
    if raw.pop() != b"" or len(raw) % 2:
        raise RuntimeError("Malformed Git delta inventory")
    paths: dict[bytes, tuple[str, bool, str, str]] = {}
    for index in range(0, len(raw), 2):
        fields = raw[index].split()
        if len(fields) != 5 or not fields[0].startswith(b":") or fields[4] not in {b"A", b"D", b"M", b"T"}:
            raise RuntimeError("Unsupported tracked change in release delta")
        deleted = fields[4] == b"D"
        if (deleted and fields[1] != b"000000") or (not deleted and fields[1] not in {b"100644", b"100755"}):
            raise RuntimeError("Only tracked regular files and deletions are supported in release delta")
        name = raw[index + 1]
        if name in paths:
            raise RuntimeError("Duplicate tracked path in release delta")
        paths[name] = (
            _safe_path(root, name, deleted=deleted),
            deleted,
            fields[1].decode("ascii"),
            fields[3].decode("ascii"),
        )
    stats: dict[bytes, bool] = {}
    for record in _git(["diff", "--numstat", "-z", *options, base, head, "--"], root=root).split(b"\0"):
        if not record:
            continue
        counts = record.split(b"\t", 2)
        if len(counts) != 3 or counts[2] in stats:
            raise RuntimeError("Malformed Git text/binary inventory")
        if counts[:2] == [b"-", b"-"]:
            stats[counts[2]] = True
        elif all(count.isdigit() for count in counts[:2]):
            stats[counts[2]] = False
        else:
            raise RuntimeError("Malformed Git text/binary counts")
    if paths.keys() != stats.keys():
        raise RuntimeError("Git delta inventories disagree")

    flagged: list[str] = []
    admitted: list[str] = []
    unadmitted: list[str] = []
    scanned = binary = deleted_count = no_additions = 0
    for name, (path, deleted, mode, blob) in paths.items():
        if deleted:
            deleted_count += 1
            continue
        if stats[name]:
            binary += 1
            continue
        patch = _git(["diff", "--unified=0", *options, base, head, "--", path], root=root)
        additions: list[bytes] = []
        in_hunk = False
        for line in patch.splitlines():
            if line.startswith(b"@@ "):
                in_hunk = True
            elif in_hunk and line.startswith(b"+"):
                additions.append(line[1:])
        if not additions:
            no_additions += 1
            continue
        try:
            text = b"\n".join(additions).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise RuntimeError(f"Non-UTF-8 text delta requires separate review: {json.dumps(path)}") from exc
        scanned += 1
        if is_proprietary_content(text):
            flagged.append(path)
            if (
                path == REVIEWED_SYNTHETIC_FIXTURE_PATH
                and mode == REVIEWED_SYNTHETIC_FIXTURE_MODE
                and blob == REVIEWED_SYNTHETIC_FIXTURE_GIT_BLOB
                and hashlib.sha256(_git(["cat-file", "blob", blob], root=root)).hexdigest()
                == REVIEWED_SYNTHETIC_FIXTURE_SHA256
            ):
                admitted.append(path)
            else:
                unadmitted.append(path)
    if _git(["rev-parse", "--verify", "HEAD"], root=root).strip().decode("ascii") != head:
        raise RuntimeError("HEAD changed during release-delta scan")
    _require_clean_head(root, head, options)
    return {
        "mode": "committed-release-delta",
        "base": base.lower(),
        "head": head,
        "worktree_and_index_match_head": True,
        "scope": "committed added UTF-8 lines; untracked files, deleted contents and binaries are not classified",
        "classifier": "local proprietary/pay-walled text heuristic; no model call or secret scan",
        "changed_paths": len(paths),
        "scanned_text_files": scanned,
        "flagged_files": len(flagged),
        "flagged_paths": flagged,
        "reviewed_synthetic_fixture_files": len(admitted),
        "reviewed_synthetic_fixture_paths": admitted,
        "unadmitted_positive_files": len(unadmitted),
        "unadmitted_positive_paths": unadmitted,
        "reviewed_synthetic_fixture": {
            "path": REVIEWED_SYNTHETIC_FIXTURE_PATH,
            "sha256": REVIEWED_SYNTHETIC_FIXTURE_SHA256,
            "git_blob": REVIEWED_SYNTHETIC_FIXTURE_GIT_BLOB,
            "mode": REVIEWED_SYNTHETIC_FIXTURE_MODE,
            "disposition": "reviewed synthetic Apache-2.0 classifier regression fixture; positive finding retained",
        },
        "binary_files_not_scanned": binary,
        "deleted_files_not_scanned": deleted_count,
        "text_files_without_additions": no_additions,
    }


def main(argv: Sequence[str] | None = None) -> int:
    """Run the staged hook or explicitly bounded release-delta check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="exact ancestor commit SHA for a tracked release-delta scan")
    args = parser.parse_args(argv)
    if args.base is not None:
        try:
            if os.getenv("ALLOW_PRIVATE_TEXT") == "1":
                raise RuntimeError("ALLOW_PRIVATE_TEXT cannot override an explicit release-delta scan")
            report = release_delta(args.base)
        except (OSError, RuntimeError) as exc:
            sys.stderr.write(f"Release-delta scan failed: {exc}\n")
            return 2
        print(json.dumps(report, sort_keys=True))
        return 1 if report["unadmitted_positive_files"] else 0

    if os.getenv("ALLOW_PRIVATE_TEXT") == "1":
        return 0

    flagged: List[str] = []
    for path in staged_files():
        if scan_file(path):
            flagged.append(str(path))

    if flagged:
        sys.stderr.write("Private or pay-walled text detected in:\n" + "\n".join(flagged) + "\n")
        sys.stderr.write("Set ALLOW_PRIVATE_TEXT=1 to override.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
