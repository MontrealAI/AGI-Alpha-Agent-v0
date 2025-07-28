# SPDX-License-Identifier: Apache-2.0
import importlib
import importlib.util
import types
import unittest
from typing import Any
from unittest import mock

import check_env


class TestCheckEnvOpenAIAgentsVersion(unittest.TestCase):
    def _run_check(self, module_name: str, version: str | None) -> int:
        fake_mod = types.SimpleNamespace()
        if version is not None:
            fake_mod.__version__ = version
        # Provide required attributes so check_env performs the
        # version validation path instead of skipping it.
        fake_mod.AgentRuntime = object
        fake_mod.Agent = object
        fake_mod.Tool = object
        fake_mod.__spec__ = types.SimpleNamespace(loader=object())
        orig_import_module = importlib.import_module
        orig_find_spec = importlib.util.find_spec

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> object:
            if name == module_name:
                return fake_mod
            return orig_import_module(name, *args, **kwargs)

        def _fake_find_spec(name: str, *args: Any, **kwargs: Any) -> object:
            if name == module_name:
                return object()
            if name in {"openai_agents", "agents"}:
                return None
            return orig_find_spec(name, *args, **kwargs)

        with (
            mock.patch("importlib.import_module", side_effect=_fake_import),
            mock.patch("importlib.util.find_spec", side_effect=_fake_find_spec),
            mock.patch.object(check_env, "REQUIRED", []),
            mock.patch.object(check_env, "OPTIONAL", ["openai_agents", "agents"]),
            mock.patch.object(check_env, "warn_missing_core", lambda: []),
        ):
            return int(check_env.main([]))

    def test_old_version_fails(self) -> None:
        for name in ("openai_agents", "agents"):
            with self.subTest(module=name):
                self.assertNotEqual(self._run_check(name, "0.0.13"), 0)

    def test_new_version_ok(self) -> None:
        for name in ("openai_agents", "agents"):
            with self.subTest(module=name):
                self.assertEqual(self._run_check(name, "0.0.17"), 0)

    def test_missing_version_fails(self) -> None:
        for name in ("openai_agents", "agents"):
            with self.subTest(module=name):
                self.assertNotEqual(self._run_check(name, None), 0)

    def test_missing_spec_allowed_with_flag(self) -> None:
        """Allow basic fallback when __spec__ is None."""
        fake_mod = types.SimpleNamespace(
            __version__="0.0.17",
            __spec__=None,
            OpenAIAgent=object,
            AgentRuntime=object,
            Agent=object,
            Tool=object,
        )

        orig_import_module = importlib.import_module
        orig_find_spec = importlib.util.find_spec

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return fake_mod
            return orig_import_module(name, *args, **kwargs)

        def _fake_find_spec(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return object()
            if name == "agents":
                return None
            return orig_find_spec(name, *args, **kwargs)

        with (
            mock.patch("importlib.import_module", side_effect=_fake_import),
            mock.patch("importlib.util.find_spec", side_effect=_fake_find_spec),
            mock.patch.object(check_env, "REQUIRED", []),
            mock.patch.object(check_env, "OPTIONAL", ["openai_agents"]),
            mock.patch.object(check_env, "warn_missing_core", lambda: []),
            mock.patch.object(check_env, "check_openai_agents_version", return_value=True) as chk,
        ):
            self.assertEqual(check_env.main(["--allow-basic-fallback"]), 0)
            chk.assert_called_once()

    def test_missing_spec_skips_check_without_flag(self) -> None:
        fake_mod = types.SimpleNamespace(
            __version__="0.0.17",
            __spec__=None,
            OpenAIAgent=object,
            AgentRuntime=object,
            Agent=object,
            Tool=object,
        )

        orig_import_module = importlib.import_module
        orig_find_spec = importlib.util.find_spec

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return fake_mod
            return orig_import_module(name, *args, **kwargs)

        def _fake_find_spec(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return object()
            if name == "agents":
                return None
            return orig_find_spec(name, *args, **kwargs)

        with (
            mock.patch("importlib.import_module", side_effect=_fake_import),
            mock.patch("importlib.util.find_spec", side_effect=_fake_find_spec),
            mock.patch.object(check_env, "REQUIRED", []),
            mock.patch.object(check_env, "OPTIONAL", ["openai_agents"]),
            mock.patch.object(check_env, "warn_missing_core", lambda: []),
            mock.patch.object(check_env, "check_openai_agents_version", return_value=True) as chk,
        ):
            self.assertEqual(check_env.main([]), 0)
            chk.assert_called_once()

    def test_missing_attributes_skips_version_check(self) -> None:
        fake_mod = types.SimpleNamespace(__version__="0.0.17")

        orig_import_module = importlib.import_module
        orig_find_spec = importlib.util.find_spec

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return fake_mod
            return orig_import_module(name, *args, **kwargs)

        def _fake_find_spec(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return object()
            if name == "agents":
                return None
            return orig_find_spec(name, *args, **kwargs)

        with (
            mock.patch("importlib.import_module", side_effect=_fake_import),
            mock.patch("importlib.util.find_spec", side_effect=_fake_find_spec),
            mock.patch.object(check_env, "REQUIRED", []),
            mock.patch.object(check_env, "OPTIONAL", ["openai_agents"]),
            mock.patch.object(check_env, "warn_missing_core", lambda: []),
            mock.patch.object(check_env, "check_openai_agents_version", return_value=True) as chk,
        ):
            self.assertEqual(check_env.main([]), 0)
            chk.assert_not_called()


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
