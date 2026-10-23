#!/usr/bin/env python3
"""Verify the delivered companion's exact original files without executing them."""
from hashlib import sha256
from pathlib import Path
import sys

root = Path(__file__).resolve().parent
failures = []
count = 0
for line in (root / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines():
    expected, relative = line.split("  ", 1)
    path = root / relative
    if path.is_symlink() or not path.is_file():
        failures.append(f"Missing or non-regular: {relative}")
    elif sha256(path.read_bytes()).hexdigest() != expected:
        failures.append(f"Changed: {relative}")
    count += 1
for failure in failures:
    print(failure, file=sys.stderr)
print(f"Checked {count} original files; {len(failures)} mismatches. New run files are not part of this manifest.")
sys.exit(bool(failures))
