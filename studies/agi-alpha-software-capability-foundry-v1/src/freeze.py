# SPDX-License-Identifier: Apache-2.0
"""Prospective source boundary; verification never rewrites a boundary."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

def verify(root: Path) -> dict:
    path = root / "protocol/FREEZE.json"
    record = json.loads(path.read_text())
    for name, expected in record["files"].items():
        current = root / name
        if not current.is_file() or hashlib.sha256(current.read_bytes()).hexdigest() != expected:
            raise ValueError("Frozen source differs: " + name)
    return {"passed": True, "files": len(record["files"]), "freeze_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
