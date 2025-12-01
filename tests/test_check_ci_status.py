"""Unit tests for :mod:`scripts.check_ci_status`."""

from __future__ import annotations

from io import BytesIO
import urllib.error

import pytest

from scripts import check_ci_status


def _http_error(code: int, body: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        url="https://example.invalid",
        code=code,
        msg="Forbidden",
        hdrs=None,
        fp=BytesIO(body.encode()),
    )


def test_rerun_workflow_stops_on_forbidden(monkeypatch: pytest.MonkeyPatch) -> None:
    """403 responses should not trigger a fallback rerun."""

    def fake_urlopen(request, timeout=30):  # noqa: ANN001
        raise _http_error(403, '{"message":"This workflow run cannot be retried"}')

    def fail_if_called(*_, **__):  # noqa: ANN002, ANN003
        pytest.fail("should not attempt rerun-failed-jobs after a 403")

    monkeypatch.setattr(check_ci_status.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(check_ci_status, "_rerun_failed_jobs", fail_if_called)

    run = {"id": 123, "rerun_url": "https://api.github.com/runs/123/rerun"}
    result = check_ci_status._rerun_workflow("owner/repo", run, token="secret")

    assert result.startswith("rerun forbidden (HTTP 403:"), result
