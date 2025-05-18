"""Simple equity alpha scanning helpers for demo purposes."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


def scan_equity_alpha(symbols: list[str]) -> dict[str, float]:
    """Return 1-day percent change for each ticker.

    Parameters
    ----------
    symbols:
        List of ticker symbols (e.g., ["AAPL", "MSFT"]).

    Returns
    -------
    dict
        Mapping of symbol → 1-day percent return, sorted descending.
    """
    data = yf.download(symbols, period="2d", interval="1d", progress=False)
    if isinstance(data, pd.DataFrame) and not data.empty:
        last = data["Close"].iloc[-1]
        prev = data["Close"].iloc[-2]
        pct = ((last - prev) / prev * 100).to_dict()
        return dict(sorted(pct.items(), key=lambda kv: kv[1], reverse=True))
    return {}

__all__ = ["scan_equity_alpha"]
