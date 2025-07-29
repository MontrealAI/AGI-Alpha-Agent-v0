#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Ensure requirements.lock is in sync with requirements.txt."""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    req_txt = repo_root / "requirements.txt"
    lock_file = repo_root / "requirements.lock"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "requirements.lock"
        pip_compile = shutil.which("pip-compile")
        if pip_compile:
            cmd = [pip_compile]
        else:
            cmd = [sys.executable, "-m", "piptools", "compile"]
        wheelhouse = os.getenv("WHEELHOUSE")
        cmd += ["--generate-hashes", "--quiet"]
        if wheelhouse:
            wheelhouse_path = str(Path(wheelhouse))
            cmd += ["--no-index", "--find-links", wheelhouse_path]
        cmd += [str(req_txt), "-o", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            return result.returncode
        if out_path.read_bytes() != lock_file.read_bytes():
            extra = ""
            if wheelhouse:
                extra = f"--no-index --find-links {shlex.quote(wheelhouse_path)} "
            sys.stderr.write(
                f"requirements.lock is outdated. Run 'pip-compile {extra}--generate-hashes --quiet "
                "requirements.txt -o requirements.lock'\n"
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
