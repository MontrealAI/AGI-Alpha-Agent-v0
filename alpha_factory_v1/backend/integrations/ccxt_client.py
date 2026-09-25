# SPDX-License-Identifier: Apache-2.0
"""
Secure, test-net-only wrapper around **CCXT** (crypto exchange client).

Used by:
    • FinanceAlphaAgent   – live (test) trading bot
    • MacroSentinelAgent  – hedge executions
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Dict

_LOG = logging.getLogger("alpha_factory.ccxt")
_LOG.addHandler(logging.NullHandler())

try:
    import ccxt.async_support as ccxt  # optional heavy import

    _CCXT_OK = True
except ModuleNotFoundError:
    ccxt = None  # type: ignore
    _CCXT_OK = False


class ExchangeStub:
    """Fallback deterministic pseudo-exchange for offline demos."""

    def __init__(self) -> None:
        self._price: Dict[str, float] = {}

    async def fetch_ticker(self, symbol: str) -> Dict[str, float]:
        p = self._price.setdefault(symbol, random.uniform(100, 200))
        # Random walk
        self._price[symbol] = p + random.uniform(-1, 1)
        return {"last": round(self._price[symbol], 2), "timestamp": int(time.time() * 1000)}

    async def create_order(self, symbol: str, side: str, amount: float) -> Dict[str, str]:  # noqa: D401
        _LOG.info("Simulated order: %s %s %s", side, amount, symbol)
        return {"id": f"sim-{int(time.time()*1000)}", "status": "filled"}


def _build_ccxt_client() -> object:
    if not _CCXT_OK:
        _LOG.warning("CCXT not installed – using offline price stub")
        return ExchangeStub()

    key = os.getenv("BINANCE_API_KEY", "")
    secret = os.getenv("BINANCE_API_SECRET", "")
    if not key or not secret:
        _LOG.warning("BINANCE_API_KEY/SECRET missing – offline price stub engaged")
        return ExchangeStub()

    client = ccxt.binanceusdm(
        {
            "apiKey": key,
            "secret": secret,
            "enableRateLimit": True,
            "options": {"defaultType": "future"},  # testnet futures
        }
    )
    # Selecting a futures market does not select the test network. Set sandbox
    # mode before any exchange request so this test-only wrapper cannot trade
    # on production endpoints when credentials are present.
    client.set_sandbox_mode(True)
    return client


# --------------------------------------------------------------------- #
#  Public singleton                                                     #
# --------------------------------------------------------------------- #
CLIENT = _build_ccxt_client()
