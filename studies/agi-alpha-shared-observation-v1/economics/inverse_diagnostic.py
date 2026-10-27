# SPDX-License-Identifier: Apache-2.0
"""Postconfirmation inverse-price diagnostic; primary policy is unchanged."""

import itertools
import json
from pathlib import Path

from economic import evaluate


def threshold(technical: dict, assumptions: dict) -> dict:
    """Maximum equal-shared acquisition price for any voluntary nonempty subset."""
    a = assumptions
    q = a["first_pass_acceptance"]["E"]
    h = 1 - a["common_package_failure_probability"]
    candidates = []
    ops = [op for op in technical["operators"] if op["valid"]]
    for n in range(1, len(ops) + 1):
        for subset in itertools.combinations(ops, n):
            bound = n * (q * (min(op["value_of_information"] for op in subset) - a["package_fee"])
                         - a["customer_adaptation_cost"] / h)
            candidates.append({"operators": [op["id"] for op in subset], "maximum_acquisition": bound})
    best = max(candidates, key=lambda x: x["maximum_acquisition"])
    result = {"fixed_service_fee": a["package_fee"], "best_subset": best,
              "any_feasible_nonnegative_acquisition": best["maximum_acquisition"] >= 0,
              "formula": "K_max(S)=|S|*[q*(min_i VOI_i-fee)-adaptation/(1-common_failure)]"}
    if best["maximum_acquisition"] >= 0:
        test = evaluate(technical, {**a, "acquisition_cost": best["maximum_acquisition"]})
        result["conditional_expected_operating_profit_at_bound"] = test["expected"]["operating_profit_before_BC"]
        result["launch_probability_at_bound"] = test["launch_probability"]
    return result


def main() -> None:
    """Inspect only the origin and nominated recipient using the declared grid."""
    root = Path(__file__).resolve().parents[1]
    a = json.loads((root / "economics/assumptions-v1.json").read_text())
    origin = json.loads((root / "results/origin.json").read_text())
    recipient = json.loads((root / "evaluation/confirmation-v1/confirmation-041/candidate.json").read_text())
    grid = []
    for acquisition, fee in itertools.product(a["acquisition_cost_range"], a["package_fee_range"]):
        r = evaluate(recipient, {**a, "acquisition_cost": acquisition, "package_fee": fee})
        grid.append({"acquisition": acquisition, "fee": fee, "launch_probability": r["launch_probability"],
                     "provider_expected_profit": r["expected"]["operating_profit_before_BC"],
                     "buyer_expected_net_value": r["expected"]["customer_net_value"]})
    result = {"evidence": "postconfirmation_diagnostic_not_new_fresh_evidence_or_market_quote",
              "origin": threshold(origin, a), "recipient_041": threshold(recipient, a),
              "recipient_grid": grid, "recipient_grid_jointly_viable_cells":
              sum(x["launch_probability"] > 0 and x["provider_expected_profit"] > 0 for x in grid),
              "reserve_formula": "required_seed=max_t(refundable_liability_t+unpaid_obligations_t+provider_reserve-net_cashflow_t)",
              "extra_financing_formula": "max(0,required_seed-existing_seed)",
              "buyer_cash_formula": "acquisition_share+FULL_service_fee+adaptation+peak_fallback_action_reserve"}
    (root / "results/economics/inverse_diagnostic.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "recipient_grid"}, indent=2))


if __name__ == "__main__":
    main()
