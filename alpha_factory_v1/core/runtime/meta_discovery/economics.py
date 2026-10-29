# SPDX-License-Identifier: Apache-2.0
"""Separate profit, payback, liquidity, provenance and evidence gates."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass
class Financials:
    opening: int = 0
    revenue: int = 0
    expenses: int = 0
    collections: int = 0
    payments: int = 0
    capex: int = 0
    amortization: int = 0
    debt: int = 0
    restricted: int = 0
    reserve: int = 0
    working_capital: int = 0
    historical_investment: int = 0

    def report(self) -> dict[str, int]:
        cash = self.opening + self.debt + self.collections - self.payments - self.capex
        profit = self.revenue - self.expenses - self.amortization
        payable = max(0, self.expenses - self.payments)
        available = max(0, cash - payable - self.reserve - self.working_capital)
        return {
            "profit": profit,
            "cash": cash,
            "receivables": self.revenue - self.collections,
            "payables": payable,
            "restricted": self.restricted,
            "available": available,
            "unrestrictedEarned": max(
                0, min(available, self.collections - self.payments - self.capex - self.reserve - self.working_capital)
            ),
            "unrecoveredInvestment": max(0, self.historical_investment - max(0, self.revenue - self.expenses)),
        }

    def invest(self, cost: int, expected_net_value: int, funded_by: str = "earned") -> dict[str, Any]:
        state = self.report()
        if type(cost) is not int or cost <= 0 or funded_by not in {"earned", "equity", "debt", "mixed"}:
            raise ValueError("investment policy")
        funds = state["unrestrictedEarned"] if funded_by == "earned" else state["available"]
        return {
            "decision": "CONTINUE" if cost <= funds and expected_net_value > 0 else "HOLD INVESTMENT",
            "funding": funded_by,
            "shortfall": max(0, cost - funds),
            "profit": state["profit"],
            "paybackComplete": state["unrecoveredInvestment"] == 0,
        }


def priced_costs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    seen = set()
    total = Decimal(0)
    retained = []
    rejected = []
    for row in rows:
        if row["id"] in seen:
            raise ValueError("cost counted twice")
        seen.add(row["id"])
        if row["layer"] not in {"A", "B", "C"} or row["basis"] not in {"measured", "estimated", "unavailable"}:
            raise ValueError("cost classification")
        if not row.get("justification") or row.get("fictional_human"):
            rejected.append(row)
            continue
        if row["basis"] == "unavailable":
            retained.append(row)
            continue
        cost = Decimal(str(row["quantity"])) * Decimal(str(row["rate"]))
        if cost < 0:
            raise ValueError("negative cost")
        total += cost
        retained.append({**row, "cost": str(cost)})
    return {
        "conditionalTotal": str(total),
        "retained": retained,
        "rejected": rejected,
        "fullyMetered": all(x["basis"] == "measured" for x in retained),
    }


def decisions(
    *,
    operation: bool,
    causal_gain: bool,
    fresh: bool,
    bridge: bool,
    blue_sky: bool,
    profit: int,
    investment: bool,
    successor_net: int,
    installed: bool,
    full_gates: bool,
) -> dict[str, str]:
    return {
        "META OPERATION": "CONTINUE" if operation else "STOP",
        "META VALUE": "CONTINUE" if operation and causal_gain and fresh else "IMPROVE",
        "BLUE SKY FLAGSHIP": "CONTINUE" if blue_sky and bridge else "HOLD",
        "COMMERCIAL VIABILITY": "CONTINUE" if profit > 0 else "PIVOT",
        "INVESTMENT": "CONTINUE" if investment else "HOLD INVESTMENT",
        "SUCCESSOR VALUE": "CONTINUE" if successor_net > 0 and fresh else "HOLD",
        "NATIVE INTEGRATION": "SCOPED" if installed else "HOLD",
        "RELEASE": "CONTINUE" if full_gates else "HOLD",
    }


class Budget:
    def __init__(self, total: int, protected: int) -> None:
        if not 0 <= protected <= total:
            raise ValueError("budget")
        self.total, self.protected, self.used = total, protected, 0

    def charge(self, amount: int, verification: bool = False) -> None:
        if (
            type(amount) is not int
            or amount < 0
            or self.used + amount > self.total - (0 if verification else self.protected)
        ):
            raise ValueError("protected resource exhaustion")
        self.used += amount


def requalify(asset: dict[str, Any], current: dict[str, Any]) -> bool:
    keys = {"agent", "skillVersion", "sourceHash", "model", "context", "authority"}
    return (
        keys <= asset.keys()
        and keys <= current.keys()
        and not current.get("revoked", True)
        and all(asset[k] == current[k] for k in keys)
    )


def correct_claim(records: list[dict[str, Any]], premise: str, correction: str) -> list[dict[str, Any]]:
    output = [dict(x) for x in records]
    changed = {premise}
    while True:
        new = {x["id"] for x in output if set(x.get("depends", [])) & changed} - changed
        if not new:
            break
        changed |= new
    for record in output:
        if record["id"] in changed:
            record["qualification"] = "REQUALIFY"
            record["correction"] = correction
    return output
