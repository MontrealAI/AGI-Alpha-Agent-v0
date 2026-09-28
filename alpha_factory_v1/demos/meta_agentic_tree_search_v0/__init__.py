# SPDX-License-Identifier: Apache-2.0
"""Meta-Agentic Tree Search v0 demo package."""

from importlib import import_module
from typing import Any

__all__ = ["run_demo", "mats", "openai_agents_bridge"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    module = import_module(f"{__name__}.{name}")
    value = module.run if name == "run_demo" else module
    globals()[name] = value
    return value
