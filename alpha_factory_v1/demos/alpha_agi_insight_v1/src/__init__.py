# SPDX-License-Identifier: Apache-2.0
"""Entry point for the Insight demo package.

This package exposes lightweight agents, the orchestrator and helper
utilities used by the α‑AGI Insight example. Interface layers under
``interface`` provide a CLI, optional Streamlit dashboards and a REST API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["planning_agent", "orchestrator", "self_improver"]

if TYPE_CHECKING:  # pragma: no cover - import-time type hints only
    from alpha_factory_v1.core import orchestrator as _orchestrator
    from alpha_factory_v1.core.self_evolution import self_improver as _self_improver
    from .agents import planning_agent as _planning_agent


def __getattr__(name: str) -> Any:
    """Lazily import heavy modules to keep smoke tests fast."""

    if name == "planning_agent":
        from .agents import planning_agent as _planning_agent

        return _planning_agent
    if name == "orchestrator":
        from alpha_factory_v1.core import orchestrator as _orchestrator

        return _orchestrator
    if name == "self_improver":
        from alpha_factory_v1.core.self_evolution import (
            self_improver as _self_improver,
        )

        return _self_improver
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
