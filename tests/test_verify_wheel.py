# SPDX-License-Identifier: Apache-2.0
import unittest
from pathlib import Path

from alpha_factory_v1.backend import agents


PUB_KEY_B64 = "SeBX1drfWBvGZXOsV7KAfyI3+BsmiPXJeAfr8oW4Iik="
WHEEL_PATH = Path("tests/resources/dummy_agent.whl")
SIG_PATH = Path("tests/resources/dummy_agent.whl.sig")


@unittest.skipUnless(agents.ed25519, "cryptography not installed")
class VerifyWheelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orig_pub = agents._WHEEL_PUBKEY
        self.orig_sigs = agents._WHEEL_SIGS.copy()
        agents._WHEEL_PUBKEY = PUB_KEY_B64
        sig = SIG_PATH.read_text().strip()
        agents._WHEEL_SIGS = {WHEEL_PATH.name: sig}

    def tearDown(self) -> None:
        agents._WHEEL_PUBKEY = self.orig_pub
        agents._WHEEL_SIGS = self.orig_sigs

    def test_valid_signature_passes(self) -> None:
        self.assertTrue(agents._verify_wheel(WHEEL_PATH))

    def test_invalid_signature_fails(self) -> None:
        agents._WHEEL_SIGS = {WHEEL_PATH.name: "invalid"}
        self.assertFalse(agents._verify_wheel(WHEEL_PATH))
