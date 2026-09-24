# SPDX-License-Identifier: Apache-2.0
"""Shared utilities, loaded on demand so isolation does not initialize integrations."""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "CFG",
    "get_secret",
    "plot_pareto",
    "view",
    "str_replace",
    "generate_proof",
    "publish_proof",
    "verify_proof",
    "aggregate_proof",
    "verify_aggregate_proof",
    "alerts",
    "logging",
    "tracing",
]


def __getattr__(name: str) -> Any:
    """Preserve legacy exports without requiring their optional services at import."""
    if name not in __all__:
        raise AttributeError(name)
    value = getattr(import_module(f"{__name__}._legacy_exports"), name)
    globals()[name] = value
    return value
