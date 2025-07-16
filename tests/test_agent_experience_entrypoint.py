# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import asyncio
import importlib
import sys
import types

import pytest


class DummyButton:
    def click(self, *a, **k):
        pass


class DummyBlocks:
    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def Markdown(self, *a, **k):
        pass

    def Dataframe(self, *a, **k):
        pass

    def Button(self, *a, **k):
        return DummyButton()


def mount_gradio_app(app, ui, path="/"):
    return app


def _run_main(monkeypatch: pytest.MonkeyPatch, openai_key: str | None, base_url: str | None) -> str | None:
    recorded: dict[str, str | None] = {}

    stub = types.ModuleType("openai_agents")

    def Tool(*_a, **_k):
        def dec(f):
            return f

        return dec

    class DummyMemory:
        def __init__(self, *a, **k):
            pass

        def recent(self, _n: int):
            return []

    class DummyAgent:
        def __init__(self, *a, **k) -> None:
            self.memory = DummyMemory()

        async def act(self) -> str:
            return "done"

        def observe(self, *_a) -> None:
            pass

    def DummyOpenAIAgent(*_a, **kw):
        recorded["base_url"] = kw.get("base_url")
        return object()

    stub.Agent = DummyAgent
    stub.OpenAIAgent = DummyOpenAIAgent
    stub.Tool = Tool
    stub.memory = types.SimpleNamespace(LocalQdrantMemory=DummyMemory)

    gr_stub = types.SimpleNamespace(
        Blocks=DummyBlocks,
        Markdown=lambda *_a, **_k: None,
        Dataframe=lambda *_a, **_k: None,
        Button=lambda *_a, **_k: DummyButton(),
        mount_gradio_app=mount_gradio_app,
    )

    class DummyConfig:
        def __init__(self, *a, **k):
            pass

    class DummyServer:
        def __init__(self, *a, **k):
            pass

        async def serve(self) -> None:
            pass

    uvicorn_stub = types.SimpleNamespace(Config=DummyConfig, Server=DummyServer)

    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    monkeypatch.setitem(sys.modules, "gradio", gr_stub)
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn_stub)

    if openai_key is None:
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("OPENAI_API_KEY", openai_key)
    if base_url is None:
        monkeypatch.delenv("LLM_BASE_URL", raising=False)
    else:
        monkeypatch.setenv("LLM_BASE_URL", base_url)

    module_name = "alpha_factory_v1.demos.era_of_experience.agent_experience_entrypoint"
    sys.modules.pop(module_name, None)
    mod = importlib.import_module(module_name)

    async def one_event():
        yield {"id": 1, "t": "0", "user": "a", "kind": "health", "payload": {}}

    monkeypatch.setattr(mod, "experience_stream", one_event)

    async def _sleep(*_a: object, **_kw: object) -> None:
        return None

    monkeypatch.setattr(mod.asyncio, "sleep", _sleep)
    asyncio.run(mod.main())
    return recorded.get("base_url")


def test_main_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    base = _run_main(monkeypatch, openai_key="dummy", base_url="http://ollama")
    assert base is None


def test_main_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    base = _run_main(monkeypatch, openai_key="", base_url="http://ollama")
    assert base == "http://ollama"
