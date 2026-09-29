#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Minimal helper to drive the FinanceAgent programmatically.

This script uses the OpenAI Agents SDK when available and falls back to
plain REST requests otherwise. It targets a running Alpha-Factory demo
on ``localhost``.
"""

from __future__ import annotations
import os
import json
import sys
from typing import Any

import af_requests as requests

PORT = int(os.getenv("PORT_API", "8000"))
BASE = f"http://localhost:{PORT}"


def _rest_positions() -> Any:
    """Return positions via the REST fallback."""
    return requests.get(f"{BASE}/api/finance/positions", timeout=3).json()


def _rest_pnl() -> Any:
    """Return P&L via the REST fallback."""
    return requests.get(f"{BASE}/api/finance/pnl", timeout=3).json()


if __name__ == "__main__":
    try:
        from openai.agents import AgentRuntime

        rt = AgentRuntime(base_url=BASE, api_key=None)
        fin = rt.get_agent("FinanceAgent")
        print("Alpha signals:", fin.alpha_signals())
        print("Portfolio book:", fin.portfolio_state())
    except Exception as exc:  # noqa: BLE001
        print("OpenAI Agents SDK unavailable – using REST fallback:", exc)
        print("Positions:", json.dumps(_rest_positions(), indent=2))
        print("PnL:", json.dumps(_rest_pnl(), indent=2))
    sys.exit(0)
