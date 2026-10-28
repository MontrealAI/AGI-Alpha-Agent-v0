# SPDX-License-Identifier: Apache-2.0
"""Derive readable operating metrics from saved fresh-confirmation records."""

from __future__ import annotations

import collections
import hashlib
import json
import statistics
from pathlib import Path
from typing import Any


def main() -> None:
    root = Path(__file__).resolve().parent / "confirmation"
    summary = json.loads((root / "summary.json").read_text())
    manifest = json.loads((root / "world_manifest.json").read_text())
    for entry in manifest:
        actual = hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            raise ValueError(f"Confirmation world changed: {entry['path']}")
    report: dict[str, Any] = {}
    for name in summary:
        paths = sorted((root / "worlds").glob(name + "-*.json"))
        if not paths:
            continue
        worlds = [json.loads(path.read_text()) for path in paths]

        def average_dictionary(key: str) -> dict[str, float]:
            keys = set().union(*(world[key].keys() for world in worlds))
            return {
                item: statistics.mean(world[key].get(item, 0) for world in worlds)
                for item in sorted(keys)
            }

        categories = sorted(
            {
                key
                for world in worlds
                for key in world["final_account_balances"]
                if key.startswith("expense:")
            }
        )
        expenses = {
            key.removeprefix("expense:"): statistics.mean(
                world["final_account_balances"].get(key, 0) for world in worlds
            )
            / 100
            for key in categories
        }
        events = collections.Counter(
            event["event_type"] for world in worlds for event in world["journal"]
        )
        terminal_accounts = (
            "customer_deposits", "refund_payable", "support_payable", "debt",
            "restricted_cash", "receivables",
        )
        report[name] = {
            "worlds": len(worlds),
            "mean_counts": average_dictionary("counts"),
            "mean_choices": average_dictionary("choices"),
            "mean_hours": average_dictionary("hours"),
            "mean_expense_usd": expenses,
            "mean_refunds_usd": statistics.mean(world["refunds_cents"] for world in worlds) / 100,
            "mean_net_collections_usd": statistics.mean(world["net_collections_cents"] for world in worlds) / 100,
            "mean_final_usable_cash_usd": statistics.mean(world["usable_cash_cents"] for world in worlds) / 100,
            "minimum_usable_cash_usd": min(world["minimum_usable_cash_cents"] for world in worlds) / 100,
            "event_counts": dict(events),
            "journal_events": sum(len(world["journal"]) for world in worlds),
            "maximum_contracts": max(len(world["contracts"]) for world in worlds),
            "all_terminal_liabilities_zero": all(
                all(world["final_account_balances"].get(key, 0) == 0 for key in terminal_accounts)
                for world in worlds
            ),
            "all_contracts_closed": all(
                contract["closed"] for world in worlds for contract in world["contracts"]
            ),
        }
    (root / "reporting_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"scenarios": len(report), "journal_events": sum(row["journal_events"] for row in report.values())}))


if __name__ == "__main__":
    main()
