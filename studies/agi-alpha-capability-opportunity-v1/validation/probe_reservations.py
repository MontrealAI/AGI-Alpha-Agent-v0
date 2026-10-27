# SPDX-License-Identifier: Apache-2.0
"""Demonstrate that unobserved early stopping cannot determine job admission."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any

STUDY = Path(__file__).resolve().parent.parent


class AuditedIndex(dict[tuple[str, str, int], dict[str, Any]]):
    """Record whether a simulator queried a future task's outcome."""

    def __init__(self, rows: dict[tuple[str, str, int], dict[str, Any]]) -> None:
        super().__init__(rows)
        self.reads: list[tuple[str, str, int]] = []

    def get(self, key: Any, default: Any = None) -> Any:
        self.reads.append(key)
        return super().get(key, default)


def probe(source: Path) -> dict[str, Any]:
    """Execute cash/capacity boundary examples against a selected immutable source."""
    spec = importlib.util.spec_from_file_location("reviewed_economics", source)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load reviewed source")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scenario = json.loads((STUDY / "economics/scenario.json").read_text())
    offerings = {o["id"]: o for o in json.loads((STUDY / "economics/offerings.json").read_text())["offerings"]}
    route = {
        "method": "beta_direct",
        "budget": 96,
        "price": 100.0,
        "quality_forecast": 1.0,
        "expected_profit_per_arrival": 80.0,
    }
    policy = {
        "name": "review-fixture",
        "setup_calls": 0,
        "origin_calls_A": 0,
        "fixed_B": 0,
        "fixed_C": 0,
        "retained_versions": [],
        "base_methods": ["beta_direct"],
        "routes": {
            name: {"origin": copy.deepcopy(route) if name == "verified_design" else None, "peer": None}
            for name in offerings
        },
    }
    learning = {"events": [{"category": "A", "accepted": False}]}
    events = [
        {
            "event_id": 0,
            "day": 1,
            "task_id": "future-task",
            "offering": "verified_design",
            "agent": 0,
            "buyer_u": 0.9,
            "transfer_u": 0.9,
            "validator_bad": False,
        }
    ]
    row = {
        "task_id": "future-task",
        "method": "beta_direct",
        "budget": 96,
        "oracle_calls": 2,
        "design_accepted": True,
        "observed_seconds": 0.0,
    }
    results = []
    for name in ["insufficient_cash", "insufficient_capacity"]:
        config = copy.deepcopy(scenario)
        config.update(
            horizon_days=1,
            agents=1,
            warranty_reserve_fraction=0.0,
            collection_delay_days=100,
            starting_cash=2019.5 if name == "insufficient_cash" else 12000.0,
            agent_hours_per_day=8 if name == "insufficient_cash" else 10 * 30 / 3600,
        )
        index = AuditedIndex({("future-task", "beta_direct", 96): row})
        report, ledger = module.simulate(policy, events, index, offerings, config, learning, True)
        event = next(r for r in ledger if r.get("event_id") == 0)
        expected = "preserve_cash" if name == "insufficient_cash" else "capacity_decline"
        results.append(
            {
                "name": name,
                "expected_decision": expected,
                "actual_decision": event["decision"],
                "future_outcome_reads": index.reads,
                "passed": event["decision"] == expected and not index.reads,
                "realized_queries_if_executed": 2,
                "declared_queries_before_execution": 96,
                "cash_before_admission": config["starting_cash"] - module.job_cost(0, "beta_adaptive", config),
                "reserve_floor": config["reserve_floor"],
                "cash_identity_residual": report["cash_identity_residual"],
                "query_calls": report["query_calls"],
                "query_capacity": report["query_capacity"],
                "ledger": ledger,
            }
        )
    return {
        "schema": "nonanticipative-admission-probe/v1",
        "source_path": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "controls": results,
        "all_passed": all(r["passed"] for r in results),
        "scope": "Wholly artificial boundary fixtures; no claimed enterprise result or measured revenue.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=STUDY / "economics/run_economics.py")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = probe(args.source)
    if args.out.exists():
        raise FileExistsError("Preserve the prior probe result")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "all_passed": result["all_passed"],
                "controls": [
                    {key: r[key] for key in ["name", "actual_decision", "future_outcome_reads", "passed"]}
                    for r in result["controls"]
                ],
            }
        )
    )
