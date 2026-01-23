# SPDX-License-Identifier: Apache-2.0
"""Tests for the Insight demo API server."""

import importlib
import os
from typing import Any, cast

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.interface import api_server
from alpha_factory_v1.utils.disclaimer import DISCLAIMER


@pytest.fixture()
def client() -> TestClient:
    os.environ.setdefault("API_TOKEN", "test-token")
    os.environ.setdefault("API_RATE_LIMIT", "1000")
    api = importlib.reload(api_server)
    with TestClient(cast(Any, api.app)) as client:
        yield client


def test_root_disclaimer_plain(client: TestClient) -> None:
    """Plain text disclaimer is returned by default."""

    r = client.get("/")
    assert r.status_code == 200
    assert r.text.strip() == DISCLAIMER


def test_root_disclaimer_html(client: TestClient) -> None:
    """HTML disclaimer is returned when requested."""

    r = client.get("/", headers={"Accept": "text/html"})
    assert r.status_code == 200
    assert DISCLAIMER in r.text
    assert r.headers.get("content-type", "").startswith("text/html")
