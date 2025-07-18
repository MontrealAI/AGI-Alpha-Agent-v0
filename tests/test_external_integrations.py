# SPDX-License-Identifier: Apache-2.0
import importlib
import types
import pytest

HAS_OAI = importlib.util.find_spec("openai_agents") or importlib.util.find_spec("agents")
HAS_ADK = importlib.util.find_spec("google_adk") or importlib.util.find_spec("google.adk")


@pytest.mark.skipif(not HAS_OAI, reason="openai_agents package not installed")
def test_build_llm_missing_api_key(monkeypatch):
    if importlib.util.find_spec("openai_agents"):
        import openai_agents as oa
    else:  # pragma: no cover - legacy package name
        import agents as oa

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
