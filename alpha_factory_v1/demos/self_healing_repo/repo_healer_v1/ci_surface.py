# SPDX-License-Identifier: Apache-2.0
"""Discover canonical validator commands from repository workflow files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class CISurface:
    """Subset of CI commands relevant to Repo-Healer v1 replay."""

    pr_ruff_command: list[str]
    pr_smoke_command: list[str]


def discover_ci_surface(repo_root: Path) -> CISurface:
    """Read `.github/workflows/pr-ci.yml` and extract canonical run commands."""
    workflow = repo_root / ".github" / "workflows" / "pr-ci.yml"
    if not workflow.exists():
        return _defaults()

    try:
        payload = yaml.safe_load(workflow.read_text(encoding="utf-8"))
    except Exception:
        return _defaults()

    jobs = (payload or {}).get("jobs", {})
    lint_steps = jobs.get("lint", {}).get("steps", [])
    smoke_steps = jobs.get("smoke", {}).get("steps", [])
    ruff = _extract_run_command(lint_steps, "Ruff check") or _defaults().pr_ruff_command
    smoke = _extract_run_command(smoke_steps, "Run smoke tests") or _defaults().pr_smoke_command
    return CISurface(pr_ruff_command=ruff, pr_smoke_command=smoke)


def _extract_run_command(steps: list[dict[str, object]], step_name: str) -> list[str] | None:
    for step in steps:
        if str(step.get("name", "")) != step_name:
            continue
        run_block = str(step.get("run", ""))
        for line in run_block.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.endswith("\\"):
                return _split_command(run_block)
            return stripped.split()
        return None
    return None


def _split_command(block: str) -> list[str]:
    command = " ".join(line.strip().rstrip("\\") for line in block.splitlines() if line.strip())
    return command.split()


def _defaults() -> CISurface:
    return CISurface(
        pr_ruff_command=["ruff", "check", "."],
        pr_smoke_command=[
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
    )
