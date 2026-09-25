# SPDX-License-Identifier: Apache-2.0
"""Python/PowerShell entry point for the canonical offline-capable browser build.

The former independent compiler is preserved verbatim in
``build/manual_build_legacy.py.txt`` for historical reference.
"""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    if sys.version_info < (3, 11):
        sys.exit("Python >=3.11 required")
    root = Path(__file__).resolve().parent
    env = os.environ.copy()
    env["PATH"] = str(root / "node_modules" / ".bin") + os.pathsep + env.get("PATH", "")
    if shutil.which("tsc", path=env["PATH"]) is None:
        sys.exit("TypeScript compiler not found – run `npm ci` first.")
    if shutil.which("node", path=env["PATH"]) is None:
        sys.exit("Node.js 22+ is required.")
    # The shared pipeline bundles all workers and applies identical CSP,
    # integrity, cache, asset checks and offline sandbox preparation.
    return subprocess.call(["node", "build.js", *sys.argv[1:]], cwd=root, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
