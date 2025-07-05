#!/usr/bin/env python
# SPDX-License-Identifier: Apache-2.0
"""Ensure alpha_factory_v1/requirements-colab.lock matches requirements-colab.txt."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    req_txt = repo_root / "alpha_factory_v1" / "requirements-colab.txt"
    lock_file = repo_root / "alpha_factory_v1" / "requirements-colab.lock"

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
            cmd += ["--no-index", "--find-links", wheelhouse]
        cmd += [str(req_txt), "-o", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        if result.returncode != 0:
            return result.returncode
        if out_path.read_bytes() != lock_file.read_bytes():
            extra = ""
            if wheelhouse:
                extra = f"--no-index --find-links {wheelhouse} "
            msg = (
                "alpha_factory_v1/requirements-colab.lock is outdated. Run 'pip-compile "
                f"{extra}--generate-hashes --quiet alpha_factory_v1/requirements-colab.txt -o "
                "alpha_factory_v1/requirements-colab.lock'\n"
            )
            sys.stderr.write(msg)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
