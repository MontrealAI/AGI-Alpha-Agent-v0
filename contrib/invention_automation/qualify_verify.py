# SPDX-License-Identifier: Apache-2.0
"""Compatibility forwarder; frozen checks bind the installed implementation."""

from __future__ import annotations

from typing import Any

from alpha_factory_v1.core.runtime.invention_verification import qualify_verify as _implementation

__all__ = [name for name in vars(_implementation) if not name.startswith("_")]


def __getattr__(name: str) -> Any:
    return getattr(_implementation, name)


def __dir__() -> list[str]:
    return dir(_implementation)


if __name__ == "__main__":
    _implementation.main()
