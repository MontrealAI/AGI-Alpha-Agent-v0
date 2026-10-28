# SPDX-License-Identifier: Apache-2.0
"""Force lifecycle branches as accounting controls, never as market trajectories."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from check_accounts import reconcile


def main() -> None:
    """Execute labeled branch controls and prove that the checker rejects corruption."""
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("controlled_economics_model", args.study / "economics/model.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load economics model")
    model = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = model
    spec.loader.exec_module(model)
    original_config = copy.deepcopy(model.CONFIG)
    original_functions = {name: getattr(model, name) for name in ("buyer", "choice", "poisson", "uniform")}
    policy = json.loads((args.study / "economics/selected_policy.json").read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    summaries, worlds = [], {}
    labels = ("accepted_renewal_credit", "failed_delivery_refund", "corrected_warranty_refund",
              "strategic_default_writeoff", "strategic_default_recovered", "capacity_supplier_shock")
    try:
        for label in labels:
            config = copy.deepcopy(original_config)
            if label == "accepted_renewal_credit":
                config["opening_equity_cents"] = 3500000
            model.CONFIG = config

            def controlled_buyer(seed: int, key: str, scenario: dict[str, Any], renewal: bool = False) -> dict[str, Any]:
                return {"key": key, "value": 8000000, "budget": 3000000, "internal_capacity": False,
                        "urgency": 0.25, "future_relationship_value": 0 if "default" in label else 2000000,
                        "bundle_customer": False, "renewal": renewal,
                        "free_quality": scenario.get("free_quality", 0.82),
                        "free_hours": scenario.get("free_hours", 16), "free_delay": scenario.get("free_delay", 2)}

            def controlled_uniform(seed: int, key: str) -> float:
                if key.endswith(":qualify") or key.endswith(":new_need"):
                    return 0.01
                if key.endswith(":delivery"):
                    return 0.01 if label in ("failed_delivery_refund", "corrected_warranty_refund") else 0.99
                if key.endswith(":repair"):
                    return 0.99 if label == "failed_delivery_refund" else 0.01
                if key.endswith(":warranty"):
                    return 0.01 if label == "corrected_warranty_refund" else 0.99
                if key.endswith(":recovery"):
                    return 0.01 if label == "strategic_default_recovered" else 0.99
                return 0.99

            model.buyer = controlled_buyer
            model.uniform = controlled_uniform
            model.choice = lambda seed, key, values, rationality: "enterprise"
            model.poisson = lambda seed, key, mean: 4 if label == "capacity_supplier_shock" else 2
            scenario = "payment_deviation" if "default" in label else "supplier_shock" if "supplier" in label else "reference"
            world = model.run_world(12001, scenario, policy)
            world["control_scope"] = "Named branches forcibly selected; excluded from market simulation estimates"
            worlds[label] = (world, config)
            (args.output / f"{label}.json").write_text(json.dumps(world, indent=2) + "\n")
            (args.output / f"{label}_config.json").write_text(json.dumps(config, indent=2) + "\n")
            receipt = reconcile(world, config)
            receipt["control_name"] = label
            summaries.append(receipt)
        events = set().union(*(set(row["all_event_types"]) for row in summaries))
        required = {"acceptance", "correction_required", "failed_delivery_refund", "bad_debt", "late_collection",
                    "renewal_choice", "support_closed", "warranty_refund_payment", "credit_draw", "repay_credit",
                    "capacity_decline", "supplier_terms"}
        assert required <= events, f"Unexercised lifecycle branches: {required - events}"
        mutations = []
        for name in ("omit_startup", "wrong_profit", "missing_refund", "wrong_collection_total"):
            label = "failed_delivery_refund" if name == "missing_refund" else "accepted_renewal_credit"
            world, config = worlds[label]
            altered = copy.deepcopy(world)
            if name == "omit_startup":
                altered["journal"] = [entry for entry in altered["journal"] if entry["event_type"] != "research"]
            elif name == "wrong_profit":
                altered["profit_cents"] += 1
            elif name == "missing_refund":
                index = next(i for i, entry in enumerate(altered["journal"])
                             if entry["event_type"] == "failed_delivery_refund")
                del altered["journal"][index]
            else:
                altered["collections_cents"] += 1
            try:
                reconcile(altered, config)
            except AssertionError as error:
                mutations.append({"mutation": name, "status": "correctly_rejected", "reason": str(error)})
            else:
                raise AssertionError(f"Independent checker accepted mutation: {name}")
        summary = {"status": "pass", "scope": "Forced branch controls, not observed or sampled demand",
                   "worlds": summaries, "required_branches_exercised": sorted(required), "mutations": mutations}
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps({"status": "pass", "worlds": len(summaries), "mutations_rejected": len(mutations),
                          "required_branches_exercised": sorted(required)}))
    finally:
        model.CONFIG = original_config
        for name, function in original_functions.items():
            setattr(model, name, function)


if __name__ == "__main__":
    main()
