# SPDX-License-Identifier: Apache-2.0
"""Health checks for the Insight API server."""

import os

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

# Ensure required environment variables are present for the API
os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("AGI_INSIGHT_ALLOW_INSECURE", "1")

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface import api_server


@pytest.fixture()
def client() -> TestClient:
    with TestClient(api_server.app) as client:
        yield client


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.text == "ok"


def test_readiness(client: TestClient) -> None:
    resp = client.get("/readiness")
    assert resp.status_code == 200
    assert resp.text == "ok"
