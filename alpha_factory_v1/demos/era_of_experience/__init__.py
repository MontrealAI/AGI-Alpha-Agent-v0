# SPDX-License-Identifier: Apache-2.0
"""Experience Lab and lazily loaded, preserved research examples."""
from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "detect_yield_curve_alpha",
    "detect_supply_chain_alpha",
    "SimpleExperienceEnv",
    "ExperienceAgent",
    "FederatedExperienceAgent",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    module = (
        "alpha_detection"
        if name.startswith("detect_")
        else "simulation"
        if name == "SimpleExperienceEnv"
        else "stub_agents"
    )
    value = getattr(import_module(f"{__name__}.{module}"), name)
    globals()[name] = value
    return value
