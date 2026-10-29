# SPDX-License-Identifier: Apache-2.0
"""Construct a bounded fixed-route energy/time adaptation of capacity accounting."""

from __future__ import annotations

from decimal import Decimal
import hashlib
import re
from typing import Any

from .contracts import digest

ASSUMPTIONS = [
    "linear-charge-and-discharge",
    "fixed-orders-and-complete-passenger-pairs",
    "independent-vehicles-unlimited-station-concurrency",
    "declared-travel-times-not-real-dispatch",
    "numerical-tolerance-1e-7",
]
UPDATES = {"travel_multiplier", "charge_multiplier", "consumption_multiplier", "window_shift", "window_scale"}


def number(value: Any) -> Decimal:
    if not isinstance(value, str) or not re.fullmatch(r"-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", value):
        raise ValueError("finite decimal string required")
    result = Decimal(value)
    if not result.is_finite() or abs(result) > 10**9:
        raise ValueError("bounded decimal required")
    return result


def parse(target: dict[str, Any]) -> dict[str, Any]:
    required = {"id", "adapter_id", "instance_text", "instance_sha256", "routes", "updates", "assumptions", "need"}
    if set(target) != required or target["adapter_id"] != "eadarp-temporal/v1":
        raise ValueError("unsupported target contract; shared-station/uncertainty needs a new construction")
    raw = target["instance_text"]
    if (
        not isinstance(raw, str)
        or len(raw.encode()) > 200000
        or hashlib.sha256(raw.encode()).hexdigest() != target["instance_sha256"]
    ):
        raise ValueError("raw instance identity")
    if not all(x in target["assumptions"] for x in ASSUMPTIONS) or set(target["updates"]) != UPDATES:
        raise ValueError("explicit model assumptions and update contract required")
    update = {k: number(v) for k, v in target["updates"].items()}
    if any(update[k] <= 0 for k in UPDATES - {"window_shift"}):
        raise ValueError("positive scale factors required")
    lines = [x.split() for x in raw.splitlines() if x.strip()]
    header = [int(x) for x in lines[0]]
    if len(header) != 7 or not 1 <= header[0] <= 8 or not 1 <= header[1] <= 32:
        raise ValueError("bounded public instance header")
    nodes, index = {}, 1
    while index < len(lines) and len(lines[index]) == 7:
        row = lines[index]
        ident = int(row[0])
        if ident in nodes:
            raise ValueError("duplicate node")
        nodes[ident] = [number(x) for x in row[1:]]
        index += 1
    data = [[number(x) for x in row] for row in lines[index:]]
    size = len(nodes)
    if (
        sorted(nodes) != list(range(1, size + 1))
        or len(data) != 13 + size
        or any(len(row) != size for row in data[13:])
    ):
        raise ValueError("complete asymmetric travel matrix required; Euclidean substitution is unsupported")
    if (
        len(data[2]) != header[0]
        or len(data[6]) != header[0]
        or len(data[7]) != header[0]
        or len(data[8]) != header[0]
        or len(data[9]) != header[0]
    ):
        raise ValueError("vehicle parameter cardinality")
    if len(data[5]) != header[1] or len(data[10]) != len(data[4]) or len(data[11]) != 1 or len(data[12]) != 2:
        raise ValueError("ride/charge/weight parameter cardinality")
    stations = [int(x) for x in data[4]]
    travel = [[x * 2 * update["travel_multiplier"] for x in row] for row in data[13:]]
    return {
        "n": header[1],
        "vehicles": header[0],
        "horizon": Decimal(header[-1]),
        "nodes": nodes,
        "origins": [int(x) for x in data[2]],
        "destinations": [int(x) for x in data[3]],
        "stations": stations,
        "ride": data[5],
        "capacity": data[6],
        "initial": data[7],
        "battery": data[8],
        "reserve": data[9],
        "alpha": {s: rate * update["charge_multiplier"] for s, rate in zip(stations, data[10])},
        "beta": data[11][0] * update["consumption_multiplier"],
        "weights": data[12],
        "travel": travel,
        "updates": update,
    }


def compile_model(target: dict[str, Any]) -> dict[str, Any]:
    ins = parse(target)
    routes = target["routes"]
    if not isinstance(routes, list) or len(routes) != ins["vehicles"]:
        raise ValueError("one complete order per vehicle required")
    served, models = [], []
    for vehicle, route in enumerate(routes):
        if (
            not isinstance(route, list)
            or not 2 <= len(route) <= 100
            or any(type(x) is not int or x not in ins["nodes"] for x in route)
        ):
            raise ValueError("bounded route node identities")
        if route[0] != ins["origins"][vehicle] or route[-1] not in ins["destinations"] or len(set(route)) != len(route):
            raise ValueError("invalid depot or duplicate visit")
        positions = {node: j for j, node in enumerate(route)}
        load = Decimal(0)
        for node in route:
            load += ins["nodes"][node][3]
            if not 0 <= load <= ins["capacity"][vehicle] or (node in ins["stations"] and load != 0):
                raise ValueError("seats or passenger-free charging condition")
            if 1 <= node <= ins["n"]:
                if node + ins["n"] not in positions or positions[node] >= positions[node + ins["n"]]:
                    raise ValueError("pickup/drop precedence")
                served.append(node)
            elif ins["n"] < node <= 2 * ins["n"] and node - ins["n"] not in positions:
                raise ValueError("unpaired delivery")
        if load:
            raise ValueError("passengers left on vehicle")
        length = len(route)
        variables, rows = [], []
        for kind in ["T", "C", "B"]:
            for j, node in enumerate(route):
                upper = (
                    ins["horizon"]
                    if kind == "T" or (kind == "C" and node in ins["stations"])
                    else ins["battery"][vehicle]
                    if kind == "B"
                    else Decimal(0)
                )
                variables.append({"name": f"{kind}:{vehicle}:{j}", "lower": "0", "upper": str(upper)})

        def add(name: str, terms: list[tuple[int, Any]], rhs: Any) -> None:
            merged: dict[int, Decimal] = {}
            for key, val in terms:
                merged[key] = merged.get(key, Decimal(0)) + Decimal(val)
            rows.append(
                {
                    "name": name,
                    "terms": [[key, str(val)] for key, val in sorted(merged.items()) if val],
                    "rhs": str(rhs),
                }
            )

        for i, variable in enumerate(variables):
            kind, _, j = variable["name"].split(":")
            add(f"bound:{vehicle}:{kind}:{j}:lower", [(i, -1)], -Decimal(variable["lower"]))
            add(f"bound:{vehicle}:{kind}:{j}:upper", [(i, 1)], Decimal(variable["upper"]))
        initial = ins["initial"][vehicle]
        add(f"initial:{vehicle}:positive", [(2 * length, 1)], initial)
        add(f"initial:{vehicle}:negative", [(2 * length, -1)], -initial)
        add(f"end_reserve:{vehicle}", [(3 * length - 1, -1)], -ins["reserve"][vehicle] * ins["battery"][vehicle])
        drive, objective, constant = Decimal(0), {}, Decimal(0)
        for j, node in enumerate(route):
            info, alpha = ins["nodes"][node], ins["alpha"].get(node, Decimal(0))
            low = info[4] + ins["updates"]["window_shift"]
            high = low + (info[5] - info[4]) * ins["updates"]["window_scale"]
            add(f"window:{vehicle}:{j}:lower", [(j, -1)], -low)
            add(f"window:{vehicle}:{j}:upper", [(j, 1)], high)
            add(f"charge_cap:{vehicle}:{j}", [(2 * length + j, 1), (length + j, alpha)], ins["battery"][vehicle])
            if j + 1 < length:
                travel = ins["travel"][node - 1][route[j + 1] - 1]
                drive += travel
                add(f"arc_time:{vehicle}:{j}", [(j, 1), (length + j, 1), (j + 1, -1)], -info[2] - travel)
                energy = [(2 * length + j + 1, 1), (2 * length + j, -1), (length + j, -alpha)]
                add(f"arc_energy:{vehicle}:{j}:positive", energy, -ins["beta"] * travel)
                add(f"arc_energy:{vehicle}:{j}:negative", [(k, -v) for k, v in energy], ins["beta"] * travel)
            if 1 <= node <= ins["n"]:
                drop = positions[node + ins["n"]]
                direct = ins["travel"][node - 1][node + ins["n"] - 1]
                add(f"ride_max:{vehicle}:{node}", [(drop, 1), (j, -1)], ins["ride"][node - 1] + info[2])
                add(f"ride_min:{vehicle}:{node}", [(j, 1), (drop, -1)], -direct - info[2])
                objective[drop] = objective.get(drop, Decimal(0)) + ins["weights"][1]
                objective[j] = objective.get(j, Decimal(0)) - ins["weights"][1]
                constant -= ins["weights"][1] * (direct + info[2])
        constant += ins["weights"][0] * drive
        models.append(
            {
                "vehicle": vehicle,
                "route": route,
                "variables": variables,
                "rows": rows,
                "objective": {"terms": [[k, str(v)] for k, v in sorted(objective.items())], "constant": str(constant)},
            }
        )
    if sorted(served) != list(range(1, ins["n"] + 1)):
        raise ValueError("every passenger exactly once is required")
    return {"vehicles": models}


def solve_model(target: dict[str, Any], model: dict[str, Any]) -> dict[str, Any]:
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
        lp = linprog(objective, A_ub=matrix, b_ub=rhs, bounds=[(None, None)] * len(variables), method="highs")
        if not lp.success:
            dual = linprog(
                np.array(rhs),
                A_eq=np.vstack([matrix.T, np.ones(len(rows))]),
                b_eq=np.r_[np.zeros(len(variables)), 1],
                bounds=(0, None),
                method="highs",
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
                lower = sum((min(r * Decimal(v["lower"]), r * Decimal(v["upper"])) for r, v in zip(residual, variables)), Decimal(0))
                witness["contradiction"] = str(lower - weighted_rhs)
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
