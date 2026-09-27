# SPDX-License-Identifier: Apache-2.0
import os
import sys
import unittest
import tempfile
from pathlib import Path, PureWindowsPath
from unittest import mock

from alpha_factory_v1 import quickstart


class QuickstartUtilsTest(unittest.TestCase):
    def test_venv_python_posix(self):
        with mock.patch.object(os, "name", "posix"):
            self.assertEqual(quickstart._venv_python(Path("/tmp/venv")), Path("/tmp/venv/bin/python"))

    def test_venv_python_windows(self):
        with mock.patch.object(os, "name", "nt"):
            path = PureWindowsPath("C:/v")
            self.assertEqual(quickstart._venv_python(path), path / "Scripts" / "python.exe")

    def test_venv_pip_posix(self):
        with mock.patch.object(os, "name", "posix"):
            self.assertEqual(quickstart._venv_pip(Path("/tmp/venv")), Path("/tmp/venv/bin/pip"))

    def test_venv_pip_windows(self):
        with mock.patch.object(os, "name", "nt"):
            path = PureWindowsPath("C:/v")
            self.assertEqual(quickstart._venv_pip(path), path / "Scripts" / "pip.exe")

    def test_create_venv_runs_commands_when_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            venv = Path(temp) / "new environment"

            def execute(command):
                if command[:3] == [sys.executable, "-m", "venv"]:
                    venv.mkdir()

            with mock.patch("subprocess.check_call", side_effect=execute) as cc:
                quickstart._create_venv(venv)
            called = [call.args[0] for call in cc.call_args_list]
            self.assertEqual(called[0], [sys.executable, "-m", "venv", str(venv)])
            self.assertIn("--require-hashes", called[1])
            self.assertEqual(called[2], [str(quickstart._venv_python(venv)), "-m", "pip", "check"])
            self.assertNotIn("-U", called[1])

    def test_create_venv_skips_when_exists(self):
        with tempfile.TemporaryDirectory() as temp:
            venv = Path(temp)
            py = quickstart._venv_python(venv)
            py.parent.mkdir()
            py.touch()
            with mock.patch("subprocess.check_call") as cc:
                quickstart._create_venv(venv)
            cc.assert_called_once_with([str(py), "-m", "pip", "check"])


if __name__ == "__main__":
    unittest.main()
