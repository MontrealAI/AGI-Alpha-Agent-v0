# SPDX-License-Identifier: Apache-2.0
import base64
import unittest
from pathlib import Path

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
    )
    from cryptography.hazmat.primitives import serialization

    HAVE_CRYPTO = True
except Exception:  # pragma: no cover - optional dependency
    HAVE_CRYPTO = False

from alpha_factory_v1.backend import agents as agents_mod
from alpha_factory_v1.backend.agents import registry as agents_registry


@unittest.skipUnless(HAVE_CRYPTO, "cryptography not installed")
class TestWheelSignature(unittest.TestCase):
    def test_verify_wheel(self) -> None:
        priv = Ed25519PrivateKey.generate()
        pub_b64 = base64.b64encode(
            priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode()
        wheel = Path("test.whl")
        wheel.write_bytes(b"demo")
        sig = base64.b64encode(priv.sign(b"demo")).decode()
        sig_file = Path("test.whl.sig")
        sig_file.write_text(sig)
        orig_pub = agents_registry._WHEEL_PUBKEY
        orig_sigs = agents_registry._WHEEL_SIGS.copy()
        try:
            agents_registry._WHEEL_PUBKEY = pub_b64
            agents_registry._WHEEL_SIGS = {wheel.name: sig}
            self.assertTrue(agents_mod._verify_wheel(wheel))
        finally:
            agents_registry._WHEEL_PUBKEY = orig_pub
            agents_registry._WHEEL_SIGS = orig_sigs
            wheel.unlink()
            sig_file.unlink()


if __name__ == "__main__":
    unittest.main()
