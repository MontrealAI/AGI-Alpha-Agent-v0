# SPDX-License-Identifier: Apache-2.0
import base64
import tempfile
import unittest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from pathlib import Path

from alpha_factory_v1.backend import agents


WHEEL_PATH = Path("tests/resources/dummy_agent.whl")


@unittest.skipUnless(agents.ed25519, "cryptography not installed")
class VerifyWheelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orig_pub = agents._WHEEL_PUBKEY
        self.orig_sigs = agents._WHEEL_SIGS.copy()
        self.temporary = tempfile.TemporaryDirectory()
        self.wheel = Path(self.temporary.name) / WHEEL_PATH.name
        self.wheel.write_bytes(WHEEL_PATH.read_bytes())
        key = Ed25519PrivateKey.generate()
        agents._WHEEL_PUBKEY = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
        sig = base64.b64encode(key.sign(self.wheel.read_bytes())).decode()
        self.wheel.with_suffix(".whl.sig").write_text(sig)
        agents._WHEEL_SIGS = {self.wheel.name: sig}

    def tearDown(self) -> None:
        agents._WHEEL_PUBKEY = self.orig_pub
        agents._WHEEL_SIGS = self.orig_sigs
        self.temporary.cleanup()

    def test_valid_signature_passes(self) -> None:
        self.assertTrue(agents._verify_wheel(self.wheel))

    def test_invalid_signature_fails(self) -> None:
        agents._WHEEL_SIGS = {WHEEL_PATH.name: "invalid"}
        self.assertFalse(agents._verify_wheel(self.wheel))
