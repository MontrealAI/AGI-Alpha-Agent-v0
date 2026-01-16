# SPDX-License-Identifier: Apache-2.0
import base64
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from alpha_factory_v1.backend import agents
from alpha_factory_v1.backend.agents import registry as agents_registry


WHEEL_PATH = Path("tests/resources/dummy_agent.whl")


@unittest.skipUnless(agents.ed25519, "cryptography not installed")
class VerifyWheelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orig_pub = agents_registry._WHEEL_PUBKEY
        self.orig_sigs = agents_registry._WHEEL_SIGS.copy()
        self._tmpdir = tempfile.TemporaryDirectory()
        self.wheel_path = Path(self._tmpdir.name) / WHEEL_PATH.name
        self.wheel_path.write_bytes(WHEEL_PATH.read_bytes())
        priv = agents.ed25519.Ed25519PrivateKey.generate()
        agents_registry._WHEEL_PUBKEY = base64.b64encode(
            priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        sig = base64.b64encode(priv.sign(self.wheel_path.read_bytes())).decode()
        self.wheel_path.with_suffix(self.wheel_path.suffix + ".sig").write_text(sig)
        agents_registry._WHEEL_SIGS = {self.wheel_path.name: sig}

    def tearDown(self) -> None:
        agents_registry._WHEEL_PUBKEY = self.orig_pub
        agents_registry._WHEEL_SIGS = self.orig_sigs
        self._tmpdir.cleanup()

    def test_valid_signature_passes(self) -> None:
        self.assertTrue(agents._verify_wheel(self.wheel_path))

    def test_invalid_signature_fails(self) -> None:
        agents_registry._WHEEL_SIGS = {self.wheel_path.name: "invalid"}
        self.assertFalse(agents._verify_wheel(self.wheel_path))
