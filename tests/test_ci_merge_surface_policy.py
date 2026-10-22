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


def test_lint_and_tests_run_full_matrix_on_main() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert 'python-version: ${{ fromJSON(\'["3.11","3.12"]\') }}' in workflow
    assert (
        'if [[ "${{ github.event_name }}" == "push" && "${{ github.ref }}" == "refs/heads/main" ]]; then'
        not in workflow
    )
    expected_pytest = (
        "pytest --cov --cov-report=xml:artifacts/coverage.xml --cov-fail-under=80 "
        "--junitxml=artifacts/test-reports/pytest.xml"
    )
    assert expected_pytest in workflow
