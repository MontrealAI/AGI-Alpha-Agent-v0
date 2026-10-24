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


def test_integration_smoke_is_required_and_full_coverage_has_one_owner() -> None:
    import yaml

    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    tests = workflow["jobs"]["tests"]
    assert tests["timeout-minutes"] == 45
    assert tests["strategy"]["fail-fast"] is False
    assert tests["strategy"]["matrix"]["python-version"] == ["3.12"]
    assert not tests.get("continue-on-error")
    steps = tests["steps"]
    smoke = next(step for step in steps if step.get("name") == "Run focused integration smoke")
    assert "if" not in smoke and not smoke.get("continue-on-error")
    assert (
        "pytest --noconftest -o addopts= tests/test_ping_agent.py tests/test_af_requests.py "
        "tests/test_macro_simulation_boundaries.py tests/test_openai_bridge_integration.py "
        "-q --junitxml=artifacts/test-reports/pytest.xml"
    ) in smoke["run"]
    assert next(step for step in steps if step.get("name") == "Upload pytest results")["if"] == "always()"
    for name in ("Mutation tests", "Run benchmark", "Generate benchmark comment"):
        diagnostic = next(step for step in steps if step.get("name") == name)
        assert diagnostic["if"] == "github.event_name == 'workflow_dispatch'"
        assert diagnostic["continue-on-error"] is True
    release = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    regression = release["jobs"]["regression"]
    assert not regression.get("continue-on-error")
    coverage = next(
        step
        for step in regression["steps"]
        if step.get("name") == "Offline regression including notebooks (four held native tests excluded)"
    )
    assert "if" not in coverage and not coverage.get("continue-on-error")
    assert "python -m scripts.run_local_tests -q --cov" in coverage["run"]
    assert "--cov-fail-under=80" in coverage["run"]
    assert "--junitxml=evidence/regression.xml" in coverage["run"]
    assert "regression" in release["jobs"]["package"]["needs"]
