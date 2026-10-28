# SPDX-License-Identifier: Apache-2.0
"""Reconstruct enterprise accounts and contract closure from raw journal events."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

ASSETS = {"cash", "restricted_cash", "receivables"}
LIABILITIES = {"customer_deposits", "refund_payable", "support_payable", "debt"}
STARTUP = {"research", "failed_discovery", "development", "independent_validation", "documentation",
           "startup_inference", "startup_compute", "startup_tools"}
EXCLUDED_OPERATING = STARTUP | {"financing_fee", "financing_interest", "successor_experiment"}
COLLECTION_EVENTS = {"restricted_deposit_collection", "final_collection", "late_collection"}
REFUND_EVENTS = {"failed_delivery_refund", "warranty_refund_payment"}


def reconcile(world: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Check identities, lifecycle semantics and funding after every raw event."""
    balances: dict[str, int] = collections.defaultdict(int)
    contract_events: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    event_counts: dict[str, int] = collections.defaultdict(int)
    gross_collections, refunds, peak_funding = 0, 0, 0
    minimum_usable: int | None = None
    previous_tick = -1
    for index, entry in enumerate(world["journal"]):
        amount = entry["amount_cents"]
        assert type(amount) is int and amount >= 0, f"Invalid amount at event {index}"
        assert entry["world_id"] == world["world_id"]
        assert type(entry["tick"]) is int and entry["tick"] >= previous_tick, "Nonmonotonic event time"
        previous_tick = entry["tick"]
        event = entry["event_type"]
        event_counts[event] += 1
        if amount:
            debit, credit = entry["debit_account"], entry["credit_account"]
            assert debit and credit and debit != credit
            balances[debit] += amount
            balances[credit] -= amount
        assert sum(balances.values()) == 0, "Unbalanced reconstructed trial balance"
        assert all(balances[key] >= 0 for key in ASSETS), f"Negative asset at event {index}: {event}"
        assert all(balances[key] <= 0 for key in LIABILITIES), f"Negative liability at event {index}: {event}"
        assert balances["restricted_cash"] >= -balances["customer_deposits"], "Customer deposit is not segregated"
        assert -balances["debt"] <= config["credit_limit_cents"], "Finite credit limit exceeded"
        usable = balances["cash"] + balances["support_payable"] + balances["refund_payable"]
        minimum_usable = usable if minimum_usable is None else min(minimum_usable, usable)
        peak_funding = max(peak_funding, -balances["equity"] - balances["debt"] - balances["cash"])
        if event in COLLECTION_EVENTS:
            gross_collections += amount
        if event in REFUND_EVENTS:
            refunds += amount
        if entry["contract_id"] is not None:
            contract_events[entry["contract_id"]].append(entry)
    assert event_counts["opening_equity"] == 1
    assert -balances["equity"] == config["opening_equity_cents"]
    for category, effort, rate in config["startup"]:
        assert event_counts[category] == 1, f"Startup cost duplicated or omitted: {category}"
        assert balances[f"expense:{category}"] == int(round(effort * rate * 100))
    for category in ("startup_inference", "startup_compute", "startup_tools"):
        assert event_counts[category] == 1
        assert balances[f"expense:{category}"] == config[f"{category}_cents"]
    assert event_counts["enterprise_exit"] == 1
    assert all(balances[key] == 0 for key in LIABILITIES | {"restricted_cash", "receivables"}), "Unclosed balances"
    expected_balances = {key: value for key, value in balances.items() if value}
    actual_balances = {key: value for key, value in world["final_account_balances"].items() if value}
    assert expected_balances == actual_balances, "Reported final accounts differ from raw journal"
    cost = sum(value for key, value in balances.items() if key.startswith("expense:"))
    profit = -balances["revenue"] - cost
    operating = -balances["revenue"] - sum(value for key, value in balances.items()
                                            if key.startswith("expense:") and key[8:] not in EXCLUDED_OPERATING)
    expected = {"profit_cents": profit, "operating_contribution_cents": operating,
                "recognized_revenue_cents": -balances["revenue"], "collections_cents": gross_collections,
                "refunds_cents": refunds, "net_collections_cents": gross_collections - refunds,
                "restricted_cash_cents": balances["restricted_cash"], "usable_cash_cents": balances["cash"],
                "total_project_cost_cents": cost, "cash_requirement_cents": peak_funding,
                "minimum_usable_cash_cents": minimum_usable}
    for key, value in expected.items():
        assert world[key] == value, f"Incorrect aggregate: {key}"
    assert balances["cash"] - config["opening_equity_cents"] == profit
    contracts = world["contracts"]
    assert len(contracts) == len({contract["id"] for contract in contracts})
    assert world["counts"]["signed"] == len(contracts) == event_counts["contract"]
    assert world["counts"]["accepted"] == sum(bool(c["accepted"]) for c in contracts)
    assert world["counts"]["failed"] == event_counts["failed_delivery_refund"]
    assert world["counts"]["corrected"] == event_counts["correction_required"]
    assert world["counts"]["renewals"] == sum(bool(c["buyer"]["renewal"]) for c in contracts)
    total_contract_revenue = 0
    for contract in contracts:
        entries = contract_events[contract["id"]]
        counts = collections.Counter(entry["event_type"] for entry in entries)
        lifecycle = collections.Counter(entry["event_type"] for entry in entries if entry["amount_cents"] == 0)
        assert counts["contract"] == counts["restricted_deposit_collection"] == lifecycle["delivery"] == 1
        assert sum(entry["debit_account"] == "expense:delivery" for entry in entries) == 1
        assert counts["contract_closed"] == 1 and contract["closed"]
        collected = sum(e["amount_cents"] for e in entries if e["event_type"] in COLLECTION_EVENTS)
        returned = sum(e["amount_cents"] for e in entries if e["event_type"] in REFUND_EVENTS)
        assert collected == contract["collected"] and returned == contract["refunded"]
        assert returned <= collected, "Refund exceeds collected customer funds"
        if contract["accepted"]:
            assert counts["acceptance"] == counts["payment_choice"] == counts["support_closed"] == 1
            assert counts["recognize_deposit"] == counts["release_restricted_deposit"] == counts["invoice_balance"] == 1
            assert counts["final_collection"] + counts["late_collection"] + counts["bad_debt"] == 1
            assert contract["collection_closed"]
            total_contract_revenue += contract["price"]
        else:
            assert counts["failed_delivery_refund"] == 1 and returned == contract["deposit"]
            assert counts["acceptance"] == 0
    assert total_contract_revenue == -balances["revenue"]
    return {"status": "pass", "world_id": world["world_id"], "journal_events": len(world["journal"]),
            "contracts_checked": len(contracts), "profit_cents": profit, "cash_requirement_cents": peak_funding,
            "closed_terminal_balances": True, "per_event_nonnegative_cash": True,
            "all_event_types": sorted(event_counts)}


def main() -> None:
    """Reconcile one world or every saved world in a completed simulation."""
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    paths = sorted((args.input / "worlds").glob("*.json")) if args.input.is_dir() else [args.input]
    if not paths:
        raise ValueError("No saved worlds to reconcile")
    results = []
    for path in paths:
        result = reconcile(json.loads(path.read_text()), config)
        result["source_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        result["path"] = str(path)
        results.append(result)
    summary = {"schema": "possibility-engine-independent-accounting-v1", "status": "pass", "worlds": len(results),
               "journal_events": sum(item["journal_events"] for item in results),
               "contracts_checked": sum(item["contracts_checked"] for item in results),
               "all_event_types": sorted(set().union(*(set(item["all_event_types"]) for item in results))),
               "results": results}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key not in ("results", "all_event_types")}))


if __name__ == "__main__":
    main()
