#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Install verified release assets into a new Python 3.11–3.13 virtual environment."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import venv


def verify_assets(root: Path) -> tuple[Path, Path]:
    """Validate required local assets before creating or changing an environment."""
    manifest = root / "SHA256SUMS"
    if not manifest.is_file():
        raise ValueError("Download SHA256SUMS, the Alpha Factory wheel and requirements-agent.lock into --release-dir")
    checksums: dict[str, str] = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if not match:
            raise ValueError("Invalid SHA256SUMS; download it again from the same official release")
        expected, name = match.groups()
        if Path(name).name != name or "\\" in name or name in {".", ".."} or name in checksums:
            raise ValueError("Invalid or duplicate filename in SHA256SUMS")
        checksums[name] = expected.lower()
    wheels = list(root.glob("alpha_factory_v1-*.whl"))
    if len(wheels) != 1:
        raise ValueError("Release directory must contain exactly one Alpha Factory wheel; use an empty download folder")
    required = (wheels[0], root / "requirements-agent.lock")
    for path in required:
        if not path.is_file():
            raise ValueError(f"Missing release asset: {path.name}")
        if path.name not in checksums or hashlib.sha256(path.read_bytes()).hexdigest() != checksums[path.name]:
            raise ValueError(f"Release checksum mismatch: {path.name}; download matching assets again")
    return required


def main(argv: list[str] | None = None) -> int:
    """Check or install matching assets, reporting failures without touching old state."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=Path.cwd())
    parser.add_argument("--venv", type=Path, default=Path(".venv-agent"))
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--check-only", action="store_true", help="Verify inputs without installing or writing files")
    args = parser.parse_args(argv)
    if not (3, 11) <= sys.version_info[:2] < (3, 14):
        parser.error("Python 3.11, 3.12 or 3.13 is required")
    target = args.venv.expanduser().absolute()
    phase = "checking release inputs"
    try:
        required = verify_assets(args.release_dir.expanduser().resolve())
        if os.path.lexists(target):
            raise ValueError("Virtual environment path already exists; select a new --venv directory")
        wheels = args.wheelhouse.expanduser().resolve() if args.wheelhouse else None
        if wheels is not None and (not wheels.is_dir() or not any(wheels.glob("*.whl"))):
            raise ValueError("--wheelhouse must be an existing directory containing dependency wheels")
        if args.check_only:
            print(
                "Release checksums and installation paths verified. No environment was created or packages installed."
            )
            return 0
        phase = "creating the new virtual environment"
        venv.EnvBuilder(with_pip=True).create(target)
        python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        offline = ["--no-index", "--find-links", str(wheels)] if wheels is not None else []
        phase = "installing hash-locked dependencies"
        subprocess.run(
            [str(python), "-m", "pip", "install", *offline, "--require-hashes", "-r", str(required[1])], check=True
        )
        phase = "installing the verified wheel"
        subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(required[0])], check=True)
        phase = "checking installed dependencies"
        subprocess.run([str(python), "-m", "pip", "check"], check=True)
        executable = target / ("Scripts/alpha-agent.exe" if os.name == "nt" else "bin/alpha-agent")
        subprocess.run([str(executable), "--version"], check=True)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        detail = (
            f"command exited with status {exc.returncode}"
            if isinstance(exc, subprocess.CalledProcessError)
            else str(exc)
        )
        print(f"Installation stopped while {phase}: {detail}", file=sys.stderr)
        if phase != "checking release inputs":
            print(
                f"Partial environment retained at {target}. Resolve the error and retry with a new --venv path.",
                file=sys.stderr,
            )
        return 1
    command = (
        "& '" + str(executable).replace("'", "''") + "' init"
        if os.name == "nt"
        else shlex.join([str(executable), "init"])
    )
    shell = " in PowerShell" if os.name == "nt" else ""
    print(f"Installed. Initialize a new private agent{shell} with: {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
