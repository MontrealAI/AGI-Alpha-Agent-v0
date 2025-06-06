# SPDX-License-Identifier: Apache-2.0
"""Test the AI-GA OpenAI bridge runtime."""

import asyncio
import importlib
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


class TestAIGABridgeRuntime(unittest.TestCase):
    def test_tools_use_evolver(self) -> None:
        """evolve should invoke run_generations and best_alpha should return stats."""

        stub = types.ModuleType("openai_agents")
        stub.Agent = object
        stub.AgentRuntime = MagicMock()
        stub.OpenAIAgent = MagicMock()

        def _tool(*_a, **_k):
            def _decorator(func):
                return func

            return _decorator

        stub.Tool = _tool

        env_stub = types.ModuleType("curriculum_env")
        class DummyEnv:
            pass

        env_stub.CurriculumEnv = DummyEnv

        evo_stub = types.ModuleType("meta_evolver")
        class DummyEvolver:
            def __init__(self, *a, **k) -> None:
                pass

            def run_generations(self, *_a) -> None:
                pass

            def latest_log(self) -> str:
                return "log"

            best_architecture = "arch"
            best_fitness = 1.23

        evo_stub.MetaEvolver = DummyEvolver

        with patch.dict(
            sys.modules,
            {
                "openai_agents": stub,
                "alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env": env_stub,
                "alpha_factory_v1.demos.aiga_meta_evolution.meta_evolver": evo_stub,
            },
        ):
            mod = importlib.import_module(
                "alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge"
            )

            dummy = MagicMock()
            dummy.best_architecture = "arch"
            dummy.best_fitness = 1.23
            dummy.latest_log.return_value = "ok"

            with patch.object(mod, "EVOLVER", dummy):
                asyncio.run(mod.evolve(1))
                dummy.run_generations.assert_called_once_with(1)

                result = asyncio.run(mod.best_alpha())
                self.assertEqual(result, {"architecture": "arch", "fitness": 1.23})

    def test_offline_fallback_base_url(self) -> None:
        """OpenAI bridge should use OLLAMA_BASE_URL when api key is empty."""

        def fake_openai_agent(*_a, **kwargs):
            return types.SimpleNamespace(base_url=kwargs.get("base_url"))

        stub = types.ModuleType("openai_agents")
        stub.Agent = object
        stub.AgentRuntime = object
        stub.OpenAIAgent = fake_openai_agent

        env_stub = types.ModuleType("curriculum_env")
        env_stub.CurriculumEnv = object

        evo_stub = types.ModuleType("meta_evolver")
        evo_stub.MetaEvolver = object

        with patch.dict(
            sys.modules,
            {
                "openai_agents": stub,
                "alpha_factory_v1.demos.aiga_meta_evolution.curriculum_env": env_stub,
                "alpha_factory_v1.demos.aiga_meta_evolution.meta_evolver": evo_stub,
            },
        ), patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "", "OLLAMA_BASE_URL": "http://example.com"},
            clear=False,
        ):
            mod = importlib.reload(
                importlib.import_module(
                    "alpha_factory_v1.demos.aiga_meta_evolution.openai_agents_bridge"
                )
            )

            self.assertEqual(mod.LLM.base_url, "http://example.com")


if __name__ == "__main__":  # pragma: no cover - manual run
    unittest.main()
