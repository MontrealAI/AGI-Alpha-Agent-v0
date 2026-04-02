# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.ci_bundle import build_failure_bundle
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import SupportMode, ValidatorClass


def test_build_failure_bundle_from_workflow_run_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
