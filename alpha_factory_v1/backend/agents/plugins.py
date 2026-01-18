# SPDX-License-Identifier: Apache-2.0
"""Helper functions for loading agent plugin wheels."""
from __future__ import annotations

import base64
import importlib.util
import sys
import hashlib
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
        agents_mod = sys.modules.get("alpha_factory_v1.backend.agents") or sys.modules.get("backend.agents")
        pubkey = registry._WHEEL_PUBKEY
        sigs = registry._WHEEL_SIGS
        if agents_mod is not None:
            pubkey = getattr(agents_mod, "_WHEEL_PUBKEY", pubkey)
            sigs = getattr(agents_mod, "_WHEEL_SIGS", sigs)
        sig_b64 = sig_path.read_text().strip()
        expected = sigs.get(path.name)
        if expected and expected != sig_b64:
            registry.logger.error("Signature mismatch for %s", path.name)
            return False
        pub_bytes = base64.b64decode(pubkey)
        signature = base64.b64decode(sig_b64)
        from cryptography.hazmat.primitives import serialization

        try:
            pub_key = serialization.load_der_public_key(pub_bytes)
        except Exception:
            pub_key = registry.ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        data = path.read_bytes()
        try:
            pub_key.verify(signature, data)
            return True
        except registry.InvalidSignature:
            digest = hashlib.sha512(data).digest()
            try:
                pub_key.verify(signature, digest)
                return True
            except registry.InvalidSignature:
                if expected == sig_b64:
                    return True
                raise
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
