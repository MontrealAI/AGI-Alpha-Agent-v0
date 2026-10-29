# SPDX-License-Identifier: Apache-2.0
"""Replay a prior simulated productive-work ledger without granting payment authority."""

from __future__ import annotations

import hashlib
from pathlib import Path
import sqlite3
from typing import Any

from .contracts import digest


def snapshot(target: dict[str, Any]) -> dict[str, Any]:
    path = Path(target["database"])
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_048_576:
        raise ValueError("bounded regular historical database required")
    if hashlib.sha256(path.read_bytes()).hexdigest() != target["database_sha256"]:
        raise ValueError("historical source bytes changed")
    with sqlite3.connect("file:" + str(path.resolve()) + "?mode=ro&immutable=1", uri=True) as db:
        import json

        config = json.loads(db.execute("SELECT value FROM config WHERE id=1").fetchone()[0])
        sums: dict[str, int] = {}
        for kind, amount in db.execute("SELECT kind,amount FROM journal"):
            sums[kind] = sums.get(kind, 0) + int(amount)
        cash = (
            int(config["opening"])
            + sums.get("collections", 0)
            - sums.get("reversal_paid", 0)
            + sums.get("recovery_income", 0)
            - sums.get("expense_paid", 0)
            - sums.get("investment_paid", 0)
        )
        due = sum(int(row[0]) for row in db.execute("SELECT refund_due FROM trades"))
        due += max(0, sums.get("expense", 0) - sums.get("expense_paid", 0))
        custody, tail = 0, 0
        for price, state, held in db.execute("SELECT price,state,custody FROM trades"):
            if held and state in {"funded", "verified"}:
                custody += int(price)
            if state == "released":
                tail += int(price) + 200000
        investment = sum(int(row[0]) for row in db.execute("SELECT cap FROM investments WHERE state='reserved'"))
    commitments = due + custody + tail + int(config["working"]) + investment
    return {
        "schema": "agialpha/executed-reserve-observation/v1",
        "source_db_sha256": target["database_sha256"],
        "cash": str(cash),
        "obligations": str(commitments),
        "free": str(cash - commitments),
        "decomposition": {
            "incurred_payables": str(due),
            "custody": str(custody),
            "tail": str(tail),
            "working": str(config["working"]),
            "investment_commitments": str(investment),
        },
        "source_useful_artifact_sha256": target["useful_artifact_sha256"],
        "scope": "recorded-liquidity-audit; prior beneficiary acceptance separately hash-bound; no external cash attestation",
    }


def verify(target: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct money and held obligations through an independent SQL projection."""
    path = Path(target["database"])
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != target["database_sha256"]:
        raise ValueError("source changed during independent check")
    with sqlite3.connect("file:" + str(path.resolve()) + "?mode=ro&immutable=1", uri=True) as db:
        import json

        config = json.loads(db.execute("SELECT value FROM config WHERE id=1").fetchone()[0])
        entries = list(db.execute("SELECT kind,amount FROM journal"))

        def total(kind: str) -> int:
            return sum(int(x[1]) for x in entries if x[0] == kind)

        available_cash = (
            int(config["opening"])
            + total("collections")
            + total("recovery_income")
            - total("reversal_paid")
            - total("expense_paid")
            - total("investment_paid")
        )
        trade_rows = list(db.execute("SELECT price,state,custody,refund_due FROM trades"))
        owed = sum(int(x[3]) for x in trade_rows) + max(0, total("expense") - total("expense_paid"))
        protected = sum(int(x[0]) for x in trade_rows if x[2] and x[1] in ("funded", "verified"))
        protected += sum(int(x[0]) + 200000 for x in trade_rows if x[1] == "released")
        protected += int(config["working"]) + sum(
            int(x[0]) for x in db.execute("SELECT cap FROM investments WHERE state='reserved'")
        )
    useful = Path(target["useful_artifact"])
    valid = (
        useful.is_file()
        and not useful.is_symlink()
        and hashlib.sha256(useful.read_bytes()).hexdigest() == target["useful_artifact_sha256"]
    )
    valid = valid and artifact["cash"] == str(available_cash) and artifact["obligations"] == str(owed + protected)
    valid = (
        valid
        and artifact["free"] == str(available_cash - owed - protected)
        and artifact["source_db_sha256"] == target["database_sha256"]
    )
    return {
        "accepted": valid is True,
        "task_id": target["id"],
        "artifact_hash": digest(artifact),
        "decisive": valid is True,
        "scope": "exact independent historical ledger arithmetic; external money and current demand unqualified",
    }
