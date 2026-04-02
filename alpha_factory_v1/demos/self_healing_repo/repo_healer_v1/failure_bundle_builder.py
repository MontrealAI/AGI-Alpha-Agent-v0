# SPDX-License-Identifier: Apache-2.0
"""Build structured Repo-Healer failure bundles from GitHub workflow events."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .models import FailureBundle, FailureSignal, SupportMode, ValidatorClass


def build_bundle_from_github_event(
    event_path: Path,
    repository: str,
    token: str | None,
    run_attempt_threshold: int = 2,
) -> FailureBundle:
    """Create a normalized failure bundle from a GitHub workflow_run payload."""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    run = payload.get("workflow_run", {})
    jobs = _fetch_failed_jobs(repository=repository, run_id=run.get("id"), token=token)
    first_failed_job: dict[str, Any] = jobs[0] if jobs else {}
    step_name = _first_failed_step_name(first_failed_job) or "workflow summary"
    annotations = _annotations_from_jobs(jobs)
    logs_text = "\n".join(
        [
            f"workflow={run.get('name', 'unknown')}",
            f"conclusion={run.get('conclusion', 'unknown')}",
            *[f"{job.get('name', 'job')}: {step}" for job, step in _job_failed_steps(jobs)],
        ]
    )
    run_attempt = int(run.get("run_attempt", 1) or 1)
    support_mode = SupportMode.AUTOPATCH_SAFE if run_attempt >= run_attempt_threshold else SupportMode.REPORT_ONLY

    bundle = FailureBundle(
        workflow=run.get("name", "manual"),
        job=str(first_failed_job.get("name", "workflow_run")),
        step=step_name,
        run_id=str(run.get("id", "manual")),
        sha=run.get("head_sha", os.getenv("GITHUB_SHA", "unknown")),
        platform=_infer_platform(first_failed_job),
        failure_class="workflow_run_failure",
        exit_code=1,
        candidate_files=sorted({a.path for a in annotations if a.path}),
        validator_class=_infer_validator_class(logs_text, step_name),
        risk_tier="tier1",
        support_mode=support_mode,
        logs=logs_text,
        annotations=annotations,
        artifacts={"event_path": str(event_path), "run_attempt": str(run_attempt)},
    )
    return _enrich_from_junit_if_present(bundle)


def _fetch_failed_jobs(repository: str, run_id: object, token: str | None) -> list[dict[str, Any]]:
    """Fetch failed jobs from the workflow run API."""
    if not run_id or not token:
        return []
    url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (TimeoutError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
        return []
    jobs = payload.get("jobs", [])
    if not isinstance(jobs, list):
        return []
    typed_jobs = [job for job in jobs if isinstance(job, dict)]
    return [job for job in typed_jobs if job.get("conclusion") == "failure"]


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    raw_steps = job.get("steps", [])
    if not isinstance(raw_steps, list):
        return []
    return [step for step in raw_steps if isinstance(step, dict)]


def _job_failed_steps(jobs: list[dict[str, Any]]) -> list[tuple[dict[str, Any], str]]:
    items: list[tuple[dict[str, Any], str]] = []
    for job in jobs:
        for step in _steps(job):
            if step.get("conclusion") == "failure":
                items.append((job, str(step.get("name", "step"))))
    return items


def _first_failed_step_name(job: dict[str, Any]) -> str | None:
    for step in _steps(job):
        if step.get("conclusion") == "failure":
            return str(step.get("name", "step"))
    return None


def _annotations_from_jobs(jobs: list[dict[str, Any]]) -> list[FailureSignal]:
    annotations: list[FailureSignal] = []
    for job in jobs:
        job_name = str(job.get("name", "job"))
        for step in _steps(job):
            if step.get("conclusion") != "failure":
                continue
            annotations.append(
                FailureSignal(
                    source=f"gha:{job_name}",
                    message=f"failed step: {step.get('name', 'step')}",
                    code=str(step.get("number", "")),
                )
            )
    return annotations


def _infer_platform(job: dict[str, Any]) -> str:
    labels = " ".join(str(label).lower() for label in job.get("labels", []))
    haystack = f"{labels} {str(job.get('runner_name', '')).lower()} {str(job.get('name', '')).lower()}"
    if "windows" in haystack:
        return "windows"
    if "macos" in haystack or "mac" in haystack:
        return "macos"
    return "linux"


def _infer_validator_class(logs_text: str, step_name: str) -> ValidatorClass:
    joined = f"{logs_text}\n{step_name}".lower()
    if "ruff" in joined:
        return ValidatorClass.RUFF
    if "mypy" in joined:
        return ValidatorClass.MYPY
    if "mkdocs" in joined or "docs" in joined:
        return ValidatorClass.MKDOCS
    if "import" in joined:
        return ValidatorClass.IMPORT
    if "smoke" in joined:
        return ValidatorClass.SMOKE
    if "pytest" in joined or "test" in joined:
        return ValidatorClass.PYTEST
    return ValidatorClass.NONE


def _enrich_from_junit_if_present(bundle: FailureBundle) -> FailureBundle:
    junit_path = os.getenv("REPO_HEALER_JUNIT_XML")
    if not junit_path:
        return bundle
    path = Path(junit_path)
    if not path.exists():
        return bundle

    candidates = set(bundle.candidate_files)
    annotations = list(bundle.annotations)
    try:
        root = ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError:
        return bundle
    for case in root.iter("testcase"):
        file_path = case.attrib.get("file")
        if file_path:
            candidates.add(file_path)
        for node in case:
            if node.tag in {"failure", "error"}:
                annotations.append(
                    FailureSignal(
                        source="junit",
                        message=(node.attrib.get("message") or (node.text or "")).strip()[:400],
                        path=file_path,
                    )
                )
    bundle.junit_xml = str(path)
    bundle.candidate_files = sorted(candidates)
    bundle.annotations = annotations
    return bundle
