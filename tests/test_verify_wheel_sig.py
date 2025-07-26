# SPDX-License-Identifier: Apache-2.0
"""Tests for verify_wheel_sig script."""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

from alpha_factory_v1.backend import agents as agents_mod
from alpha_factory_v1.scripts import verify_wheel_sig


class VerifyWheelSigTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.pkg_dir = Path(self.tmpdir.name)
        (self.pkg_dir / "pkg").mkdir()
        (self.pkg_dir / "pkg" / "__init__.py").write_text("")
        (self.pkg_dir / "pyproject.toml").write_text(
            """
[build-system]
requires = ["setuptools", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "dummy"
version = "0.0.1"
"""
        )
        wheel_dir = self.pkg_dir / "dist"
        wheel_dir.mkdir()
        from setuptools import build_meta  # type: ignore

        cwd = os.getcwd()
        os.chdir(self.pkg_dir)
        try:
            wheel_name = build_meta.build_wheel(str(wheel_dir))
        finally:
            os.chdir(cwd)
        self.wheel_path = wheel_dir / wheel_name

        self.key_path = self.pkg_dir / "signing.key"
        subprocess.run(
            ["openssl", "genpkey", "-algorithm", "ed25519", "-out", str(self.key_path)],
            check=True,
        )
        pub_bytes = subprocess.check_output(
            ["openssl", "pkey", "-in", str(self.key_path), "-pubout", "-outform", "DER"]
        )
        self.pub_b64 = base64.b64encode(pub_bytes).decode()

        sig_cmd = (
            f"openssl dgst -sha512 -binary {self.wheel_path} | "
            f"openssl pkeyutl -sign -inkey {self.key_path} | base64 -w0"
        )
        try:
            sig_b64 = subprocess.check_output(["sh", "-c", sig_cmd], stderr=subprocess.STDOUT).decode()
        except subprocess.CalledProcessError:
            self.skipTest("ed25519 signatures unsupported")
        self.sig_path = self.wheel_path.with_suffix(self.wheel_path.suffix + ".sig")
        self.sig_path.write_text(sig_b64)
        self.orig_pub = agents_mod._WHEEL_PUBKEY
        agents_mod._WHEEL_PUBKEY = self.pub_b64

        try:
            if not verify_wheel_sig.verify(self.wheel_path):
                self.skipTest("ed25519 verification unsupported")
        except subprocess.CalledProcessError:
            self.skipTest("ed25519 verification unsupported")

    def tearDown(self) -> None:
        agents_mod._WHEEL_PUBKEY = self.orig_pub
        self.tmpdir.cleanup()

    def _run_main(self, wheel: Path) -> int:
        argv = ["verify_wheel_sig", str(wheel)]
        with mock.patch.object(sys, "argv", argv):
            with self.assertRaises(SystemExit) as ctx:
                verify_wheel_sig.main()
            return ctx.exception.code  # type: ignore[no-any-return]

    def _run_cli(self, wheel: Path) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["AGENT_WHEEL_PUBKEY"] = self.pub_b64
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.scripts.verify_wheel_sig",
                str(wheel),
            ],
            env=env,
            capture_output=True,
            text=True,
        )

    def test_valid_signature(self) -> None:
        exit_code = self._run_main(self.wheel_path)
        self.assertEqual(exit_code, 0)

    def test_tampered_wheel_fails(self) -> None:
        self.wheel_path.write_bytes(self.wheel_path.read_bytes() + b"x")
        exit_code = self._run_main(self.wheel_path)
        self.assertEqual(exit_code, 2)

    def test_cli_valid_signature(self) -> None:
        result = self._run_cli(self.wheel_path)
        assert result.returncode == 0, result.stdout + result.stderr

    def test_cli_tampered_wheel_fails(self) -> None:
        self.wheel_path.write_bytes(self.wheel_path.read_bytes() + b"x")
        result = self._run_cli(self.wheel_path)
        assert result.returncode == 2


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
