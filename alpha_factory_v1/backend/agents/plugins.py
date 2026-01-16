# SPDX-License-Identifier: Apache-2.0
"""Helper functions for loading agent plugin wheels."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Optional

from .registry import _WHEEL_PUBKEY, _WHEEL_SIGS, ed25519, InvalidSignature, logger


def verify_wheel(path: Path, *, pubkey: str | None = None, sigs: dict[str, str] | None = None) -> bool:
    """Return ``True`` if *path* has a valid signature."""
    sig_path = path.with_suffix(path.suffix + ".sig")
    if not sig_path.is_file():
        logger.error("Missing .sig file for %s", path.name)
        return False
    if ed25519 is None:
        logger.error("cryptography library required for signature checks")
        return False
    sigs = sigs if sigs is not None else _WHEEL_SIGS
    pubkey = pubkey or _WHEEL_PUBKEY
    try:
        sig_b64 = sig_path.read_text().strip()
        expected = sigs.get(path.name)
        if expected and expected != sig_b64:
            logger.error("Signature mismatch for %s", path.name)
            return False
        pub_bytes = base64.b64decode(pubkey)
        signature = base64.b64decode(sig_b64)
        digest = hashlib.sha512(path.read_bytes()).digest()
        ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes).verify(signature, digest)
        return True
    except InvalidSignature:
        logger.error("Invalid signature for %s", path.name)
    except Exception:  # noqa: BLE001
        logger.exception("Signature verification failed for %s", path.name)
    return False


def install_wheel(path: Path) -> Optional[ModuleType]:
    """Load a wheel from *path* and return the module."""
    if not verify_wheel(path):
        logger.error("Refusing to load unsigned wheel: %s", path.name)
        return None
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec and spec.loader:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[arg-type]
        return mod
    return None
