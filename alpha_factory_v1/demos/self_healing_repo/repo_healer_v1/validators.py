# SPDX-License-Identifier: Apache-2.0
"""Validator registry for targeted and broader replay commands."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

PYTHON = sys.executable


@dataclass(frozen=True)
class ValidatorPlan:
    """Targeted and broader validation commands."""

    targeted: list[str]
    broader: list[str]


REGISTRY: dict[str, ValidatorPlan] = {
    "ruff": ValidatorPlan(["ruff", "check", "."], ["pre-commit", "run", "--all-files"]),
    "mypy": ValidatorPlan(["mypy", "--config-file", "mypy.ini", "."], [PYTHON, "-m", "pytest", "-q"]),
    "import": ValidatorPlan([PYTHON, "-m", "pytest", "tests/test_imports.py", "-q"], [PYTHON, "-m", "pytest", "-q"]),
    "pytest": ValidatorPlan([PYTHON, "-m", "pytest", "-q"], [PYTHON, "-m", "pytest", "-q"]),
    "mkdocs": ValidatorPlan(["mkdocs", "build", "--strict"], [PYTHON, "-m", "pytest", "tests/test_notebooks.py", "-q"]),
    "smoke": ValidatorPlan([PYTHON, "scripts/check_python_deps.py"], [PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "-q"]),
}


def run_validator(cmd: list[str], cwd: str) -> tuple[int, str]:
    """Run one validator command and return (exit_code, combined_output)."""
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return proc.returncode, proc.stdout + proc.stderr


def get_plan(key: str) -> ValidatorPlan:
    """Resolve validator plan by triage key."""
    return REGISTRY.get(key, REGISTRY["smoke"])
