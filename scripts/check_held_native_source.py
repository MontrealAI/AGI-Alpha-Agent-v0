# SPDX-License-Identifier: Apache-2.0
"""Preserve five reviewed source identities without importing or testing their behavior."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import sys
from pathlib import Path
from typing import Mapping

BASELINE_COMMIT = "f9d2e3ff90ba6c8f1fcf85a3160d820e5dcb80c9"
# These are exact identities reviewed for this finite experimental coverage scope.
# Updating them requires a new eligible, exact-source coverage disposition.
PINNED_FILES = {
    "tests/test_successor_capability_delivery.py": (
        40493,
        "db4fac243db988b418968d8fbb11ae38b5a88ca86d703d5643583ab2c57b84f1",
    ),
    "tests/browser/fleet_receipt_native.mjs": (
        17520,
        "52e57f09122ddb0cbfa41e3932a5bc089d98234a330a4cae1747c405bd824c85",
    ),
    "tests/browser/fleet_git_metadata.mjs": (
        4323,
        "6f778aef9b870b4560a507ca6479f9f004932f453b2d2c25ac27bec4153a4686",
    ),
    "tests/browser/fleet_module_boundary.mjs": (
        8953,
        "8d3575ece582c158c30f3cc1c5f438b9b32ad2a31f190d6867acf9712beedad5",
    ),
    "tests/browser/test_discovery_lab_continuation.py": (
        18984,
        "f3113b522c3f9264931fdce6f11b066a9203d0043a569385717444f97006a966",
    ),
}


def _file_identity(target: Path, expected_bytes: int) -> tuple[int, str]:
    """Read one direct regular file, retaining descriptor/path stability checks."""
    if target.resolve(strict=True) != target:
        raise ValueError("Source path or ancestor is a symlink")
    selected = target.lstat()
    if not stat.S_ISREG(selected.st_mode):
        raise ValueError("Source must be a regular file")
    descriptor = os.open(target, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0))
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (selected.st_dev, selected.st_ino):
            raise ValueError("Selected source changed before capture")
        if before.st_size != expected_bytes:
            raise ValueError("Source byte count differs from its exact reviewed identity")
        digest = hashlib.sha256()
        count = 0
        # The extra byte detects growth; the reviewed byte count is an identity,
        # not a general file-size policy or a configurable admission limit.
        while count <= expected_bytes:
            raw = os.read(descriptor, min(65536, expected_bytes + 1 - count))
            if not raw:
                break
            count += len(raw)
            digest.update(raw)
        after = os.fstat(descriptor)
        current = target.lstat()
        keys = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        if count != expected_bytes or any(getattr(before, key) != getattr(after, key) for key in keys):
            raise ValueError("Source changed during capture")
        if target.resolve(strict=True) != target or any(getattr(after, key) != getattr(current, key) for key in keys):
            raise ValueError("Source path changed during capture")
        return count, digest.hexdigest()
    finally:
        os.close(descriptor)


def check_identities(root: Path, pins: Mapping[str, tuple[int, str]]) -> list[dict[str, object]]:
    """Compare inert bytes only; callers cannot select code through this check."""
    root = root.resolve(strict=True)
    results: list[dict[str, object]] = []
    for name, (size, expected) in pins.items():
        result: dict[str, object] = {"path": name, "expectedBytes": size, "expectedSha256": expected}
        try:
            count, actual = _file_identity(root / name, size)
            result.update(bytes=count, sha256=actual, matched=actual == expected)
            if actual != expected:
                result["reason"] = "Source digest differs from its exact reviewed identity"
        except (OSError, ValueError) as error:
            result.update(matched=False, reason=str(error))
        results.append(result)
    return results


def main() -> int:
    if len(sys.argv) != 1:
        print("This fixed identity guard accepts no source, manifest or root selectors.", file=sys.stderr)
        return 2
    checks = check_identities(Path(__file__).resolve().parents[1], PINNED_FILES)
    matched = all(item["matched"] is True for item in checks)
    print(
        json.dumps(
            {
                "schema": "agialpha.held-native-source-preservation.v1",
                "baselineCommit": BASELINE_COMMIT,
                "status": "STATIC_SOURCE_IDENTITY_PRESERVED" if matched else "STATIC_SOURCE_IDENTITY_DRIFT",
                "checks": checks,
                "omittedBehaviorQualified": False,
                "scope": "Regular-file identity only. No target test is imported or run; no omitted outcome or later "
                "invocation is qualified, and the original action restrictions remain unchanged.",
            },
            indent=2,
        )
    )
    return 0 if matched else 1


if __name__ == "__main__":
    raise SystemExit(main())
