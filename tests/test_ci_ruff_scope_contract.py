# SPDX-License-Identifier: Apache-2.0
"""Regression guards for explicit Ruff target selection in CI workflows."""

from __future__ import annotations

from pathlib import Path


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
