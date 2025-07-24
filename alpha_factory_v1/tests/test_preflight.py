# SPDX-License-Identifier: Apache-2.0
import unittest
import sys
import tempfile
from pathlib import Path
from unittest import mock

from alpha_factory_v1.scripts import preflight


class PreflightTest(unittest.TestCase):
    def test_banner_colours(self) -> None:
        with mock.patch("builtins.print") as p:
            preflight.banner("msg", "RED")
            p.assert_called_once()
            args, _ = p.call_args
            self.assertIn("msg", args[0])
            self.assertIn(preflight.COLORS["RED"], args[0])
            self.assertIn(preflight.COLORS["RESET"], args[0])

    def test_check_python_version(self) -> None:
        with mock.patch.object(sys, "version_info", (3, 11)):
            self.assertTrue(preflight.check_python())
        with mock.patch.object(sys, "version_info", (3, 10)):
            self.assertFalse(preflight.check_python())

    def test_check_cmd(self) -> None:
        with mock.patch("shutil.which", return_value="/bin/foo"):
            self.assertTrue(preflight.check_cmd("foo"))
        with mock.patch("shutil.which", return_value=None):
            self.assertFalse(preflight.check_cmd("foo"))

    def test_check_docker_daemon(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            self.assertFalse(preflight.check_docker_daemon())
        with mock.patch("shutil.which", return_value="/bin/docker"):
            with mock.patch("subprocess.run") as run:
                run.return_value = mock.Mock(returncode=0)
                self.assertTrue(preflight.check_docker_daemon())
            with mock.patch("subprocess.run", side_effect=Exception):
                self.assertFalse(preflight.check_docker_daemon())

    def test_check_docker_compose(self) -> None:
        with mock.patch("shutil.which", return_value=None):
            self.assertFalse(preflight.check_docker_compose())
        with mock.patch("shutil.which", return_value="/bin/docker"):
            with mock.patch("subprocess.run") as run:
                run.return_value = mock.Mock(returncode=0)
                self.assertTrue(preflight.check_docker_compose())
            with mock.patch("subprocess.run", side_effect=Exception):
                self.assertFalse(preflight.check_docker_compose())

    def test_check_pkg(self) -> None:
        with mock.patch("importlib.util.find_spec", return_value=object()):
            self.assertTrue(preflight.check_pkg("x"))
        with mock.patch("importlib.util.find_spec", return_value=None):
            self.assertFalse(preflight.check_pkg("y"))

    def test_ensure_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "d"
            preflight.ensure_dir(path)
            self.assertTrue(path.exists())

    def test_check_network(self) -> None:
        with mock.patch("socket.gethostbyname", return_value="1.2.3.4"):
            self.assertTrue(preflight.check_network())
        with mock.patch("socket.gethostbyname", side_effect=OSError):
            with mock.patch.object(preflight, "banner") as b:
                self.assertFalse(preflight.check_network())
                b.assert_called()

    def test_main_success_and_failure(self) -> None:
        with mock.patch.multiple(
            preflight,
            check_python=lambda: True,
            check_cmd=lambda cmd: True,
            check_docker_daemon=lambda: True,
            check_docker_compose=lambda: True,
            check_pkg=lambda pkg, optional=False: True,
            ensure_dir=lambda p: None,
            banner=lambda *a, **k: None,
        ):
            preflight.main([])
        with mock.patch.multiple(
            preflight,
            check_python=lambda: False,
            check_cmd=lambda cmd: False,
            check_docker_daemon=lambda: False,
            check_docker_compose=lambda: False,
            check_pkg=lambda pkg, optional=False: False,
            ensure_dir=lambda p: None,
            banner=lambda *a, **k: None,
            check_network=lambda: True,
        ):
            with self.assertRaises(SystemExit):
                preflight.main([])

    def test_main_offline_skips_network(self) -> None:
        with mock.patch.multiple(
            preflight,
            check_python=lambda: True,
            check_cmd=lambda cmd: True,
            check_docker_daemon=lambda: True,
            check_docker_compose=lambda: True,
            check_pkg=lambda pkg, optional=False: True,
            ensure_dir=lambda p: None,
            banner=lambda *a, **k: None,
        ):
            with mock.patch.object(preflight, "check_network") as cn:
                preflight.main(["--offline"])
                cn.assert_not_called()


if __name__ == "__main__":
    unittest.main()
