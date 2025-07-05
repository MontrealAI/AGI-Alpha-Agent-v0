# SPDX-License-Identifier: Apache-2.0
"""backend.alpha_model
======================

Tiny **price‑action** helpers used by the FinanceAgent.
All routines depend solely on ``numpy`` (already shipped with PyTorch) and
gracefully handle short input series. The module is deliberately self‑contained
so it can run on constrained edge devices without optional extras.
"""

from __future__ import annotations

from typing import Sequence

try:
    import numpy as np  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - lightweight fallback
    np = None  # type: ignore

__all__ = [
    "momentum",
    "sma_crossover",
    "ema",
    "rsi",
    "bollinger_bands",
]


def momentum(prices: Sequence[float], lookback: int = 20) -> float:
    """Return percentage momentum over ``lookback`` periods.

    Parameters
    ----------
    prices:
        Ordered price series (oldest → newest).
    lookback:
        Number of periods to look back. ``lookback`` ≤ ``len(prices) - 1``
        is required for a meaningful result.
    """

    if lookback <= 0:
        raise ValueError("lookback must be positive")
    if len(prices) < lookback + 1:
        return 0.0
    base = float(prices[-lookback - 1])
    return (float(prices[-1]) - base) / base


def sma_crossover(prices: Sequence[float], fast: int = 20, slow: int = 50) -> int:
    """Detect a simple moving-average cross-over.

    Returns ``+1`` for a bullish cross, ``-1`` for a bearish cross and ``0``
    otherwise.
    """

    if fast <= 0 or slow <= 0:
        raise ValueError("periods must be positive")
    if fast >= slow:
        raise ValueError("fast period must be shorter than slow period")
    if len(prices) < slow + 1:
        return 0

    if np is not None:
        prices_arr = np.asarray(prices, dtype=float)
        fast_now = float(np.mean(prices_arr[-fast:]))
        slow_now = float(np.mean(prices_arr[-slow:]))
        fast_slice_start = -fast - 1
        slow_slice_start = -slow - 1
        fast_prev = float(np.mean(prices_arr[fast_slice_start:-1]))
        slow_prev = float(np.mean(prices_arr[slow_slice_start:-1]))
    else:  # fallback to pure Python
        fast_now = sum(prices[-fast:]) / fast
        slow_now = sum(prices[-slow:]) / slow
        fast_slice_start = -fast - 1
        slow_slice_start = -slow - 1
        fast_prev = sum(prices[fast_slice_start:-1]) / fast
        slow_prev = sum(prices[slow_slice_start:-1]) / slow

    if fast_prev <= slow_prev and fast_now > slow_now:
        return +1
    if fast_prev >= slow_prev and fast_now < slow_now:
        return -1
    return 0


def ema(prices: Sequence[float], span: int = 20) -> float:
    """Return the exponential moving average over ``span`` periods."""

    if span <= 0:
        raise ValueError("span must be positive")
    if not prices:
        return 0.0

    alpha = 2 / (span + 1)
    ema_val = float(prices[0])
    for p in prices[1:]:
        ema_val = (float(p) - ema_val) * alpha + ema_val
    return ema_val


def rsi(prices: Sequence[float], period: int = 14) -> float:
    """Compute the relative strength index (0‒100)."""

    if period <= 0:
        raise ValueError("period must be positive")
    if len(prices) <= period:
        return 0.0

    if np is not None:
        deltas = np.diff(np.asarray(prices, dtype=float))
        gains = np.clip(deltas, 0, None)
        losses = np.clip(-deltas, 0, None)

        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))

        for g, loss_val in zip(gains[period:], losses[period:]):
            avg_gain = (avg_gain * (period - 1) + float(g)) / period
            avg_loss = (avg_loss * (period - 1) + float(loss_val)) / period
    else:
        deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
        gains = [max(d, 0.0) for d in deltas]
        losses = [max(-d, 0.0) for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for g, loss_val in zip(gains[period:], losses[period:]):
            avg_gain = (avg_gain * (period - 1) + g) / period
            avg_loss = (avg_loss * (period - 1) + loss_val) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1 + rs))


def bollinger_bands(
    prices: Sequence[float],
    window: int = 20,
    num_std: float = 2.0,
) -> tuple[float, float]:
    """Return the lower and upper Bollinger Bands."""

    if window <= 0:
        raise ValueError("window must be positive")
    if len(prices) < window:
        return (0.0, 0.0)

    if np is not None:
        arr = np.asarray(prices[-window:], dtype=float)
        mean = float(arr.mean())
        std = float(arr.std(ddof=1))
    else:
        slice_ = [float(p) for p in prices[-window:]]
        mean = sum(slice_) / window
        variance = sum((p - mean) ** 2 for p in slice_) / (window - 1)
        std = variance**0.5
    band = num_std * std
    return (mean - band, mean + band)
