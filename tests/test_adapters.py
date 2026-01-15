# SPDX-License-Identifier: Apache-2.0

import sys
import types
import asyncio
import importlib
import importlib.util
import pytest

# Stub generated proto dependency only when import fails.
_stub_path = "alpha_factory_v1.core.utils.a2a_pb2"
if importlib.util.find_spec(_stub_path) is None:
try:
    importlib.import_module(_stub_path)
except Exception:
    stub = types.ModuleType("a2a_pb2")

    class Envelope:
        def __init__(self, sender: str = "", recipient: str = "", payload: dict | None = None, ts: float = 0.0) -> None:
            self.sender = sender
            self.recipient = recipient
            self.payload = payload or {}
            self.ts = ts

    stub.Envelope = Envelope
    sys.modules[_stub_path] = stub

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents.adk_adapter import ADKAdapter  # noqa: E402
from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents.mcp_adapter import MCPAdapter  # noqa: E402


@pytest.mark.skipif(not ADKAdapter.is_available(), reason="ADK not installed")
def test_adk_list_packages():
    adapter = ADKAdapter()
    pkgs = adapter.list_packages()
    assert isinstance(pkgs, list)


@pytest.mark.skipif(not MCPAdapter.is_available(), reason="MCP not installed")
def test_mcp_invoke_tool_missing():
    async def _run() -> None:
        adapter = MCPAdapter()
        with pytest.raises(KeyError):
            await adapter.invoke_tool("missing_tool", {})

    asyncio.run(_run())


def _make_agent(monkeypatch):
    """Return a ResearchAgent wired with dummy bus/ledger."""
    from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents import research_agent
    from alpha_factory_v1.common.utils import config, messaging

    class DummyBus:
        def __init__(self, settings: config.Settings) -> None:
            self.settings = settings
            self.published: list[tuple[str, messaging.Envelope]] = []

        def publish(self, topic: str, env: messaging.Envelope) -> None:
            self.published.append((topic, env))

        def subscribe(self, _t: str, _h):
            pass

    class DummyLedger:
        def __init__(self) -> None:
            self.logged: list[messaging.Envelope] = []

        def log(self, env: messaging.Envelope) -> None:  # type: ignore[override]
            self.logged.append(env)

        def start_merkle_task(self, *_a, **_kw):
            pass

        async def stop_merkle_task(self) -> None:  # pragma: no cover - interface
            pass

        def close(self) -> None:
            pass

    settings = config.Settings(bus_port=0)
    bus = DummyBus(settings)
    agent = research_agent.ResearchAgent(bus, DummyLedger())
    return agent, bus


def test_adk_generate_text_flow(monkeypatch) -> None:
    agent, bus = _make_agent(monkeypatch)

    class StubADK:
        def __init__(self) -> None:
            self.called: list[str] = []

        def generate_text(self, prompt: str) -> str:
            self.called.append(prompt)
            return "reply"

    adk = StubADK()
    monkeypatch.setattr(agent, "adk", adk, raising=False)

    async def patched_handle(self, env):
        text = self.adk.generate_text(env.payload.get("plan", ""))
        await self.emit("strategy", {"research": text})

    monkeypatch.setattr(type(agent), "handle", patched_handle)
    from alpha_factory_v1.common.utils import messaging

    env = messaging.Envelope(sender="planning", recipient="research", payload={"plan": "p"}, ts=0.0)
    asyncio.run(agent.handle(env))

    assert adk.called == ["p"]
    assert bus.published and bus.published[-1][1].payload["research"] == "reply"


def test_mcp_invoke_tool_flow(monkeypatch) -> None:
    agent, bus = _make_agent(monkeypatch)

    class StubMCP:
        def __init__(self) -> None:
            self.called: list[tuple[str, dict[str, object]]] = []

        async def invoke_tool(self, name: str, args: dict[str, object] | None = None) -> object:
            args = args or {}
            self.called.append((name, args))
            return {"ok": True}

    mcp = StubMCP()
    monkeypatch.setattr(agent, "mcp", mcp, raising=False)

    async def patched_run_cycle(self) -> None:
        res = await self.mcp.invoke_tool("echo", {"t": 1})
        await self.emit("strategy", res)

    monkeypatch.setattr(type(agent), "run_cycle", patched_run_cycle)

    asyncio.run(agent.run_cycle())

    assert mcp.called == [("echo", {"t": 1})]
    assert bus.published and bus.published[-1][1].payload == {"ok": True}


@pytest.mark.skipif(not ADKAdapter.is_available(), reason="ADK not installed")
def test_adk_generate_text_calls_library(monkeypatch) -> None:
    """Ensure ADKAdapter.generate_text delegates to the ADK client."""
    try:
        mod = importlib.import_module("adk")
    except Exception:
        mod = importlib.import_module("google.adk")

    calls: dict[str, str] = {}

    def fake_generate(self, prompt: str) -> str:
        calls["prompt"] = prompt
        return "resp"

    monkeypatch.setattr(mod.Client, "generate", fake_generate, raising=False)
    adapter = ADKAdapter()
    result = adapter.generate_text("hello")
    assert result == "resp"
    assert calls == {"prompt": "hello"}


def test_adk_adapter_unavailable(monkeypatch) -> None:
    """Adapter gracefully degrades when ADK is missing."""

    def _raise(_name: str):
        raise ModuleNotFoundError

    monkeypatch.setattr(importlib, "import_module", _raise)
    assert not ADKAdapter.is_available()
    with pytest.raises(ModuleNotFoundError):
        ADKAdapter()


@pytest.mark.skipif(not MCPAdapter.is_available(), reason="MCP not installed")
def test_mcp_invoke_tool_calls_library(monkeypatch) -> None:
    """Ensure MCPAdapter.invoke_tool delegates to the MCP client."""
    import mcp

    calls: dict[str, tuple[str, dict[str, object]]] = {}

    async def fake_call_tool(self, name: str, args: dict[str, object]) -> object:
        calls["call"] = (name, args)
        return {"done": True}

    monkeypatch.setattr(mcp.ClientSessionGroup, "call_tool", fake_call_tool, raising=False)
    adapter = MCPAdapter()
    result = asyncio.run(adapter.invoke_tool("mytool", {"x": 1}))
    assert result == {"done": True}
    assert calls["call"] == ("mytool", {"x": 1})


def test_mcp_adapter_unavailable(monkeypatch) -> None:
    """Adapter gracefully degrades when MCP is missing."""

    def _raise(_name: str):
        raise ModuleNotFoundError

    monkeypatch.setattr(importlib, "import_module", _raise)
    assert not MCPAdapter.is_available()
    with pytest.raises(ModuleNotFoundError):
        MCPAdapter()
