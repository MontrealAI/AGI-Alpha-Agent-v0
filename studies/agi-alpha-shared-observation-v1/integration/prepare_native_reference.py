# SPDX-License-Identifier: Apache-2.0
"""Reconcile one explicit successful modeled service branch with the native ledger."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from bundle import regular_bytes, sha256
from native_replay import run as replay

CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]


def micro(value: Any) -> int:
    """Use a declared micro-USD rounding boundary for this monetary projection."""
    return int((Decimal(str(value)) * 1_000_000).to_integral_value())


def run(assumptions: Path, events: Path, output: Path) -> dict[str, Any]:
    """Map net service economics; leave refundable sensor custody in the event ledger."""
    if output.exists():
        raise ValueError("new native projection output required")
    raw_assumptions, raw_events = regular_bytes(assumptions), regular_bytes(events)
    parameters, tree = json.loads(raw_assumptions), json.loads(raw_events)
    cases = [
        (index, case)
        for index, case in enumerate(tree["paths"])
        if case["available_operators"]
        and all(case["available_operators"])
        and not case["common_failure"]
        and case["statuses"]
        and all(status == "paid" for status in case["statuses"])
    ]
    if len(cases) != 1:
        raise ValueError("exactly one all-available all-paid illustration required")
    index, case = cases[0]
    source = {
        "assumptions_sha256": sha256(raw_assumptions),
        "event_tree_sha256": sha256(raw_events),
        "path_index": index,
    }

    def evidence(label: str) -> str:
        return sha256(json.dumps({**source, "event": label}, sort_keys=True).encode())

    commands: list[dict[str, Any]] = []
    mission = "modeled-origin-service"
    for action, value in [("capital", parameters["seed_capital"]), ("invoice", case["earned_gross_service_revenue"])]:
        commands.append(
            {
                "action": action,
                "record": {
                    "record_id": "modeled-" + action,
                    "mission_id": mission,
                    "amount_micro_usd": micro(value),
                    "evidence_digest": evidence(action),
                },
            }
        )
    workload = parameters["modeled_Astra_workload"]
    tariff = parameters["tariffs"]["Astra"]
    model_cost = (
        Decimal(str(workload["uncached_input_tokens"])) * Decimal(str(tariff["input_per_million"]))
        + Decimal(str(workload["output_tokens"])) * Decimal(str(tariff["output_per_million"]))
    ) / 1_000_000
    total_A = micro(case["A_cash_cost"])
    if micro(model_cost) > total_A:
        raise ValueError("included model estimate exceeds total assumed delivery cost")
    for bucket, scope in [("A", mission), ("B", "modeled-retention-hold"), ("C", "modeled-gym-hold")]:
        for category in CATEGORIES:
            amount = 0
            if bucket == "A" and category == "model":
                amount = micro(model_cost)
            if bucket == "A" and category == "overhead":
                amount = total_A - micro(model_cost)
            note = (
                "MODELED reference branch. Aggregate non-model A cost is allocated to overhead by convention; "
                "other category zeros mean no additional allocation, not absent resource use. "
                "B/C are held investments with zero incremental modeled spend. No observed invoice."
            )
            commands.append(
                {
                    "action": "charge",
                    "record": {
                        "activity_id": "modeled-" + bucket + "-" + category,
                        "mission_id": scope,
                        "bucket": bucket,
                        "category": category,
                        "accrued_micro_usd": amount,
                        "paid_micro_usd": amount,
                        "basis": "attested",
                        "evidence_digest": evidence(bucket + category),
                        "note": note,
                    },
                }
            )
        commands.append(
            {
                "action": {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket],
                "record": {
                    "mission_id": scope,
                    "categories": CATEGORIES,
                    "evidence_digest": evidence("seal-" + bucket),
                },
            }
        )
    commands.append(
        {
            "action": "collection",
            "record": {
                "record_id": "modeled-service-collection",
                "mission_id": mission,
                "amount_micro_usd": micro(case["collected_service_revenue"]),
                "evidence_digest": evidence("collection"),
            },
        }
    )
    commands.append({"action": "reserve", "record": micro(parameters["provider_reserve"])})
    output.mkdir(parents=True)
    commands_path = output / "commands.json"
    commands_path.write_text(json.dumps({"source": source, "commands": commands}, indent=2) + "\n")
    native = replay(commands_path, output / "native.json")
    actual = native["replay"]["report"]
    expected = {
        "costs": {"A": total_A, "B": 0, "C": 0},
        "collected_revenue": micro(case["collected_service_revenue"]),
        "complete_cost_profit": micro(case["operating_profit_before_BC"]),
        "cash": micro(case["end_cash"]),
        "obligations": 0,
        "reserve": micro(parameters["provider_reserve"]),
        "available_funds": micro(case["end_available_funds"]),
    }
    checks = [{"field": field, "passed": actual[field] == value} for field, value in expected.items()]
    checks.append(
        {
            "field": "separate-custody-terminal-cancellation",
            "passed": micro(case["pass_through_collected"]) == micro(case["sensor_paid"])
            and micro(case["pass_through_refunded"]) == 0,
        }
    )
    record = {
        "schema": "shared-observation-native-reference-reconciliation/v1",
        "evidence_type": "EXECUTED_NATIVE_ACCOUNTING_WITH_MODELED_SERVICE_AMOUNTS",
        "source": source,
        "selected_branch": case,
        "selection": "Illustrative all-available all-paid branch; not an expected result or observed sale.",
        "expected_native_micro_usd": expected,
        "native_report": actual,
        "checks": checks,
        "passed": sum(check["passed"] for check in checks),
        "total": len(checks),
        "sensor_pass_through_in_native_revenue": False,
        "custody_boundary": "Interim agency deposits, liabilities and refunds are checked by the separate event ledger.",
        "completeness_boundary": "Native completeness closes declared modeled categories, not an observed complete bill.",
        "actual_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "actual_complete_profit_usd": None,
        "production_authority": False,
    }
    (output / "reconciliation.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assumptions", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.assumptions, args.events, args.out)
    print(json.dumps({key: result[key] for key in ["passed", "total", "expected_native_micro_usd"]}))
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
