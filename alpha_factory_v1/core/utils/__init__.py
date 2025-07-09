# SPDX-License-Identifier: Apache-2.0
"""Shared utilities and configuration."""

from typing import Any, Iterable
from pathlib import Path

from .config import CFG, get_secret

try:
    from .visual import plot_pareto
except Exception:  # pragma: no cover - optional dependency

    def plot_pareto(elites: Iterable[Any], out_path: Path) -> None:
        """Stub when plotly is unavailable."""
        return None


from .file_ops import view, str_replace
from . import alerts, tracing
from alpha_factory_v1.common.utils import logging
from .snark import (
    generate_proof,
    publish_proof,
    verify_proof,
    aggregate_proof,
    verify_aggregate_proof,
)

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
