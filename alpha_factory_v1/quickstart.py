#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Cross-platform source launcher with explicit operator and research profiles."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def _venv_python(venv: Path) -> Path:
    """Return the interpreter path for the current platform."""
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _venv_pip(venv: Path) -> Path:
    """Retain the historical helper for callers inspecting their environment."""
    return venv / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")


def _create_venv(venv: Path, requirements: Path | None = None, wheelhouse: Path | None = None) -> None:
    """Install one locked profile into a new environment; retain failed evidence."""
    requirements = requirements or Path(__file__).resolve().with_name("requirements.lock")
    marker = venv / ".alpha-factory-bootstrap.json"
    if venv.exists():
        if not _venv_python(venv).is_file():
            raise ValueError("Existing environment has no interpreter; choose a new --venv path")
        if marker.exists():
            state = json.loads(marker.read_text(encoding="utf-8"))
            if state != {"requirements": requirements.name, "complete": True}:
                raise ValueError("Partial or different-profile environment; choose a new --venv path")
        subprocess.check_call([str(_venv_python(venv)), "-m", "pip", "check"])
        return
    subprocess.check_call([sys.executable, "-m", "venv", str(venv)])
    marker.write_text(json.dumps({"requirements": requirements.name, "complete": False}), encoding="utf-8")
    command = [str(_venv_python(venv)), "-m", "pip", "install", "--require-hashes", "-r", str(requirements)]
    if wheelhouse:
        command += ["--no-index", "--find-links", str(wheelhouse)]
    subprocess.check_call(command)
    subprocess.check_call([str(_venv_python(venv)), "-m", "pip", "check"])
    marker.write_text(json.dumps({"requirements": requirements.name, "complete": True}), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """Check or launch without changing the caller's environment or overwriting data."""
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--profile", choices=("agent", "legacy"), default="legacy")
    parser.add_argument("--venv", type=Path, help="Separate environment path (resolved from the invoking directory)")
    parser.add_argument("--wheelhouse", type=Path, help="Install only from local dependency wheels")
    parser.add_argument(
        "--offline", action="store_true", help="Disable network preflight; require wheels for a new install"
    )
    parser.add_argument("--preflight", action="store_true", help="Check only; do not install or launch")
    parser.add_argument("--skip-preflight", action="store_true", help="Explicitly skip checks before launching")
    parser.add_argument("--wizard", action="store_true", help="Ask before creating a new environment")
    args, forwarded = parser.parse_known_args(argv)
    if forwarded[:1] == ["--"]:
        forwarded = forwarded[1:]
    repo = Path(__file__).resolve().parents[1]
    venv = (args.venv or repo / (".venv-agent" if args.profile == "agent" else ".venv")).resolve()
    wheels = args.wheelhouse or (Path(os.environ["WHEELHOUSE"]) if os.environ.get("WHEELHOUSE") else None)
    wheels = wheels.resolve() if wheels else None
    environment = {**os.environ, "PYTHONPATH": str(repo) + os.pathsep + os.environ.get("PYTHONPATH", "")}
    checks = [str(repo / "alpha_factory_v1/scripts/preflight.py"), "--profile", args.profile]
    if args.offline or wheels:
        checks.append("--offline")
    try:
        if not (3, 11) <= sys.version_info[:2] < (3, 14):
            raise ValueError("Python >=3.11,<3.14 is required")
        if wheels and not wheels.is_dir():
            raise ValueError("The wheelhouse must be an existing directory")
        if args.preflight:
            interpreter = _venv_python(venv) if _venv_python(venv).is_file() else Path(sys.executable)
            subprocess.check_call([str(interpreter), *checks], cwd=repo, env=environment)
            return 0
        if args.offline and not wheels and not venv.exists():
            raise ValueError("Offline installation requires --wheelhouse or an existing environment")
        if args.wizard and not venv.exists():
            if input(f"Create the {args.profile} environment at {venv}? [y/N] ").strip().lower() not in {"y", "yes"}:
                return 0
        requirements = repo / (
            "requirements-agent.lock" if args.profile == "agent" else "alpha_factory_v1/requirements.lock"
        )
        _create_venv(venv, requirements, wheels)
        py = str(_venv_python(venv))
        if not args.skip_preflight:
            subprocess.check_call([py, *checks], cwd=repo, env=environment)
        module = "alpha_factory_v1.core.runtime.cli" if args.profile == "agent" else "alpha_factory_v1.run"
        if args.profile == "agent" and not forwarded:
            forwarded = ["--help"]
        subprocess.check_call([py, "-m", module, *forwarded], env=environment)
        return 0
    except (OSError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"Quickstart stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
