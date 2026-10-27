# SPDX-License-Identifier: Apache-2.0
"""Read-only verification of every entry in the delivered evidence manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def verify(manifest_path: Path) -> tuple[int, int]:
    manifest_path = manifest_path.resolve(strict=True)
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("schema") != "next-advantage-evidence/v1" or not isinstance(manifest.get("files"), list):
        raise ValueError("unsupported evidence manifest schema")
    errors = []
    seen = set()
    total = 0
    for entry in manifest["files"]:
        if not isinstance(entry, dict):
            raise ValueError("manifest file entries must be objects")
        name = entry.get("path")
        expected = entry.get("sha256")
        size = entry.get("bytes")
        if not isinstance(name, str) or name in seen:
            raise ValueError("manifest paths must be unique strings")
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("manifest path must stay inside the study")
        if not isinstance(expected, str) or len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("invalid SHA-256 entry: " + name)
        if type(size) is not int or size < 0:
            raise ValueError("invalid byte count: " + name)
        seen.add(name)
        path = root / relative
        try:
            if any(parent.is_symlink() for parent in [path, *path.parents] if parent != root.parent):
                raise ValueError("symbolic link is not a regular evidence file")
            resolved = path.resolve(strict=True)
            if not resolved.is_relative_to(root) or not resolved.is_file():
                raise ValueError("missing or non-regular evidence file")
            actual = hashlib.sha256()
            count = 0
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    count += len(block)
                    actual.update(block)
            if count != size or actual.hexdigest() != expected:
                errors.append(name + ": byte count or SHA-256 mismatch")
            total += count
        except (OSError, ValueError) as error:
            errors.append(name + ": " + str(error))
    if errors:
        raise ValueError("Evidence verification failed:\n" + "\n".join(errors))
    return len(seen), total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("evidence_manifest.json"))
    args = parser.parse_args()
    try:
        count, size = verify(args.manifest)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    print(f"PASS: {count} files and {size} bytes match the delivered manifest; no files changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
