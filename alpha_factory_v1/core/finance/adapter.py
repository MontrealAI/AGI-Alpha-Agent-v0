# SPDX-License-Identifier: Apache-2.0
"""Finance adapter utilities."""

from __future__ import annotations

from typing import Dict, Any

import csv
import json
from pathlib import Path


_MAP_PATH = Path(__file__).resolve().parents[3] / "data" / "sector_equity_map.csv"


def delta_sector_to_dcf(sector_state: Dict[str, float]) -> Dict[str, Any]:
    """Convert ``sector_state`` deltas into a discounted cash flow representation.

    The input dictionary should contain the following keys:

    - ``delta_revenue``: annual revenue delta (absolute value).
    - ``margin``: operating margin as a decimal.
    - ``discount_rate``: discount rate as a decimal.
    - ``years``: number of forecast years.

    Returns a dictionary with calculated ``cash_flows`` and ``npv``.
    """

    delta_revenue = float(sector_state.get("delta_revenue", 0.0))
    margin = float(sector_state.get("margin", 0.0))
    discount_rate = float(sector_state.get("discount_rate", 0.1))
    years = int(sector_state.get("years", 1))

    cash_flow = delta_revenue * margin
    cash_flows = [cash_flow for _ in range(years)]
    npv = sum(cf / ((1 + discount_rate) ** (i + 1)) for i, cf in enumerate(cash_flows))
    return {"cash_flows": cash_flows, "npv": npv}


def load_sector_equity_map(path: str | Path = _MAP_PATH) -> Dict[str, list[str]]:
    """Return the sector-to-equity mapping from ``path``."""

    mapping: Dict[str, list[str]] = {}
    with Path(path).open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            sector = (row.get("sector") or "").strip()
            ticker = (row.get("ticker") or "").strip()
            if not sector or not ticker:
                continue
            mapping.setdefault(sector, []).append(ticker)
    return mapping


def propagate_shocks_to_tickers(shocks: Dict[str, float], *, map_path: str | Path = _MAP_PATH) -> str:
    """Propagate ``shocks`` to equity tickers and return the result as JSON."""

    mapping = load_sector_equity_map(map_path)
    impacts: Dict[str, float] = {}
    for sector, pct in shocks.items():
        tickers = mapping.get(sector, [])
        for ticker in tickers:
            impacts[ticker] = impacts.get(ticker, 0.0) + float(pct)
    return json.dumps(impacts)
