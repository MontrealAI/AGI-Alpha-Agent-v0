# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.ci_ingest import build_bundle_from_event
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.models import FailureBundle, FailureClass
from alpha_factory_v1.demos.self_healing_repo.repo_healer_v1.triage import triage_bundle


def test_build_bundle_from_event_reads_job_and_annotations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    jobs = {
        "jobs": [
            {
                "name": "lint-type",
                "conclusion": "failure",
                "labels": ["ubuntu-latest"],
                "steps": [{"name": "Mypy type-check", "conclusion": "failure"}],
            }
        ]
    }
    annotations = {
        "annotations": [
            {
                "message": "mypy: error: Name 'abc' is not defined",
                "path": "alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/models.py",
                "start_line": 10,
                "annotation_level": "failure",
            }
        ]
    }
    jobs_path = tmp_path / "jobs.json"
    ann_path = tmp_path / "annotations.json"
    jobs_path.write_text(json.dumps(jobs), encoding="utf-8")
    ann_path.write_text(json.dumps(annotations), encoding="utf-8")

    monkeypatch.setenv("REPO_HEALER_JOBS_JSON", str(jobs_path))
    monkeypatch.setenv("REPO_HEALER_ANNOTATIONS_JSON", str(ann_path))

    bundle = build_bundle_from_event(
        {"workflow_run": {"name": "✅ PR CI", "id": 42, "head_sha": "abc", "conclusion": "failure"}},
        tmp_path,
    )

    assert bundle.job == "lint-type"
    assert bundle.step == "Mypy type-check"
    assert bundle.validator_class.value == "mypy"
    assert bundle.candidate_files == ["alpha_factory_v1/demos/self_healing_repo/repo_healer_v1/models.py"]


def test_triage_marks_unsupported_platform() -> None:
    bundle = FailureBundle("wf", "job", "step", "1", "abc", platform="solaris")
    triage = triage_bundle(bundle)
    assert triage.classification == FailureClass.UNSUPPORTED_PLATFORM_SPECIFIC
