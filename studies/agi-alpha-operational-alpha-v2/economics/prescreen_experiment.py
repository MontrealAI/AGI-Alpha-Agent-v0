# SPDX-License-Identifier: Apache-2.0
"""Fresh synthetic comparison of old cheap screening and reachable screening."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def stream(seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    rows = []
    for index in range(24):
        uses = rng.choice([2, 8, 20, 50])
        cap = rng.choice([50, 150, 500])
        transfer = rng.choice([0.3, 0.6, 1.0])
        fee = rng.choice([20, 75, 200])
        fixed = rng.choice([100, 500, 2000])
        fraction = rng.uniform(-0.3, 1)
        rows.append(
            {
                "id": f"{seed}-{index}",
                "uses": uses,
                "cap_cents": cap,
                "transfer": transfer,
                "fee_cents": fee,
                "fixed_cents": fixed,
                "assessment_cents": 200,
                "realized_fraction": fraction,
                "assay_noise": rng.gauss(0, 0.08),
                "correlated_assay_error": rng.random() < 0.06,
                "failure": rng.random() < 0.04,
            }
        )
    return rows


def execute(seed: int, rule: str) -> dict[str, Any]:
    cash = 20000
    cost = benefit = assessments = admissions = false_admissions = failures = 0
    history = []
    for item in stream(seed):
        maximum = item["uses"] * item["transfer"] * item["cap_cents"]
        total = item["uses"] * item["fee_cents"] + item["fixed_cents"] + item["assessment_cents"]
        reachable = maximum >= 1.25 * total and maximum > total
        buy = maximum >= 0.6 * item["fixed_cents"] if rule == "old_screen" else reachable
        buy = buy and cash >= item["assessment_cents"] + item["fixed_cents"] + item["uses"] * item["fee_cents"]
        row = {
            "id": item["id"],
            "maximum_gross_cents": maximum,
            "hurdle_costs_cents": 1.25 * total,
            "reachable": reachable,
            "assessed": buy,
            "admitted": False,
        }
        if buy:
            cost += item["assessment_cents"]
            cash -= item["assessment_cents"]
            assessments += 1
            if item["failure"]:
                failures += 1
                row["assessment_failed"] = True
            else:
                estimate = min(
                    1.0,
                    item["realized_fraction"] + item["assay_noise"] + (1.0 if item["correlated_assay_error"] else 0),
                )
                forecast = maximum * estimate
                admit = forecast >= 1.25 * total and forecast > total
                row.update(assay_estimated_fraction=estimate, admitted=admit)
                if admit:
                    admissions += 1
                    spend = item["fixed_cents"] + item["uses"] * item["fee_cents"]
                    true_value = round(maximum * item["realized_fraction"])
                    cost += spend
                    benefit += true_value
                    cash += true_value - spend
                    false_admissions += int(true_value <= total)
                    row.update(realized_gross_benefit_cents=true_value, remaining_expense_cents=spend)
        row.update(cash_cents=cash, cumulative_net_cents=benefit - cost)
        history.append(row)
    return {
        "seed": seed,
        "rule": rule,
        "net_cents": benefit - cost,
        "cost_cents": cost,
        "benefit_cents": benefit,
        "cash_cents": cash,
        "assessments": assessments,
        "admissions": admissions,
        "false_admissions": false_admissions,
        "assessment_failures": failures,
        "unreachable_assessments": sum(row["assessed"] and not row["reachable"] for row in history),
        "history": history,
    }


def freeze(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    if (out / "PRESCREEN_FREEZE.json").exists():
        raise ValueError("freeze already exists")
    value = {
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "seeds": [31000, 31127],
        "candidates_per_world": 24,
        "hurdle": 1.25,
        "cost_units": "integer USD cents",
        "seed_capital_cents": 20000,
        "rules": ["old_screen", "reachable_first"],
        "label": "New prospective artificial candidate process; not replay or recovered profit of old study.",
        "limits": "Benefit distributions, bounds, error and reuse are assumptions. Neither rule grants live authority. Old unreachable assessments cannot admit under the same cap; downstream liquidity may still change decisions.",
    }
    (out / "PRESCREEN_FREEZE.json").write_text(json.dumps(value, indent=2) + "\n")


def confirm(out: Path) -> None:
    frozen = json.loads((out / "PRESCREEN_FREEZE.json").read_text())
    if frozen["source_sha256"] != hashlib.sha256(Path(__file__).read_bytes()).hexdigest():
        raise ValueError("source changed after freeze")
    target = out / "prescreen_confirmation.json"
    if target.exists():
        raise ValueError("confirmation exists")
    rows = [
        execute(seed, rule) for seed in range(frozen["seeds"][0], frozen["seeds"][1] + 1) for rule in frozen["rules"]
    ]
    target.write_text(json.dumps(rows, indent=2) + "\n")
    differences = [(rows[i + 1]["net_cents"] - rows[i]["net_cents"]) / 100 for i in range(0, len(rows), 2)]
    mean = statistics.mean(differences)
    se = statistics.stdev(differences) / math.sqrt(len(differences))
    summary = {
        "worlds": len(differences),
        "paired_mean_net_increment_usd": mean,
        "conditional_monte_carlo_95_interval_usd": [mean - 1.96 * se, mean + 1.96 * se],
        "old_unreachable_assessments": sum(r["unreachable_assessments"] for r in rows if r["rule"] == "old_screen"),
        "new_unreachable_assessments": sum(
            r["unreachable_assessments"] for r in rows if r["rule"] == "reachable_first"
        ),
        "same_admissions_worlds": sum(
            rows[i]["admissions"] == rows[i + 1]["admissions"] for i in range(0, len(rows), 2)
        ),
        "false_admissions": {
            rule: sum(r["false_admissions"] for r in rows if r["rule"] == rule) for rule in frozen["rules"]
        },
        "assay_failures": {
            rule: sum(r["assessment_failures"] for r in rows if r["rule"] == rule) for rule in frozen["rules"]
        },
        "warning": frozen["label"],
    }
    (out / "prescreen_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["freeze", "confirm"])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    (freeze if args.action == "freeze" else confirm)(args.out)


if __name__ == "__main__":
    main()
