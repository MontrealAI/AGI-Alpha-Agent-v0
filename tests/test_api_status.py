# SPDX-License-Identifier: Apache-2.0
"""Verify the /status endpoint and CLI output."""

import importlib
import os
from typing import Any, cast
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from click.testing import CliRunner

os.environ.setdefault("API_TOKEN", "test-token")
os.environ.setdefault("API_RATE_LIMIT", "1000")
os.environ.setdefault("AGI_INSIGHT_ALLOW_INSECURE", "1")
os.environ.setdefault("AGI_INSIGHT_OFFLINE", "1")


def _make_client() -> TestClient:
    from alpha_factory_v1.core.interface import api_server

    api_server = importlib.reload(api_server)
    client = TestClient(cast(Any, api_server.app))
    client.__enter__()  # start lifespan
    return client


def test_status_endpoint() -> None:
    client = _make_client()
    headers = {"Authorization": "Bearer test-token"}
    resp = client.get("/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert data.get("agents")
    client.__exit__(None, None, None)


def test_cli_agents_status_parses_mapping() -> None:
    from alpha_factory_v1.core.interface import cli

    payload = {"agents": {"agent1": {"last_beat": 1.0, "restarts": 0}}}

    class Dummy:
        status_code = 200

        def json(self) -> dict:
            return payload

    with patch.object(cli._insight_cli.requests, "get", return_value=Dummy()):
        result = CliRunner().invoke(cli.main, ["agents-status"])
    assert "agent1" in result.output
