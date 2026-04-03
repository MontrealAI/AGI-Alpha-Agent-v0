# SPDX-License-Identifier: Apache-2.0
"""Validator registry aligned with the repository's canonical CI surfaces.

The command plans mirror the current CI gates:
- ✅ PR CI (ruff + smoke pytest subset)
- 🚀 CI — Insight Demo (mypy, full pytest, mkdocs --strict)
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from .models import ValidatorClass

PYTHON = sys.executable


@dataclass(frozen=True)
class ValidatorPlan:
    """Targeted validator command plus broader follow-up command."""

    targeted: list[str]
    broader: list[str]


DEFAULT_SMOKE_TARGETED = [
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
]

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
        targeted=DEFAULT_SMOKE_TARGETED,
        broader=[PYTHON, "-m", "pytest", "-q"],
    ),
    ValidatorClass.SMOKE: ValidatorPlan(
        targeted=DEFAULT_SMOKE_TARGETED,
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
    plan = REGISTRY.get(kind, REGISTRY[ValidatorClass.NONE])
    if kind not in {ValidatorClass.PYTEST, ValidatorClass.SMOKE}:
        return plan

    smoke_cmd = _extract_smoke_pytest_command()
    if not smoke_cmd:
        return plan
    return ValidatorPlan(targeted=smoke_cmd, broader=plan.broader)


def canonical_ci_surface() -> dict[str, list[str]]:
    """Expose canonical CI workflow names by reading current workflow files.

    Falls back to known defaults when workflow files are unavailable.
    """
    defaults = {
        "pr_gate": ["✅ PR CI"],
        "full_ci": ["🚀 CI — Insight Demo"],
        "optional": ["🔥 Smoke Test", "📚 Docs"],
    }
    repo_root = Path(__file__).resolve().parents[4]
    mapping = {
        "pr_gate": repo_root / ".github/workflows/pr-ci.yml",
        "full_ci": repo_root / ".github/workflows/ci.yml",
        "optional_smoke": repo_root / ".github/workflows/smoke.yml",
        "optional_docs": repo_root / ".github/workflows/docs.yml",
    }
    try:
        loaded: dict[str, str] = {}
        for key, path in mapping.items():
            if not path.exists():
                continue
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            name = payload.get("name")
            if isinstance(name, str) and name.strip():
                loaded[key] = name.strip()
        return {
            "pr_gate": [loaded.get("pr_gate", defaults["pr_gate"][0])],
            "full_ci": [loaded.get("full_ci", defaults["full_ci"][0])],
            "optional": [
                loaded.get("optional_smoke", defaults["optional"][0]),
                loaded.get("optional_docs", defaults["optional"][1]),
            ],
        }
    except Exception:
        return defaults


def _extract_smoke_pytest_command() -> list[str]:
    """Read PR CI workflow and extract the smoke pytest command."""
    workflow = Path(__file__).resolve().parents[4] / ".github/workflows/pr-ci.yml"
    if not workflow.exists():
        return []
    payload = yaml.safe_load(workflow.read_text(encoding="utf-8")) or {}
    jobs = payload.get("jobs", {})
    smoke = jobs.get("smoke", {}) if isinstance(jobs, dict) else {}
    steps = smoke.get("steps", []) if isinstance(smoke, dict) else []
    for step in steps:
        if not isinstance(step, dict):
            continue
        run = step.get("run")
        if not isinstance(run, str) or "pytest" not in run:
            continue
        cmd = _parse_first_pytest_command(run)
        if cmd:
            return cmd
    return []


def _parse_first_pytest_command(run_block: str) -> list[str]:
    """Parse the first pytest command from a workflow run block."""
    lines = [line.rstrip() for line in run_block.strip().splitlines() if line.strip()]
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("pytest "):
            continue
        command_parts = [stripped]
        cursor = index + 1
        while command_parts[-1].endswith("\\") and cursor < len(lines):
            command_parts[-1] = command_parts[-1][:-1].rstrip()
            command_parts.append(lines[cursor].strip())
            cursor += 1
        joined = " ".join(command_parts)
        tokens = shlex.split(joined)
        if not tokens:
            return []
        if tokens[0] == "pytest":
            return [PYTHON, "-m", *tokens]
        return tokens
    return []
