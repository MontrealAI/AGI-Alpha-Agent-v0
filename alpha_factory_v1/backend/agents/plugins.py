# SPDX-License-Identifier: Apache-2.0
"""Helper functions for loading agent plugin wheels."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Optional

from . import registry


def verify_wheel(path: Path) -> bool:
    """Return ``True`` if *path* has a valid signature."""
    sig_path = path.with_suffix(path.suffix + ".sig")
    if not sig_path.is_file():
        registry.logger.error("Missing .sig file for %s", path.name)
        return False
    if registry.ed25519 is None:
        registry.logger.error("cryptography library required for signature checks")
        return False
    try:
        sig_b64 = sig_path.read_text().strip()
        expected = registry._WHEEL_SIGS.get(path.name)
        if expected and expected != sig_b64:
            registry.logger.error("Signature mismatch for %s", path.name)
            return False
        pub_bytes = base64.b64decode(registry._WHEEL_PUBKEY)
        signature = base64.b64decode(sig_b64)
        data = path.read_bytes()
        pub = registry.ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        try:
            pub.verify(signature, data)
            return True
        except registry.InvalidSignature:
            digest = hashlib.sha512(data).digest()
            pub.verify(signature, digest)
            return True
    except registry.InvalidSignature:
        registry.logger.error("Invalid signature for %s", path.name)
    except Exception:  # noqa: BLE001
        registry.logger.exception("Signature verification failed for %s", path.name)
    return False


def install_wheel(path: Path) -> Optional[ModuleType]:
    """Load a wheel from *path* and return the module."""
    if not verify_wheel(path):
        registry.logger.error("Refusing to load unsigned wheel: %s", path.name)
        return None
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[arg-type]
        return mod
    return None
