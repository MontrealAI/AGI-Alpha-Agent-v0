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
