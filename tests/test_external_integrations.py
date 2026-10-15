# SPDX-License-Identifier: Apache-2.0
import importlib
import types
import sys
from packaging.version import Version
import pytest


def _oai_available() -> bool:
    for name in ("openai_agents", "agents"):
        try:
            spec = importlib.util.find_spec(name)
        except ValueError:
            spec = None
        if spec is None:
            continue
        mod = importlib.import_module(name)
        if Version(getattr(mod, "__version__", "0")) >= Version("0.0.17"):
            return True
    return False


HAS_OAI = _oai_available()


def _adk_available() -> bool:
    for name in ("google_adk", "google.adk"):
        try:
            spec = importlib.util.find_spec(name)
        except ValueError:
            spec = None
        if spec is None:
            continue
        mod = importlib.import_module(name)
        if hasattr(mod, "Router"):
            return True
    return False


HAS_ADK = _adk_available()


def test_build_llm_missing_api_key(monkeypatch):
    # This tests constructor wiring, not real provider availability. Do not
    # mutate the repository shim while retaining its deliberately rejected flag.
    oa = types.ModuleType("openai_agents")
    monkeypatch.setitem(sys.modules, "openai_agents", oa)

    captured = {}

    class DummyAgent:
        def __init__(self, *a, base_url=None, **kw):
            captured["base_url"] = base_url

    monkeypatch.setattr(oa, "OpenAIAgent", DummyAgent, raising=False)
    monkeypatch.setattr(oa, "Agent", DummyAgent, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://testserver")

    import importlib as _imp

    mod = _imp.reload(_imp.import_module("alpha_factory_v1.demos.aiga_meta_evolution.utils"))
    llm = mod.build_llm()
    assert isinstance(llm, DummyAgent)
    assert captured.get("base_url") == "http://testserver"


def test_build_llm_rejects_marked_repository_shim(monkeypatch):
    oa = types.ModuleType("openai_agents")
    oa.__alpha_factory_stub__ = True

    class ForbiddenShim:
        def __init__(self, **_kwargs):
            pytest.fail("Marked repository shim must never become a provider")

    oa.OpenAIAgent = ForbiddenShim
    monkeypatch.setitem(sys.modules, "openai_agents", oa)
    monkeypatch.setitem(sys.modules, "agents", types.ModuleType("agents"))
    mod = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.utils")
    llm = mod.build_llm()
    assert llm.__alpha_factory_unavailable__ is True
    import asyncio

    with pytest.raises(RuntimeError, match="No compatible inference adapter"):
        asyncio.run(llm("no synthetic output"))


@pytest.mark.skipif(not HAS_ADK, reason="google_adk package not installed")
def test_adk_auto_register(monkeypatch):
    if importlib.util.find_spec("google_adk"):
        import google_adk as gadk
    else:  # pragma: no cover - alt module path
        from google import adk as gadk

    registered = []

    class DummyRouter:
        def __init__(self):
            self.app = types.SimpleNamespace(middleware=lambda *_a, **_k: lambda f: f)

        def register_agent(self, agent):
            registered.append(agent)

    monkeypatch.setattr(gadk, "Router", DummyRouter)
    monkeypatch.setenv("ALPHA_FACTORY_ENABLE_ADK", "true")

    import importlib as _imp

    bridge = _imp.reload(_imp.import_module("alpha_factory_v1.backend.adk_bridge"))

    class Dummy:
        name = "dummy"

        def run(self, prompt: str):
            return "ok"

    bridge.auto_register([Dummy()])
    assert registered

    called = {}

    def fake_run(app, host, port, log_level="info", **kw):
        called["host"] = host
        called["port"] = port

    monkeypatch.setattr("uvicorn.run", fake_run)

    bridge.maybe_launch(host="127.0.0.1", port=1234)
    assert called == {"host": "127.0.0.1", "port": 1234}


@pytest.mark.skipif(not HAS_ADK, reason="google_adk package not installed")
def test_adk_auto_register_disabled(monkeypatch):
    if importlib.util.find_spec("google_adk"):
        import google_adk as gadk
    else:  # pragma: no cover
        from google import adk as gadk

    class DummyRouter:
        def __init__(self):
            self.app = types.SimpleNamespace(middleware=lambda *_a, **_k: lambda f: f)

        def register_agent(self, agent):
            raise AssertionError("should not register")

    monkeypatch.setattr(gadk, "Router", DummyRouter)
    monkeypatch.delenv("ALPHA_FACTORY_ENABLE_ADK", raising=False)

    import importlib as _imp

    bridge = _imp.reload(_imp.import_module("alpha_factory_v1.backend.adk_bridge"))
    bridge.auto_register([object()])  # no error
