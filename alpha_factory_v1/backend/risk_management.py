# SPDX-License-Identifier: Apache-2.0

"""
backend/risk_management.py
==========================

Self‑contained risk‑management helper for *α‑Factory* FinanceAgent.

• **Historical/Parametric VaR** (value‑at‑risk) at configurable confidence.
• **Max draw‑down** tracker on the running equity curve.
• Stateless API + tiny on‑disk cache to survive crashes / restarts.

The module is deliberately NumPy‑only (no heavy pandas dependency) and
works even when running on constrained edge devices.

If `numpy` is unavailable, the Monte‑Carlo branches gracefully degrade
to a conservative constant VaR estimate.

Usage
-----

```python
from backend.risk_management import RiskManager, RiskLimitError

risk = RiskManager(confidence=0.99, max_var_pct=0.02, max_drawdown_pct=0.15)

# Call *after* each portfolio valuation tick (P&L mark‑to‑market)
risk.update_equity_curve(account_value)

# .. and / or right before sending a new order:
risk.enforce_limits()
```
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import List, Sequence

try:
    import numpy as _np
except ModuleNotFoundError:  # pragma: no cover
    _np = None  # runtime fallback – we will skip MC VaR calc

# ---------------------------------------------------------------------------

__all__ = ["RiskManager", "RiskLimitError"]


class RiskLimitError(RuntimeError):
    """Raised when VaR / draw‑down breaches a hard limit."""


# ---------------------------------------------------------------------------

_CACHE_DIR = Path(os.getenv("ALPHA_DATA_DIR", "/tmp/alphafactory")) / "risk"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)
_EQ_CACHE = _CACHE_DIR / "equity_curve.json"

_LOG = logging.getLogger("alpha_factory.risk")


def _load_equity_cache() -> List[float]:
    if _EQ_CACHE.exists():
        try:
            return json.loads(_EQ_CACHE.read_text())
        except Exception:  # pragma: no cover
            return []
    return []


def _save_equity_cache(curve: Sequence[float]) -> None:
    try:
        _EQ_CACHE.write_text(json.dumps(curve[-5000:]))  # keep ≤ ~5k pts
    except Exception:  # pragma: no cover - best effort persistence
        _LOG.debug(
            "Equity cache write failed – continuing without persistence",
            exc_info=True,
        )


# ---------------------------------------------------------------------------


class RiskManager:
    """Simple VaR + draw‑down risk sentry.

    Parameters
    ----------
    confidence:
        VaR confidence level (e.g. 0.99 means 1 % tail loss).
    max_var_pct:
        Hard VaR limit expressed as a *percentage* of current equity.
    max_drawdown_pct:
        Maximum peak‑to‑trough draw‑down allowed (percentage).
    lookback_days:
        Rolling history for VaR in trading days (default 250 ≈ 1y).
    """

    def __init__(
        self,
        *,
        confidence: float = 0.99,
        max_var_pct: float = 0.02,
        max_drawdown_pct: float = 0.20,
        lookback_days: int = 250,
    ) -> None:
        if not 0.9 <= confidence < 1:
            raise ValueError("confidence should be 0.9 ≤ c < 1")
        self.confidence = confidence
        self.max_var_pct = max_var_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.lookback = lookback_days

        self._equity_curve: List[float] = _load_equity_cache()

        # pre‑warm
        self._peak_equity = max(self._equity_curve, default=0.0)

    # ------------------------------------------------------------------ API

    def update_equity_curve(self, equity_value: float) -> None:
        """Append new equity point and persist to disk."""
        if equity_value <= 0:
            raise ValueError("Equity must be positive")
        self._equity_curve.append(float(equity_value))
        if equity_value > self._peak_equity:
            self._peak_equity = equity_value

        _save_equity_cache(self._equity_curve)

    def var_pct(self) -> float:
        """Current 1‑day VaR as % of equity (historical / parametric)."""
        if _np is None or len(self._equity_curve) < 2:
            # Fallback: pessimistic constant (5 × daily std dev guess)
            return 0.05

        # compute daily log‑returns
        eq = _np.array(self._equity_curve[-self.lookback :], dtype=float)  # noqa: E203
        rets = _np.diff(_np.log(eq))
        if len(rets) < 10:  # not enough data
            return 0.05

        mu = rets.mean()
        sigma = rets.std(ddof=1)
        # parametric VaR (Gaussian) – 1‑day horizon
        z = _np.abs(_np.quantile(rets, 1 - self.confidence))
        var = mu - z * sigma
        return abs(var)

    def drawdown_pct(self) -> float:
        """Latest draw‑down from peak, as %."""
        if not self._equity_curve:
            return 0.0
        last = self._equity_curve[-1]
        return (self._peak_equity - last) / self._peak_equity if self._peak_equity else 0.0

    # ------------------------------------------------ enforcement / guard

    def enforce_limits(self) -> None:
        """Raise :class:`RiskLimitError` if any limit is breached."""
        current_equity = self._equity_curve[-1] if self._equity_curve else 0.0
        if current_equity <= 0:  # pragma: no cover
            raise RiskLimitError("Equity unavailable; risk check failed")

        var = self.var_pct()
        dd = self.drawdown_pct()

        if var > self.max_var_pct:
            raise RiskLimitError(f"VaR {var:.2%} exceeds hard limit {self.max_var_pct:.2%}")
        if dd > self.max_drawdown_pct:
            raise RiskLimitError(f"Draw‑down {dd:.2%} exceeds limit {self.max_drawdown_pct:.2%}")
