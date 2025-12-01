from __future__ import annotations

import types

from scripts import verify_branch_protection


def _make_response(*, status_code: int, text: str = "", json_data: dict | None = None) -> types.SimpleNamespace:
    return types.SimpleNamespace(
        status_code=status_code,
        ok=status_code < 400,
        text=text,
        json=lambda: json_data or {},
    )


def test_forbidden_responses_are_reported_and_skipped(monkeypatch, capsys):
    monkeypatch.setenv("GITHUB_REPOSITORY", "owner/repo")
    monkeypatch.setenv("GITHUB_TOKEN", "placeholder")

    monkeypatch.setattr(
        verify_branch_protection.requests,
        "get",
        lambda *args, **kwargs: _make_response(status_code=403, text="forbidden"),
    )

    called = False

    def _fail_if_called(**_: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(verify_branch_protection, "_configure_required_checks", _fail_if_called)

    exit_code = verify_branch_protection.main(["--branch", "main", "--apply"])

    assert exit_code == 0
    assert called is False
    assert "Missing permission to read branch protection" in capsys.readouterr().err
