# SPDX-License-Identifier: Apache-2.0
"""DuckDB backed archive storing solutions by sector and approach."""
from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    import duckdb
except Exception:  # pragma: no cover - optional dependency
    duckdb = None

try:
    import orjson
except Exception:  # pragma: no cover - optional dependency
    orjson = None


@dataclass(slots=True)
class Solution:
    sector: str
    approach: str
    score: float
    data: Mapping[str, Any]
    ts: float


class SolutionArchive:
    """Archive storing solutions in bins keyed by ``(sector, approach, band)``."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if duckdb is not None:
            self.conn = duckdb.connect(str(self.path))
        else:  # pragma: no cover - fallback
            self.conn = sqlite3.connect(str(self.path))
        self._ensure()

    def _ensure(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS solutions(
                sector TEXT,
                approach TEXT,
                score DOUBLE,
                band INTEGER,
                data TEXT,
                ts DOUBLE
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_bins ON solutions(sector, approach, band)")
        if isinstance(self.conn, sqlite3.Connection):
            self.conn.commit()

    @staticmethod
    def _band(score: float) -> int:
        return int(score // 10)

    def add(self, sector: str, approach: str, score: float, data: Mapping[str, Any]) -> None:
        """Insert a solution entry grouped by sector and approach."""
        band = self._band(score)
        payload = json.dumps(dict(data)) if orjson is None else orjson.dumps(dict(data)).decode("utf-8")
        self.conn.execute(
            "INSERT INTO solutions(sector, approach, score, band, data, ts) VALUES (?,?,?,?,?,?)",
            (sector, approach, score, band, payload, time.time()),
        )
        if isinstance(self.conn, sqlite3.Connection):  # pragma: no cover - sqlite
            self.conn.commit()

    def query(
        self,
        sector: str | None = None,
        approach: str | None = None,
        band: int | None = None,
    ) -> list[Solution]:
        """Return solutions matching the provided filters."""
        clauses: list[str] = []
        params: list[Any] = []
        if sector is not None:
            clauses.append("sector=?")
            params.append(sector)
        if approach is not None:
            clauses.append("approach=?")
            params.append(approach)
        if band is not None:
            clauses.append("band=?")
            params.append(band)
        sql = "SELECT sector, approach, score, data, ts FROM solutions"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        cur = self.conn.execute(sql, params)
        rows = cur.fetchall()
        result = [
            Solution(
                sector=row[0],
                approach=row[1],
                score=float(row[2]),
                data=json.loads(row[3]) if orjson is None else orjson.loads(row[3]),
                ts=float(row[4]),
            )
            for row in rows
        ]
        return result

    def diversity_histogram(self) -> dict[tuple[str, str], int]:
        """Return entry counts keyed by ``(sector, approach)``."""
        cur = self.conn.execute("SELECT sector, approach, COUNT(*) FROM solutions GROUP BY sector, approach")
        rows = cur.fetchall()
        return {(r[0], r[1]): int(r[2]) for r in rows}

    def close(self) -> None:
        """Close the underlying connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


__all__ = ["Solution", "SolutionArchive"]
