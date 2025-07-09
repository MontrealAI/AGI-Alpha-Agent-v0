# SPDX-License-Identifier: Apache-2.0
"""Demo package utilities and CLI helpers.

The module originally imported :mod:`validate_demos` at import time which
loaded the validator whenever ``alpha_factory_v1.demos`` was imported.  This
eager import caused the validator module to execute twice in some helpers that
first imported ``alpha_factory_v1.demos`` and later executed ``validate_demos``
via ``python -m``.  To avoid the duplicate load we lazily import the validator
on first access using ``__getattr__``.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["validate_demos"]


def __getattr__(name: str) -> Any:
    if name == "validate_demos":
        return import_module(f".{name}", __name__)
    raise AttributeError(f"module {__name__!r} has no attribute {name}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + __all__)
