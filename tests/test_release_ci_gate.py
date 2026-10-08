# SPDX-License-Identifier: Apache-2.0
"""A release must not race failing or unrelated historical CI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import package_agent_release, wait_for_release_ci
from scripts.wait_for_release_ci import (
    REPOSITORY,
    WORKFLOWS,
    assess_runs,
    require_historical_evidence,
    validate_snapshot,
)

SHA = "a" * 40


def run(**overrides: object) -> dict:
    return (
        dict(id=1, head_sha=SHA, head_branch="main", event="push", status="completed", conclusion="success") | overrides
    )


def test_exact_main_push_success() -> None:
    assert assess_runs([run()], SHA)


@pytest.mark.parametrize(
    "override", [{"head_sha": "b" * 40}, {"head_branch": "other"}, {"event": "pull_request"}, {"status": "in_progress"}]
)
def test_unrelated_or_pending_runs_do_not_authorize_release(override: dict) -> None:
    assert not assess_runs([run(**override)], SHA)


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "timed_out", None])
def test_unsuccessful_run_blocks_release(conclusion: str | None) -> None:
    with pytest.raises(RuntimeError, match="did not pass"):
        assess_runs([run(conclusion=conclusion)], SHA)


def test_latest_run_must_pass_even_when_an_older_run_passed() -> None:
    with pytest.raises(RuntimeError, match="did not pass"):
        assess_runs([run(), run(id=2, conclusion="failure")], SHA)
    assert not assess_runs([], SHA)


def snapshot() -> dict:
    return {
        "commit": SHA,
        "repository": REPOSITORY,
        "ref": "refs/heads/main",
        "required": True,
        "workflows": {workflow: [run(path=f".github/workflows/{workflow}")] for workflow in WORKFLOWS},
    }


def test_complete_main_snapshot_is_accepted() -> None:
    validate_snapshot(snapshot(), SHA, REPOSITORY, "refs/heads/main")


@pytest.mark.parametrize(
    "change",
    [
        {"commit": "b" * 40},
        {"repository": "other/repository"},
        {"ref": "refs/heads/candidate"},
        {"required": False},
        {"required": 1},
        {"workflows": {}},
        {"workflows": {"ci.yml": []}},
    ],
)
def test_main_snapshot_rejects_stale_candidate_and_incomplete_records(change: dict) -> None:
    with pytest.raises(ValueError):
        validate_snapshot(snapshot() | change, SHA, REPOSITORY, "refs/heads/main")


@pytest.mark.parametrize(
    "change",
    [
        {"status": "in_progress", "conclusion": None},
        {"conclusion": "failure"},
        {"conclusion": "cancelled"},
        {"conclusion": "timed_out"},
        {"head_sha": "b" * 40},
        {"head_branch": "candidate"},
        {"event": "workflow_dispatch"},
        {"path": ".github/workflows/unrelated.yml"},
        {"id": True},
        {"id": -1},
    ],
)
def test_main_snapshot_requires_each_workflows_latest_successful_main_push(change: dict) -> None:
    evidence = snapshot()
    evidence["workflows"]["ci.yml"] = [run(path=".github/workflows/ci.yml") | change]
    with pytest.raises((ValueError, RuntimeError)):
        validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/main")


def test_successful_retry_snapshot_replaces_timed_out_snapshot(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    path = tmp_path / "historical-ci" / "historical-ci.json"
    path.parent.mkdir()
    success = snapshot()
    stale = copy.deepcopy(success)
    stale["workflows"]["ci.yml"][0].update(status="in_progress", conclusion=None)
    path.write_text(json.dumps(stale))
    with pytest.raises(ValueError, match="completed successful main push"):
        require_historical_evidence(tmp_path, SHA)
    path.write_text(json.dumps(success))
    assert require_historical_evidence(tmp_path, SHA)["required"] is True


def test_latest_failed_run_blocks_packaging_even_when_old_success_is_present() -> None:
    evidence = snapshot()
    evidence["workflows"]["ci.yml"].append(run(id=2, path=".github/workflows/ci.yml", conclusion="failure"))
    with pytest.raises(RuntimeError, match="did not pass"):
        validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/main")


def test_candidate_scope_is_bound_to_its_own_ref_and_never_authorizes_main() -> None:
    ref = "refs/heads/candidate"
    candidate = snapshot() | {"required": False, "ref": ref, "workflows": {}}
    validate_snapshot(candidate, SHA, REPOSITORY, ref)
    with pytest.raises(ValueError):
        validate_snapshot(candidate, SHA, REPOSITORY, "refs/heads/main")
    with pytest.raises(ValueError, match="non-publishing scope"):
        validate_snapshot(candidate | {"required": True}, SHA, REPOSITORY, ref)


@pytest.mark.parametrize("content", [None, b"not-json", b"x" * 65])
def test_missing_malformed_and_oversized_snapshots_fail_closed(
    tmp_path: Path, monkeypatch, content: bytes | None
) -> None:
    monkeypatch.setattr(wait_for_release_ci, "MAX_SNAPSHOT_BYTES", 64)
    path = tmp_path / "historical-ci" / "historical-ci.json"
    path.parent.mkdir()
    if content is not None:
        path.write_bytes(content)
    with pytest.raises(ValueError):
        require_historical_evidence(tmp_path, SHA)


def test_candidate_cli_writes_bound_scope_without_querying_github(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/candidate")
    monkeypatch.setattr(sys, "argv", ["wait_for_release_ci", "--candidate"])
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: pytest.fail("Candidate queried GitHub"))
    wait_for_release_ci.main()
    evidence = json.loads(Path("evidence/historical-ci.json").read_text())
    validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/candidate")
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    with pytest.raises(ValueError, match="not candidate evidence"):
        wait_for_release_ci.main()


def test_waiter_allows_historical_tests_to_finish_after_the_old_fifty_minute_deadline(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(sys, "argv", ["wait_for_release_ci"])
    clock = iter([0, 3001])
    monkeypatch.setattr(wait_for_release_ci.time, "monotonic", lambda: next(clock))
    rounds = []
    monkeypatch.setattr(wait_for_release_ci.time, "sleep", lambda seconds: rounds.append(seconds))

    def response(command: list[str], **kwargs) -> str:
        workflow = command[-1].split("/workflows/")[1].split("/")[0]
        record = snapshot()["workflows"][workflow][0]
        if workflow == "ci.yml" and not rounds:
            record.update(status="in_progress", conclusion=None)
        return json.dumps({"workflow_runs": [record]})

    monkeypatch.setattr(subprocess, "check_output", response)
    wait_for_release_ci.main()
    assert rounds == [30]
    evidence = json.loads(Path("evidence/historical-ci.json").read_text())
    validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/main")


def test_packaging_rejects_stale_historical_evidence_before_creating_assets(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["package", "--output", "release", "--evidence", "evidence"])
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: SHA)
    path = tmp_path / "evidence" / "historical-ci" / "historical-ci.json"
    path.parent.mkdir(parents=True)
    stale = snapshot()
    stale["workflows"]["ci.yml"][0].update(status="in_progress", conclusion=None)
    path.write_text(json.dumps(stale))
    with pytest.raises(ValueError, match="completed successful main push"):
        package_agent_release.main()
    assert not Path("release").exists()
