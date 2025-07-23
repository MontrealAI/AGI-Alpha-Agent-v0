# SPDX-License-Identifier: Apache-2.0
"""ADK gateway startup unit tests."""
from __future__ import annotations

import importlib
import sys
import types

import pytest


@pytest.fixture
def stub_adk(monkeypatch):
    """Provide a minimal google_adk stub."""
    dummy = types.ModuleType("google_adk")

    class _Router:
        def __init__(self):
            self.app = object()

        def register_agent(self, _agent):
            pass

    dummy.Router = _Router
    dummy.Agent = object
    dummy.AgentException = Exception
    monkeypatch.setitem(sys.modules, "google_adk", dummy)
    monkeypatch.setenv("ALPHA_FACTORY_ENABLE_ADK", "1")
    yield
    monkeypatch.delenv("ALPHA_FACTORY_ENABLE_ADK", raising=False)
    sys.modules.pop("google_adk", None)


def test_maybe_launch_starts_uvicorn(stub_adk, monkeypatch):
    """maybe_launch should call uvicorn.run when ADK is enabled."""
    uvicorn = pytest.importorskip("uvicorn")
    from alpha_factory_v1.backend import adk_bridge as module

    module = importlib.reload(module)

    called = {}

    def fake_run(app, host, port, log_level="info", **kw):
        called["app"] = app
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr(uvicorn, "run", fake_run)

    class DummyThread:
        def __init__(self, target, *a, **k):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(module.threading, "Thread", DummyThread)

    module.maybe_launch(host="1.2.3.4", port=1234)
    assert called == {"app": module._ensure_router().app, "host": "1.2.3.4", "port": 1234}


@pytest.mark.skipif(
    importlib.util.find_spec("openai_agents") is not None,
    reason="openai-agents installed",
)
def test_openai_agents_stub_call(monkeypatch):
    """Calling Agent from the shim should raise ModuleNotFoundError."""
    sys.modules.pop("openai_agents", None)
    sys.modules.pop("agents", None)
    importlib.reload(importlib.import_module("alpha_factory_v1.backend"))

    from openai_agents import Agent

    with pytest.raises(ModuleNotFoundError, match="OpenAI Agents SDK is required"):
        Agent()
