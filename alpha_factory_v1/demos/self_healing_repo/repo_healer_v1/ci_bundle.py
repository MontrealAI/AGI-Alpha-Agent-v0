# SPDX-License-Identifier: Apache-2.0
"""Build normalized Repo-Healer failure bundles from GitHub workflow_run payloads."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, cast

from .models import FailureBundle, FailureSignal, SupportMode, ValidatorClass

PYTHON = sys.executable


def _api_get(url: str, token: str | None) -> dict[str, Any]:
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return cast(dict[str, Any], json.loads(response.read().decode("utf-8")))


def _infer_validator(step_name: str, job_name: str) -> ValidatorClass:
    text = f"{step_name}\n{job_name}".lower()
    if "ruff" in text:
        return ValidatorClass.RUFF
    if "mypy" in text:
        return ValidatorClass.MYPY
    if "mkdocs" in text:
        return ValidatorClass.MKDOCS
    if any(marker in text for marker in ("docs build", "documentation", "📚 docs", "docs-deploy")):
        return ValidatorClass.MKDOCS
    if "importerror" in text or "modulenotfound" in text:
        return ValidatorClass.IMPORT
    if "pytest" in text or "smoke" in text:
        return ValidatorClass.PYTEST
    return ValidatorClass.NONE


def _classname_to_path(classname: str) -> str | None:
    normalized = classname.strip()
    if not normalized:
        return None

    parts = normalized.split(".")
    if parts and parts[0] == "tests":
        parts = parts[1:]
    if parts and parts[-1][:1].isupper():
        parts = parts[:-1]
    if not parts:
        return None
    return f"tests/{'/'.join(parts)}.py"


def _collect_junit_signals(junit_path: pathlib.Path) -> list[FailureSignal]:
    if not junit_path.exists():
        return []
    try:
        root = ET.fromstring(junit_path.read_text(encoding="utf-8"))
    except ET.ParseError:
        return []

    out: list[FailureSignal] = []
    for case in root.findall(".//testcase"):
        failed = case.find("failure")
        if failed is None:
            failed = case.find("error")
        if failed is None:
            continue
        classname = case.attrib.get("classname", "")
        name = case.attrib.get("name", "")
        msg = failed.attrib.get("message") or (failed.text or "test failure")
        out.append(
            FailureSignal(
                source="junit",
                message=f"{classname}::{name}: {msg}".strip(),
                path=_classname_to_path(classname),
            )
        )
    return out


def _default_reproduction_command(validator: ValidatorClass, candidate_files: list[str]) -> list[str]:
    if validator == ValidatorClass.RUFF:
        return ["ruff", "check", "."]
    if validator == ValidatorClass.MYPY:
        return ["mypy", "--config-file", "mypy.ini", "."]
    if validator == ValidatorClass.IMPORT:
        return [PYTHON, "-m", "pytest", "tests/test_imports.py", "-q"]
    if validator in {ValidatorClass.PYTEST, ValidatorClass.SMOKE}:
        tests = [path for path in candidate_files if path.startswith("tests/") and path.endswith(".py")]
        if tests:
            return [PYTHON, "-m", "pytest", *tests, "-q"]
        return [
            PYTHON,
            "-m",
            "pytest",
            "-m",
            "smoke",
            "tests/test_af_requests.py",
            "tests/test_cache_version.py",
            "tests/test_check_env_core.py",
            "tests/test_check_env_network.py",
            "tests/test_config_settings.py",
            "tests/test_config_utils.py",
            "tests/test_ping_agent.py",
            "-q",
        ]
    if validator == ValidatorClass.MKDOCS:
        return ["mkdocs", "build", "--strict"]
    return []


def _risk_tier(validator: ValidatorClass, platform: str) -> str:
    if platform.lower() in {"windows", "macos"}:
        return "tier2"
    if validator in {
        ValidatorClass.RUFF,
        ValidatorClass.MYPY,
        ValidatorClass.IMPORT,
        ValidatorClass.PYTEST,
        ValidatorClass.SMOKE,
        ValidatorClass.MKDOCS,
    }:
        return "tier1"
    return "tier2"


def _job_platform(job: dict[str, Any]) -> str:
    name = str(job.get("name", "")).lower()
    labels = [str(label).lower() for label in job.get("labels", [])]
    haystack = " ".join([name, *labels])
    if "windows" in haystack:
        return "windows"
    if "macos" in haystack:
        return "macos"
    return "linux"


def _select_failed_job(failed_jobs: list[dict[str, Any]]) -> dict[str, Any]:
    for job in failed_jobs:
        if _job_platform(job) == "linux":
            return job
    return failed_jobs[0]


def build_failure_bundle(
    event_path: pathlib.Path,
    repository: str,
    token: str | None,
    junit_path: pathlib.Path | None = None,
) -> FailureBundle:
    """Create a structured failure bundle for one failed workflow run."""
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    run = payload.get("workflow_run", {})
    run_id = str(run.get("id", "manual"))
    sha = run.get("head_sha") or payload.get("after") or os.environ.get("GITHUB_SHA", "unknown")

    bundle = FailureBundle(
        workflow=run.get("name", "manual"),
        job="unknown",
        step="unknown",
        run_id=run_id,
        sha=sha,
        logs=f"conclusion={run.get('conclusion', 'unknown')}",
        artifacts={"event": str(event_path), "run_attempt": str(run.get("run_attempt", 1))},
        support_mode=SupportMode.AUTOPATCH_SAFE,
    )

    if not run.get("id"):
        bundle.support_mode = SupportMode.REPORT_ONLY
        bundle.logs = "manual dispatch without workflow_run payload"
        return bundle

    jobs_url = f"https://api.github.com/repos/{repository}/actions/runs/{run_id}/jobs?per_page=100"
    try:
        jobs_payload = _api_get(jobs_url, token)
    except urllib.error.HTTPError as exc:
        bundle.support_mode = SupportMode.REPORT_ONLY
        bundle.logs = f"failed to fetch jobs payload: HTTP {exc.code}"
        return bundle
    except urllib.error.URLError as exc:
        bundle.support_mode = SupportMode.REPORT_ONLY
        bundle.logs = f"failed to fetch jobs payload: {exc.reason}"
        return bundle

    failed_jobs = [job for job in jobs_payload.get("jobs", []) if job.get("conclusion") == "failure"]
    if not failed_jobs:
        bundle.support_mode = SupportMode.REPORT_ONLY
        bundle.logs = "no failed jobs found"
        return bundle

    failed_job = _select_failed_job(failed_jobs)
    job_name = str(failed_job.get("name", "unknown"))
    step_name = "unknown"
    exit_code = 1

    for step in failed_job.get("steps", []):
        if step.get("conclusion") == "failure":
            step_name = str(step.get("name", "unknown"))
            step_number = step.get("number")
            if isinstance(step_number, int):
                exit_code = step_number
            break

    platform = _job_platform(failed_job)

    annotations: list[FailureSignal] = []
    for annotation in failed_job.get("steps", []):
        if annotation.get("conclusion") != "failure":
            continue
        annotations.append(
            FailureSignal(
                source="gha-step",
                message=str(annotation.get("name", "failed step")),
                line=annotation.get("number"),
            )
        )

    if junit_path is not None:
        annotations.extend(_collect_junit_signals(junit_path))

    logs = "\n".join([f"job={job_name}", f"step={step_name}"])
    validator = _infer_validator(step_name, job_name)

    candidate_files = sorted({signal.path for signal in annotations if signal.path})
    bundle.job = job_name
    bundle.step = step_name
    bundle.platform = platform
    bundle.exit_code = exit_code
    bundle.logs = logs
    bundle.validator_class = validator
    bundle.candidate_files = candidate_files
    bundle.reproduction_command = _default_reproduction_command(validator, candidate_files)
    bundle.risk_tier = _risk_tier(validator, platform)
    bundle.annotations = annotations
    bundle.artifacts["jobs_api"] = jobs_url
    if junit_path:
        bundle.junit_xml = str(junit_path)
    return bundle


def main() -> int:
    """CLI to create repo_healer_bundle.json and placeholder candidates file."""
    parser = argparse.ArgumentParser(description="Build Repo-Healer failure bundle from GitHub event")
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--token", default="")
    parser.add_argument("--junit", default="")
    parser.add_argument("--bundle-out", default="repo_healer_bundle.json")
    parser.add_argument("--candidates-out", default="repo_healer_candidates.json")
    args = parser.parse_args()

    junit_path = pathlib.Path(args.junit) if args.junit else None
    bundle = build_failure_bundle(
        pathlib.Path(args.event_path),
        repository=args.repository,
        token=args.token or None,
        junit_path=junit_path,
    )

    pathlib.Path(args.bundle_out).write_text(json.dumps(bundle.to_dict(), indent=2), encoding="utf-8")
    pathlib.Path(args.candidates_out).write_text("[]\n", encoding="utf-8")
    print(json.dumps(bundle.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
