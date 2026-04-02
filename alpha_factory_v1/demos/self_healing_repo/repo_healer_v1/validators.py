# SPDX-License-Identifier: Apache-2.0
"""Validator registry aligned with the repository's canonical CI surfaces."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .ci_surface import discover_ci_surface
from .models import ValidatorClass

PYTHON = sys.executable
SURFACE = discover_ci_surface(Path.cwd())
SMOKE_ARGS = SURFACE.pr_smoke_command[1:] if SURFACE.pr_smoke_command[:1] == ["pytest"] else SURFACE.pr_smoke_command


@dataclass(frozen=True)
class ValidatorPlan:
    """Targeted validator command plus broader follow-up command."""

    targeted: list[str]
    broader: list[str]


REGISTRY: dict[ValidatorClass, ValidatorPlan] = {
    ValidatorClass.RUFF: ValidatorPlan(
        targeted=SURFACE.pr_ruff_command,
        broader=[PYTHON, "-m", "pytest", *SMOKE_ARGS],
    ),
    ValidatorClass.MYPY: ValidatorPlan(
        targeted=["mypy", "--config-file", "mypy.ini"],
        broader=[PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "tests/test_af_requests.py", "-q"],
    ),
    ValidatorClass.IMPORT: ValidatorPlan(
        targeted=[PYTHON, "-m", "pytest", "tests/test_imports.py", "-q"],
        broader=[PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "tests/test_af_requests.py", "-q"],
    ),
    ValidatorClass.PYTEST: ValidatorPlan(
        targeted=[PYTHON, "-m", "pytest", *SMOKE_ARGS],
        broader=[PYTHON, "-m", "pytest", *SMOKE_ARGS],
    ),
    ValidatorClass.SMOKE: ValidatorPlan(
        targeted=[PYTHON, "-m", "pytest", *SMOKE_ARGS],
        broader=[PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "tests/test_af_requests.py", "-q"],
    ),
    ValidatorClass.MKDOCS: ValidatorPlan(
        targeted=["mkdocs", "build", "--strict"],
        broader=[PYTHON, "scripts/check_python_deps.py"],
    ),
    ValidatorClass.NONE: ValidatorPlan(
        targeted=[PYTHON, "-c", "print('diagnose-only')"], broader=[PYTHON, "-c", "print('diagnose-only')"]
    ),
}


def run_validator(cmd: list[str], cwd: str) -> tuple[int, str]:
    """Run one validator command and return (exit_code, combined_output)."""
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return proc.returncode, proc.stdout + proc.stderr


def get_plan(kind: ValidatorClass) -> ValidatorPlan:
    """Resolve validator plan by triage validator class."""
    return REGISTRY.get(kind, REGISTRY[ValidatorClass.NONE])
