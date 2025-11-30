"""Tests for the CI status helper script."""

from __future__ import annotations

import io
import json
import urllib.error

import scripts.check_ci_status as ci_status


def _http_error(status: int, message: str) -> urllib.error.HTTPError:
    body = io.BytesIO(message.encode("utf-8"))
    return urllib.error.HTTPError("https://example.com", status, "reason", None, body)


def test_can_rerun_respects_missing_url():
    assert not ci_status._can_rerun({})
    assert ci_status._can_rerun({"rerun_url": "https://example.com"})


def test_rerun_workflow_handles_non_retriable_runs(monkeypatch):
    run = {"id": 123, "rerun_url": "https://example.com/rerun"}
    message = json.dumps({"message": "This workflow run cannot be retried"})

    def _raise_forbid(request, timeout=None):  # noqa: ARG001
        raise _http_error(403, message)

    rerun_failed_called = False

    def _rerun_failed_jobs(repo, run_id, token):  # noqa: ARG001
        nonlocal rerun_failed_called
        rerun_failed_called = True
        return "dispatched"

    monkeypatch.setattr(ci_status.urllib.request, "urlopen", _raise_forbid)
    monkeypatch.setattr(ci_status, "_rerun_failed_jobs", _rerun_failed_jobs)

    result = ci_status._rerun_workflow("owner/repo", run, "token")

    assert result == "rerun not permitted for this workflow run"
    assert not rerun_failed_called
