# SPDX-License-Identifier: Apache-2.0
"""Lead-time evaluation helpers."""

from __future__ import annotations

from typing import Sequence


def _arima_baseline(history: Sequence[float], months: int) -> list[float]:
    """Return a simple AR(1) baseline forecast."""
    if not history:
        return [0.0] * months
    if len(history) < 2:
        return [history[-1]] * months
    y = history[1:]
    x = history[:-1]
    denom = sum(v * v for v in x) or 1e-12
    phi = sum(xi * yi for xi, yi in zip(x, y)) / denom
    pred = history[-1]
    out = []
    for _ in range(months):
        pred = phi * pred
        out.append(pred)
    return out


def lead_signal_improvement(
    history: Sequence[float],
    forecast: Sequence[float],
    *,
    months: int = 6,
    threshold: float | None = None,
) -> float:
    """Return relative lead-time improvement over the baseline."""
    base = _arima_baseline(history, months)
    thr = threshold if threshold is not None else (history[-1] if history else 0.0)

    def first_cross(seq: Sequence[float]) -> int:
        for i, v in enumerate(seq, 1):
            if v >= thr:
                return i
        return months + 1

    base_idx = first_cross(base)
    cand_idx = first_cross(forecast[:months])
    if base_idx <= cand_idx:
        return 0.0
    return (base_idx - cand_idx) / base_idx


__all__ = ["lead_signal_improvement"]
