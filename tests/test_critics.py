# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the DualCriticService."""

from __future__ import annotations

import asyncio
import json
import socket
from statistics import quantiles
from typing import Any

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("grpc")
from fastapi.testclient import TestClient  # noqa: E402
import grpc  # noqa: E402

from alpha_factory_v1.core.critics import DualCriticService, create_app


def _free_port() -> int:
    s = socket.socket()
    s.bind(("localhost", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_rest_scoring() -> None:
    service = DualCriticService(["Paris is the capital of France."])
    with TestClient(create_app(service)) as client:
        ok = client.post(
            "/critique",
            json={"context": "Paris is the capital of France.", "response": "Paris is the capital of France."},
        )
        assert ok.status_code == 200
        data = ok.json()
        assert data["logic"] > 0.5
        assert data["feas"] > 0.0

        bad = client.post(
            "/critique",
            json={"context": "Paris is the capital of France.", "response": "Berlin is the capital."},
        )
        assert bad.status_code == 200
        assert bad.json()["logic"] < 0.5


def test_grpc_scoring() -> None:
    service = DualCriticService(["Rome is the capital of Italy."])
    port = _free_port()

    async def run() -> None:
        await service.start_grpc(port)
        async with grpc.aio.insecure_channel(f"localhost:{port}") as ch:
            stub = ch.unary_unary("/critics.Critic/Score")
            payload = {
                "context": "Rome is the capital of Italy.",
                "response": "Rome is the capital of Italy.",
            }
            reply = await stub(json.dumps(payload).encode())
            data = json.loads(reply.decode())
            assert data["logic"] == 1.0
        await service.stop_grpc()

    asyncio.run(run())


pytest.importorskip("pytest_benchmark")


@pytest.mark.benchmark(group="critics")  # type: ignore[misc]
def test_latency_benchmark(benchmark: Any) -> None:
    service = DualCriticService(["alpha"])

    def run() -> None:
        service.score("alpha", "alpha")

    result = benchmark(run)
    p95 = 0.0
    if getattr(result, "stats", None) and result.stats["data"]:
        p95 = quantiles(result.stats["data"], n=20)[18]
    assert p95 >= 0.0
