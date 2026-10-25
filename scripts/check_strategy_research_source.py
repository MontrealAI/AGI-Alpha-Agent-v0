#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify inert research bytes and a finite, exact Ruff compatibility profile."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import sys
import tomllib
from pathlib import Path, PurePosixPath
from typing import Any

SOURCE_COMMIT = "d69133291d72942c7d5f6be8ee0571cd83267110"
PINS_FILE = Path(__file__).with_name("strategy_research_source_pins.json")
# This proposed identity is reviewed with this source; there is no regeneration mode.
PINS_SHA256 = "c1e49a841fcb33849dec5a8e54849b6aa8a4625e85991664b28a404c5da8bb52"
STUDY = "studies/agi-alpha-flywheel-strategy-succession-v1"
ALLOWED_RULES = {"E701", "E702", "F841"}
CONFIG_NAMES = ("ruff.toml", ".ruff.toml", "pyproject.toml")
NON_RUFF_PROJECT = "contrib/strategy_succession/pyproject.toml"


def _relative(name: str) -> None:
    path = PurePosixPath(name)
    if not name or path.is_absolute() or "\\" in name or ":" in name or ".." in path.parts:
        raise ValueError("Pinned paths must remain relative regular source paths")
    if path.as_posix() != name:
        raise ValueError("Pinned paths must be canonical")


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


def load_pins() -> dict[str, Any]:
    """Read only the fixed, checksum-bound pin table supplied with this script."""
    raw = _capture(PINS_FILE.absolute(), maximum=256_000)
    if hashlib.sha256(raw).hexdigest() != PINS_SHA256:
        raise ValueError("Static pin table differs from the proposed reviewed identity")
    value: dict[str, Any] = json.loads(raw, object_pairs_hook=_unique_pairs)
    if (
        value.get("schema") != "agialpha.strategy-research-static-pins/v1"
        or value.get("source_commit") != SOURCE_COMMIT
    ):
        raise ValueError("Static pin source identity changed")
    if value.get("study_namespace") != STUDY or value.get("original_study_file_count") != 239:
        raise ValueError("The original research inventory cannot be replaced")
    files, exceptions = value["files"], value["ruff_per_file_ignores"]
    if len([name for name in files if name.startswith(STUDY + "/")]) != 239:
        raise ValueError("The complete original study inventory is required")
    for name, identity in files.items():
        _relative(name)
        if type(identity.get("bytes")) is not int or identity["bytes"] < 0:
            raise ValueError("Static byte identities require nonnegative integer sizes")
        if not re.fullmatch(r"[0-9a-f]{64}", identity.get("sha256", "")):
            raise ValueError("Static source identities require SHA256")
    if set(value["allowed_compatibility_rules"]) != ALLOWED_RULES:
        raise ValueError("Compatibility cannot add lint rule families")
    for name, rules in exceptions.items():
        if name not in files or not name.endswith(".py") or not rules or len(set(rules)) != len(rules):
            raise ValueError("Every compatibility entry needs one exact pinned Python body")
        if not set(rules) <= ALLOWED_RULES:
            raise ValueError("Compatibility cannot suppress another rule")
    if set(value.get("non_ruff_project_configs", {})) != {NON_RUFF_PROJECT}:
        raise ValueError("Only the exact reviewed non-Ruff package metadata may coexist")
    return value


def expected_ruff_config(pins: dict[str, Any]) -> dict[str, Any]:
    """Describe the exact existing Ruff scope plus this finite compatibility map."""
    expected: dict[str, Any] = copy.deepcopy(pins["ruff_baseline"])
    expected.setdefault("lint", {})["per-file-ignores"] = copy.deepcopy(pins["ruff_per_file_ignores"])
    return expected


def check(root: Path) -> dict[str, Any]:
    """Check inert bytes and effective configuration; never import research source."""
    root = root.resolve(strict=True)
    pins = load_pins()
    checks: list[dict[str, Any]] = []
    for name, identity in pins["files"].items():
        item: dict[str, Any] = {"path": name, "expectedSha256": identity["sha256"], "expectedBytes": identity["bytes"]}
        try:
            body = _capture(root / name, identity["bytes"])
            actual = hashlib.sha256(body).hexdigest()
            item.update(matched=actual == identity["sha256"], sha256=actual)
        except (OSError, ValueError) as error:
            item.update(matched=False, reason=str(error))
        checks.append(item)
    metadata_checks: list[dict[str, Any]] = []
    for name, identity in pins["non_ruff_project_configs"].items():
        item = {"path": name, "expectedSha256": identity["sha256"], "expectedBytes": identity["bytes"]}
        try:
            body = _capture(root / name, identity["bytes"])
            actual = hashlib.sha256(body).hexdigest()
            metadata = tomllib.loads(body.decode("utf-8"))
            tool = metadata.get("tool", {})
            if not isinstance(tool, dict):
                raise ValueError("Project metadata tool configuration must be a table")
            has_ruff = "ruff" in tool
            item.update(matched=actual == identity["sha256"] and not has_ruff, sha256=actual, ruffTablePresent=has_ruff)
        except (OSError, ValueError) as error:
            item.update(matched=False, reason=str(error))
        metadata_checks.append(item)
    config_errors: list[str] = []
    try:
        config = tomllib.loads(_capture(root / "pyproject.toml", maximum=1_000_000).decode("utf-8"))
        if config.get("tool", {}).get("ruff") != expected_ruff_config(pins):
            config_errors.append("Ruff configuration differs from the exact finite compatibility profile")
    except (OSError, ValueError) as error:
        config_errors.append(str(error))
    ancestors: set[Path] = {root}
    for name in pins["files"]:
        current = (root / name).parent
        while current != root:
            ancestors.add(current)
            current = current.parent
    for directory in sorted(ancestors):
        for name in CONFIG_NAMES:
            target = directory / name
            if target == root / "pyproject.toml":
                continue
            if target.relative_to(root).as_posix() in pins["non_ruff_project_configs"]:
                continue
            if target.exists() or target.is_symlink():
                config_errors.append(
                    "Unreviewed Ruff configuration can override guarded source: " + target.relative_to(root).as_posix()
                )
    matched = all(item["matched"] is True for item in [*checks, *metadata_checks]) and not config_errors
    return {
        "schema": "agialpha.strategy-research-source-preservation/v1",
        "sourceCommit": SOURCE_COMMIT,
        "pinsSha256": PINS_SHA256,
        "status": "STATIC_SOURCE_AND_LINT_PROFILE_PRESERVED" if matched else "STATIC_SOURCE_OR_LINT_PROFILE_DRIFT",
        "matched": matched,
        "checks": checks,
        "projectConfigurationChecks": metadata_checks,
        "configurationErrors": config_errors,
        "scope": "Inert source identity and exact lint compatibility only; configured review remains required. "
        "No scientific result, execution permission, original restriction disposition or production authority is granted.",
        "runtimeQualified": False,
        "productionAuthority": False,
    }


def require_preserved(root: Path) -> dict[str, Any]:
    """Fail before lint when preserved source or its finite compatibility scope differs."""
    report = check(root)
    if report["matched"] is not True:
        raise ValueError("Strategy research source or exact lint compatibility profile drifted")
    return report


def main() -> int:
    if len(sys.argv) != 1:
        print("This fixed guard accepts no root, source, pin or regeneration selectors.", file=sys.stderr)
        return 2
    try:
        report = check(Path(__file__).resolve().parents[1])
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({"matched": False, "reason": str(error), "productionAuthority": False}))
        return 1
    print(json.dumps(report, indent=2))
    return 0 if report["matched"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
