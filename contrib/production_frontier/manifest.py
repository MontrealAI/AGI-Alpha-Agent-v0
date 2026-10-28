# SPDX-License-Identifier: Apache-2.0
"""Fail closed on changed frozen source, acceptance, policy or case generation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def freeze(root: Path, paths: list[str], destination: Path) -> dict[str, Any]:
    """Create a new manifest once; a revision needs a new named experiment."""
    if destination.exists():
        raise FileExistsError("an existing frozen experiment cannot be overwritten")
    records = {}
    for name in sorted(paths):
        path = root / name
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root.resolve()):
            raise ValueError("freeze requires regular files inside the chosen source root")
        records[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"schema": "production-frontier-freeze/v1", "files": records}
    with destination.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def verify_freeze(root: Path, manifest: dict[str, Any]) -> None:
    """Verify raw bytes before execution; a name or old result is insufficient."""
    if manifest.get("schema") != "production-frontier-freeze/v1" or not manifest.get("files"):
        raise ValueError("invalid frozen manifest")
    for name, expected in manifest["files"].items():
        path = root / name
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.resolve().is_relative_to(root.resolve())
            or hashlib.sha256(path.read_bytes()).hexdigest() != expected
        ):
            raise ValueError(f"frozen input changed: {name}")
