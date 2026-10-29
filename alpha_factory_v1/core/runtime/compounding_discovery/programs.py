# SPDX-License-Identifier: Apache-2.0
"""Restricted executable LP strategy grammar; no supplied code or evaluator mutation.

The certificate encoding follows the preceding eADARP implementation; the final
Decimal checker remains an independently written module.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Any
from ..structural_transfer.contracts import digest


def canonical_decimal(value: Decimal) -> str:
    """Remove insignificant fractional zeros without changing the exact value."""
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def validate_program(program: dict[str, Any]) -> None:
    if (
        set(program) != {"op", "method", "presolve"}
        or program["op"] != "per-vehicle-lp"
        or program["method"] not in {"highs", "highs-ds", "highs-ipm"}
        or type(program["presolve"]) is not bool
    ):
        raise ValueError("unsupported executable strategy program")


def invent(seed: int) -> list[dict[str, Any]]:
    import random

    programs = [
        {"op": "per-vehicle-lp", "method": m, "presolve": p}
        for m in ["highs", "highs-ds", "highs-ipm"]
        for p in [True, False]
    ]
    default = {"op": "per-vehicle-lp", "method": "highs", "presolve": True}
    programs.remove(default)
    random.Random(seed).shuffle(programs)
    return [default] + programs[:2]


def solve_program(target: dict[str, Any], model: dict[str, Any], program: dict[str, Any], meter: Any) -> dict[str, Any]:
    validate_program(program)
    import numpy as np
    from scipy.optimize import linprog

    schedules, total = [], Decimal(0)
    for item in model["vehicles"]:
        variables, rows = item["variables"], item["rows"]
        matrix = np.zeros((len(rows), len(variables)))
        rhs, objective = [], np.zeros(len(variables))
        for r, row in enumerate(rows):
            for index, coefficient in row["terms"]:
                matrix[r, index] = float(coefficient)
            rhs.append(float(row["rhs"]))
        for index, coefficient in item["objective"]["terms"]:
            objective[index] = float(coefficient)
        meter.solver()
        lp = linprog(
            objective,
            A_ub=matrix,
            b_ub=rhs,
            bounds=[(None, None)] * len(variables),
            method=program["method"],
            options={"presolve": program["presolve"], "time_limit": meter.remaining()},
        )
        if not lp.success:
            meter.solver()
            dual = linprog(
                np.array(rhs),
                A_eq=np.vstack([matrix.T, np.ones(len(rows))]),
                b_eq=np.r_[np.zeros(len(variables)), 1],
                bounds=(0, None),
                method=program["method"],
                options={"presolve": program["presolve"], "time_limit": meter.remaining()},
            )
            witness = {"type": "bounded-farkas/v1", "vehicle": item["vehicle"], "rows": [], "contradiction": "0"}
            if dual.success and dual.fun < -1e-7:
                witness["rows"] = [
                    {"id": row["name"], "multiplier": format(max(0, float(y)), ".15g")}
                    for row, y in zip(rows, dual.x)
                    if y > 0
                ]
                multipliers = {x["id"]: Decimal(x["multiplier"]) for x in witness["rows"]}
                residual = [Decimal(0)] * len(variables)
                weighted_rhs = Decimal(0)
                for row in rows:
                    multiplier = multipliers.get(row["name"], Decimal(0))
                    weighted_rhs += multiplier * Decimal(row["rhs"])
                    for index, coefficient in row["terms"]:
                        residual[index] += multiplier * Decimal(coefficient)
                lower = sum(
                    (min(r * Decimal(v["lower"]), r * Decimal(v["upper"])) for r, v in zip(residual, variables)),
                    Decimal(0),
                )
                witness["contradiction"] = canonical_decimal(lower - weighted_rhs)
            return {
                "schema": "agialpha/eadarp-certificate/v1",
                "task_hash": digest(target),
                "status": "INFEASIBLE" if witness["rows"] else "UNRESOLVED",
                "vehicles": [],
                "objective": "0",
                "witness": witness,
                "scope": "declared-eADARP-linear-model-only",
            }
        values = [format(float(x), ".15g") for x in lp.x]
        length = len(item["route"])
        schedules.append(
            {
                "vehicle": item["vehicle"],
                "route": item["route"],
                "start_min": values[:length],
                "charge_min": values[length : 2 * length],
                "arrival_kwh": values[2 * length :],
            }
        )
        total += Decimal(item["objective"]["constant"]) + sum(
            (Decimal(c) * Decimal(values[i]) for i, c in item["objective"]["terms"]), Decimal(0)
        )
    return {
        "schema": "agialpha/eadarp-certificate/v1",
        "task_hash": digest(target),
        "status": "FEASIBLE",
        "vehicles": schedules,
        "objective": str(total),
        "witness": {},
        "scope": "declared-eADARP-linear-model-only",
    }
