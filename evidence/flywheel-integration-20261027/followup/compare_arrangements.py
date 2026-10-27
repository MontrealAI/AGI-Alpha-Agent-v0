# SPDX-License-Identifier: Apache-2.0
"""Use the existing arrangement calculator for five conditional constructions.

Run from the repository root with PYTHONPATH=. and explicit --source/--output.
No ledger, authority, customer acceptance or market observation is created.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from alpha_factory_v1.core.runtime.successor.flywheel_arrangements import Arrangement, assess_arrangement

M = 1_000_000
AUTOMATED = {"model", "tools", "execution", "verification", "retry-correction", "packaging"}
METHODS = {
    "existing-individual-human": "Individual human implementation of the same scoped packet",
    "technical-change-alone": "Competent conventional automated construction, without extra coordination benefit",
    "commercial-coordination-alone": "Human pathway coordinated commercially, without an unmeasured pooling saving",
    "complete-joint": "Existing automated packet plus commercial arrangement, without an unmeasured coordination premium",
    "equally-capable-conventional-shared": "Same inputs, assets, automation, terms and obligations as the joint arrangement",
}
MEASURES = (
    "expected_cash_contribution_micro_usd",
    "expected_economic_contribution_micro_usd",
    "required_prefunding_micro_usd",
    "liquidity_feasible",
    "decision",
)


def compare(source: Path) -> dict:
    body = source.read_bytes()
    economics = json.loads(body)["economics"]
    rows = []
    for policy in economics["policies"]:
        reference = economics["human_development_reference"][policy["cost_case"]]
        human_cost = reference["hours"] * reference["loaded_hourly_usd"]
        for method, meaning in METHODS.items():
            terms = copy.deepcopy(policy["arrangement"])
            terms["arrangement_id"] += "/" + method
            human = method in {"existing-individual-human", "commercial-coordination-alone"}
            if human:
                for scenario in terms["scenarios"]:
                    revised = []
                    for cost in scenario["costs"]:
                        component = cost["activity_id"].split("-", 1)[-1]
                        if cost["bucket"] == "A" and component in AUTOMATED:
                            if component != "model":
                                continue
                            cost["cash_micro_usd"] = human_cost * M
                            cost["basis"] = (
                                f"Unquoted human pathway: {reference['hours']} hours at "
                                f"USD{reference['loaded_hourly_usd']}/hour for source interpretation, finite "
                                "implementation, adverse checks and packaging; replaces automation components"
                            )
                        revised.append(cost)
                    scenario["costs"] = revised
            assessment = assess_arrangement(Arrangement.model_validate(terms), 10_000 * M, 500 * M)
            if not human:
                assert all(assessment[key] == policy["assessment"][key] for key in MEASURES)
            unit = (
                human_cost
                + sum(value for name, value in policy["components_usd_per_attempt"].items() if name not in AUTOMATED)
                if human
                else sum(policy["components_usd_per_attempt"].values())
            )
            rows.append(
                {
                    "method": method,
                    "meaning": meaning,
                    "cost_case": policy["cost_case"],
                    "price_usd": policy["price_usd"],
                    "assumed_participants": policy["assumed_participants"],
                    "human_pathway_hours": reference["hours"] if human else 0,
                    "human_pathway_loaded_usd_per_hour": reference["loaded_hourly_usd"] if human else None,
                    "modeled_unit_cost_usd": unit,
                    "assessment": {key: value for key, value in assessment.items() if key != "branches"},
                }
            )
    for case in ("low", "base", "high"):
        for price in (400, 800, 1000, 1200):
            matched = [row for row in rows if row["cost_case"] == case and row["price_usd"] == price]
            joint = next(row for row in matched if row["method"] == "complete-joint")
            ordinary = next(row for row in matched if row["method"] == "equally-capable-conventional-shared")
            assert all(joint["assessment"][key] == ordinary["assessment"][key] for key in MEASURES)
    return {
        "schema": "agi-alpha.conditional-five-arrangement-comparison.v1",
        "source_path": source.as_posix(),
        "source_sha256": hashlib.sha256(body).hexdigest(),
        "calculator_source_sha256": hashlib.sha256(
            Path("alpha_factory_v1/core/runtime/successor/flywheel_arrangements.py").read_bytes()
        ).hexdigest(),
        "scope": "Unvalidated future offering scenarios; no demonstrated technical or commercial superiority",
        "requirements": "Same finite permission-fact packet, declared four outcomes, price family and obligations",
        "demand": "Same hypothetical values and participation; no observed willingness to pay or buyer acceptance",
        "coordination": "No saving credited without evidence; an ordinary shared arrangement is equally capable",
        "human_reference": economics["human_development_reference"],
        "cost_boundary": {
            "automatic": "Native model/tools/execution/checking/correction/packaging forecast; no extra manual-review fee",
            "human": "Replace those automation components with the explicit human estimate; never add both",
            "all": "Retain residual coordination, support, attributable business overhead, failed attempts, defaults and refunds",
            "B": "Retain the single USD5 no-retention screen once per arrangement",
            "C": "Not commissioned or charged here; optional source research estimates remain separate",
            "cash": "Calculator retains USD10000 initial cash, USD500 reserves and time-ordered prefunding; neither is profit",
        },
        "pricing": "Four value-based price hypotheses with declining assumed participation; a finite optimum is not demand",
        "actual_customer_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "actual_profit_usd": None,
        "retained_alpha": "No measured reusable saving; ordinary identical-content construction ties",
        "rows": rows,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("preserve the previous comparison; select a new output")
    args.output.write_text(json.dumps(compare(args.source), indent=2) + "\n")
