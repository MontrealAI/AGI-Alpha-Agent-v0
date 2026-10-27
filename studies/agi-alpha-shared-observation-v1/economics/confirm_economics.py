# SPDX-License-Identifier: Apache-2.0
"""Apply the frozen policy to every supplied fresh mission without selecting successes."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

from economic import evaluate


def main() -> None:
    """Retain one compact row per valid or refused technical case."""
    parser = argparse.ArgumentParser()
    parser.add_argument("confirmation", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assumption_path = Path(__file__).with_name("assumptions-v1.json")
    a = json.loads(assumption_path.read_text())
    rows = []
    for path in sorted(args.confirmation.glob("confirmation-*/candidate.json")):
        data = json.loads(path.read_text())
        valid = data["observation_accepted"] and all(op["valid"] for op in data["operators"])
        row = {"mission_id": data["mission_id"], "technical_valid": valid,
               "operators": len(data["operators"]), "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "value_of_information": data["total_value_of_information"]}
        if valid:
            result = evaluate(data, a)
            row.update({"decision": "conditional_order_possible" if result["launch_probability"] else "decline",
                        "launch_probability": result["launch_probability"],
                        "expected_accepted_packages": result["expected"]["accepted"],
                        "expected_service_collections": result["expected"]["collected_service_revenue"],
                        "expected_operating_profit": result["expected"]["operating_profit_before_BC"],
                        "expected_sensor_orders_cost": result["expected"]["sensor_paid"],
                        "expected_buyer_net_value": result["expected"]["customer_net_value"]})
        else:
            row.update({"decision": "refuse_original_mission_technical_scope", "launch_probability": 0.,
                        "expected_accepted_packages": 0., "expected_service_collections": 0.,
                        "expected_operating_profit": -a["per_operator_quote_cost"] * len(data["operators"]),
                        "expected_sensor_orders_cost": 0., "expected_buyer_net_value": 0.})
        rows.append(row)
    if not rows:
        raise ValueError("No fresh candidate outputs found")
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "confirmation.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"evidence": "frozen_policy_on_hand_designed_synthetic_confirmation_not_market_sample",
               "assumptions_sha256": hashlib.sha256(assumption_path.read_bytes()).hexdigest(),
               "cases": len(rows), "technically_valid": sum(r["technical_valid"] for r in rows),
               "cases_with_positive_launch_probability": sum(r["launch_probability"] > 0 for r in rows),
               "cases_with_positive_expected_operating_profit": sum(r["expected_operating_profit"] > 0 for r in rows),
               "sum_expected_quote_and_operating_profit": sum(r["expected_operating_profit"] for r in rows),
               "sum_expected_service_collections": sum(r["expected_service_collections"] for r in rows),
               "sum_expected_acquisition_orders_cost": sum(r["expected_sensor_orders_cost"] for r in rows),
               "actual_customer_collections": 0,
               "quote_policy": "All cases are offered the same 2 USD/operator preliminary assessment; refusals collect no fee.",
               "recipient_041": next((r for r in rows if r["mission_id"] == "confirmation-041"), None)}
    (args.output / "confirmation_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
