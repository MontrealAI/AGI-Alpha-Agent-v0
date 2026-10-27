# SPDX-License-Identifier: Apache-2.0
"""Adversarial information-boundary and accounting checks on the replay."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import run_economics as econ


class ProtectedOutcomes(dict):
    """Refuse any attempt to inspect protected outcomes before commitment."""

    def get(self, key: Any, default: Any = None) -> Any:
        raise AssertionError("Protected outcome was read despite an unaffordable reservation")


def run() -> dict[str, Any]:
    config = econ.read_json(econ.HERE / "scenario.json")
    offerings = {o["id"]: o for o in econ.read_json(econ.HERE / "offerings.json")["offerings"]}
    route = {"method": "beta_direct", "budget": 96, "price": 200.0,
             "quality_forecast": 1.0, "expected_profit_per_arrival": 100.0}
    policy = {"name": "boundary-fixture", "setup_calls": 0, "origin_calls_A": 0,
              "fixed_B": 0, "fixed_C": 0, "retained_versions": [], "base_methods": ["beta_direct"],
              "routes": {k: {"origin": route, "peer": route} for k in offerings}}
    learning = {"events": [{"category": "A", "accepted": False}]}
    event = {"event_id": 0, "day": 1, "task_id": "protected", "offering": "verified_design",
             "agent": 0, "buyer_u": .9, "transfer_u": .5, "validator_bad": False}
    checks = []
    low_capacity = copy.deepcopy(config)
    low_capacity.update(agent_hours_per_day=50 * config["query_seconds_assumed"] / (3 * 3600))
    result, _ = econ.simulate(policy, [event], ProtectedOutcomes(), offerings, low_capacity, learning, True)
    assert result["capacity_rejections"] == 1 and result["jobs_executed"] == 0
    checks.append({"name": "capacity-reservation-before-protected-row-access", "passed": True})
    low_cash = copy.deepcopy(config)
    low_cash.update(starting_cash=100.0, reserve_floor=0.0, query_cost_assumed=1.0)
    result, _ = econ.simulate(policy, [event], ProtectedOutcomes(), offerings, low_cash, learning, True)
    assert result["cash_rejections"] == 1 and result["jobs_executed"] == 0
    checks.append({"name": "cash-reservation-before-protected-row-access", "passed": True})
    row = {"task_id": "protected", "method": "beta_direct", "budget": 96,
           "oracle_calls": 1, "observed_seconds": .001, "design_accepted": False}
    correlated = copy.deepcopy(config)
    correlated.update(starting_cash=150.0, reserve_floor=0.0, warranty_reserve_fraction=1.0)
    events = [{**event, "validator_bad": True}, {**event, "event_id": 1, "validator_bad": True}]
    result, ledger = econ.simulate(policy, events, {("protected", "beta_direct", 96): row},
                                   offerings, correlated, learning, True)
    decisions = [r["decision"] for r in ledger if "decision" in r]
    assert decisions == ["deliver", "preserve_cash"]
    assert result["false_acceptances"] == 1 and result["true_accepted_jobs"] == 0
    assert result["simulated_revenue"] == 0 and result["refunds_paid"] == 200
    equity = result["cash"] + result["receivables"] - result["obligations"] - result["seed_capital"]
    assert abs(equity - result["profit"]) < 1e-7
    checks.append({"name": "correlated-validator-failure-affects-reserve-and-refund", "passed": True})
    checks.append({"name": "cash-balance-and-accrual-profit-reconcile", "passed": True})
    first = next(r for r in ledger if r.get("decision") == "deliver")
    assert first["reserved_query_calls"] == 96 and first["query_calls"] == 1
    assert first["released_unused_query_calls"] == 95
    checks.append({"name": "settle-actual-and-release-unused-reservation", "passed": True})
    result = {"schema": "economics-boundary-verification-v1", "checks": checks,
              "all_passed": all(c["passed"] for c in checks),
              "fixture_status": "artificial adverse tests, not study outcomes",
              "execution_code_sha256": econ.digest(Path(econ.__file__))}
    econ.write_json(econ.HERE / "results" / "verification.json", result)
    return result


if __name__ == "__main__":
    print(json.dumps(run()))
