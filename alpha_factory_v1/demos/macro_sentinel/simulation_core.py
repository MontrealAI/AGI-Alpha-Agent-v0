# SPDX-License-Identifier: Apache-2.0
# alpha_factory_v1/demos/macro_sentinel/simulation_core.py
# © 2025 MONTREAL.AI Apache-2.0 License
"""Illustrative Macro-Sentinel scenarios over supplied observations.

The fixed coefficients and regime probability are demonstration assumptions,
not a validated calibration or investment recommendation. Both optional NumPy
and standard-library backends use the same marginal log-return model, but their
random streams differ. No market orders are submitted by this module.
"""

from __future__ import annotations

from itertools import islice
import math
import random

try:  # optional deps
    import numpy as np
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - simplified fallback
    np = None
    pd = None
from typing import Dict, Sequence, Any

# ─────────────────────────  calibration constants  ──────────────────────────

# Illustrative daily log-return regimes; no empirical calibration is claimed.
SIGMA_LOW, SIGMA_HIGH = 0.011, 0.028
P_SWITCH = 0.07  # illustrative probability of the high-volatility regime per path
MAX_PATH_STEPS = 2_000_000  # bound aggregate allocation before drawing any samples

# Illustrative covariance drivers (slope, flow).
VOL_SLOPE = 0.0009
VOL_FLOW = 12.5
VOL_RET = SIGMA_LOW  # initial

if np is not None:
    RHO = np.array([[1.00, 0.18, -0.32], [0.18, 1.00, 0.07], [-0.32, 0.07, 1.00]])
    SIGMA_BASE = np.diag([VOL_SLOPE, VOL_FLOW, VOL_RET])
    CHOL_LOW = np.linalg.cholesky(SIGMA_BASE @ RHO @ SIGMA_BASE)
else:  # pragma: no cover - fallback values
    RHO = None
    SIGMA_BASE = None
    CHOL_LOW = None

# Swap curve DV01 table (per 1 bp – USD notional)
DV01_TABLE = {2: 0.019, 5: 0.042, 10: 0.079, 30: 0.151}  # simplistic


def _choose_dv01(years: int = 10) -> float:
    """Return DV01 in USD per bp for the given swap tenor."""
    return DV01_TABLE.get(years, DV01_TABLE[10])


# ─────────────────────────  simulator class  ────────────────────────────────
class MonteCarloSimulator:
    """Simple Monte-Carlo engine for ES factor shocks."""

    def __init__(self, n_paths: int = 20_000, horizon: int = 30, seed: int | None = None):
        """Create a simulator.

        Args:
            n_paths: Number of Monte-Carlo scenarios.
            horizon: Days to simulate.
            seed: Optional RNG seed for deterministic results.
        """
        if type(n_paths) is not int or not 1 <= n_paths <= 100_000:  # noqa: E721
            raise ValueError("n_paths must be an integer from 1 to 100000")
        if type(horizon) is not int or not 1 <= horizon <= 365:  # noqa: E721
            raise ValueError("horizon must be an integer from 1 to 365")
        if n_paths * horizon > MAX_PATH_STEPS:
            raise ValueError("n_paths times horizon must not exceed 2000000")
        self.n, self.h = n_paths, horizon
        self.dt = 1.0
        self.beta_slope = -8.1e-3  # illustrative coefficient
        self.beta_flow = 9.7e-5
        if np is not None and pd is not None:
            self.rng = np.random.default_rng(seed)
        else:  # pragma: no cover - fallback
            self.rng = random.Random(seed)

    # ─────────── internal helpers ───────────
    def _drift_vec(self, obs: Dict[str, float]) -> Any:
        """Return drift vector based on ``obs``."""
        if not isinstance(obs, dict):
            raise ValueError("observations must be a dictionary")
        values = {}
        for key in ("yield_10y", "yield_3m", "stable_flow"):
            value = obs.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{key} must be a finite number")
            if abs(value) > 1_000_000 or not math.isfinite(value):
                raise ValueError(f"{key} must be finite with absolute value at most 1000000")
            values[key] = value
        slope = values["yield_10y"] - values["yield_3m"]
        mu_es = slope * self.beta_slope + values["stable_flow"] * self.beta_flow
        if np is not None:
            return np.array([0.0, 0.0, mu_es])
        return [0.0, 0.0, mu_es]

    def _chol(self, high_vol: bool) -> Any:
        """Return Cholesky matrix for the selected volatility regime."""
        if np is None:
            return None
        if not high_vol:
            return CHOL_LOW
        Σ = np.diag([VOL_SLOPE, VOL_FLOW, SIGMA_HIGH])
        return np.linalg.cholesky(Σ @ RHO @ Σ)

    # ─────────── public API ───────────
    def simulate(self, obs: Dict[str, float]) -> Any:
        """Simulate ES price factors given current observations."""
        mu = self._drift_vec(obs)
        if abs(float(mu[2])) * self.h > 100:
            raise ValueError("illustrative drift exceeds the bounded simulation range")
        if np is None or pd is None:
            vals = []
            for _ in range(self.n):
                sigma = SIGMA_HIGH if self.rng.random() < P_SWITCH else SIGMA_LOW
                log_factor = math.fsum(float(mu[2]) + self.rng.gauss(0, sigma) for _ in range(self.h))
                vals.append(math.exp(log_factor))
            return vals
        high = self.rng.random(self.n) < P_SWITCH  # regime flag per path
        chol = np.where(high[:, None, None], self._chol(True), CHOL_LOW)

        noise = self.rng.standard_normal((self.n, self.h, 3))
        shocks = (chol[:, None] @ noise[..., None]).squeeze(-1)
        steps = mu * self.dt + shocks
        log_es = steps[..., 2].sum(axis=1)
        return pd.Series(np.exp(log_es), name="es_factor")

    @staticmethod
    def _values(s: Sequence[float]) -> list[float]:
        data = list(islice(s, 100_001))
        if not 1 <= len(data) <= 100_000 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 < x <= 1e100 or not math.isfinite(x)
            for x in data
        ):
            raise ValueError("scenario factors require 1–100000 finite numbers in (0, 1e100]")
        return sorted(float(x) for x in data)

    @staticmethod
    def _percentile(data: list[float], a: float) -> float:
        if isinstance(a, bool) or not isinstance(a, (int, float)) or not 0 <= a <= 1 or not math.isfinite(a):
            raise ValueError("percentile must be between 0 and 1")
        position = (len(data) - 1) * a
        lower = int(position)
        upper = min(lower + 1, len(data) - 1)
        return data[lower] + (data[upper] - data[lower]) * (position - lower)

    @staticmethod
    def var(s: Sequence[float], a: float = 0.05) -> float:
        """Return the linearly interpolated lower-tail quantile minus one."""
        return MonteCarloSimulator._percentile(MonteCarloSimulator._values(s), a) - 1

    @staticmethod
    def cvar(s: Sequence[float], a: float = 0.05) -> float:
        """Return the mean of samples at or below the same quantile minus one."""
        data = MonteCarloSimulator._values(s)
        threshold = MonteCarloSimulator._percentile(data, a)
        tail = [x for x in data if x <= threshold]
        return math.fsum(tail) / len(tail) - 1

    @staticmethod
    def skew(s: Sequence[float]) -> float:
        """Return population skewness, or zero for a constant sample."""
        data = MonteCarloSimulator._values(s)
        mean = math.fsum(data) / len(data)
        variance = math.fsum((x - mean) ** 2 for x in data) / len(data)
        if variance == 0:
            return 0.0
        return math.fsum((x - mean) ** 3 for x in data) / len(data) / variance**1.5

    def hedge(self, s: Sequence[float], port_usd: float, swap_tenor: int = 10) -> Dict[str, Any]:
        """Return hedge notionals and risk metrics.

        Args:
            s: Scenario results as ES factors.
            port_usd: Portfolio value in USD.
            swap_tenor: Swap maturity in years.

        Returns:
            Dictionary with ES and DV01 notionals and metrics.
        """
        if isinstance(port_usd, bool) or not isinstance(port_usd, (int, float)):
            raise ValueError("portfolio must be a finite nonnegative number")
        if not 0 <= port_usd <= 1e15 or not math.isfinite(port_usd):
            raise ValueError("portfolio must be between zero and 1e15")
        var = self.var(s)
        cvar = self.cvar(s)
        dv01 = _choose_dv01(swap_tenor)
        es_notional = -var * port_usd
        dv01_usd = -0.5 * port_usd / dv01  # naive 50 % hedge to rates

        return {
            "es_notional": float(es_notional),
            "dv01_usd": float(dv01_usd),
            "metrics": {"var": float(var), "cvar": float(cvar), "skew": float(self.skew(s))},
        }

    # convenience for UI
    def scenario_table(self, s: Sequence[float]) -> Any:
        """Return median, VaR 5 % and stress 1 % rows for UI tables."""
        data = self._values(s)
        quant = [self._percentile(data, p) for p in (0.5, 0.05, 0.01)]
        rows = [
            {"Scenario": name, "ES factor": round(value, 3)}
            for name, value in zip(("Median", "VaR 5 %", "Stress 1 %"), quant)
        ]
        return pd.DataFrame(rows) if pd is not None else rows


def draft_order(hedge: dict[str, Any]) -> dict[str, Any]:
    """Describe an illustrative whole-contract quantity without authorizing execution."""
    notional = hedge.get("es_notional") if isinstance(hedge, dict) else None
    if isinstance(notional, bool) or not isinstance(notional, (int, float)):
        raise ValueError("es_notional must be a finite number")
    if abs(notional) > 1e15 or not math.isfinite(notional):
        raise ValueError("es_notional must be finite with absolute value at most 1e15")
    quantity = int(abs(notional) // 50_000)
    return {
        "symbol": "MES",
        "qty": quantity,
        "side": ("SELL" if notional > 0 else "BUY") if quantity else "NONE",
        "type": "MKT",
        "mode": "illustrative draft",
        "executionAuthorized": False,
        "assumedContractNotionalUsd": 50_000,
        "assumptionScope": "Illustrative fixed conversion; not a current MES price or contract valuation",
    }
