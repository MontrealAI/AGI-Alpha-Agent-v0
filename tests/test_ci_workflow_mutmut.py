from __future__ import annotations

from pathlib import Path


def test_ci_mutmut_step_is_config_driven() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "mutmut --version" in workflow
    assert 'PYTEST_ADDOPTS="tests/test_mutation_smoke_target.py -q" timeout 20m mutmut run' in workflow
    assert "[tool.mutmut] must be configured in pyproject.toml" in workflow
    assert "[tool.mutmut].paths_to_mutate must be configured" in workflow
    assert "[tool.mutmut].pytest_add_cli_args_test_selection must be configured" in workflow
    assert "args+=(--paths-to-mutate" not in workflow
    assert "args+=(--runner" not in workflow
    assert "mutmut run --paths-to-mutate" not in workflow
    assert "mutmut run --runner" not in workflow


def test_mutmut_paths_configured_in_pyproject() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.mutmut]" in pyproject
    assert "scripts/mutation_smoke_target.py" in pyproject
    assert "pytest_add_cli_args_test_selection" in pyproject
    assert "mutate_only_covered_lines = true" in pyproject


def test_mutmut_version_is_pinned_in_dev_lockfile() -> None:
    lock = Path("requirements-dev.lock").read_text(encoding="utf-8")
    assert "mutmut==3.3.0 \\" in lock


def test_integration_tests_have_finite_headroom_without_reducing_scope() -> None:
    import yaml

    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    tests = workflow["jobs"]["tests"]
    assert tests["timeout-minutes"] == 90
    assert tests["strategy"]["fail-fast"] is False
    assert tests["strategy"]["matrix"]["python-version"] == '${{ fromJSON(\'["3.11","3.12"]\') }}'
    assert not tests.get("continue-on-error")
    steps = tests["steps"]
    coverage = next(step for step in steps if step.get("name") == "Run tests with coverage")
    assert "if" not in coverage and not coverage.get("continue-on-error")
    assert (
        "pytest --cov --cov-report=xml:artifacts/coverage.xml --cov-fail-under=80 "
        "--junitxml=artifacts/test-reports/pytest.xml --durations=25"
    ) in coverage["run"]
    assert next(step for step in steps if step.get("name") == "Upload pytest results")["if"] == "always()"
