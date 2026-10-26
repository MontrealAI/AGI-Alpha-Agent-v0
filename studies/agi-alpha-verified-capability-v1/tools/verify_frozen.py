# SPDX-License-Identifier: Apache-2.0
"""Verify delivered frozen input identities without executing a mission."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def verify(root: Path, manifest_path: str) -> dict:
    raw = (root / manifest_path).read_bytes()
    manifest = json.loads(raw)
    seen = set()
    total = 0
    for row in manifest["files"]:
        relative = row["path"]
        if relative in seen:
            raise ValueError(f"Duplicate frozen path: {relative}")
        seen.add(relative)
        file = root / relative
        if not file.resolve().is_relative_to(root.resolve()):
            raise ValueError(f"Outside root: {relative}")
        for parent in [file, *file.parents]:
            if parent == root:
                break
            if parent.is_symlink():
                raise ValueError(f"Symlink in frozen path: {relative}")
        data = file.read_bytes()
        if hashlib.sha256(data).hexdigest() != row["sha256"] or len(data) != row["bytes"]:
            raise ValueError(f"Frozen bytes changed: {relative}")
        total += len(data)
    return {"manifest": manifest_path, "sha256": hashlib.sha256(raw).hexdigest(),
            "files": len(seen), "bytes": total, "status": "PASS"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = {"schema": "agi-alpha-delivered-freeze-verification/v1", "status": "PASS",
              "scope": "Byte custody only; no truth, live identity or economic assertion.",
              "results": [verify(args.root.resolve(), p) for p in
                          ["protocol/production-freeze.json", "protocol/market-freeze.json"]]}
    if args.output:
        with args.output.open("x") as output:
            output.write(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
