# SPDX-License-Identifier: Apache-2.0

import os
from typing import Any, cast

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")

from alpha_factory_v1.core.interface import api_server as api


def make_client() -> TestClient:
    return TestClient(cast(Any, api.app))


def test_metrics_endpoint() -> None:
    with make_client() as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "api_requests_total" in resp.text
        assert "api_request_seconds" in resp.text
        assert "dgm_best_score" in resp.text
        assert "dgm_archive_mean" in resp.text
        assert "dgm_lineage_depth" in resp.text
