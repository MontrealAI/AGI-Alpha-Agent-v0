# SPDX-License-Identifier: Apache-2.0
"""Alpha‑Factory v1 package root.

This module exposes the public entry points of the project while keeping the
import footprint minimal.  Submodules listed in :data:`__all__` are loaded on
demand via :func:`__getattr__` so that importing :mod:`alpha_factory_v1` is
lightweight and side‑effect free.
"""

from __future__ import annotations

import importlib
from typing import Any

try:  # attempt to read the installed package version
    from importlib.metadata import version as _version

    __version__ = _version(__name__)
except Exception:  # pragma: no cover - fallback when not installed
    __version__ = "0.1.0-alpha"

__all__ = ["backend", "core", "demos", "ui", "run", "get_version"]


def get_version() -> str:
    """Return the Alpha‑Factory package version."""

    return __version__


def __getattr__(name: str) -> Any:  # pragma: no cover - thin wrapper
    """Lazily import top‑level modules.

    This keeps ``import alpha_factory_v1`` fast and avoids importing heavy
    dependencies until actually needed.
    """

    if name in {"backend", "core", "demos", "ui", "run"}:
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name}")


def __dir__() -> list[str]:  # pragma: no cover - environment driven
    """Return module attributes for ``dir()`` calls."""

    return sorted(list(globals().keys()) + __all__)
