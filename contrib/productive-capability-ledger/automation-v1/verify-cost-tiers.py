# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
Quantity = Fraction | None


def known(fact: dict[str, Any]) -> Quantity:
    return None if fact["value"] is None else Fraction(fact["value"])


def multiply(left: Quantity, right: Quantity) -> Quantity:
    return None if left is None or right is None else left * right


def divide(left: Quantity, right: Quantity) -> Quantity:
    return None if left is None or right is None or right == 0 else left / right


def add(left: Quantity, right: Quantity) -> Quantity:
    return None if left is None or right is None else left + right


def total(values: list[Quantity]) -> Quantity:
    result: Quantity = Fraction(0)
    for value in values:
        result = add(result, value)
    return result


def upward(value: Quantity) -> int | None:
    return None if value is None else (value.numerator + value.denominator - 1) // value.denominator


def calculate(scenario: dict[str, Any]) -> tuple[dict[str, int | None], dict[str, dict[str, Any]]]:
    requests = multiply(
        known(scenario["capacityRequestsPerMonth"]), divide(known(scenario["utilizationBps"]), Fraction(10000))
    )
    acceptance = divide(known(scenario["acceptanceBps"]), Fraction(10000))
    attempts = divide(known(scenario["attemptsPerRequestPpm"]), Fraction(1000000))
    accepted = multiply(requests, acceptance)
    operations = []
    for row in scenario["operations"]:
        frequency = {"request": Fraction(1), "attempt": attempts, "accepted": acceptance}[row["frequency"]]
        units = divide(known(row["unitsPerOccurrencePpm"]), Fraction(1000000))
        operations.append(multiply(multiply(frequency, units), known(row["unitCostMicros"])))
    residual = []
    for row in scenario["residual"]:
        exceptions = divide(known(row["exceptionsPerRequestPpm"]), Fraction(1000000))
        minutes = multiply(exceptions, known(row["minutesPerException"]))
        residual.append(multiply(minutes, divide(known(row["hourlyCostMicros"]), Fraction(60))))
    variable = total(operations + residual)
    shared = total(
        [
            multiply(known(row["amountMicros"]), divide(known(row["allocationBps"]), Fraction(10000)))
            for row in scenario["monthly"]
        ]
    )
    amortized = total(
        [
            divide(
                multiply(known(row["amountMicros"]), divide(known(row["allocationBps"]), Fraction(10000))),
                known(row["amortizationMonths"]),
            )
            for row in scenario["investments"]
        ]
    )
    variable_monthly = multiply(variable, requests)
    tiers = {
        "marginal": divide(variable, acceptance),
        "recurring": divide(add(variable_monthly, shared), accepted),
        "fullyLoaded": divide(add(add(variable_monthly, shared), amortized), accepted),
    }
    costs = {
        "nextRequestMicros": upward(variable),
        "marginalMicrosPerAccepted": upward(tiers["marginal"]),
        "recurringMicrosPerAccepted": upward(tiers["recurring"]),
        "fullyLoadedMicrosPerAccepted": upward(tiers["fullyLoaded"]),
        "variableMonthlyMicros": upward(variable_monthly),
        "sharedMonthlyMicros": upward(shared),
        "amortizedMonthlyMicros": upward(amortized),
    }
    hourly = known(scenario["humanBaseline"]["hourlyCostMicros"])
    human = multiply(known(scenario["humanBaseline"]["minutesPerAccepted"]), divide(hourly, Fraction(60)))
    comparison = {}
    for name, cost in tiers.items():
        delta = None if cost is None or human is None else human - cost
        minutes = multiply(divide(cost, hourly), Fraction(60))
        comparison[name] = {
            "outcome": "unknown" if delta is None else "win" if delta > 0 else "loss" if delta < 0 else "tie",
            "seconds": upward(multiply(minutes, Fraction(60))),
            "minutes": None if minutes is None else float(minutes),
        }
    return costs, comparison


def verify(paths: list[Path]) -> dict[str, Any]:
    checks = 0
    scenarios = 0
    identities = {}
    for path in paths:
        raw = path.read_bytes()
        record = json.loads(raw)
        identities[path.relative_to(ROOT).as_posix()] = hashlib.sha256(raw).hexdigest()
        code = (
            "import fs from 'node:fs';"
            "import {evaluateAutomatedCosts} from './examples/successor-alpha/automated-costs.mjs';"
            "console.log(JSON.stringify(evaluateAutomatedCosts(JSON.parse(fs.readFileSync(process.argv[1],'utf8')))));"
        )
        observed = json.loads(
            subprocess.check_output(
                ["node", "--input-type=module", "-e", code, str(path)], cwd=ROOT, text=True, timeout=20
            )
        )
        if len(record["scenarios"]) != len(observed["scenarios"]):
            raise AssertionError("Scenario count differs")
        for source, result in zip(record["scenarios"], observed["scenarios"]):
            expected_costs, expected_comparison = calculate(source)
            for field, expected in expected_costs.items():
                if result["costs"][field] != expected:
                    raise AssertionError((path.name, source["name"], field, expected, result["costs"][field]))
                checks += 1
            for name, expected in expected_comparison.items():
                actual = result["comparison"][name]
                if actual["outcome"] != expected["outcome"] or actual["breakEvenHumanSeconds"] != expected["seconds"]:
                    raise AssertionError((source["name"], name, expected, actual))
                checks += 2
                actual_minutes = actual["breakEvenHumanMinutes"]
                if expected["minutes"] is None:
                    if actual_minutes is not None:
                        raise AssertionError("Unknown human timing became known")
                elif not math.isclose(actual_minutes, expected["minutes"], rel_tol=1e-12, abs_tol=1e-12):
                    raise AssertionError((source["name"], name, expected["minutes"], actual_minutes))
                checks += 1
            scenarios += 1
    source = ROOT / "examples/successor-alpha/automated-costs.mjs"
    return {
        "schema": "alpha-automated-cost-independent-arithmetic/v1",
        "passed": True,
        "checks": checks,
        "records": len(paths),
        "scenarios": scenarios,
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "recordSha256": identities,
        "method": "Separately implemented Python fractions.Fraction oracle against the Node implementation",
        "scope": (
            "Conditional arithmetic only; no live executor, measured full cost " "or independent organizational custody"
        ),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path, nargs="*")
    args = parser.parse_args()
    paths = args.records or [
        ROOT / "examples/successor-alpha/fixtures/automated-costs-example.json",
        ROOT / "examples/successor-alpha/fixtures/automated-costs-unknown.json",
    ]
    print(json.dumps(verify([path.resolve() for path in paths]), indent=2))
