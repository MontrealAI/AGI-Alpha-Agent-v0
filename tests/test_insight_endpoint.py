# SPDX-License-Identifier: Apache-2.0
import os
from typing import Any, cast

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")
os.environ.setdefault("AGI_INSIGHT_ALLOW_INSECURE", "1")
os.environ.setdefault("NO_LLM", "1")

def _setup_simulations(api) -> None:
    api._simulations.clear()
    api._simulations["a"] = api.ResultsResponse(
        id="a",
        forecast=[api.ForecastPoint(year=1, capability=0.1)],
        population=None,
    )
    api._simulations["b"] = api.ResultsResponse(
        id="b",
        forecast=[api.ForecastPoint(year=1, capability=0.9)],
        population=None,
    )


def test_insight_aggregates_results() -> None:
    headers = {"Authorization": "Bearer test-token"}
    from alpha_factory_v1.core.interface import api_server as api

    with TestClient(cast(Any, api.app)) as client:
        _setup_simulations(api)
        resp = client.post("/insight", json={"ids": ["a", "b"]}, headers=headers)
        assert resp.status_code == 200
        assert resp.json() == {"forecast": [{"year": 1, "capability": 0.5}]}


def test_insight_invalid_token() -> None:
    from alpha_factory_v1.core.interface import api_server as api

    with TestClient(cast(Any, api.app)) as client:
        _setup_simulations(api)
        resp = client.post("/insight", json={}, headers={"Authorization": "Bearer bad"})
        assert resp.status_code == 403


def test_insight_missing_ids() -> None:
    headers = {"Authorization": "Bearer test-token"}
    from alpha_factory_v1.core.interface import api_server as api

    with TestClient(cast(Any, api.app)) as client:
        _setup_simulations(api)
        resp = client.post("/insight", json={"ids": ["missing"]}, headers=headers)
        assert resp.status_code == 404
