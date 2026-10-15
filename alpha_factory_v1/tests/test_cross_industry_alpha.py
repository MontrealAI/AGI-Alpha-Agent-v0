# SPDX-License-Identifier: Apache-2.0
import os
import json
import tempfile
import types
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from alpha_factory_v1.demos.cross_industry_alpha_factory import cross_alpha_discovery_stub as stub


class TestCrossIndustryAlpha(unittest.TestCase):
    def test_discover_alpha_offline(self) -> None:
        openai_mock = types.SimpleNamespace(ChatCompletion=types.SimpleNamespace(create=Mock()))
        with patch.object(stub, "openai", openai_mock, create=True):
            with patch.dict(os.environ, {}, clear=True):
                picks = stub.discover_alpha(num=1, ledger=None, model="gpt-4o-mini", sample=True)
        openai_mock.ChatCompletion.create.assert_not_called()
        self.assertIsInstance(picks, list)
        self.assertEqual(len(picks), 1)

    def test_discover_alpha_invalid_num(self) -> None:
        with self.assertRaises(ValueError):
            stub.discover_alpha(num=0, ledger=None, model="gpt-4o-mini", sample=True)

    def test_discover_alpha_invalid_zero_default_model(self) -> None:
        with self.assertRaises(ValueError):
            stub.discover_alpha(num=0, ledger=None, sample=True)

    def test_discover_alpha_negative_num(self) -> None:
        with self.assertRaises(ValueError):
            stub.discover_alpha(num=-1, ledger=None, sample=True)

    def test_discover_alpha_online(self) -> None:
        resp = types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=json.dumps([stub.SAMPLE_ALPHA[0]])))]
        )
        openai_mock = types.SimpleNamespace(ChatCompletion=types.SimpleNamespace(create=Mock(return_value=resp)))
        with patch.dict(os.environ, {"OPENAI_API_KEY": "x"}):
            with patch.object(stub, "openai", openai_mock, create=True):
                stub.discover_alpha(num=1, ledger=None, model="gpt-4o-mini", generate=True)
        openai_mock.ChatCompletion.create.assert_called_once()
        kwargs = openai_mock.ChatCompletion.create.call_args.kwargs
        self.assertEqual(kwargs.get("response_format"), {"type": "json_object"})
        self.assertEqual(kwargs.get("timeout"), stub.OPENAI_TIMEOUT_SEC)

    def test_ledger_path_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "dir" / "log.json"
            path = stub._ledger_path(ledger)
            self.assertEqual(path, ledger.resolve())
            self.assertTrue(path.parent.exists())

    def test_ledger_env_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_home, tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "ledger.json"
            env = {"HOME": tmp_home, "CROSS_ALPHA_LEDGER": str(target)}
            with patch.dict(os.environ, env, clear=False):
                path = stub._ledger_path(None)
            self.assertEqual(path, target.resolve())
            self.assertTrue(path.parent.exists())

    def test_ledger_default_home(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            default = Path(tmp) / "default" / "ledger.json"
            with patch.object(stub, "DEFAULT_LEDGER", default), patch.dict(
                os.environ, {"CROSS_ALPHA_LEDGER": ""}, clear=False
            ):
                path = stub._ledger_path(None)
            self.assertEqual(path, default.resolve())
            self.assertTrue(path.parent.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
