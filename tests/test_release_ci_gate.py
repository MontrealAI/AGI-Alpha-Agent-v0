# SPDX-License-Identifier: Apache-2.0
"""A release must not race failing or unrelated historical CI."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

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
        dict(
            id=1,
            run_attempt=1,
            head_sha=SHA,
            head_branch="main",
            event="push",
            status="completed",
            conclusion="success",
        )
        | overrides
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


def job(**overrides: object) -> dict:
    return {
        "id": 100,
        "run_id": 1,
        "run_attempt": 1,
        "head_sha": SHA,
        "name": "Full software qualification",
        "status": "completed",
        "conclusion": "success",
    } | overrides


def qualification(**overrides: object) -> dict:
    return {
        "run_id": 1,
        "run_attempt": 1,
        "head_sha": SHA,
        "endpoint": f"repos/{REPOSITORY}/actions/runs/1/attempts/1/jobs",
        "total_count": 1,
        "jobs": [job()],
    } | overrides


class IntSubclass(int):
    """A numerically equal value must not satisfy exact JSON integer fields."""


@pytest.mark.parametrize("field", ["id", "run_attempt"])
@pytest.mark.parametrize("value", [True, IntSubclass(1)])
def test_qualification_endpoint_refuses_bool_and_integer_subclasses(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="exact positive"):
        wait_for_release_ci.jobs_endpoint(REPOSITORY, run(**{field: value}))


@pytest.mark.parametrize(
    "field,job_field",
    [
        ("run_id", False),
        ("run_attempt", False),
        ("total_count", False),
        ("id", True),
        ("run_id", True),
        ("run_attempt", True),
    ],
)
@pytest.mark.parametrize("value", [True, IntSubclass(1)])
def test_qualification_inventory_refuses_bool_and_integer_subclasses(
    field: str, job_field: bool, value: object
) -> None:
    record = qualification()
    if job_field:
        record["jobs"][0][field] = value
    else:
        record[field] = value
    with pytest.raises(ValueError):
        wait_for_release_ci.validate_qualification(record, run(), REPOSITORY)


def snapshot() -> dict:
    return {
        "commit": SHA,
        "repository": REPOSITORY,
        "ref": "refs/heads/main",
        "required": True,
        "workflows": {workflow: [run(path=f".github/workflows/{workflow}")] for workflow in WORKFLOWS},
        "qualification_jobs": {workflow: qualification() for workflow in WORKFLOWS},
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
    candidate = snapshot() | {"required": False, "ref": ref, "workflows": {}, "qualification_jobs": {}}
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


@pytest.mark.parametrize("elapsed", [3001, 4801])
def test_waiter_allows_historical_tests_to_finish_after_previous_deadlines(
    tmp_path: Path, monkeypatch, elapsed: int
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(sys, "argv", ["wait_for_release_ci"])
    clock = iter([0, elapsed])
    monkeypatch.setattr(wait_for_release_ci.time, "monotonic", lambda: next(clock))
    rounds = []
    monkeypatch.setattr(wait_for_release_ci.time, "sleep", lambda seconds: rounds.append(seconds))

    def response(command: list[str], **kwargs) -> str:
        if "/attempts/" in command[-1]:
            return json.dumps({"total_count": 1, "jobs": [job()]})
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


def test_historical_job_leaves_time_to_record_waiter_evidence() -> None:
    import yaml

    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/agent-release.yml").read_text())
    timeout = workflow["jobs"]["historical-ci"]["timeout-minutes"]
    assert timeout * 60 >= wait_for_release_ci.WAIT_SECONDS + 5 * 60
    assert wait_for_release_ci.WAIT_SECONDS <= 120 * 60


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


def test_waiter_deadline_still_rejects_unfinished_historical_ci(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(sys, "argv", ["wait_for_release_ci"])
    clock = iter([0, wait_for_release_ci.WAIT_SECONDS])
    monkeypatch.setattr(wait_for_release_ci.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(wait_for_release_ci.time, "sleep", lambda seconds: pytest.fail("Expired wait must stop"))

    def response(command: list[str], **kwargs) -> str:
        if "/attempts/" in command[-1]:
            return json.dumps({"total_count": 1, "jobs": [job()]})
        workflow = command[-1].split("/workflows/")[1].split("/")[0]
        record = snapshot()["workflows"][workflow][0]
        if workflow == "ci.yml":
            record.update(status="in_progress", conclusion=None)
        return json.dumps({"workflow_runs": [record]})

    monkeypatch.setattr(subprocess, "check_output", response)
    with pytest.raises(TimeoutError, match="release deadline"):
        wait_for_release_ci.main()
    evidence = json.loads(Path("evidence/historical-ci.json").read_text())
    with pytest.raises(ValueError, match="completed successful main push"):
        validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/main")


@pytest.mark.parametrize(
    "mutate",
    [
        "missing",
        "empty",
        "skipped",
        "failed",
        "pending",
        "duplicate",
        "old-run",
        "old-attempt",
        "wrong-sha",
        "wrong-endpoint",
        "incomplete",
        "bool-id",
    ],
)
def test_green_paper_workflow_cannot_supply_full_runtime_evidence(mutate: str) -> None:
    evidence = snapshot()
    record = evidence["qualification_jobs"]["ci.yml"]
    if mutate == "missing":
        evidence.pop("qualification_jobs")
    elif mutate == "empty":
        record.update(jobs=[], total_count=0)
    elif mutate == "skipped":
        record["jobs"][0]["conclusion"] = "skipped"
    elif mutate == "failed":
        record["jobs"][0]["conclusion"] = "failure"
    elif mutate == "pending":
        record["jobs"][0].update(status="in_progress", conclusion=None)
    elif mutate == "duplicate":
        record["jobs"].append(job(id=101))
        record["total_count"] = 2
    elif mutate == "old-run":
        record["jobs"][0]["run_id"] = 2
    elif mutate == "old-attempt":
        record["jobs"][0]["run_attempt"] = 2
    elif mutate == "wrong-sha":
        record["jobs"][0]["head_sha"] = "b" * 40
    elif mutate == "wrong-endpoint":
        record["endpoint"] = f"repos/{REPOSITORY}/actions/runs/1/jobs?filter=all"
    elif mutate == "incomplete":
        record["total_count"] = 5
    else:
        record["run_id"] = True
    with pytest.raises((ValueError, RuntimeError)):
        validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/main")


def test_latest_run_attempt_cannot_reuse_prior_attempt_marker() -> None:
    evidence = snapshot()
    evidence["workflows"]["ci.yml"][0]["run_attempt"] = 2
    with pytest.raises(ValueError, match="latest exact run"):
        validate_snapshot(evidence, SHA, REPOSITORY, "refs/heads/main")


def test_jobs_are_paginated_for_the_exact_run_attempt(monkeypatch) -> None:
    calls = []

    def response(command: list[str], **kwargs) -> str:
        endpoint = command[-1]
        calls.append(endpoint)
        assert "/runs/7/attempts/3/jobs?per_page=100&page=" in endpoint
        if endpoint.endswith("page=1"):
            jobs = [job(id=index, run_id=7, run_attempt=3, name=f"test-{index}") for index in range(1, 101)]
        else:
            jobs = [job(id=101, run_id=7, run_attempt=3)]
            # The public API may omit this field; the exact endpoint binds it.
            jobs[0].pop("run_attempt")
        return json.dumps({"total_count": 101, "jobs": jobs})

    monkeypatch.setattr(subprocess, "check_output", response)
    latest = run(id=7, run_attempt=3)
    result = wait_for_release_ci.fetch_qualification_jobs(REPOSITORY, latest)
    assert len(calls) == 2
    assert result["total_count"] == 101
    assert result["jobs"][-1]["run_attempt"] == 3
    wait_for_release_ci.validate_qualification(result, latest, REPOSITORY)


@pytest.mark.parametrize(
    "problem", ["wrong-run", "wrong-attempt", "wrong-sha", "truncated", "changing-total", "duplicate"]
)
def test_paginated_jobs_fail_closed_on_inconsistent_inventory(monkeypatch, problem: str) -> None:
    count = 0

    def response(command: list[str], **kwargs) -> str:
        nonlocal count
        count += 1
        record = job()
        if problem == "wrong-run":
            record["run_id"] = 2
        elif problem == "wrong-attempt":
            record["run_attempt"] = 2
        elif problem == "wrong-sha":
            record["head_sha"] = "b" * 40
        if problem == "truncated":
            return json.dumps({"total_count": 2, "jobs": [record] if count == 1 else []})
        if problem == "changing-total":
            return json.dumps({"total_count": 2 if count == 1 else 3, "jobs": [record]})
        if problem == "duplicate":
            return json.dumps({"total_count": 2, "jobs": [record, record]})
        return json.dumps({"total_count": 1, "jobs": [record]})

    monkeypatch.setattr(subprocess, "check_output", response)
    with pytest.raises(ValueError):
        wait_for_release_ci.fetch_qualification_jobs(REPOSITORY, run())


def test_offline_packaging_rejects_green_paper_scope_before_building(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["package", "--output", "release", "--evidence", "evidence"])
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: SHA)
    path = tmp_path / "evidence" / "historical-ci" / "historical-ci.json"
    path.parent.mkdir(parents=True)
    evidence = snapshot()
    evidence["qualification_jobs"]["ci.yml"]["jobs"][0]["conclusion"] = "skipped"
    path.write_text(json.dumps(evidence))
    with pytest.raises(RuntimeError, match="Full software qualification"):
        package_agent_release.main()
    assert not Path("release").exists()


class IntegerSubclass(int):
    """An equal numeric value must not satisfy an exact builtin schema."""


@pytest.mark.parametrize("value", [True, 1.0, IntegerSubclass(1)])
@pytest.mark.parametrize("field", ["id", "run_attempt"])
def test_qualification_endpoint_rejects_nonbuiltin_integer_ids(field: str, value: object) -> None:
    with pytest.raises(ValueError, match="exact positive"):
        wait_for_release_ci.jobs_endpoint(REPOSITORY, run(**{field: value}))


@pytest.mark.parametrize("value", [True, 1.0, IntegerSubclass(1)])
@pytest.mark.parametrize("field", ["run_id", "run_attempt", "total_count", "job.id", "job.run_id", "job.run_attempt"])
def test_qualification_record_rejects_nonbuiltin_integer_fields(field: str, value: object) -> None:
    record = qualification()
    if field.startswith("job."):
        record["jobs"][0][field.removeprefix("job.")] = value
    else:
        record[field] = value
    with pytest.raises(ValueError):
        wait_for_release_ci.validate_qualification(record, run(), REPOSITORY)


@pytest.mark.parametrize("value", [True, 1.0, IntegerSubclass(1)])
@pytest.mark.parametrize("field", ["total_count", "job.id", "job.run_id", "job.run_attempt"])
def test_fetched_job_inventory_rejects_nonbuiltin_integer_fields(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    response: dict[str, Any] = {"total_count": 1, "jobs": [job()]}
    if field.startswith("job."):
        response["jobs"][0][field.removeprefix("job.")] = value
    else:
        response[field] = value
    monkeypatch.setattr(subprocess, "check_output", lambda *args, **kwargs: "captured response")
    monkeypatch.setattr(json, "loads", lambda raw: response)
    with pytest.raises(ValueError):
        wait_for_release_ci.fetch_qualification_jobs(REPOSITORY, run())


def preflight_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GITHUB_SHA", SHA)
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GITHUB_REF", "refs/heads/main")
    monkeypatch.setattr(wait_for_release_ci.time, "sleep", lambda *args: pytest.fail("Preflight must never poll"))
    monkeypatch.setattr(wait_for_release_ci.time, "monotonic", lambda: pytest.fail("Preflight has no wait deadline"))
    monkeypatch.setattr(
        subprocess, "check_output", lambda *args, **kwargs: pytest.fail("Preflight must not use gh credentials")
    )


def preflight_response(evidence: dict, calls: list[str]):
    def response(endpoint: str) -> dict:
        calls.append(endpoint)
        if "/attempts/" in endpoint:
            assert "/runs/1/attempts/1/jobs?per_page=100&page=1" in endpoint
            return {"total_count": 1, "jobs": [job()]}
        assert endpoint.endswith(f"/runs?head_sha={SHA}&per_page=100")
        workflow = endpoint.split("/workflows/")[1].split("/")[0]
        return {"workflow_runs": evidence["workflows"][workflow]}

    return response


@pytest.mark.parametrize("state", ["complete", "missing", "queued", "in_progress", "requested", "waiting", "pending"])
def test_preflight_is_one_shot_and_never_records_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture, state: str
) -> None:
    preflight_environment(tmp_path, monkeypatch)
    evidence, calls = snapshot(), []
    if state == "missing":
        evidence["workflows"]["ci.yml"] = []
    elif state != "complete":
        evidence["workflows"]["ci.yml"][0].update(status=state, conclusion=None)
    monkeypatch.setattr(wait_for_release_ci, "_public_json", preflight_response(evidence, calls))
    assert wait_for_release_ci.preflight() is (state == "complete")
    assert len(calls) == (6 if state == "complete" else 5)
    assert len([endpoint for endpoint in calls if "/workflows/" in endpoint]) == 3
    assert list(tmp_path.iterdir()) == []
    output = capsys.readouterr().out
    assert "final release acceptance is still required" in output if state == "complete" else "PENDING" in output


@pytest.mark.parametrize("conclusion", ["failure", "cancelled", "skipped", "timed_out", None])
def test_preflight_rejects_terminal_unsuccessful_exact_push(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conclusion: str | None
) -> None:
    preflight_environment(tmp_path, monkeypatch)
    evidence, calls = snapshot(), []
    evidence["workflows"]["ci.yml"][0]["conclusion"] = conclusion
    monkeypatch.setattr(wait_for_release_ci, "_public_json", preflight_response(evidence, calls))
    with pytest.raises(RuntimeError, match="did not pass"):
        wait_for_release_ci.preflight()
    assert len(calls) == 1
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("conclusion", ["skipped", "failure", "cancelled", "timed_out", None])
def test_preflight_rejects_green_run_without_successful_full_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conclusion: str | None
) -> None:
    preflight_environment(tmp_path, monkeypatch)
    calls = []
    response = preflight_response(snapshot(), calls)

    def paper_response(endpoint):
        result = response(endpoint)
        if "jobs" in result:
            result["jobs"][0]["conclusion"] = conclusion
        return result

    monkeypatch.setattr(wait_for_release_ci, "_public_json", paper_response)
    with pytest.raises(RuntimeError, match="exact main push has no successful full"):
        wait_for_release_ci.preflight()
    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == []


def test_preflight_uses_latest_exact_main_push_and_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preflight_environment(tmp_path, monkeypatch)
    evidence, calls = snapshot(), []
    evidence["workflows"]["ci.yml"] += [
        run(id=2, run_attempt=3, path=".github/workflows/ci.yml"),
        run(id=3, event="workflow_dispatch", path=".github/workflows/ci.yml"),
        run(id=4, head_branch="candidate", path=".github/workflows/ci.yml"),
        run(id=5, head_sha="b" * 40, path=".github/workflows/ci.yml"),
    ]

    def response(endpoint):
        calls.append(endpoint)
        if "/attempts/" in endpoint:
            assert "/runs/2/attempts/3/jobs?per_page=100&page=1" in endpoint
            return {"total_count": 1, "jobs": [job(run_id=2, run_attempt=2)]}
        return {"workflow_runs": evidence["workflows"]["ci.yml"]}

    monkeypatch.setattr(wait_for_release_ci, "_public_json", response)
    with pytest.raises(ValueError, match="requested run, attempt and SHA"):
        wait_for_release_ci.preflight()
    assert len(calls) == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "payload",
    ["not-json", "[]", "{}", '{"workflow_runs":{}}', '{"workflow_runs":[false]}'],
)
def test_preflight_refuses_malformed_api_without_writing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: str
) -> None:
    preflight_environment(tmp_path, monkeypatch)
    monkeypatch.setattr(wait_for_release_ci, "_public_json", lambda *args, **kwargs: payload)
    with pytest.raises(ValueError):
        wait_for_release_ci.preflight()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "change",
    [
        {"id": True},
        {"run_attempt": 0},
        {"path": ".github/workflows/other.yml"},
        {"status": "unknown"},
        {"status": "in_progress", "conclusion": "success"},
        {"head_sha": 1},
        {"head_sha": "a" * 39},
        {"head_branch": None},
        {"event": False},
    ],
)
def test_preflight_refuses_malformed_run_states(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, change: dict) -> None:
    preflight_environment(tmp_path, monkeypatch)
    evidence, calls = snapshot(), []
    evidence["workflows"]["ci.yml"][0].update(change)
    monkeypatch.setattr(wait_for_release_ci, "_public_json", preflight_response(evidence, calls))
    with pytest.raises(ValueError):
        wait_for_release_ci.preflight()
    assert list(tmp_path.iterdir()) == []


def test_preflight_refuses_duplicate_run_inventory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preflight_environment(tmp_path, monkeypatch)
    evidence, calls = snapshot(), []
    evidence["workflows"]["ci.yml"] *= 2
    monkeypatch.setattr(wait_for_release_ci, "_public_json", preflight_response(evidence, calls))
    with pytest.raises(ValueError, match="Duplicate"):
        wait_for_release_ci.preflight()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "variable,value",
    [("GITHUB_REPOSITORY", "other/repo"), ("GITHUB_REF", "refs/heads/candidate"), ("GITHUB_SHA", "a" * 39)],
)
def test_preflight_rejects_unauthorized_context_before_api_or_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, variable: str, value: str
) -> None:
    preflight_environment(tmp_path, monkeypatch)
    monkeypatch.setenv(variable, value)
    monkeypatch.setattr(
        wait_for_release_ci, "_public_json", lambda *args: pytest.fail("Invalid context queried GitHub")
    )
    with pytest.raises(ValueError, match="authorized exact main"):
        wait_for_release_ci.preflight()
    assert list(tmp_path.iterdir()) == []


def test_preflight_cli_preserves_existing_acceptance_snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    preflight_environment(tmp_path, monkeypatch)
    old = tmp_path / "evidence" / "historical-ci.json"
    old.parent.mkdir()
    old.write_bytes(b"existing acceptance must not be overwritten")
    evidence, calls = snapshot(), []
    evidence["workflows"]["ci.yml"] = []
    monkeypatch.setattr(wait_for_release_ci, "_public_json", preflight_response(evidence, calls))
    monkeypatch.setattr(sys, "argv", ["wait_for_release_ci", "--preflight"])
    wait_for_release_ci.main()
    assert old.read_bytes() == b"existing acceptance must not be overwritten"


def test_preflight_workflow_is_early_blocking_and_final_queue_is_unchanged() -> None:
    import yaml

    workflow = yaml.safe_load((Path(__file__).resolve().parents[1] / ".github/workflows/agent-release.yml").read_text())
    jobs = workflow["jobs"]
    preflight_job = jobs["publication-preflight"]
    commands = [step.get("run") for step in preflight_job["steps"]]
    early = "python -m scripts.wait_for_release_ci --preflight"
    assert commands.index("python -m scripts.publish_agent_release --preflight") + 1 == commands.index(early)
    step = preflight_job["steps"][commands.index(early)]
    assert step["if"] == "github.ref == 'refs/heads/main' && github.repository == 'MontrealAI/AGI-Alpha-Agent-v0'"
    assert set(step) == {"name", "if", "run"}
    assert preflight_job["timeout-minutes"] == 5 and not preflight_job.get("continue-on-error")
    assert "permissions" not in preflight_job
    assert jobs["regression"]["needs"] == ["paper-scope", "publication-preflight"]
    expected = (set(jobs["package"]["needs"]) - {"historical-ci"}) | {"publication-preflight"}
    assert set(jobs["historical-ci"]["needs"]) == expected
    assert "historical-ci" in jobs["package"]["needs"]


class PublicResponse:
    status = 200

    def __init__(self, raw: bytes):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self, maximum: int) -> bytes:
        assert maximum == wait_for_release_ci.MAX_SNAPSHOT_BYTES + 1
        return self.raw


def test_preflight_public_reads_are_fixed_anonymous_bounded_gets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "must-never-be-transmitted")
    monkeypatch.setenv("GITHUB_TOKEN", "must-never-be-transmitted")
    endpoints = [
        f"repos/{REPOSITORY}/actions/workflows/ci.yml/runs?head_sha={SHA}&per_page=100",
        f"repos/{REPOSITORY}/actions/runs/1/attempts/2/jobs?per_page=100&page=3",
    ]
    calls = []

    def open_public(request, **kwargs):
        calls.append(request.full_url)
        assert request.full_url == "https://api.github.com/" + endpoints[len(calls) - 1]
        assert request.get_method() == "GET" and request.data is None
        assert request.headers == {"User-agent": "Alpha-historical-release-preflight"}
        assert kwargs == {"timeout": 30}
        return PublicResponse(b"{}")

    monkeypatch.setattr(wait_for_release_ci, "urlopen", open_public)
    for endpoint in endpoints:
        assert wait_for_release_ci._public_json(endpoint) == {}
    assert len(calls) == 2


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://example.com",
        "repos/other/repo/actions/runs/1/attempts/1/jobs?per_page=100&page=1",
        f"repos/{REPOSITORY}/actions/runs/1/jobs",
        f"repos/{REPOSITORY}/actions/runs/1/attempts/1/jobs?per_page=100&page=0",
    ],
)
def test_preflight_public_reader_refuses_other_endpoints_before_network(
    monkeypatch: pytest.MonkeyPatch, endpoint: str
) -> None:
    monkeypatch.setattr(wait_for_release_ci, "urlopen", lambda *args, **kwargs: pytest.fail("Invalid endpoint queried"))
    with pytest.raises(ValueError, match="fixed public"):
        wait_for_release_ci._public_json(endpoint)


@pytest.mark.parametrize("raw", [b"not-json", b"[]", b"x" * 65])
def test_preflight_public_reader_refuses_malformed_or_oversized_bodies(
    monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    monkeypatch.setattr(wait_for_release_ci, "MAX_SNAPSHOT_BYTES", 64)
    monkeypatch.setattr(wait_for_release_ci, "urlopen", lambda *args, **kwargs: PublicResponse(raw))
    with pytest.raises(ValueError):
        wait_for_release_ci._public_json(
            f"repos/{REPOSITORY}/actions/workflows/ci.yml/runs?head_sha={SHA}&per_page=100"
        )


@pytest.mark.parametrize("error", [TimeoutError("public API timed out"), OSError("public API refused")])
def test_preflight_network_errors_stop_without_retry_or_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    preflight_environment(tmp_path, monkeypatch)
    calls = []

    def failed_open(*args, **kwargs):
        calls.append(args)
        raise error

    monkeypatch.setattr(wait_for_release_ci, "urlopen", failed_open)
    with pytest.raises(type(error), match="public API"):
        wait_for_release_ci.preflight()
    assert len(calls) == 1 and list(tmp_path.iterdir()) == []
