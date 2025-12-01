from __future__ import annotations

import io
import urllib.error
import urllib.request

import pytest

from scripts import check_ci_status


def test_rerun_workflow_skips_fallback_on_forbidden(monkeypatch):
    token = "test-token"
    run = {"id": 123, "rerun_url": "https://api.github.com/workflow/rerun"}

    def fake_urlopen(request, timeout=30):  # noqa: ARG001
        raise urllib.error.HTTPError(
            url="https://api.github.com/example",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=io.BytesIO(b"This workflow run cannot be retried"),
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    fallback_called = False

    def fake_rerun_failed_jobs(repo, run_id, token):  # noqa: ARG001
        nonlocal fallback_called
        fallback_called = True
        return "should not be called"

    monkeypatch.setattr(check_ci_status, "_rerun_failed_jobs", fake_rerun_failed_jobs)

    result = check_ci_status._rerun_workflow("owner/repo", run, token)

    assert result.startswith("rerun forbidden (HTTP 403):")
    assert fallback_called is False

