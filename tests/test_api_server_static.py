# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the API server's static endpoints."""

import importlib
import os
import time
from collections import deque
from pathlib import Path
from typing import Any, cast

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")


def test_throttle_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """Trigger rate limit alert when the counter resets."""
    monkeypatch.setenv("API_RATE_LIMIT", "1")
    from alpha_factory_v1.core.interface import api_server as mod

    api = importlib.reload(mod)

    sent: list[str] = []
    monkeypatch.setattr(api.alerts, "send_alert", lambda msg, url=None: sent.append(msg))

    client = TestClient(cast(Any, api.app))
    headers = {"Authorization": "Bearer test-token"}

    client.get("/runs", headers=headers)
    client.get("/runs", headers=headers)

    metrics = api.app.state.metrics
    limiter = api.app.state.limiter
    metrics.window_start = time.time() - 61
    limiter.counters["testclient"] = deque()

    client.get("/runs", headers=headers)

    assert sent, "alert not triggered"

    monkeypatch.setenv("API_RATE_LIMIT", "1000")
    importlib.reload(api)


def test_lineage_detail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify lineage details include the specified record."""
    monkeypatch.setenv("API_RATE_LIMIT", "1000")
    monkeypatch.setenv("ARCHIVE_PATH", str(tmp_path / "a.db"))
    from alpha_factory_v1.core.archive import Archive

    arch = Archive(tmp_path / "a.db")
    arch.add({"diff": "root"}, 0.1)
    arch.add({"parent": 1, "diff": "child"}, 0.2)

    from alpha_factory_v1.core.interface import api_server as mod

    api = importlib.reload(mod)

    client = TestClient(cast(Any, api.app))
    headers = {"Authorization": "Bearer test-token"}
    resp = client.get("/lineage/2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[-1]["id"] == 2
