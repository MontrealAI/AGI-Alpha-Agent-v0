# SPDX-License-Identifier: Apache-2.0
"""Offline integration test for the AI-GA OpenAI bridge."""
# mypy: ignore-errors

import asyncio
import importlib
import socket
import sys
import types
import requests
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Return an available localhost port."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------


def test_aiga_openai_bridge_offline(monkeypatch: pytest.MonkeyPatch) -> None:
    port = _free_port()

    stub = types.ModuleType("openai_agents")

    last_runtime: dict[str, object] = {}

    class Agent:
        pass

    class AgentRuntime:
        def __init__(self, *a, port: int = 5001, **k) -> None:
            last_runtime["inst"] = self
            self.port = port
            self.registered: list[object] = []

        def register(self, agent: object) -> None:
            self.registered.append(agent)

        def run(self) -> None:
            pass

    class OpenAIAgent:
        def __init__(self, *a, base_url: str | None = None, **_k) -> None:
            self.base_url = base_url.rstrip("/") if base_url else None

        def __call__(self, prompt: str) -> str:
            if not self.base_url:
                return "no base url"
            r = requests.post(
                f"{self.base_url}/chat/completions",
                json={"model": "stub", "messages": [{"role": "user", "content": prompt}]},
                timeout=5,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    def Tool(*_a, **_k):
        def dec(f):
            return f

        return dec

    stub.Agent = Agent
    stub.AgentRuntime = AgentRuntime
    stub.OpenAIAgent = OpenAIAgent
    stub.Tool = Tool
    stub.last_runtime = last_runtime

    class DummyResponse:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict[str, object]:
            return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(requests, "post", lambda *_a, **_k: DummyResponse())

    monkeypatch.setitem(sys.modules, "openai_agents", stub)
    sys.modules.pop("agents", None)

    import alpha_factory_v1.backend  # noqa: F401 - trigger shim

    monkeypatch.setitem(sys.modules, "openai_agents", stub)

    env_stub = types.ModuleType("curriculum_env")

    class DummyEnv:
        pass

    env_stub.CurriculumEnv = DummyEnv
    monkeypatch.setitem(
        sys.modules,
        "alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env",
        env_stub,
    )

    evo_stub = types.ModuleType("meta_evolver")

    class _DummyEvolver:
        def __init__(self, *a, **k):
            pass

        def run_generations(self, *_a):
            pass

        def latest_log(self):
            return "stub"

        best_architecture = "arch"
        best_fitness = 1.0

    evo_stub.MetaEvolver = _DummyEvolver
    monkeypatch.setitem(
        sys.modules,
        "alpha_factory_v1.demos.aiga_meta_evolution.meta_evolver",
        evo_stub,
    )

    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OLLAMA_BASE_URL", f"http://127.0.0.1:{port}/v1")
    monkeypatch.setenv("AGENTS_RUNTIME_PORT", str(port))

    mod = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge")

    class DummyEvolver:
        def __init__(self, *a, llm=None, **_k) -> None:
            self.llm = llm

        def run_generations(self, *_a) -> None:
            pass

        def latest_log(self) -> str:
            return self.llm("hi") if self.llm else "done"

        best_architecture = "arch"
        best_fitness = 1.0

    mod.EVOLVER = DummyEvolver(llm=mod.LLM)

    mod.main()
    runtime = stub.last_runtime["inst"]
    assert runtime.port == port
    assert any(isinstance(a, mod.EvolverAgent) for a in runtime.registered)
    result = asyncio.run(mod.evolve(1))
    assert result == "ok"
