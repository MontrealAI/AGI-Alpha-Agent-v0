# SPDX-License-Identifier: Apache-2.0
"""Real signatures must bind the wheel bytes regardless of registry membership."""

import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
import pytest

from alpha_factory_v1.backend import agents
from alpha_factory_v1.scripts import verify_wheel_sig


@pytest.mark.parametrize("tamper", ["wheel", "key", "signature", "base64", "none"])
def test_registry_entry_never_replaces_signature_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    wheel = tmp_path / "agent.whl"
    wheel.write_bytes(b"approved wheel content")
    key = Ed25519PrivateKey.generate()
    signature = base64.b64encode(key.sign(wheel.read_bytes())).decode()
    public = base64.b64encode(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)).decode()
    if tamper == "wheel":
        wheel.write_bytes(b"unapproved replacement content")
    elif tamper == "key":
        public = base64.b64encode(
            Ed25519PrivateKey.generate().public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
        ).decode()
    elif tamper == "signature":
        signature = base64.b64encode(bytes(64)).decode()
    elif tamper == "base64":
        signature += "!"
    wheel.with_suffix(".whl.sig").write_text(signature)
    monkeypatch.setattr(agents, "_WHEEL_PUBKEY", public)
    monkeypatch.setattr(agents, "_WHEEL_SIGS", {wheel.name: signature})
    assert agents._verify_wheel(wheel) is (tamper == "none")
    assert verify_wheel_sig.verify(wheel) is (tamper == "none")
