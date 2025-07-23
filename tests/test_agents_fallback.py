# SPDX-License-Identifier: Apache-2.0
# mypy: ignore-errors
"""Test fallback between ``openai_agents`` and ``agents`` packages."""
from __future__ import annotations

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


@pytest.mark.parametrize("present", ["openai_agents", "agents"])
@pytest.mark.skipif(
    importlib.util.find_spec("openai_agents") is not None,
    reason="openai-agents installed",
)
def test_agents_import_fallback(monkeypatch, present):
    """Ensure modules import with either package name."""
    missing = "agents" if present == "openai_agents" else "openai_agents"

    stub = types.ModuleType(present)
    stub.Agent = object
    stub.AgentRuntime = object

    class DummyAgent:
        pass

    stub.OpenAIAgent = DummyAgent

    def _tool(*_a, **_k):
        def _decorator(func):
            return func

        return _decorator

    stub.Tool = _tool

    monkeypatch.setitem(sys.modules, present, stub)
    monkeypatch.delitem(sys.modules, missing, raising=False)

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == missing:
            raise ModuleNotFoundError(name)
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    for mod_name in MODULES:
        mod = importlib.reload(importlib.import_module(mod_name))
        assert mod.OpenAIAgent is stub.OpenAIAgent
        if mod_name.endswith("utils"):
            llm = mod.build_llm()
            assert isinstance(llm, stub.OpenAIAgent)
