# SPDX-License-Identifier: Apache-2.0
"""Lifecycle test for the backend orchestrator."""

from __future__ import annotations

import asyncio
import socket
import sys
import types

import importlib
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("grpc")


class DummyAgent:
    NAME = "dummy"
    CYCLE_SECONDS = 0.0

    async def run_cycle(self) -> None:  # pragma: no cover - simple stub
        return None


@pytest.mark.asyncio  # type: ignore[misc]
async def test_orchestrator_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Start the orchestrator, verify health, then shut down cleanly."""

    # Allocate random ports
    with socket.socket() as s:
        s.bind(("", 0))
        rest_port = s.getsockname()[1]
    with socket.socket() as s:
        s.bind(("", 0))
        grpc_port = s.getsockname()[1]

    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("API_TOKEN", "t")
    monkeypatch.setenv("NEO4J_PASSWORD", "x")
    monkeypatch.setenv("PORT", str(rest_port))
    monkeypatch.setenv("A2A_PORT", str(grpc_port))
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    # Prepare stub packages before importing orchestrator
    for module_name in list(sys.modules):
        if module_name.startswith(("alpha_factory_v1.backend.agents", "backend.agents")):
            sys.modules.pop(module_name, None)
    for module_name in (
        "alpha_factory_v1.backend",
        "backend",
        "alpha_factory_v1.backend.agents",
        "backend.agents",
        "alpha_factory_v1.backend.agents.finance_agent",
        "backend.finance_agent",
    ):
        sys.modules.pop(module_name, None)
    agents_stub = types.ModuleType("backend.agents")
    setattr(agents_stub, "list_agents", lambda _detail=False: ["dummy"])
    setattr(agents_stub, "get_agent", lambda name: DummyAgent())
    setattr(agents_stub, "start_background_tasks", lambda: asyncio.sleep(0))

    fin_stub = types.ModuleType("alpha_factory_v1.backend.agents.finance_agent")
    setattr(fin_stub, "metrics_asgi_app", lambda: None)

    mem_stub = types.ModuleType("backend.memory_fabric")
    setattr(
        mem_stub,
        "mem",
        types.SimpleNamespace(
            vector=types.SimpleNamespace(
                recent=lambda *a, **k: [],
                search=lambda *a, **k: [],
            )
        ),
    )

    monkeypatch.setitem(sys.modules, "backend.agents", agents_stub)
    monkeypatch.setitem(sys.modules, "alpha_factory_v1.backend.agents", agents_stub)
    monkeypatch.setitem(sys.modules, "backend.memory_fabric", mem_stub)
    monkeypatch.setitem(sys.modules, "alpha_factory_v1.backend.agents.finance_agent", fin_stub)
    monkeypatch.setitem(sys.modules, "backend.finance_agent", fin_stub)

    orch_mod = importlib.import_module("alpha_factory_v1.backend.orchestrator")

    # Provide minimal protobuf stubs so gRPC server starts
    pb2 = types.SimpleNamespace(
        StreamReply=object,
        Ack=object,
        AgentStat=object,
        StatusReply=object,
    )
    pb2_grpc = types.SimpleNamespace(
        PeerServiceServicer=object,
        add_PeerServiceServicer_to_server=lambda serv, server: None,
    )
    proto_pkg = types.ModuleType("backend.proto")
    setattr(proto_pkg, "a2a_pb2", pb2)
    setattr(proto_pkg, "a2a_pb2_grpc", pb2_grpc)
    monkeypatch.setitem(sys.modules, "backend.proto", proto_pkg)
    monkeypatch.setitem(sys.modules, "backend.proto.a2a_pb2", pb2)
    monkeypatch.setitem(sys.modules, "backend.proto.a2a_pb2_grpc", pb2_grpc)

    stop = asyncio.Event()
    orch = orch_mod.Orchestrator()

    run_task = asyncio.create_task(orch.run(stop))
    await asyncio.sleep(0.2)  # allow servers to start

    assert orch.api_server.rest_task is not None
    assert orch.api_server.grpc_server is not None

    import httpx

    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"http://localhost:{rest_port}/healthz",
            headers={"Authorization": "Bearer t"},
        )
    assert res.status_code == 200 and res.text == "ok"

    stop.set()
    await run_task

    assert orch.api_server.rest_task.done()
    for r in orch.manager.runners.values():
        assert r.task is None or r.task.done()
