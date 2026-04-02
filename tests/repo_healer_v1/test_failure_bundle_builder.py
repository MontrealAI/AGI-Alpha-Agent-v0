# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.failure_bundle_builder import build_bundle_from_github_event


def test_builder_uses_report_only_before_rerun_threshold(tmp_path: Path) -> None:
    event = {
        "workflow_run": {
            "name": "✅ PR CI",
            "id": 1234,
            "head_sha": "abc123",
            "conclusion": "failure",
            "run_attempt": 1,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    bundle = build_bundle_from_github_event(
        event_path=event_path,
        repository="owner/repo",
        token=None,
        run_attempt_threshold=2,
    )

    assert bundle.support_mode.value == "REPORT_ONLY"
    assert bundle.workflow == "✅ PR CI"
    assert bundle.run_id == "1234"


def test_builder_promotes_autopatch_after_rerun_threshold(tmp_path: Path) -> None:
    event = {
        "workflow_run": {
            "name": "🔥 Smoke Test",
            "id": 99,
            "head_sha": "def456",
            "conclusion": "failure",
            "run_attempt": 2,
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")

    bundle = build_bundle_from_github_event(
        event_path=event_path,
        repository="owner/repo",
        token=None,
        run_attempt_threshold=2,
    )

    assert bundle.support_mode.value == "AUTOPATCH_SAFE"
