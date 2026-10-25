# SPDX-License-Identifier: Apache-2.0
"""Regression guards for explicit Ruff target selection in CI workflows."""

from __future__ import annotations

from pathlib import Path
import re

import yaml


def test_integration_ci_ruff_step_uses_target_script() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "name: Ruff lint" in workflow
    assert "run: python scripts/ruff_targets.py --run" in workflow
    assert "name: Ruff lint\n        run: python -m ruff check ." not in workflow


def test_pr_ci_ruff_step_uses_target_script() -> None:
    workflow = Path(".github/workflows/pr-ci.yml").read_text(encoding="utf-8")

    assert "name: Ruff check" in workflow
    assert "run: python scripts/ruff_targets.py --run" in workflow
    assert "run: python -m ruff check ." not in workflow


def test_ruff_exclude_contains_git_metadata() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "exclude = [" in pyproject
    assert '".git"' in pyproject


def test_pre_commit_ruff_matches_locked_ci_version_without_rule_or_fix_changes() -> None:
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repo = next(item for item in config["repos"] if item["repo"] == "https://github.com/astral-sh/ruff-pre-commit")
    # This upstream immutable commit declares ruff==0.12.5 and retains the legacy
    # ruff hook alias; changing the lock requires separately checking its mirror.
    assert repo["rev"] == "73b0f6d59bbfcb75e17a4653d581c9dfaca13969"
    locked = re.search(r"(?m)^ruff==([^\s\\]+)", Path("requirements-dev.lock").read_text(encoding="utf-8"))
    assert locked is not None and locked.group(1) == "0.12.5"
    assert repo["hooks"] == [
        {"id": "ruff", "exclude": "alpha_factory_v1/backend/agent_factory.py"},
        {"id": "ruff-format", "exclude": "alpha_factory_v1/backend/agent_factory.py"},
    ]


def test_release_quality_checks_committed_delta_before_blocking_hooks() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["quality"]["steps"]
    checks = next(
        step for step in steps if step.get("name") == "Verify immutable sources and committed release evidence"
    )
    assert checks["run"].splitlines() == [
        "python scripts/check_strategy_research_source.py",
        "python scripts/check_no_binary_diff.py --base 5499495911bf8822ac0aa8c9007f00789c1132b5",
        "python scripts/dp_scrubber.py --base 5499495911bf8822ac0aa8c9007f00789c1132b5",
    ]
    assert checks.get("if") is None
    assert checks.get("continue-on-error", False) is False
    hooks = next(step for step in steps if step.get("name") == "Require the blocking repository hook report")
    assert steps.index(checks) < steps.index(hooks)


def test_strategy_security_hook_keeps_pinned_tool_and_always_checks_fixed_python_scope() -> None:
    config = yaml.safe_load(Path(".pre-commit-config.yaml").read_text(encoding="utf-8"))
    repo = next(item for item in config["repos"] if item["repo"] == "https://github.com/semgrep/semgrep")
    assert repo["rev"] == "2bbd0a55b3655b26991c936b92e0c0f6d6f4fa94"
    assert repo["hooks"] == [
        {
            "id": "semgrep",
            "entry": "python -I scripts/check_strategy_python_security.py",
            "args": [],
            "additional_dependencies": ["setuptools>=75,<81"],
            "types": ["python"],
            "pass_filenames": False,
            "always_run": True,
        }
    ]


def test_release_quality_requires_actual_security_regressions_after_installed_hooks() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["quality"]["steps"]
    regressions = next(
        step for step in steps if step.get("name") == "Verify scoped security hook with its installed tool"
    )
    assert regressions["run"] == (
        "STRATEGY_REQUIRE_SEMGREP=1 python -m pytest --noconftest -o addopts= "
        "-p no:cacheprovider tests/test_strategy_python_security.py -q"
    )
    assert regressions.get("if") is None
    assert regressions.get("continue-on-error", False) is False
    hooks = next(step for step in steps if step.get("name") == "Require blocking hooks on every release change")
    assert steps.index(regressions) > steps.index(hooks)
