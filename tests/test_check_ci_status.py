import io
import urllib.error

import scripts.check_ci_status as ci_status


def test_rerun_workflow_forbidden_skips_fallback(monkeypatch):
    run = {"id": 123, "rerun_url": "https://example"}
    error_body = b'{"message":"This workflow run cannot be retried","status":"403"}'
    http_error = urllib.error.HTTPError(
        "https://api.github.com",
        403,
        "Forbidden",
        hdrs=None,
        fp=io.BytesIO(error_body),
    )

    fallback_called = False

    def fake_rerun_failed_jobs(repo: str, run_id: int, token: str | None) -> str:
        nonlocal fallback_called
        fallback_called = True
        return "dispatched"

    def fake_urlopen(request, timeout=30):  # noqa: ANN001
        raise http_error

    monkeypatch.setattr(ci_status.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(ci_status, "_rerun_failed_jobs", fake_rerun_failed_jobs)

    result = ci_status._rerun_workflow("owner/repo", run, "token")

    assert result.startswith("rerun forbidden (HTTP 403)")
    assert fallback_called is False
