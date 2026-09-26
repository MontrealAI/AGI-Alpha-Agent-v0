from __future__ import annotations

import ast
import io
import json
from pathlib import Path

from scripts import verify_branch_protection


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status: int = 200) -> None:
        self.status = status
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        return None


def test_missing_token_skips_verification(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    assert verify_branch_protection.main([]) == 0
    captured = capsys.readouterr()
    assert "skipping branch protection" in captured.err


def test_missing_permission_skips_verification(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    def fake_urlopen(request, timeout=30):  # noqa: ARG001
        raise verify_branch_protection.urllib.error.HTTPError(
            url=request.full_url,
            code=403,
            msg="forbidden",
            hdrs=None,
            fp=io.BytesIO(b'{"message": "Resource not accessible by integration"}'),
        )

    monkeypatch.setattr(verify_branch_protection.urllib.request, "urlopen", fake_urlopen)
    assert verify_branch_protection.main([]) == 0
    captured = capsys.readouterr()
    assert "Missing permission to read branch protection" in captured.err


def test_verification_succeeds_without_requests_dependency(monkeypatch):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "token")

    protection = {
        "required_status_checks": {
            "strict": True,
            "contexts": [
                "Lint (ruff)",
                "Smoke tests",
            ],
            "required_check_runs": [],
        }
    }

    monkeypatch.setattr(
        verify_branch_protection.urllib.request,
        "urlopen",
        lambda _request, timeout=30: _FakeResponse(protection),  # noqa: ARG005
    )

    assert verify_branch_protection.main([]) == 0


def test_script_does_not_import_requests() -> None:
    script = Path("scripts/verify_branch_protection.py").read_text(encoding="utf-8")
    tree = ast.parse(script)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name != "requests" and not alias.name.startswith("requests.") for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module != "requests" and not module.startswith("requests.")


def test_required_names_match_real_workflow_jobs() -> None:
    import yaml

    workflow = yaml.safe_load(Path(".github/workflows/pr-ci.yml").read_text())
    job_names = {job.get("name", ident) for ident, job in workflow["jobs"].items()}
    configured = set(json.loads(Path("scripts/required_checks.json").read_text()))
    assert configured == set(verify_branch_protection.DEFAULT_REQUIRED_CHECKS)
    assert configured <= job_names


def test_current_check_objects_are_recognized() -> None:
    protection = {"required_status_checks": {"strict": True, "checks": [{"context": "Lint (ruff)", "app_id": 15368}]}}
    assert verify_branch_protection._required_contexts(protection) == {"Lint (ruff)"}
