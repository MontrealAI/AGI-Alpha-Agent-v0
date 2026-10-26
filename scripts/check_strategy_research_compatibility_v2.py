#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Guard the fixed v2 E721 extension without changing the legacy lint identity.

Only canonical filename arguments are accepted. Both preservation layers run
before and after lint; this does not claim an atomic filesystem snapshot across
Ruff's reads. No source, configuration, rule or executable selectors are exposed.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
from types import ModuleType
from typing import Any

PROFILE_NAME = "strategy_research_e721_compatibility_v2.json"
PROFILE_SHA256 = "fb9aae3b8e67e66deb4da42c18c22ef16150d63390d53be31b1243b7ecbe778e"
LEGACY_PATH = "scripts/check_strategy_research_source.py"
CONFIG_NAMES = ("ruff.toml", ".ruff.toml", "pyproject.toml")


def _capture(path: Path, expected_size: int | None = None, *, maximum: int = 16_000_000) -> bytes:
    """Capture a direct regular file, refusing symlinks and concurrent replacement."""
    if path.resolve(strict=True) != path:
        raise ValueError("Source path or ancestor is a symlink")
    selected = path.lstat()
    if not stat.S_ISREG(selected.st_mode) or selected.st_size > maximum:
        raise ValueError("Source must be a bounded regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (selected.st_dev, selected.st_ino):
            raise ValueError("Selected source changed before capture")
        size = before.st_size if expected_size is None else expected_size
        if before.st_size != size or size > maximum:
            raise ValueError("Source byte count differs from the proposed static identity")
        chunks: list[bytes] = []
        remaining = size + 1
        while remaining:
            chunk = os.read(descriptor, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        body = b"".join(chunks)
        after = os.fstat(descriptor)
        current = path.lstat()
        keys = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if len(body) != size or any(getattr(before, key) != getattr(after, key) for key in keys):
            raise ValueError("Source changed during capture")
        if path.resolve(strict=True) != path or any(getattr(after, key) != getattr(current, key) for key in keys):
            raise ValueError("Source path changed during capture")
        return body
    finally:
        os.close(descriptor)


def _unique_pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, value in items:
        if name in result:
            raise ValueError("Duplicate static pin field")
        result[name] = value
    return result


def _relative(name: str) -> None:
    path = PurePosixPath(name)
    if (
        not name
        or path.is_absolute()
        or name.startswith("-")
        or "\\" in name
        or ":" in name
        or ".." in path.parts
        or path.as_posix() != name
    ):
        raise ValueError("Only canonical relative filenames are accepted")


def require_preserved(root: Path) -> dict[str, Any]:
    """Verify successor identities, then execute the unchanged captured guard."""
    root = root.absolute()
    if root.resolve(strict=True) != root:
        raise ValueError("Repository root must not traverse symlinks")
    raw = _capture(root / "scripts" / PROFILE_NAME, maximum=100_000)
    if hashlib.sha256(raw).hexdigest() != PROFILE_SHA256:
        raise ValueError("Unreviewed v2 compatibility identity")
    profile = json.loads(raw, object_pairs_hook=_unique_pairs)
    if profile["schema"] != "agialpha.strategy-research-e721-compatibility/v2":
        raise ValueError("Unknown compatibility schema")
    exceptions = profile["ruff_extend_per_file_ignores"]
    if len(exceptions) != 13 or any(rules != ["E721"] for rules in exceptions.values()):
        raise ValueError("Only the thirteen exact E721 entries are admitted")
    captured = {}
    for name, identity in profile["files"].items():
        _relative(name)
        content = _capture(root / name, identity["bytes"])
        if hashlib.sha256(content).hexdigest() != identity["sha256"]:
            raise ValueError("Compatibility source identity changed: " + name)
        captured[name] = content
    if not set(exceptions) <= captured.keys():
        raise ValueError("An exception lacks a captured source identity")
    ancestors = {root}
    for name in exceptions:
        current = (root / name).parent
        while current != root:
            ancestors.add(current)
            current = current.parent
    permitted_configs = {"pyproject.toml", "contrib/strategy_succession/pyproject.toml"}
    for directory in sorted(ancestors):
        for name in CONFIG_NAMES:
            candidate = directory / name
            if candidate.relative_to(root).as_posix() in permitted_configs:
                continue
            if candidate.exists() or candidate.is_symlink():
                raise ValueError("Unreviewed nested Ruff configuration: " + str(candidate))
    legacy = ModuleType("_captured_strategy_research_source_v1")
    legacy.__file__ = str(root / LEGACY_PATH)
    # Execute only the previously hash-verified bytes, never an unchecked import.
    exec(compile(captured[LEGACY_PATH], legacy.__file__, "exec"), legacy.__dict__)
    report = legacy.require_preserved(root)
    return {
        "profileSha256": PROFILE_SHA256,
        "legacy": report,
        "exceptions": exceptions,
        "runtimeQualified": False,
        "productionAuthority": False,
    }


def compatibility_args(report: dict[str, Any]) -> list[str]:
    """Serialize the already verified finite extension, not a caller rule map."""
    if report.get("profileSha256") != PROFILE_SHA256:
        raise ValueError("A verified compatibility identity is required")
    args = []
    for name, rules in sorted(report["exceptions"].items()):
        args.extend(["--extend-per-file-ignores", name + ":" + ",".join(rules)])
    return args


def run_ruff(root: Path, targets: list[str], batch_size: int = 200) -> int:
    """Lint every supplied target with fixed extensions and preservation guards."""
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size < 1:
        raise ValueError("Batch size must be a positive integer")
    for name in targets:
        _relative(name)
    report = require_preserved(root)
    prefix = [sys.executable, "-m", "ruff", "check", "--force-exclude"] + compatibility_args(report)
    result = 0
    try:
        for start in range(0, len(targets), batch_size):
            result = subprocess.run(prefix + ["--"] + targets[start : start + batch_size], cwd=root).returncode
            if result:
                break
    finally:
        require_preserved(root)
    return result


def main() -> int:
    try:
        return run_ruff(Path(__file__).absolute().parents[1], sys.argv[1:])
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("Strategy v2 lint compatibility refused: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
