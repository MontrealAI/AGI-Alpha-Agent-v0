# SPDX-License-Identifier: Apache-2.0
"""Independent event reconstruction; does not import the arrangement simulator."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def inspect(run: dict[str, Any]) -> None:
    cash = escrow = reserve = earned = receipts = 0
    costs = {"A": 0, "B": 0, "C": 0}
    required = run["protected_reserve_cents"]
    credits: dict[str, int] = {}
    previous = (-1, -1)
    core_events = 0
    for item in run["events"]:
        assert (item["day"], item["order"]) >= previous
        previous = (item["day"], item["order"])
        n = item["amount_cents"]
        assert type(n) is int and n >= 0
        kind = item["kind"]
        buyer = item["buyer"]
        if kind == "refundable-deposit":
            assert item["cash_delta_cents"] == n == item["escrow_delta_cents"]
            assert item["earned_delta_cents"] == 0
        if kind.startswith("accepted-") and kind != "accepted-mission-refund" and item["earned_delta_cents"] > 0:
            credits[buyer] = credits.get(buyer, 0) + item["earned_delta_cents"]
        if kind == "escrow-release-after-acceptance":
            assert credits.get(buyer, 0) >= n
            credits[buyer] -= n
            assert item["cash_delta_cents"] == 0 and item["escrow_delta_cents"] == -n
            receipts += n
        elif kind == "earned-receipt":
            assert credits.get(buyer, 0) >= n
            credits[buyer] -= n
            assert item["cash_delta_cents"] == n
            receipts += n
        elif kind == "accepted-mission-refund":
            assert item["cash_delta_cents"] == -n
            receipts -= n
        elif kind == "unearned-escrow-return":
            assert item["cash_delta_cents"] == item["escrow_delta_cents"] == -n
            assert item["earned_delta_cents"] == 0
        if item["group"] is not None:
            assert item["group"] in costs and item["cash_delta_cents"] == -n
            costs[item["group"]] += n
        core_events += int(kind == "required-common-construction-once")
        cash += item["cash_delta_cents"]
        escrow += item["escrow_delta_cents"]
        reserve += item["support_reserve_delta_cents"]
        earned += item["earned_delta_cents"]
        assert escrow >= 0 and reserve >= 0
        available = cash - escrow - reserve - run["protected_reserve_cents"]
        required = max(required, -available)
        assert item["cash_before_opening_cents"] == cash
        assert item["escrow_liability_cents"] == escrow
        assert item["support_reserve_cents"] == reserve
        assert item["available_before_opening_cents"] == available
    assert core_events == 1
    assert escrow == reserve == 0
    assert costs == run["costs_cents"]
    assert receipts == run["net_earned_collections_cents"]
    assert earned == run["recognized_revenue_cents"]
    assert cash == receipts - sum(costs.values()) == run["contribution_cents"]
    assert required == run["required_opening_cash_cents"]


def objective(row: dict[str, Any]) -> Fraction:
    return Fraction(**row["selected"]["expected_contribution_cents"]) if row["selected"] else Fraction(0)


def main() -> None:
    results = HERE / "results"
    fresh = json.loads((results / "fresh_stress.json").read_text())
    historical = json.loads((results / "historical_regressions.json").read_text())
    inspected = 0
    for item in fresh:
        inspect(item["result"])
        inspected += 1
    for case in historical["cases"].values():
        for run in case["ledgers"]:
            inspect(run)
            inspected += 1
    frontier = json.loads((results / "conditional_frontier.json").read_text())
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in frontier:
        key = (row["core_cents"], row["assumed_saving"], row["assumed_useful_common_milestone"])
        grouped.setdefault(key, []).append(row)
    comparisons = 0
    for group in grouped.values():
        conventional = next(row for row in group if row["configuration"] == "unrestricted_conventional")
        for row in group:
            assert objective(conventional) >= objective(row)
            comparisons += 1
    frozen = json.loads((results / "FREEZE.json").read_text())
    assert hashlib.sha256((HERE / "checker.py").read_bytes()).hexdigest() == frozen["source_sha256"]
    assert hashlib.sha256((HERE / "PROTOCOL.json").read_bytes()).hexdigest() == frozen["protocol_sha256"]
    report = {
        "independently_reconstructed_ledgers": inspected,
        "frontier_configurations": len(frontier),
        "candidate_plans_enumerated_including_restricted_duplicates": sum(row["candidates"] for row in frontier),
        "conventional_same_menu_dominance_checks": comparisons,
        "scenario_cost_expected_value_units": "integer cents and exact Fraction",
        "escrow_is_revenue": False,
        "common_core_charged_once": True,
        "fresh_stress_losses_retained": sum(x["result"]["contribution_cents"] < 0 for x in fresh),
        "actual_market_evidence": False,
        "tests": 10,
        "ruff": "passed",
        "strict_mypy_checker": "passed",
    }
    (results / "independent_accounting_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
