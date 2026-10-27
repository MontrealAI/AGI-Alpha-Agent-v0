# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import importlib.util
import statistics
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from .run import HERE, load, save, source_bindings


def parent_module(root: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("reserve_parent_economics", root / "src/economics.py")
    if spec is None or spec.loader is None:
        raise ValueError("missing parent economic implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compact(result: dict[str, Any]) -> dict[str, Any]:
    final = result["settled"]
    revenue, cost, profit = (Decimal(str(final[key])) for key in ("revenue", "total_cost", "operating_profit"))
    if abs(revenue - cost - profit) > Decimal("0.000001"):
        raise ValueError("independent Decimal complete-profit reconciliation failed")
    if final["available_funds"] > final["cash"] + 0.000001:
        raise ValueError("obligations or reserves incorrectly increase available cash")
    if final["counts"]["accepted"] > final["counts"]["booked"]:
        raise ValueError("acceptance exceeds booked work")
    return {
        "seed": result["seed"],
        "revenue": float(revenue),
        "cost": float(cost),
        "profit": float(profit),
        "accepted": final["counts"]["accepted"],
        "booked": final["counts"]["booked"],
        "cash": final["cash"],
        "available_funds": final["available_funds"],
        "costs": final["costs"],
        "unearned_deposits": final["unearned_deposits"],
        "receivables": final["receivables"],
        "accounts_payable": final["accounts_payable"],
        "support_payable": final["support_payable"],
        "processing_payable": final["processing_payable"],
        "reserve": final["operating_reserve"],
    }


def describe(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(row["profit"] for row in rows)
    return {
        "worlds": len(rows),
        "mean_profit": statistics.mean(ordered),
        "p05_profit": ordered[int(0.05 * (len(rows) - 1))],
        "p95_profit": ordered[int(0.95 * (len(rows) - 1))],
        "profitable_worlds": sum(value > 0 for value in ordered),
        "mean_accepted": statistics.mean(row["accepted"] for row in rows),
        "mean_cash_gain_excluding_seed": statistics.mean(row["cash"] - 60000 for row in rows),
        "minimum_available_funds": min(row["available_funds"] for row in rows),
    }


def run(root: Path, output: Path) -> dict[str, Any]:
    if source_bindings(root) != load(HERE / "FREEZE.json")["bindings"]:
        raise ValueError("economic or technical source changed after freeze")
    if output.exists():
        raise ValueError("preserve the previous economic attempt; choose a new output")
    parent = parent_module(root)
    config = load(root / "config/commercial_protocol.json")
    original_freeze = load(root / "results/economics_freeze.json")
    protocol = load(HERE / "protocol.json")["commercial"]
    policies = {label: parent.Policy(**terms) for label, terms in original_freeze["selected_by_family"].items()}
    policies["no_launch"] = parent.Policy("none")
    worlds = [parent.world(config, protocol["fresh_seed_start"] + index) for index in range(protocol["fresh_worlds"])]
    rows = {
        name: [compact(parent.simulate(config, world, policy)) for world in worlds] for name, policy in policies.items()
    }
    sensitivities = []
    for refusal in protocol["refusal_probability_sensitivity"]:
        for extra in protocol["hypothetical_automatic_preflight_cost_per_booked_usd"]:
            for name, policy in policies.items():
                if name == "no_launch":
                    continue
                values = [
                    compact(
                        parent.simulate(
                            config,
                            world,
                            policy,
                            scenario={
                                "acceptance_probability": world["success_probability"] * (1 - refusal),
                                "extra_per_job": extra,
                            },
                        )
                    )
                    for world in worlds
                ]
                sensitivities.append(
                    {
                        "policy": name,
                        "refusal_probability_assumed": refusal,
                        "automatic_cost_usd_assumed": extra,
                        **describe(values),
                    }
                )
    result = {
        "evidence": "Fresh synthetic worlds under the same offering, same parent commercial assumptions and policies.",
        "seed_start": protocol["fresh_seed_start"],
        "summaries": {name: describe(values) for name, values in rows.items()},
        "policies": {
            name: {"family": policy.family, "fee": policy.fee, "deposit": policy.deposit}
            for name, policy in policies.items()
        },
        "sensitivity": sensitivities,
        "refusal_model": "Conservative post-booking nonacceptance through the parent's correction/refund policy; no claim about real refusal frequency.",
        "accounting": "Parent startup/delivery/acquisition/business/credit/failure/cash/reserve model unchanged; no repeated startup or learning charge.",
        "actual_complete_sprint_cost_usd": None,
        "actual_customer_collections_usd": 0,
        "privacy_review_allowance": "Already included in original startup. No arbitrary recurring manual surcharge added.",
        "ordinary_library_incremental_gain": 0,
        "additional_retention": "not admitted",
    }
    save(output / "worlds.json", rows)
    save(output / "SUMMARY.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--research-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.research_root, args.output)
    print({"summaries": result["summaries"], "sensitivity_policies": len(result["sensitivity"])})


if __name__ == "__main__":
    main()
