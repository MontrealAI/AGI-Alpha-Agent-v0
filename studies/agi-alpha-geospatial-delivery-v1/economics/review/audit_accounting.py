# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("commercial_under_review", ROOT / "economics" / "run.py")
assert spec and spec.loader
engine = importlib.util.module_from_spec(spec)
spec.loader.exec_module(engine)
original = json.loads((ROOT / "configs" / "economics.json").read_text())


def tiny() -> dict:
    c = copy.deepcopy(original)
    c["market"].update(months=1, qualified_invitations_per_month=2, capacity_attempts_per_month=2,
                       quality=.5, perceived_quality=.95, human_quality=.98, inhouse_fraction=0,
                       common_outage_probability=0, opening_financing=1000)
    c["inference"]["components"] = []
    c["A"].update(tools_compute=100, source_access=0, packaging_storage=0, automated_support=0,
                  operational_recovery=0, retry_cost=20, warranty_cost=40, launch_configuration=100,
                  cost_per_qualified_invitation=0, monthly_business_overhead=0)
    return c


def draws(c: dict, default_first: bool = False) -> dict:
    d = engine.worlds(c, 1, 101)
    for key in ["success", "default", "retry", "defect", "inhouse"]:
        d[key].fill(.99)
    d["success"][0, 0, 0] = .01
    if default_first:
        d["default"][0, 0, 0] = .01
    d["outage"].fill(.99)
    d["value"].fill(3)
    d["friction"].fill(0)
    d["budget"].fill(2)
    return d


records = []
for arrangement, default, expected in [
    ("acceptance_invoice", False, {"attempts": 2, "accepted": 1, "revenue": 500, "collections": 500,
                                  "bad_debt": 0, "delivery_cost": 200, "payment_cost": 15.30,
                                  "operating_profit": 184.70, "closing_cash_before_B_C": 1184.70}),
    ("conditional_deposit", False, {"attempts": 2, "accepted": 1, "revenue": 500, "collections": 500,
                                   "deposit_receipts": 250, "refunded_deposits": 125, "bad_debt": 0,
                                   "delivery_cost": 200, "payment_cost": 19.65,
                                   "operating_profit": 180.35, "closing_cash_before_B_C": 1180.35}),
    ("acceptance_invoice", True, {"revenue": 500, "collections": 0, "bad_debt": 500,
                                 "payment_cost": 0, "operating_profit": -300,
                                 "closing_cash_before_B_C": 700}),
    ("conditional_deposit", True, {"revenue": 500, "collections": 125, "bad_debt": 375,
                                  "deposit_receipts": 250, "refunded_deposits": 125,
                                  "payment_cost": 8.10, "operating_profit": -183.10,
                                  "closing_cash_before_B_C": 816.90}),
]:
    c = tiny()
    result = engine.simulate(c, {"arrangement": arrangement, "price_ratio": .5}, draws(c, default), 1000)
    comparisons = {key: {"expected": value, "actual": float(result[key][0]),
                         "pass": bool(abs(result[key][0] - value) < 1e-8)} for key, value in expected.items()}
    assert all(item["pass"] for item in comparisons.values())
    records.append({"arrangement": arrangement, "default": default, "comparisons": comparisons})

c = tiny()
result = engine.simulate(c, {"arrangement": "conditional_deposit", "price_ratio": .5}, draws(c), 1000)
preacceptance_unrestricted_cash = 1000 - 100 - 200 - 19.65
endpoint_minimum = float(result["minimum_cash"][0])
assert abs(endpoint_minimum - preacceptance_unrestricted_cash) < 1e-8
deposit_minimum = {"preacceptance_unrestricted_cash": preacceptance_unrestricted_cash,
                   "reported_minimum_cash": endpoint_minimum,
                   "difference": endpoint_minimum - preacceptance_unrestricted_cash,
                   "interpretation": "Preacceptance free cash deducts expenses before earning any deposit."
                   " A positive difference means the reported field is a monthly endpoint rather than every-prefix minimum."}

c = tiny()
c["market"].update(opening_financing=100, capacity_attempts_per_month=2)
c["A"]["launch_configuration"] = 0
r = engine.simulate(c, {"arrangement": "conditional_deposit", "price_ratio": .5}, draws(c), 1000)
assert r["attempts"][0] == 0
records.append({"case": "refundable_deposits_do_not_finance_unfunded_delivery", "pass": True})

c = tiny()
c["market"].update(opening_financing=100000, qualified_invitations_per_month=96,
                    capacity_attempts_per_month=96, perceived_quality=.90, inhouse_fraction=.4)
d = engine.worlds(c, 250, 71717)
counts = [engine.simulate(c, {"arrangement": "acceptance_invoice", "price_ratio": ratio}, d, 1000)
          ["participating_buyers"] for ratio in [.25, .5, .8, 1.0]]
assert all(np.all(b <= a) for a, b in zip(counts, counts[1:]))
records.append({"case": "higher_price_cannot_increase_single_period_participation", "worlds": 250, "pass": True})

c = tiny()
c["market"].update(common_outage_probability=1, opening_financing=100000)
r = engine.simulate(c, {"arrangement": "conditional_deposit", "price_ratio": .5}, draws(c), 1000)
assert r["accepted"][0] == 0 and r["collections"][0] == 0 and r["operating_profit"][0] < 0
assert r["deposit_receipts"][0] == r["refunded_deposits"][0]
records.append({"case": "common_failure_refunds_every_deposit_and_keeps_costs", "pass": True})

c = copy.deepcopy(original)
c["market"]["qualified_invitations_per_month"] = 0
r = engine.simulate(c, {"arrangement": "acceptance_invoice", "price_ratio": .8}, engine.worlds(c, 1, 900))
assert r["collections"][0] == 0 and r["attempts"][0] == 0 and r["operating_profit"][0] == -4700
records.append({"case": "zero_demand_loses_launch_and_seven_months_overhead_then_stops", "pass": True,
                "operating_profit": float(r["operating_profit"][0]), "scope": "Immediate shutdown cancels subsequent overhead by model assumption."})

report = {"scope": "Independent hand-calculated event cases and counterfactual invariants, not full model validation.",
          "runner_sha256": hashlib.sha256((ROOT / "economics" / "run.py").read_bytes()).hexdigest(),
          "configuration_sha256": hashlib.sha256((ROOT / "configs" / "economics.json").read_bytes()).hexdigest(),
          "event_and_counterfactual_cases": records, "deposit_cash_reporting": deposit_minimum}
path = Path(__file__).with_name("accounting_audit.json")
path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
print(json.dumps({"cases": len(records), "status": "passed", "deposit_cash_reporting": deposit_minimum}))
