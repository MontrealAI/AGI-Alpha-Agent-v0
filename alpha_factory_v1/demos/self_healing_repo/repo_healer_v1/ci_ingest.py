# SPDX-License-Identifier: Apache-2.0
"""Normalize GitHub Actions metadata into Repo-Healer failure bundles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .models import FailureBundle, FailureSignal, SupportMode, ValidatorClass


def build_bundle_from_event(event_payload: dict[str, Any], repo_root: Path) -> FailureBundle:
    """Build a normalized failure bundle from a workflow_run event payload."""
    run = event_payload.get("workflow_run", {})
    jobs_path = _env_path("REPO_HEALER_JOBS_JSON")
    annotations_path = _env_path("REPO_HEALER_ANNOTATIONS_JSON")
    junit_path = _env_path("REPO_HEALER_JUNIT_XML")

    job_name, step_name, platform, exit_code = _infer_job_context(jobs_path)
    annotations = _parse_annotations(annotations_path)
    junit_signals = _parse_junit(junit_path, repo_root)
    all_annotations = annotations + junit_signals

    logs = _compose_logs(run, jobs_path)
    validator_class = _infer_validator(logs, all_annotations)

    return FailureBundle(
        workflow=run.get("name", "manual"),
        job=job_name,
        step=step_name,
        run_id=str(run.get("id", "manual")),
        sha=run.get("head_sha", os.environ.get("GITHUB_SHA", "unknown")),
        platform=platform,
        failure_class="workflow_run_failure",
        exit_code=exit_code,
        candidate_files=_candidate_files(all_annotations),
        validator_class=validator_class,
        support_mode=SupportMode.AUTOPATCH_SAFE,
        logs=logs,
        junit_xml=str(junit_path) if junit_path else None,
        annotations=all_annotations,
        artifacts={
            "event": os.environ.get("GITHUB_EVENT_PATH", ""),
            "jobs": str(jobs_path) if jobs_path else "",
            "annotations": str(annotations_path) if annotations_path else "",
        },
    )


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    path = Path(raw)
    return path if path.exists() else None


def _infer_job_context(jobs_path: Path | None) -> tuple[str, str, str, int]:
    if not jobs_path:
        return "workflow_run", "summary", "linux", 1
    payload = json.loads(jobs_path.read_text(encoding="utf-8"))
    failed_job = next((job for job in payload.get("jobs", []) if job.get("conclusion") == "failure"), None)
    if not failed_job:
        return "workflow_run", "summary", "linux", 1

    platform_haystack = " ".join(
        [
            str(failed_job.get("runner_name", "")).lower(),
            str(failed_job.get("name", "")).lower(),
            *(str(label).lower() for label in failed_job.get("labels", [])),
        ]
    )
    platform = "windows" if "windows" in platform_haystack else "macos" if "macos" in platform_haystack else "linux"

    failed_step: dict[str, Any] = next(
        (step for step in failed_job.get("steps", []) if step.get("conclusion") == "failure"), {}
    )
    step_name = failed_step.get("name", "unknown-step")
    return str(failed_job.get("name", "workflow_run")), str(step_name), platform, 1


def _parse_annotations(path: Path | None) -> list[FailureSignal]:
    if not path:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    signals: list[FailureSignal] = []
    for item in payload.get("annotations", []):
        signals.append(
            FailureSignal(
                source="github-annotation",
                message=str(item.get("message", "")).strip(),
                path=item.get("path"),
                line=item.get("start_line") or item.get("line"),
                code=item.get("annotation_level"),
            )
        )
    return signals


def _parse_junit(path: Path | None, repo_root: Path) -> list[FailureSignal]:
    if not path:
        return []
    try:
        root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
    except ElementTree.ParseError:
        return []

    signals: list[FailureSignal] = []
    for testcase in root.findall(".//testcase"):
        failure = testcase.find("failure") or testcase.find("error")
        if failure is None:
            continue
        file_path = testcase.attrib.get("file")
        normalized = _normalize_file(file_path, repo_root) if file_path else None
        signals.append(
            FailureSignal(
                source="junit",
                message=(failure.attrib.get("message") or (failure.text or "test failure")).strip(),
                path=normalized,
                line=_parse_int(testcase.attrib.get("line")),
                code="failure",
            )
        )
    return signals


def _normalize_file(path: str, repo_root: Path) -> str:
    absolute = Path(path)
    if absolute.is_absolute():
        try:
            return str(absolute.relative_to(repo_root))
        except ValueError:
            return absolute.name
    return str(absolute)


def _compose_logs(run: dict[str, Any], jobs_path: Path | None) -> str:
    summary = [
        f"workflow={run.get('name', 'unknown')}",
        f"conclusion={run.get('conclusion', 'unknown')}",
        f"event={run.get('event', 'unknown')}",
    ]
    if jobs_path:
        summary.append(f"jobs_json={jobs_path}")
    return " ".join(summary)


def _infer_validator(logs: str, annotations: list[FailureSignal]) -> ValidatorClass:
    text = "\n".join([logs, *(a.message for a in annotations)]).lower()
    if "ruff" in text:
        return ValidatorClass.RUFF
    if "mypy" in text:
        return ValidatorClass.MYPY
    if "mkdocs" in text:
        return ValidatorClass.MKDOCS
    if "modulenotfounderror" in text or "importerror" in text:
        return ValidatorClass.IMPORT
    if "smoke" in text:
        return ValidatorClass.SMOKE
    if "pytest" in text or "assert" in text or "failure" in text:
        return ValidatorClass.PYTEST
    return ValidatorClass.NONE


def _candidate_files(signals: list[FailureSignal]) -> list[str]:
    return sorted({signal.path for signal in signals if signal.path})


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None
