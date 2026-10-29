# SPDX-License-Identifier: Apache-2.0
"""Independent journal, expense, cash and investment audit; never runs a market policy."""

import collections
from decimal import Decimal, ROUND_CEILING
import json
import sys
from pathlib import Path


def audit(directory):
    root = Path(directory)
    rows = [json.loads(line) for line in (root / "worlds.jsonl").read_text().splitlines()]
    checks = []
    for n, row in enumerate(rows):
        journal = collections.defaultdict(int)
        seen = set()
        for entry in row["journal"]:
            assert entry["seq"] not in seen
            seen.add(entry["seq"])
            journal[entry["kind"]] += int(entry["amount"])
        revenue = journal["earned_revenue"] - journal["contra_revenue"]
        cash = journal["collections"] - journal["refund_payment"]
        restricted = journal["restricted_funding"] - journal["restricted_release"] - journal["restricted_refund"]
        cost = sum(
            int(
                (Decimal(str(x["quantity"])) * Decimal(str(x["rateUSD"])) * 1000000).to_integral_value(
                    rounding=ROUND_CEILING
                )
            )
            for x in row["costLedger"]
        )
        f = row["financial"]
        payment = min(cost, row["openingCash"] + cash)
        payable = max(0, cost - payment)
        money = row["openingCash"] + cash - payment
        available = max(0, money - payable - row["reserveMicroUSD"] - row["workingCapitalMicroUSD"])
        earned = max(0, min(available, cash - payment - row["reserveMicroUSD"] - row["workingCapitalMicroUSD"]))
        invariant = {
            "journalRevenue": row["exchange"]["revenue"] == revenue,
            "journalCash": row["exchange"]["cash"] == cash,
            "noRemainingEscrow": restricted == 0,
            "completeCost": row["expenseMicroUSD"] == cost,
            "profit": f["profit"] == revenue - cost,
            "cash": f["cash"] == money,
            "liabilities": f["payables"] == payable,
            "available": f["available"] == available,
            "funding": f["unrestrictedEarned"] == earned,
            "investment": row["investment"]["decision"] == ("CONTINUE" if earned >= 10_000_000 else "HOLD INVESTMENT"),
            "noPrematureConstruction": row["actualConstruction"] is False,
            "freeCompletedOptionWins": row["scenario"] != "free_completed_alternative"
            or all(not x["participates"] for x in row["offers"]),
        }
        checks.append({"world": n, "checks": invariant})
    result = {
        "scope": "Independent arithmetic/journal audit, not a market execution or calibration",
        "worlds": len(rows),
        "passed": all(all(x["checks"].values()) for x in checks),
        "results": checks,
    }
    with (root / "independent-audit.json").open("x") as f:
        json.dump(result, f, indent=2)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}))
    assert result["passed"]


if __name__ == "__main__":
    audit(sys.argv[1])
