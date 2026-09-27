#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the same raw Ed25519 wheel signature required by the plugin loader."""

from __future__ import annotations

import sys
from pathlib import Path

from alpha_factory_v1.backend import agents as agents_mod


def verify(wheel_path: Path) -> bool:
    """Return ``True`` if ``wheel_path`` verifies against its ``.sig`` file."""
    return bool(agents_mod._verify_wheel(wheel_path))


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} <wheel>", file=sys.stderr)
        raise SystemExit(1)
    wheel = Path(sys.argv[1])
    if not wheel.is_file():
        print(f"Wheel not found: {wheel}", file=sys.stderr)
        raise SystemExit(1)
    if verify(wheel):
        print(f"OK: {wheel}")
        raise SystemExit(0)
    print(f"FAILED: {wheel}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
