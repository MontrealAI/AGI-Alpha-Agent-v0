# SPDX-License-Identifier: Apache-2.0
import importlib
import importlib.util
import types
import unittest
from typing import Any
from unittest import mock

from alpha_factory_v1.scripts import preflight


class TestPreflightOpenAIAgentsVersion(unittest.TestCase):
    def _run_check(self, module_name: str, version: str | None) -> bool:
        fake_mod = types.SimpleNamespace()
        if version is not None:
            fake_mod.__version__ = version
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
        ):
            return bool(preflight.check_openai_agents_version())

    def test_old_version_fails(self) -> None:
        for name in ("openai_agents", "agents"):
            with self.subTest(module=name):
                self.assertFalse(self._run_check(name, "0.0.13"))

    def test_new_version_ok(self) -> None:
        for name in ("openai_agents", "agents"):
            with self.subTest(module=name):
                self.assertTrue(self._run_check(name, "0.0.17"))

    def test_missing_version_fails(self) -> None:
        for name in ("openai_agents", "agents"):
            with self.subTest(module=name):
                self.assertFalse(self._run_check(name, None))

    def test_missing_spec_skips_check(self) -> None:
        fake_mod = types.SimpleNamespace(__spec__=None)

        def _fake_import(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return fake_mod
            return importlib.import_module(name, *args, **kwargs)

        def _fake_find_spec(name: str, *args: Any, **kwargs: Any) -> object:
            if name == "openai_agents":
                return object()
            if name == "agents":
                return None
            return importlib.util.find_spec(name, *args, **kwargs)

        with (
            mock.patch("importlib.import_module", side_effect=_fake_import),
            mock.patch("importlib.util.find_spec", side_effect=_fake_find_spec),
        ):
            self.assertTrue(preflight.check_openai_agents_version())


if __name__ == "__main__":  # pragma: no cover - manual execution
    unittest.main()
