# SPDX-License-Identifier: Apache-2.0
"""Insight discovery workbench and preserved optional research launchers."""
from __future__ import annotations

from importlib import import_module
from typing import Any

__version__ = "1.0.0"
__all__ = [
    "main",
    "openai_agents_bridge",
    "run_demo",
    "official_demo",
    "official_demo_final",
    "official_demo_production",
    "official_demo_zero_data",
    "beyond_human_foresight",
    "api_server",
    "insight_dashboard",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    module = import_module(f"{__name__}.{'__main__' if name == 'main' else name}")
    value = module if name == "openai_agents_bridge" else module.main
    globals()[name] = value
    return value
