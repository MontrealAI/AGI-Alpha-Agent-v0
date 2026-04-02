# SPDX-License-Identifier: Apache-2.0
"""Validator registry aligned with the repository's canonical CI surfaces.

The command plans mirror the current CI gates:
- ✅ PR CI (ruff + smoke pytest subset)
- 🚀 CI — Insight Demo (mypy, full pytest, mkdocs --strict)
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

from .models import ValidatorClass

PYTHON = sys.executable


@dataclass(frozen=True)
class ValidatorPlan:
    """Targeted validator command plus broader follow-up command."""

    targeted: list[str]
    broader: list[str]


REGISTRY: dict[ValidatorClass, ValidatorPlan] = {
    ValidatorClass.RUFF: ValidatorPlan(
        targeted=["ruff", "check", "."],
        broader=[PYTHON, "-m", "pytest", "-m", "smoke", "tests/test_ping_agent.py", "tests/test_af_requests.py", "-q"],
    ),
    ValidatorClass.MYPY: ValidatorPlan(
        targeted=["mypy", "--config-file", "mypy.ini", "."],
        broader=[PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "tests/test_af_requests.py", "-q"],
    ),
    ValidatorClass.IMPORT: ValidatorPlan(
        targeted=[PYTHON, "-m", "pytest", "tests/test_imports.py", "-q"],
        broader=[PYTHON, "-m", "pytest", "tests/test_ping_agent.py", "tests/test_af_requests.py", "-q"],
    ),
    ValidatorClass.PYTEST: ValidatorPlan(
        targeted=[
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
        broader=[PYTHON, "-m", "pytest", "-q"],
    ),
    ValidatorClass.SMOKE: ValidatorPlan(
        targeted=[
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


def canonical_ci_surface() -> dict[str, list[str]]:
    """Expose the current canonical CI workflows consumed by Repo-Healer."""
    return {
        "pr_gate": ["✅ PR CI"],
        "full_ci": ["🚀 CI — Insight Demo"],
        "optional": ["🔥 Smoke Test", "📚 Docs"],
    }
