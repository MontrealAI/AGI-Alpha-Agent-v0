# SPDX-License-Identifier: Apache-2.0
"""Validator registry for targeted and broader replay commands."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

from .models import ValidatorClass

PYTHON = sys.executable


@dataclass(frozen=True)
class ValidatorPlan:
    """Targeted and broader validation commands."""

    targeted: list[str]
    broader: list[str]


REGISTRY: dict[ValidatorClass, ValidatorPlan] = {
    ValidatorClass.RUFF: ValidatorPlan(["ruff", "check", "."], ["pre-commit", "run", "--all-files"]),
    ValidatorClass.MYPY: ValidatorPlan(["mypy", "--config-file", "mypy.ini", "."], [PYTHON, "-m", "pytest", "-q"]),
    ValidatorClass.PYTEST: ValidatorPlan([PYTHON, "-m", "pytest", "-q"], [PYTHON, "-m", "pytest", "-q"]),
    ValidatorClass.SMOKE: ValidatorPlan(
        [
            PYTHON,
            "-m",
            "pytest",
            "-m",
            "smoke",
            "tests/test_af_requests.py",
            "tests/test_cache_version.py",
            "tests/test_check_env_core.py",
            "tests/test_check_env_network.py",
            "tests/test_config_settings.py",
            "tests/test_config_utils.py",
            "tests/test_ping_agent.py",
            "-q",
        ],
        [PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "tests/test_af_requests.py", "--cov", "--cov-report=xml"],
    ),
    ValidatorClass.DOCS: ValidatorPlan(["mkdocs", "build", "--strict"], ["mkdocs", "build", "--strict"]),
    ValidatorClass.NONE: ValidatorPlan(
        [PYTHON, "-c", "print('diagnose-only')"], [PYTHON, "-c", "print('diagnose-only')"]
    ),
}


def run_validator(cmd: list[str], cwd: str) -> tuple[int, str]:
    """Run one validator command and return (exit_code, combined_output)."""
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    return proc.returncode, proc.stdout + proc.stderr


def get_plan(validator_class: ValidatorClass) -> ValidatorPlan:
    """Resolve validator plan by class."""
    return REGISTRY.get(validator_class, REGISTRY[ValidatorClass.PYTEST])
