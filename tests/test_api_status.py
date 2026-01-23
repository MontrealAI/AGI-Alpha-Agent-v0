# SPDX-License-Identifier: Apache-2.0
"""Verify the /status endpoint and CLI output."""

import contextlib
import importlib
import os
from typing import Any, Iterator, cast
from unittest.mock import patch

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from click.testing import CliRunner

os.environ["API_TOKEN"] = "test-token"
os.environ["API_RATE_LIMIT"] = "1000"
os.environ["AGI_INSIGHT_ALLOW_INSECURE"] = "1"
os.environ["AGI_INSIGHT_OFFLINE"] = "1"


@contextlib.contextmanager
def _make_client() -> Iterator[TestClient]:
    from alpha_factory_v1.core.interface import api_server

    api_server = importlib.reload(api_server)
    with TestClient(cast(Any, api_server.app)) as client:
        yield client


def test_status_endpoint() -> None:
    with _make_client() as client:
        headers = {"Authorization": "Bearer test-token"}
        resp = client.get("/status", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
        assert data.get("agents")


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
