from __future__ import annotations

from pathlib import Path

import yaml


def test_merge_to_main_validation_jobs_are_not_tag_only() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert workflow["jobs"]["paper-scope"]["uses"] == "./.github/workflows/paper-scope.yml"
    for name in ("insight-eslint", "windows-smoke", "macos-smoke", "docs-build", "docker"):
        job = workflow["jobs"][name]
        assert job["if"] == (
            "${{ !cancelled() && needs.paper-scope.outputs.mode == 'full' "
            "&& (!cancelled() && needs.owner-check.result == 'success') }}"
        )
        assert job["needs"] == ["paper-scope", "owner-check"]
        assert not job.get("continue-on-error")


def test_integration_smoke_defers_full_coverage_to_primary_release_regression() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    job = workflow["jobs"]["tests"]
    assert job["strategy"]["matrix"]["python-version"] == ["3.12"]
    smoke = next(step for step in job["steps"] if step.get("name") == "Run focused integration smoke")
    assert "--cov" not in smoke["run"]
    assert "tests/test_openai_bridge_integration.py" in smoke["run"]
    assert not smoke.get("continue-on-error")
    release = yaml.safe_load(Path(".github/workflows/agent-release.yml").read_text(encoding="utf-8"))
    regression = release["jobs"]["regression"]
    primary = next(
        step
        for step in regression["steps"]
        if step.get("name") == "Offline regression including notebooks (four held native tests excluded)"
    )
    assert "--cov-fail-under=80" in primary["run"]
    assert "--ignore" not in primary["run"]
    assert not primary.get("continue-on-error")
    assert "regression" in release["jobs"]["package"]["needs"]
