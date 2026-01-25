# SPDX-License-Identifier: Apache-2.0
"""
Tiny on‑disk trade‑ledger used by FinanceAgent.

It now **streams each fill** to the live Trace‑graph WebSocket
(`/ws/trace`) when FastAPI + `backend.trace_ws` are available.

File locking relies on :mod:`fcntl` or :mod:`msvcrt`. If neither module is
present, writes proceed without locking and a warning is emitted.
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
import time
from pathlib import Path
from dataclasses import asdict, dataclass
from typing import Dict, Iterable
import logging

logger = logging.getLogger(__name__)

try:  # optional OS specific locking modules
    import fcntl  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - Windows
    fcntl = None  # noqa: E701

try:  # pragma: no cover - POSIX
    import msvcrt  # type: ignore
except ModuleNotFoundError:
    msvcrt = None

# When both modules are missing, locking is skipped entirely.

# Directory is overridable for tests (they patch $ALPHA_DATA_DIR)
DATA_DIR = Path(os.getenv("ALPHA_DATA_DIR", "/tmp/alphafactory"))
DB_PATH = DATA_DIR / "portfolio.jsonl"
DATA_DIR.mkdir(parents=True, exist_ok=True)
_PORTFOLIO_EXECUTOR = ThreadPoolExecutor(max_workers=1)


@dataclass(slots=True)
class Fill:
    """Normalized trade fill."""

    ts: float
    symbol: str
    qty: float
    price: float
    side: str

    def to_json(self) -> str:
        """Serialize the fill to a compact JSON string."""
        return json.dumps(asdict(self), separators=(",", ":"))


class Portfolio:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        """Initialize the portfolio and load any persisted fills."""
        self._db_path = db_path
        self._positions: Dict[str, float] = {}

        # ── load existing fills (if any) ──────────────────────────────────
        if db_path.exists():
            for line in db_path.read_text().splitlines():
                try:
                    rec = Fill(**json.loads(line))
                except (json.JSONDecodeError, TypeError, KeyError) as exc:
                    logger.warning("Skipping corrupt fill record: %s", exc)
                    continue  # skip corrupt lines
                self._apply(rec, persist=False)

    # ── public API ────────────────────────────────────────────────────────
    def record_fill(self, symbol: str, qty: float, price: float, side: str) -> None:
        """
        Persist a trade fill and update in‑memory positions.

        Additionally, broadcast the event to the Trace‑graph UI (best‑effort;
        never breaks the main flow if the WebSocket layer is absent).
        """
        side = side.upper()
        if side not in {"BUY", "SELL"}:
            raise ValueError("side must be BUY or SELL")
        if qty <= 0 or price <= 0:
            raise ValueError("qty and price must be positive")

        fill = Fill(
            ts=time.time(),
            symbol=symbol,
            qty=float(qty),
            price=float(price),
            side=side,
        )

        self._apply(fill)  # update positions + append to disk
        self._broadcast(fill)  # fire‑and‑forget notification

    def book(self) -> Dict[str, float]:
        """Return a copy of the current position book."""
        return dict(self._positions)

    def history(self) -> Iterable[Fill]:
        """Iterate over all persisted fills (newest-last)."""
        if not self._db_path.exists():
            return []
        with self._db_path.open() as fh:
            for line in fh:
                try:
                    yield Fill(**json.loads(line))
                except (json.JSONDecodeError, TypeError, KeyError) as exc:
                    logger.warning("Skipping corrupt fill record: %s", exc)
                    continue

    def clear(self) -> None:
        """Erase all persisted fills and reset positions."""
        self._positions.clear()
        if self._db_path.exists():
            self._db_path.write_text("")

    async def arecord_fill(self, symbol: str, qty: float, price: float, side: str) -> None:
        """Async wrapper around :meth:`record_fill`."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(_PORTFOLIO_EXECUTOR, self.record_fill, symbol, qty, price, side)

    def position(self, symbol: str) -> float:
        """Current net position (0.0 if the symbol has never traded)."""
        return self._positions.get(symbol, 0.0)

    # ── internal helpers ──────────────────────────────────────────────────
    def _apply(self, fill: Fill, *, persist: bool = True) -> None:
        mult = 1 if fill.side == "BUY" else -1
        self._positions[fill.symbol] = self._positions.get(fill.symbol, 0.0) + mult * fill.qty
        if persist:
            self._append(fill)

    def _append(self, fill: Fill) -> None:
        """Append‑only JSONL persistence with basic file locking.

        If neither :mod:`fcntl` nor :mod:`msvcrt` is available, locking is
        skipped and a warning is emitted.
        """
        fh = self._db_path.open("a")
        try:
            if fcntl:
                fcntl.flock(fh, fcntl.LOCK_EX)
            elif msvcrt:
                msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)
            else:
                logger.warning("File locking unavailable; concurrent writes may corrupt the ledger")
            fh.write(fill.to_json() + "\n")
        finally:
            try:
                if fcntl:
                    fcntl.flock(fh, fcntl.LOCK_UN)
                elif msvcrt:
                    msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)
            finally:
                fh.close()

    # ── trace‑graph integration ───────────────────────────────────────────
    def _broadcast(self, fill: Fill) -> None:  # pragma: no cover
        """
        Best‑effort broadcast of the fill to any connected Trace‑graph UI.

        Uses a *lazy import* so the portfolio works even if `trace_ws`
        (and its FastAPI dependency) are not installed in production.
        """
        try:
            from backend.trace_ws import hub  # local import avoids cycles
        except ModuleNotFoundError:
            return  # tracing not available

        asyncio.create_task(
            hub.broadcast(
                {
                    "id": f"fill-{int(fill.ts*1000)}",
                    "label": f"{fill.side} {fill.qty} {fill.symbol} @ {fill.price}",
                    "data": asdict(fill),
                }
            )
        )


__all__ = ["Portfolio", "Fill"]
