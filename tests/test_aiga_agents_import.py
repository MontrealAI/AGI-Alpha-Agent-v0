# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
import builtins
import importlib
import sys
import types
import pytest

MODULES = [
    "alpha_factory_v1.demos.aiga_meta_evolution.utils",
    "alpha_factory_v1.demos.aiga_meta_evolution.alpha_opportunity_stub",
    "alpha_factory_v1.demos.aiga_meta_evolution.workflow_demo",
]


def test_import_with_agents_only(monkeypatch: pytest.MonkeyPatch) -> None:
    stub = types.ModuleType("agents")
    stub.Agent = object
    stub.AgentRuntime = object

    class DummyOpenAI:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

    stub.OpenAIAgent = DummyOpenAI

    def _tool(*_a: object, **_k: object) -> object:
        def _decorator(func: object) -> object:
            return func

        return _decorator

    stub.Tool = _tool

    monkeypatch.setitem(sys.modules, "agents", stub)
    sys.modules.pop("openai_agents", None)

    orig_import = builtins.__import__

    def fake_import(name: str, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai_agents":
            raise ModuleNotFoundError(name)
        if name == "alpha_opportunity_stub":
            return importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.alpha_opportunity_stub")
        if name == "alpha_conversion_stub":
            return importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.alpha_conversion_stub")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    for mod_name in MODULES:
        mod = importlib.reload(importlib.import_module(mod_name))
        assert mod.OpenAIAgent is stub.OpenAIAgent
