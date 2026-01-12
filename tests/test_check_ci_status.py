import json

from scripts import check_ci_status


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
