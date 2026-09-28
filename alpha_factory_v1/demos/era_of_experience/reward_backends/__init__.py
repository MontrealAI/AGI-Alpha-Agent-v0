# SPDX-License-Identifier: Apache-2.0

"""
reward_backends · Alpha‑Factory v1 👁️✨
──────────────────────────────────────────
Pluggable reward‑function registry inspired by Silver & Sutton’s “Era of Experience”.

Any ``*.py`` module in this package that defines **``reward(state, action, result) -> float``**
is auto‑discovered at import‑time and exposed through a thread‑safe read‑only registry.

Public helpers
--------------
• ``list_rewards()``             → tuple[str, …]      – immutable view of registered names
• ``reward_signal(name, s, a, r)`` → float           – invoke *one* backend
• ``blend(signals, weights=None)`` → float           – weighted aggregation helper
• ``refresh()``                  – rescan package at runtime (new modules)

Implementation highlights
-------------------------
• **Zero** external runtime deps beyond the Python ≥ 3.9 std‑lib
• Discovery quarantines bad modules & prints a clear diagnostic
• Read‑path fully thread‑safe via ``MappingProxyType`` & a module‑local ``_LOCK``
• Friendly logging via ``logging.getLogger(__name__)``
"""

from __future__ import annotations

import importlib
import inspect
import logging
import math
import pkgutil
import threading
import types
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Dict, Tuple

__all__ = (
    "list_rewards",
    "reward_signal",
    "blend",
    "refresh",
)

_LOG = logging.getLogger(__name__)
_PKG_PATH = Path(__file__).parent
_REGISTRY: Dict[str, Callable] = {}
_FROZEN: MappingProxyType[str, Callable] | None = None
_LOCK = threading.Lock()

# ───────────────────────── internal helpers ──────────────────────────


def _qualname(mod: types.ModuleType) -> str:  # tiny helper for nicer msgs
    return f"{mod.__name__}.reward"


def _scan_package() -> None:
    """
    Import every backend once & (re)build an immutable registry.

    Safe to call repeatedly – calls are synchronised via ``_LOCK``.
    """
    global _REGISTRY, _FROZEN

    with _LOCK:
        _REGISTRY.clear()

        for info in pkgutil.iter_modules([_PKG_PATH]):  # noqa: PD011
            if info.ispkg or info.name.startswith("_"):
                continue

            mod_name = f"{__name__}.{info.name}"
            try:
                mod = importlib.import_module(mod_name)
            except Exception as exc:  # noqa: BLE001
                _LOG.warning("Failed loading %s: %s", mod_name, exc)
                continue

            fn = getattr(mod, "reward", None)
            if not callable(fn):
                _LOG.warning("%s missing callable reward()", mod_name)
                continue

            sig = inspect.signature(fn)
            if len(sig.parameters) != 3:
                _LOG.warning(
                    "%s has invalid signature %s – expected (state, action, result)",
                    _qualname(mod),
                    sig,
                )
                continue

            _REGISTRY[info.name] = fn

        _FROZEN = MappingProxyType(_REGISTRY.copy())  # snapshots mapping
        _LOG.info("Registered reward back‑ends: %s", ", ".join(_REGISTRY) or "none")


# ─────────────────────────── public API ──────────────────────────────


def list_rewards() -> Tuple[str, ...]:
    """Immutable tuple of available back‑end *names*."""
    return tuple(_FROZEN or ())


def reward_signal(name: str, state, action, result) -> float:
    """
    Run *one* reward backend by name.

    Parameters
    ----------
    name   : str   – backend identifier (module stem)
    state  : Any   – environment / agent state snapshot
    action : Any   – action executed by agent
    result : Any   – observation / env outcome

    Returns
    -------
    float – scalar reward from the backend

    Raises
    ------
    KeyError – unknown backend
    RuntimeError – backend returned non‑numeric
    """
    fn = (_FROZEN or {}).get(name)
    if fn is None:
        raise KeyError(f"Unknown reward back‑end: {name!r}")

    value = fn(state, action, result)
    try:
        converted = float(value)
    except (TypeError, ValueError):
        raise RuntimeError(f"{name}.reward() returned non‑numeric {value!r}") from None
    if not math.isfinite(converted) or not 0.0 <= converted <= 1.0:
        raise RuntimeError(f"{name}.reward() must return a finite value in [0, 1]")
    return converted


def blend(
    signals: Dict[str, float],
    weights: Dict[str, float] | None = None,
) -> float:
    """
    Weighted aggregate of *pre‑computed* reward signals.

    Example
    -------
    >>> s = {"fitness": 0.75, "education": 0.42}
    >>> blend(s, {"fitness": 0.8, "education": 0.2})
    0.678
    """
    if not signals:
        return 0.0

    if weights is None:
        weights = {k: 1.0 for k in signals}

    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in signals.values()):
        raise ValueError("Signals must be finite values in [0, 1]")
    if any(not math.isfinite(value) for value in weights.values()):
        raise ValueError("Weights must be finite")

    # guard common foot‑guns
    negative = [k for k, w in weights.items() if w < 0]
    if negative:
        raise ValueError(f"Negative weights not allowed: {negative}")

    total_w = sum(weights.get(k, 0.0) for k in signals)
    if not math.isfinite(total_w) or total_w <= 0:
        raise ValueError("Sum of weights must be finite and greater than zero")

    return sum(signals[k] * weights.get(k, 0.0) for k in signals) / total_w


def refresh() -> None:
    """Rescan the registry for new backends; restart to load modified module code."""
    _scan_package()


# ───────────────────────── bootstrap on import ───────────────────────
_scan_package()
