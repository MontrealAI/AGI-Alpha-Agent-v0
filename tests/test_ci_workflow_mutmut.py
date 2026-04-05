from __future__ import annotations

from pathlib import Path


def test_ci_mutmut_step_supports_legacy_and_current_cli() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "mutmut_help=\"$(mutmut run --help 2>&1 || true)\"" in workflow
    assert "printf '%s\\n' \"$mutmut_help\" | grep -q -- '--paths-to-mutate'" in workflow
    assert "using pyproject.toml [tool.mutmut] configuration" in workflow


def test_mutmut_paths_configured_in_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.mutmut]" in pyproject
    assert "alpha_factory_v1/demos/alpha_agi_insight_v1/src" in pyproject
