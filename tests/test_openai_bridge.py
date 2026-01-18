# SPDX-License-Identifier: Apache-2.0
import builtins
import importlib
from pathlib import Path
import py_compile
import sys
import types


def test_asi_bridge_compiles() -> None:
    """Ensure the ASI demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/alpha_asi_world_model/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_meta_bridge_compiles() -> None:
    """Ensure the meta-agentic demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/meta_agentic_agi/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_business_bridge_compiles() -> None:
    """Ensure the business demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/alpha_agi_business_v1/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_aiga_bridge_compiles() -> None:
    """Ensure the AI-GA demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/aiga_meta_evolution/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_cross_industry_bridge_compiles() -> None:
    """Ensure the cross-industry demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/cross_industry_alpha_factory/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_mats_bridge_compiles() -> None:
    """Ensure the MATS demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/meta_agentic_tree_search_v0/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_insight_bridge_compiles() -> None:
    """Ensure the α‑AGI Insight demo bridge compiles."""
    path = Path("alpha_factory_v1/demos/alpha_agi_insight_v0/openai_agents_bridge.py")
    py_compile.compile(path, doraise=True)


def test_aiga_bridge_import_paths(monkeypatch) -> None:
    """Import the AI‑GA bridge with both `openai_agents` and `agents`."""

    stub = types.ModuleType("openai_agents")
    stub.Agent = object
    stub.AgentRuntime = object
    stub.OpenAIAgent = object

    def _tool(*_a, **_k):
        def _decorator(func):
            return func

        return _decorator

    stub.Tool = _tool

    # Import using openai_agents module
    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    sys.modules.pop("agents", None)
    mod = importlib.reload(importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge"))
    assert mod.Agent is stub.Agent

    # Import using agents fallback
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sys.modules.pop("openai_agents", None)

    stub_agents = types.ModuleType("agents")
    stub_agents.Agent = object
    stub_agents.AgentRuntime = object
    stub_agents.OpenAIAgent = object
    stub_agents.Tool = _tool
    monkeypatch.setitem(sys.modules, "agents", stub_agents)

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "openai_agents":
            raise ModuleNotFoundError(name)
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    mod = importlib.reload(importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge"))
    assert mod.Agent is stub_agents.Agent
