# SPDX-License-Identifier: Apache-2.0

import importlib
import os
from typing import Any, cast

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")


def test_rate_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify API returns 429 when the request limit is exceeded."""

    monkeypatch.setenv("API_RATE_LIMIT", "2")

    from alpha_factory_v1.core.interface import api_server

    api = importlib.reload(api_server)

    headers = {"Authorization": "Bearer test-token"}

    with TestClient(cast(Any, api.app)) as client:
        assert client.get("/runs", headers=headers).status_code == 200
        assert client.get("/runs", headers=headers).status_code == 200

        resp = client.get("/runs", headers=headers)
        assert resp.status_code == 429
