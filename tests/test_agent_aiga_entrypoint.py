# SPDX-License-Identifier: Apache-2.0
import py_compile
import unittest
from pathlib import Path
import importlib
import sys
import types
import pytest

ENTRYPOINT = Path("alpha_factory_v1/demos/aiga_meta_evolution/agent_aiga_entrypoint.py")


class TestAgentAIGAEntry(unittest.TestCase):
    def test_entrypoint_compiles(self):
        py_compile.compile(ENTRYPOINT, doraise=True)

    def test_import_without_openaiagent(self, monkeypatch: pytest.MonkeyPatch) -> None:
        stub = types.ModuleType("openai_agents")

        class Agent:
            pass

        def Tool(*_a, **_k):
            def dec(f):
                return f

            return dec

        stub.Agent = Agent
        stub.Tool = Tool
        monkeypatch.setitem(sys.modules, "openai_agents", stub)
        sys.modules.pop("agents", None)

        backend_stub = types.ModuleType("alpha_factory_v1.backend")
        backend_stub.adk_bridge = None
        monkeypatch.setitem(sys.modules, "alpha_factory_v1.backend", backend_stub)

        env_stub = types.ModuleType("curriculum_env")
        env_stub.CurriculumEnv = object
        monkeypatch.setitem(
            sys.modules,
            "alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env",
            env_stub,
        )

        utils_stub = types.ModuleType("utils")
        utils_stub.build_llm = lambda: lambda *_a, **_k: ""
        monkeypatch.setitem(
            sys.modules,
            "alpha_factory_v1.demos.aiga_meta_evolution.utils",
            utils_stub,
        )

        evo_stub = types.ModuleType("meta_evolver")

        class DummyEvolver:
            def __init__(self, *a, **k):
                pass

            def run_generations(self, *_a):
                pass

            def latest_log(self):
                return ""

            def load(self):
                pass

            def save(self):
                pass

            def reset(self):
                pass

            def history_plot(self):
                return {}

            best_architecture = "arch"
            best_fitness = 1.0

        evo_stub.MetaEvolver = DummyEvolver
        monkeypatch.setitem(
            sys.modules,
            "alpha_factory_v1.demos.aiga_meta_evolution.meta_evolver",
            evo_stub,
        )

        sys.modules.pop("alpha_factory_v1.demos.aiga_meta_evolution.agent_aiga_entrypoint", None)
        mod = importlib.import_module("alpha_factory_v1.demos.aiga_meta_evolution.agent_aiga_entrypoint")
        assert mod.OpenAIAgent is Agent
        assert isinstance(mod.service.evolver, DummyEvolver)


if __name__ == "__main__":
    unittest.main()
