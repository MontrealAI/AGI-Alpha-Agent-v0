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

from alpha_factory_v1.core.interface import api_server as api


def test_metrics_endpoint() -> None:
    with TestClient(cast(Any, api.app)) as client:
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "api_requests_total" in resp.text
        assert "api_request_seconds" in resp.text
        assert "dgm_best_score" in resp.text
        assert "dgm_archive_mean" in resp.text
        assert "dgm_lineage_depth" in resp.text
