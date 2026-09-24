#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Install verified release assets into a new Python 3.11–3.13 virtual environment."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=Path.cwd())
    parser.add_argument("--venv", type=Path, default=Path(".venv-agent"))
    parser.add_argument("--wheelhouse", type=Path)
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        parser.error("Python 3.11, 3.12 or 3.13 is required")
    root = args.release_dir.resolve()
    checksums = {}
    for line in (root / "SHA256SUMS").read_text().splitlines():
        expected, name = line.split(maxsplit=1)
        name = name.lstrip("*")
        if Path(name).name != name or len(expected) != 64:
            raise ValueError("invalid release checksum manifest")
        checksums[name] = expected
    wheels = list(root.glob("alpha_factory_v1-*.whl"))
    if len(wheels) != 1:
        raise ValueError("release directory must contain exactly one Alpha Factory wheel")
    required = [wheels[0], root / "requirements-agent.lock"]
    for path in required:
        if path.name not in checksums or hashlib.sha256(path.read_bytes()).hexdigest() != checksums[path.name]:
            raise ValueError(f"release checksum mismatch: {path.name}")
    target = args.venv.resolve()
    if target.exists():
        raise FileExistsError("virtual environment already exists; select a new directory")
    venv.EnvBuilder(with_pip=True).create(target)
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    offline = ["--no-index", "--find-links", str(args.wheelhouse.resolve())] if args.wheelhouse else []
    subprocess.run(
        [str(python), "-m", "pip", "install", *offline, "--require-hashes", "-r", str(required[1])], check=True
    )
    subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheels[0])], check=True)
    subprocess.run([str(python), "-m", "pip", "check"], check=True)
    executable = target / ("Scripts/alpha-agent.exe" if os.name == "nt" else "bin/alpha-agent")
    subprocess.run([str(executable), "--version"], check=True)
    print(f"Installed. Initialize a new private agent with: {executable} init")


if __name__ == "__main__":
    main()
