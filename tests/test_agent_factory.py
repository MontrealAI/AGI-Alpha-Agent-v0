# SPDX-License-Identifier: Apache-2.0
import importlib
import os
import sys
import unittest
from unittest import mock


class TestAgentFactory(unittest.TestCase):
    def setUp(self) -> None:
        sys.modules.pop("agents", None)
        sys.modules.pop("alpha_factory_v1.backend.agent_factory", None)
        importlib.invalidate_caches()

        orig_import_module = importlib.import_module

        def _fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "agents":
                raise ModuleNotFoundError
            return orig_import_module(name, *args, **kwargs)

        with mock.patch("importlib.import_module", side_effect=_fake_import):
            af = orig_import_module("alpha_factory_v1.backend.agent_factory")
            self.af = importlib.reload(af)

    def test_get_default_tools_base(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            tools = self.af.get_default_tools()
        names = [getattr(t, "name", str(t)) for t in tools]
        self.assertEqual(names, [])
        self.assertFalse(any(isinstance(t, self.af.ComputerTool) for t in tools))
        self.assertFalse(any(isinstance(t, self.af.PythonTool) for t in tools))

    def test_get_default_tools_with_api_and_local(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"OPENAI_API_KEY": "x", "ALPHA_FACTORY_ALLOW_LOCAL_CODE": "1"},
            clear=True,
        ):
            with mock.patch.object(self.af, "SDK_AVAILABLE", True):
                tools = self.af.get_default_tools()
        self.assertFalse(any(isinstance(t, self.af.ComputerTool) for t in tools))
        self.assertTrue(any(isinstance(t, self.af.PythonTool) for t in tools))

    def test_auto_select_model_precedence(self) -> None:
        env = {
            "OPENAI_MODEL": "foo",
            "OPENAI_API_KEY": "x",
            "ANTHROPIC_API_KEY": "y",
            "LLAMA_MODEL_PATH": "/tmp/model.bin",
        }
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(self.af._auto_select_model(), "foo")

    def test_auto_select_model_fallbacks(self) -> None:
        combos = [
            ({"OPENAI_API_KEY": "1"}, "gpt-4o-mini"),
            ({"ANTHROPIC_API_KEY": "1"}, "claude-3-sonnet-20240229"),
            ({"LLAMA_MODEL_PATH": "model.bin"}, "local-llama3-8b-q4"),
            ({}, "local-sbert"),
        ]
        for env, expected in combos:
            with self.subTest(env=env):
                with mock.patch.dict(os.environ, env, clear=True):
                    self.assertEqual(self.af._auto_select_model(), expected)

    def test_build_core_agent_stub_when_sdk_missing(self) -> None:
        os.environ.pop("OPENAI_API_KEY", None)
        sys.modules.pop("agents", None)
        sys.modules.pop("alpha_factory_v1.backend.agent_factory", None)
        importlib.invalidate_caches()

        orig_import_module = importlib.import_module

        def _fake_import(name: str, *args: object, **kwargs: object) -> object:
            if name == "agents":
                raise ModuleNotFoundError
            return orig_import_module(name, *args, **kwargs)

        with mock.patch("importlib.import_module", side_effect=_fake_import):
            af = orig_import_module("alpha_factory_v1.backend.agent_factory")
            af = importlib.reload(af)
            agent = af.build_core_agent(name="t", instructions="demo")

        self.assertTrue(hasattr(agent, "run"))
        self.assertEqual(agent.run("hi"), "[t-stub] echo: hi")
        self.assertFalse(any(isinstance(t, af.ComputerTool) for t in af.DEFAULT_TOOLS))


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
