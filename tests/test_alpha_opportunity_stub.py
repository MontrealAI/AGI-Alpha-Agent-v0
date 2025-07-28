# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
import py_compile
from pathlib import Path
from typing import Callable
import pytest

STUB = Path("alpha_factory_v1/demos/aiga_meta_evolution/alpha_opportunity_stub.py")


def test_stub_compiles() -> None:
    py_compile.compile(str(STUB), doraise=True)


def test_runtime_port_env(monkeypatch: "pytest.MonkeyPatch") -> None:
    """AgentRuntime receives AGENTS_RUNTIME_PORT."""
    import importlib
    import sys
    import types

    captured: dict[str, int] = {}

    class DummyRuntime:
        def __init__(self, *a: object, port: int = 5001, **_k: object) -> None:
            captured["port"] = port

        def register(self, *_a: object, **_k: object) -> None:
            pass

        def run(self) -> None:
            pass

    stub = types.ModuleType("openai_agents")
    stub.Agent = object
    stub.AgentRuntime = DummyRuntime
    stub.OpenAIAgent = object

    def _tool(*_a: object, **_k: object) -> Callable[[object], object]:
        def dec(f: object) -> object:
            return f

        return dec

    stub.Tool = _tool
    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    monkeypatch.delitem(sys.modules, "agents", raising=False)
    monkeypatch.setenv("AGENTS_RUNTIME_PORT", "6101")

    mod = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.alpha_opportunity_stub")
    importlib.reload(mod)
    mod.main([])
    assert captured["port"] == 6101
