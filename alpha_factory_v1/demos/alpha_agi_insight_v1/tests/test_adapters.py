# SPDX-License-Identifier: Apache-2.0
import sys
from types import ModuleType
from pathlib import Path
from typing import Iterator

import asyncio
import httpx
import pytest
from pytest_httpx import HTTPXMock

pytest.importorskip("pytest_httpx")

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents.adk_adapter import ADKAdapter
from alpha_factory_v1.demos.alpha_agi_insight_v1.src.agents.mcp_adapter import MCPAdapter


@pytest.fixture()
def stub_adk(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    mod = ModuleType("adk")

    class Client:
        def generate(self, prompt: str) -> str:
            resp = httpx.post("https://adk.example/generate", json={"prompt": prompt})
            resp.raise_for_status()
            return resp.json()["text"]

    mod.Client = Client
    monkeypatch.setitem(sys.modules, "adk", mod)
    monkeypatch.setitem(sys.modules, "google.adk", mod)
    yield mod


@pytest.fixture()
def stub_mcp(monkeypatch: pytest.MonkeyPatch) -> Iterator[ModuleType]:
    mod = ModuleType("mcp")

    class ClientSessionGroup:
        async def call_tool(self, name: str, args: dict[str, object]):
            async with httpx.AsyncClient() as client:
                resp = await client.post(f"https://mcp.example/{name}", json=args)
                resp.raise_for_status()
                return resp.json()

    mod.ClientSessionGroup = ClientSessionGroup
    monkeypatch.setitem(sys.modules, "mcp", mod)
    yield mod


def test_adk_generate_text_success(httpx_mock: HTTPXMock, stub_adk: ModuleType) -> None:
    httpx_mock.add_response(url="https://adk.example/generate", json={"text": "ok"})
    adapter = ADKAdapter()
    result = adapter.generate_text("hi")
    assert result == "ok"


def test_adk_generate_text_unreachable(httpx_mock: HTTPXMock, stub_adk: ModuleType) -> None:
    httpx_mock.add_exception(httpx.ConnectError("offline"), url="https://adk.example/generate")
    adapter = ADKAdapter()
    with pytest.raises(httpx.HTTPError):
        adapter.generate_text("hi")


def test_mcp_invoke_tool_success(httpx_mock: HTTPXMock, stub_mcp: ModuleType) -> None:
    httpx_mock.add_response(url="https://mcp.example/foo", json={"ok": True})
    adapter = MCPAdapter()
    result = asyncio.run(adapter.invoke_tool("foo", {"a": 1}))
    assert result == {"ok": True}


def test_mcp_invoke_tool_unreachable(httpx_mock: HTTPXMock, stub_mcp: ModuleType) -> None:
    httpx_mock.add_exception(httpx.ConnectError("offline"), url="https://mcp.example/foo")
    adapter = MCPAdapter()
    with pytest.raises(httpx.HTTPError):
        asyncio.run(adapter.invoke_tool("foo", {}))
