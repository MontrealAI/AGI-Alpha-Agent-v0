from __future__ import annotations

from pathlib import Path


def test_ci_mutmut_step_uses_pyproject_config_only() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "mutmut run" in workflow
    assert "args+=(--paths-to-mutate" not in workflow
    assert "args+=(--runner" not in workflow
    assert 'mutmut run --runner "pytest -q"' not in workflow


def test_ci_mutmut_step_rejects_legacy_cli_flags() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "rejects legacy CLI flags" in workflow


def test_mutmut_paths_configured_in_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.mutmut]" in pyproject
    assert "alpha_factory_v1/demos/alpha_agi_insight_v1/src" in pyproject
