# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.ci_bundle import build_failure_bundle
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import SupportMode, ValidatorClass


def test_build_failure_bundle_from_workflow_run_event(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 42,
            "name": "✅ PR CI",
            "head_sha": "abc123",
            "head_branch": "feature/repro",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "lint-and-smoke",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [
                        {"name": "Checkout", "conclusion": "success", "number": 1},
                        {"name": "Ruff check", "conclusion": "failure", "number": 7},
                    ],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert bundle.workflow == "✅ PR CI"
    assert bundle.job == "lint-and-smoke"
    assert bundle.step == "Ruff check"
    assert bundle.validator_class == ValidatorClass.RUFF
    assert bundle.support_mode == SupportMode.AUTOPATCH_SAFE
    assert bundle.artifacts["run_attempt"] == "2"


def test_build_failure_bundle_manual_dispatch_is_report_only(tmp_path: Path) -> None:
    event_path = tmp_path / "event.json"
    event_path.write_text("{}", encoding="utf-8")

    bundle = build_failure_bundle(event_path, repository="org/repo", token=None)

    assert bundle.support_mode == SupportMode.REPORT_ONLY


def test_build_failure_bundle_includes_junit_failure_signal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 77,
            "name": "✅ PR CI",
            "head_sha": "def456",
            "head_branch": "feature/junit",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        """
<testsuite tests="1" failures="1">
  <testcase classname="tests.test_sample" name="test_it">
    <failure message="boom">Traceback</failure>
  </testcase>
</testsuite>
""".strip(),
        encoding="utf-8",
    )

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "tests",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [
                        {"name": "pytest", "conclusion": "failure", "number": 10},
                    ],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(
        event_path,
        repository="org/repo",
        token="token",
        junit_path=junit_path,
    )

    assert bundle.junit_xml == str(junit_path)
    assert any(signal.source == "junit" for signal in bundle.annotations)
    assert "tests/test_sample.py" in bundle.candidate_files


def test_junit_classname_with_test_class_maps_to_module_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 90,
            "name": "✅ PR CI",
            "head_sha": "cafe123",
            "head_branch": "feature/classname",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    junit_path = tmp_path / "junit.xml"
    junit_path.write_text(
        """
<testsuite tests="1" failures="1">
  <testcase classname="tests.test_sample.TestA" name="test_case">
    <failure message="boom" />
  </testcase>
</testsuite>
""".strip(),
        encoding="utf-8",
    )

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "tests",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "pytest", "conclusion": "failure", "number": 11}],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token", junit_path=junit_path)

    assert "tests/test_sample.py" in bundle.candidate_files
    assert all(not path.endswith("/TestA.py") for path in bundle.candidate_files)


def test_branch_name_with_docs_does_not_force_mkdocs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 101,
            "name": "✅ PR CI",
            "head_sha": "123abc",
            "head_branch": "docs/refactor-ci-bits",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "lint-and-smoke",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "Ruff check", "conclusion": "failure", "number": 5}],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert bundle.validator_class == ValidatorClass.RUFF


def test_logs_exclude_head_branch_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 202,
            "name": "✅ PR CI",
            "head_sha": "bead12",
            "head_branch": "feature/workflow-cleanup",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "Ruff check", "conclusion": "failure", "number": 3}],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert "head_branch" not in bundle.logs
    assert "workflow-cleanup" not in bundle.logs


def test_selects_linux_job_when_multiple_failures_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 303,
            "name": "✅ PR CI",
            "head_sha": "feed55",
            "head_branch": "feature/matrix",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "windows-tests",
                    "conclusion": "failure",
                    "labels": ["windows-latest"],
                    "steps": [{"name": "pytest", "conclusion": "failure", "number": 8}],
                },
                {
                    "name": "linux-lint",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "Ruff check", "conclusion": "failure", "number": 4}],
                },
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert bundle.platform == "linux"
    assert bundle.job == "linux-lint"
    assert bundle.validator_class == ValidatorClass.RUFF


def test_build_bundle_sets_reproduction_and_risk_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 404,
            "name": "✅ PR CI",
            "head_sha": "a1b2c3",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "lint",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "Ruff check", "conclusion": "failure", "number": 4}],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert bundle.reproduction_command == ["ruff", "check", "."]
    assert bundle.risk_tier == "tier1"


def test_reproduction_command_uses_active_python(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 505,
            "name": "✅ PR CI",
            "head_sha": "a1b2c3",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "smoke",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "pytest", "conclusion": "failure", "number": 9}],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert bundle.reproduction_command[0] == ci_bundle.sys.executable


def test_mypy_reproduction_command_matches_ci_scope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    event = {
        "workflow_run": {
            "id": 606,
            "name": "🚀 CI — Insight Demo",
            "head_sha": "mypy123",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    def fake_api_get(_url: str, _token: str | None) -> dict[str, object]:
        return {
            "jobs": [
                {
                    "name": "lint-type",
                    "conclusion": "failure",
                    "labels": ["ubuntu-latest"],
                    "steps": [{"name": "Mypy type-check", "conclusion": "failure", "number": 12}],
                }
            ]
        }

    from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1 import ci_bundle

    monkeypatch.setattr(ci_bundle, "_api_get", fake_api_get)
    bundle = build_failure_bundle(event_path, repository="org/repo", token="token")

    assert bundle.reproduction_command == ["mypy", "--config-file", "mypy.ini"]
