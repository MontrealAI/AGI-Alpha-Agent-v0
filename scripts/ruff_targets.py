#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Emit tracked Ruff lint targets for CI.

This helper defines a deterministic lint scope for explicit ``ruff check``
steps. It intentionally enumerates tracked Python sources from Git so metadata
under ``.git/`` (for example branch refs ending in ``.py``) cannot enter the
lint target list.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def tracked_python_targets(repo_root: Path) -> list[Path]:
    """Return tracked Python files under *repo_root*.

    Args:
        repo_root: Repository root containing the Git metadata.

    Returns:
        Sorted tracked ``.py`` and ``.pyi`` files relative to ``repo_root``.
    """

    cmd = ["git", "-C", str(repo_root), "ls-files", "-z", "--", "*.py", "*.pyi"]
    result = subprocess.run(cmd, capture_output=True, text=False, check=True)
    files = [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]
    return sorted(files)


def main() -> int:
    parser = argparse.ArgumentParser(description="Print tracked Ruff targets.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Path to the repository root (default: current directory).",
    )
    parser.add_argument(
        "--as-argv",
        action="store_true",
        help="Emit newline-delimited relative paths suitable for command substitution.",
    )
    args = parser.parse_args()

    targets = tracked_python_targets(args.repo_root.resolve())
    if not targets:
        print("No tracked Python files found.", file=sys.stderr)
        return 1

    if args.as_argv:
        for path in targets:
            print(path.as_posix())
        return 0

    print("\0".join(path.as_posix() for path in targets), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
