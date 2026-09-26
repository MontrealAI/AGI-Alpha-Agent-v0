import json
from datetime import datetime, timezone

import pytest

from scripts import check_ci_status


def test_exact_commit_rejects_stale_endpoint_and_uses_verified_fallback(monkeypatch):
    correct = dict(id=2, run_attempt=1, head_sha="a" * 40, head_branch="main", path=".github/workflows/ci.yml")
    stale = {**correct, "id": 1, "head_sha": "b" * 40, "conclusion": "success"}
    calls = []

    def request(url, token):
        calls.append(url)
        assert "head_sha=" + "a" * 40 in url
        if "/workflows/" in url:
            return {"workflow_runs": [stale]}
        return {"workflow_runs": [stale, correct, {**correct, "id": 3, "path": ".github/workflows/other.yml"}]}

    monkeypatch.setattr(check_ci_status, "_github_request", request)
    assert check_ci_status._latest_run("owner/repo", "ci.yml", None, branch="main", commit="a" * 40) == correct
    assert len(calls) == 2


def test_no_matching_commit_cannot_pass(monkeypatch):
    monkeypatch.setattr(
        check_ci_status,
        "_github_request",
        lambda *args: {"workflow_runs": [{"id": 1, "head_sha": "b" * 40, "conclusion": "success"}]},
    )
    failures, _ = check_ci_status.verify_workflows("owner/repo", ["ci.yml"], None, commit="a" * 40)
    assert failures and "No runs found" in failures[0]


@pytest.mark.parametrize("conclusion", [None, "success"])
def test_pending_never_passes_when_wait_budget_expires(monkeypatch, conclusion):
    pending = dict(id=1, status="in_progress", conclusion=conclusion, created_at=datetime.now(timezone.utc).isoformat())
    monkeypatch.setattr(check_ci_status, "_latest_run", lambda *args, **kwargs: pending)
    sleeps = []
    monkeypatch.setattr(check_ci_status.time, "sleep", sleeps.append)
    failures, _ = check_ci_status.verify_workflows(
        "owner/repo", ["ci.yml"], None, wait_seconds=2, poll_interval=1, pending_grace_seconds=2700
    )
    assert failures
    assert sleeps == [1, 1]


def test_rerun_cannot_extend_watchdog_deadline(monkeypatch):
    failed = dict(id=1, status="completed", conclusion="failure", rerun_url="https://example.test")
    monkeypatch.setattr(check_ci_status, "_latest_run", lambda *args, **kwargs: failed)
    retries = []
    monkeypatch.setattr(check_ci_status, "_rerun_workflow", lambda *args: retries.append(args) or "dispatched")
    sleeps = []
    monkeypatch.setattr(check_ci_status.time, "sleep", sleeps.append)
    failures, _ = check_ci_status.verify_workflows(
        "owner/repo", ["ci.yml"], None, wait_seconds=2, poll_interval=1, rerun_failed=True
    )
    assert failures and len(retries) == 1 and sleeps == [1, 1]


def test_latest_attempt_is_selected_without_hiding_failures(monkeypatch):
    passed = dict(id=1, run_attempt=1, head_sha="a" * 40, head_branch="main", conclusion="success")
    failed = {**passed, "id": 2, "conclusion": "failure"}
    monkeypatch.setattr(check_ci_status, "_github_request", lambda *args: {"workflow_runs": [passed, failed]})
    assert check_ci_status._latest_run("owner/repo", "ci.yml", None, branch="main", commit="a" * 40) == failed


def test_workflow_filename_from_env_prefers_run_metadata(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_RUN_ID", "12345")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI Health")

    def fake_request(url: str, token: str | None):  # type: ignore[override]
        assert url.endswith("/actions/runs/12345")
        return {"path": ".github/workflows/custom-ci.yml"}

    monkeypatch.setattr(check_ci_status, "_github_request", fake_request)

    assert check_ci_status._workflow_filename_from_env("token") == "custom-ci.yml"


def test_main_skips_current_workflow(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI Health")

    monkeypatch.setattr(check_ci_status, "_workflow_filename_from_env", lambda token=None: "ci-health.yml")

    captured: list[str] = []

    def fake_verify(repo, workflows, token, **kwargs):  # type: ignore[override]
        captured.extend(workflows)
        return [], {wf: {} for wf in workflows}

    monkeypatch.setattr(check_ci_status, "verify_workflows", fake_verify)

    assert check_ci_status.main(["--repo", "owner/repo", "--once"]) == 0
    assert "ci-health.yml" not in captured


def test_main_disables_mutations_without_write_permission(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI Health")

    def fake_capability(repo: str, token: str | None):  # type: ignore[override]
        return False, "missing token"

    def fake_verify(repo, workflows, token, **kwargs):  # type: ignore[override]
        assert kwargs["rerun_failed"] is False
        return [], {wf: {} for wf in workflows}

    monkeypatch.setattr(check_ci_status, "_actions_write_capability", fake_capability)
    monkeypatch.setattr(check_ci_status, "verify_workflows", fake_verify)

    assert check_ci_status.main(["--repo", "owner/repo", "--rerun-failed", "--once"]) == 0
    output = capsys.readouterr().out
    assert "read-only mode" in output


@pytest.mark.parametrize("current", [True, False, None])
def test_superseded_or_unverifiable_commit_cannot_remediate(monkeypatch, current):
    monkeypatch.setattr(check_ci_status, "_actions_write_capability", lambda *args: (True, "write allowed"))
    monkeypatch.setattr(check_ci_status, "_workflow_filename_from_env", lambda *args: None)

    def request(url, token):
        assert url.endswith("/git/ref/heads/feature%2Ftest")
        if current is None:
            raise check_ci_status.urllib.error.URLError("temporary failure")
        return {"object": {"sha": ("a" if current else "b") * 40}}

    def verify(repo, workflows, token, **kwargs):
        assert kwargs["rerun_failed"] is (current is True)
        assert kwargs["commit"] == "a" * 40
        # No matching run would ordinarily trigger dispatch-missing. The
        # superseded/unverifiable case must leave the current build untouched.
        return (["missing"], {}) if current is not True else ([], {"pr-ci.yml": {"conclusion": "success"}})

    monkeypatch.setattr(check_ci_status, "_github_request", request)
    monkeypatch.setattr(check_ci_status, "verify_workflows", verify)
    monkeypatch.setattr(check_ci_status, "_dispatch_workflow", lambda *args: pytest.fail("unexpected dispatch"))
    result = check_ci_status.main(
        [
            "--repo",
            "owner/repo",
            "--branch",
            "feature/test",
            "--commit",
            "a" * 40,
            "--workflow",
            "pr-ci.yml",
            "--rerun-failed",
            "--cancel-stale",
            "--dispatch-missing",
            "--once",
        ]
    )
    assert result == (0 if current is True else 1)


def test_actions_write_capability_detects_fork(monkeypatch, tmp_path):
    event_payload = {
        "pull_request": {
            "head": {
                "repo": {"full_name": "someone/forked-repo"},
            }
        }
    }
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event_payload), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    def fake_request(url: str, token: str | None, **_kwargs):  # type: ignore[override]
        return {"permissions": {"admin": True}}

    monkeypatch.setattr(check_ci_status, "_github_request", fake_request)

    allowed, reason = check_ci_status._actions_write_capability("owner/repo", "token")
    assert allowed is False
    assert "fork" in reason


def test_default_workflows_for_pr_gate_workflow_run(tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"workflow_run": {"name": "✅ PR CI"}}), encoding="utf-8")

    workflows = check_ci_status._default_workflows_for_event(str(event_path))
    assert workflows == ["pr-ci.yml"]


def test_default_workflows_for_integration_workflow_run(tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"workflow_run": {"name": "🚀 Integration CI — Insight Demo"}}),
        encoding="utf-8",
    )

    workflows = check_ci_status._default_workflows_for_event(str(event_path))
    assert workflows == ["ci.yml"]


def test_default_workflows_for_docs_workflow_run(tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"workflow_run": {"name": "📚 Docs"}}),
        encoding="utf-8",
    )

    workflows = check_ci_status._default_workflows_for_event(str(event_path))
    assert workflows == ["docs.yml"]


def test_dispatch_missing_does_not_dispatch_failed_workflows(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    def fake_verify(repo, workflows, token, **kwargs):  # type: ignore[override]
        return ["pr-ci.yml: failure"], {"pr-ci.yml": {"conclusion": "failure"}}

    dispatch_calls: list[str] = []

    monkeypatch.setattr(check_ci_status, "verify_workflows", fake_verify)
    monkeypatch.setattr(check_ci_status, "_actions_write_capability", lambda repo, token: (True, "ok"))
    monkeypatch.setattr(check_ci_status, "_workflow_supports_dispatch", lambda workflow: True)
    monkeypatch.setattr(
        check_ci_status,
        "_dispatch_workflow",
        lambda repo, workflow, ref, token: (dispatch_calls.append(workflow) is None, "dispatched"),
    )

    exit_code = check_ci_status.main(
        ["--repo", "owner/repo", "--workflow", "pr-ci.yml", "--dispatch-missing", "--once"]
    )

    assert exit_code == 1
    assert dispatch_calls == []


def test_dispatch_failed_opt_in_dispatches_failed_workflow(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")

    verify_calls = {"count": 0}

    def fake_verify(repo, workflows, token, **kwargs):  # type: ignore[override]
        verify_calls["count"] += 1
        return ["pr-ci.yml: failure"], {"pr-ci.yml": {"conclusion": "failure"}}

    dispatch_calls: list[str] = []

    monkeypatch.setattr(check_ci_status, "verify_workflows", fake_verify)
    monkeypatch.setattr(check_ci_status, "_actions_write_capability", lambda repo, token: (True, "ok"))
    monkeypatch.setattr(check_ci_status, "_workflow_supports_dispatch", lambda workflow: True)

    def fake_dispatch(repo, workflow, ref, token):  # type: ignore[override]
        dispatch_calls.append(workflow)
        return True, "dispatched"

    monkeypatch.setattr(check_ci_status, "_dispatch_workflow", fake_dispatch)

    exit_code = check_ci_status.main(
        ["--repo", "owner/repo", "--workflow", "pr-ci.yml", "--dispatch-missing", "--dispatch-failed", "--once"]
    )

    assert exit_code == 1
    assert dispatch_calls == ["pr-ci.yml"]
    assert verify_calls["count"] == 1


def test_main_can_include_current_workflow_when_opted_in(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI Health")

    monkeypatch.setattr(check_ci_status, "_workflow_filename_from_env", lambda token=None: "ci-health.yml")

    captured: list[str] = []

    def fake_verify(repo, workflows, token, **kwargs):  # type: ignore[override]
        captured.extend(workflows)
        return [], {wf: {} for wf in workflows}

    monkeypatch.setattr(check_ci_status, "verify_workflows", fake_verify)

    assert (
        check_ci_status.main(["--repo", "owner/repo", "--workflow", "ci-health.yml", "--include-self", "--once"]) == 0
    )
    assert "ci-health.yml" in captured


def test_workflow_run_context_disables_dispatch(monkeypatch, tmp_path):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "workflow_run")

    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps({"workflow_run": {"name": "✅ PR CI"}}), encoding="utf-8")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))

    def fake_verify(repo, workflows, token, **kwargs):  # type: ignore[override]
        return ["pr-ci.yml: error fetching latest run: missing"], {}

    dispatch_calls: list[str] = []

    monkeypatch.setattr(check_ci_status, "verify_workflows", fake_verify)
    monkeypatch.setattr(check_ci_status, "_actions_write_capability", lambda repo, token: (True, "ok"))
    monkeypatch.setattr(check_ci_status, "_workflow_supports_dispatch", lambda workflow: True)

    def fake_dispatch(repo, workflow, ref, token):  # type: ignore[override]
        dispatch_calls.append(workflow)
        return True, "dispatched"

    monkeypatch.setattr(check_ci_status, "_dispatch_workflow", fake_dispatch)

    exit_code = check_ci_status.main(["--repo", "owner/repo", "--dispatch-missing", "--once"])

    assert exit_code == 1
    assert dispatch_calls == []


def test_branch_move_during_check_cannot_retry_an_old_run(monkeypatch):
    monkeypatch.setattr(check_ci_status, "_actions_write_capability", lambda *args: (True, "write allowed"))
    monkeypatch.setattr(check_ci_status, "_workflow_filename_from_env", lambda *args: None)
    heads = iter(["a" * 40, "b" * 40])
    monkeypatch.setattr(check_ci_status, "_github_request", lambda *args: {"object": {"sha": next(heads)}})
    failed = dict(
        id=1,
        head_sha="a" * 40,
        head_branch="main",
        status="completed",
        conclusion="failure",
        rerun_url="exists",
        run_attempt=1,
    )
    monkeypatch.setattr(check_ci_status, "_latest_run", lambda *args, **kwargs: failed)
    monkeypatch.setattr(
        check_ci_status.urllib.request, "urlopen", lambda *args, **kwargs: pytest.fail("unexpected mutation")
    )
    assert (
        check_ci_status.main(
            [
                "--repo",
                "owner/repo",
                "--token",
                "fixture",
                "--branch",
                "main",
                "--commit",
                "a" * 40,
                "--rerun-failed",
                "--once",
            ]
        )
        == 1
    )


def test_automatic_retry_cannot_loop_through_workflow_run_events(monkeypatch):
    monkeypatch.setattr(check_ci_status, "_github_request", lambda *args: pytest.fail("unexpected retry lookup"))
    run = dict(id=1, run_attempt=2, rerun_url="exists", head_branch="main", head_sha="a" * 40)
    assert "retry budget exhausted" in check_ci_status._rerun_workflow("owner/repo", run, "fixture")


def test_one_current_commit_retry_still_works(monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr(check_ci_status, "_github_request", lambda *args: {"object": {"sha": "a" * 40}})
    posts = []

    def post(request, **kwargs):
        assert request.method == "POST" and request.full_url.endswith("/actions/runs/1/rerun")
        posts.append(request.full_url)
        return nullcontext()

    monkeypatch.setattr(check_ci_status.urllib.request, "urlopen", post)
    run = dict(id=1, run_attempt=1, rerun_url="exists", head_branch="main", head_sha="a" * 40)
    assert check_ci_status._rerun_workflow("owner/repo", run, "fixture") == "dispatched"
    assert len(posts) == 1
