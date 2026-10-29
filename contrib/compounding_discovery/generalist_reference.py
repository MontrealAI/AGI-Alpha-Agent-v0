"""Standalone frontier-generalist fixed-route eADARP control.

This module reads raw public eADARP instances and uses a direct conventional LP.
It does not import the structural-transfer instrument or share its implementation.
Only fixed route order, deterministic global updates and the declared linear
battery/charging model are certified. It neither designs routes nor certifies
physical EV operation. See API.md for the freeze and chronological-cache policy.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import linprog

SCHEMA = "agialpha/eadarp-certificate/v1"
SCOPE = "declared-eADARP-linear-model-only"
TOL = Decimal("1e-7")
# Only exact prior-task replay is cached. Insertion is chronological after solve.
# No expected status, future-task labels or approximate/semantic matches are used.
_EXACT_CACHE: dict[str, dict[str, Any]] = {}


def decimal(value: Any) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a decimal")
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError) as e:
        raise ValueError("invalid decimal") from e
    if not d.is_finite():
        raise ValueError("decimal must be finite")
    return d


def ds(value: Decimal | float | int) -> str:
    d = value if isinstance(value, Decimal) else decimal(value)
    if d == 0:
        return "0"
    return format(d, "f")


def canonical_hash(target: dict[str, Any]) -> str:
    raw = json.dumps(target, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@dataclass
class Instance:
    vehicles: int
    users: int
    horizon: Decimal
    nodes: dict[int, list[Decimal]]
    origins: list[int]
    destinations: list[int]
    stations: list[int]
    ride: list[Decimal]
    seats: list[Decimal]
    initial: list[Decimal]
    battery: list[Decimal]
    reserve: list[Decimal]
    alpha: dict[int, Decimal]
    beta: Decimal
    weight: list[Decimal]
    travel: list[list[Decimal]]


def parse(text: str) -> Instance:
    if not isinstance(text, str) or len(text.encode("utf-8")) > 20_000_000:
        raise ValueError("raw instance is missing or exceeds the source byte cap")
    lines = [line.split() for line in text.splitlines() if line.strip()]
    if not lines or len(lines[0]) != 7:
        raise ValueError("invalid eADARP header")
    h = [int(x) for x in lines[0]]
    if min(h[:6]) < 0 or h[0] < 1 or h[1] < 1:
        raise ValueError("invalid instance counts")
    nodes: dict[int, list[Decimal]] = {}
    k = 1
    while k < len(lines) and len(lines[k]) == 7:
        a = lines[k]
        node = int(a[0])
        if node in nodes:
            raise ValueError("duplicate raw node identifier")
        nodes[node] = [decimal(x) for x in a[1:]]
        k += 1
    data = [[decimal(x) for x in line] for line in lines[k:]]
    count = len(nodes)
    if set(nodes) != set(range(1, count + 1)) or len(data) != 13 + count:
        raise ValueError("node/matrix dimensions disagree")
    if any(len(row) != count for row in data[13:]):
        raise ValueError("travel matrix is not square")
    origins = [int(x) for x in data[2]]
    dest = [int(x) for x in data[3]]
    stations = [int(x) for x in data[4]]
    if len(origins) != h[0] or len(data[5]) != h[1]:
        raise ValueError("vehicle/user metadata dimensions disagree")
    if any(len(data[i]) != h[0] for i in (6, 7, 8, 9)):
        raise ValueError("vehicle metadata dimensions disagree")
    if len(data[10]) != len(stations) or len(data[11]) != 1 or len(data[12]) != 2:
        raise ValueError("rate/objective metadata dimensions disagree")
    if not set(origins + dest + stations).issubset(nodes):
        raise ValueError("metadata refers to absent nodes")
    if min(data[8]) <= 0 or min(data[6]) < 0:
        raise ValueError("nonpositive battery or negative seats")
    if any(not (Decimal(0) <= b <= q) for b, q in zip(data[7], data[8])):
        raise ValueError("initial battery outside physical model")
    if any(not (Decimal(0) <= r <= Decimal(1)) for r in data[9]):
        raise ValueError("end reserve fraction outside [0,1]")
    if any(x < 0 for x in data[10]) or data[11][0] < 0:
        raise ValueError("negative energy rate")
    if any(x < 0 for row in data[13:] for x in row):
        raise ValueError("negative travel time")
    if any(a[2] < 0 or a[5] < a[4] for a in nodes.values()):
        raise ValueError("negative service time or reversed raw window")
    # The selected target is Uber-format: README explicitly requires x2.
    travel = [[Decimal(2) * x for x in row] for row in data[13:]]
    return Instance(h[0], h[1], Decimal(h[-1]), nodes, origins, dest,
                    stations, data[5], data[6], data[7], data[8], data[9],
                    dict(zip(stations, data[10])), data[11][0], data[12], travel)


def updates(target: dict[str, Any]) -> dict[str, Decimal]:
    raw = target.get("updates", {})
    if not isinstance(raw, dict):
        raise ValueError("updates must be an object")
    allowed = {"travel_multiplier", "charge_multiplier", "consumption_multiplier",
               "window_shift", "window_scale"}
    if set(raw) - allowed:
        raise ValueError("unsupported update")
    out = {name: decimal(raw.get(name, "0" if name == "window_shift" else "1"))
           for name in allowed}
    if any(out[n] <= 0 for n in allowed if n != "window_shift"):
        raise ValueError("multipliers and scale must be positive")
    return out


@dataclass
class LP:
    vehicle: int
    route: list[int]
    rows: list[tuple[str, dict[int, Decimal], Decimal]]
    lower: list[Decimal]
    upper: list[Decimal]
    cost: list[Decimal]
    travel: Decimal
    ride_constant: Decimal


def build(ins: Instance, target: dict[str, Any]) -> list[LP]:
    u = updates(target)
    routes = target.get("routes")
    if not isinstance(routes, list) or len(routes) != ins.vehicles:
        raise ValueError("one fixed route per vehicle is required")
    counts: Counter[int] = Counter()
    models: list[LP] = []
    for v, route in enumerate(routes):
        if (not isinstance(route, list) or len(route) < 2 or
                any(type(node) is not int for node in route)):
            raise ValueError("route requires integer node identifiers")
        if route[0] != ins.origins[v] or route[-1] not in ins.destinations:
            raise ValueError("route has invalid vehicle origin or destination")
        if len(route) != len(set(route)) or any(node not in ins.nodes for node in route):
            raise ValueError("route repeats or refers to absent node")
        pos = {node: j for j, node in enumerate(route)}
        load = Decimal(0)
        for node in route:
            load += ins.nodes[node][3]
            if not Decimal(0) <= load <= ins.seats[v]:
                raise ValueError("seating/load constraint violated by fixed route")
            if node in ins.stations and load != 0:
                raise ValueError("charging station visited with passengers")
            if 1 <= node <= 2 * ins.users:
                counts[node] += 1
            if 1 <= node <= ins.users:
                if node + ins.users not in pos or pos[node] >= pos[node + ins.users]:
                    raise ValueError("pickup-dropoff pairing/precedence violated")
        if load != 0:
            raise ValueError("route ends with passengers")
        m = len(route)
        T, C, B = lambda j: j, lambda j: m + j, lambda j: 2 * m + j
        # Finite BASE bounds are independent of the dynamically transformed
        # time windows. This preserves shifted windows rather than clipping.
        lower = [Decimal(0)] * (3 * m)
        upper = ([ins.horizon] * m +
                 [ins.horizon if node in ins.stations else Decimal(0) for node in route] +
                 [ins.battery[v]] * m)
        rows: list[tuple[str, dict[int, Decimal], Decimal]] = []

        def add(name: str, terms: list[tuple[int, Decimal | int]], rhs: Decimal) -> None:
            coeff: dict[int, Decimal] = {}
            for i, a in terms:
                coeff[i] = coeff.get(i, Decimal(0)) + decimal(a)
            rows.append((name, {i: a for i, a in coeff.items() if a}, rhs))

        for j, node in enumerate(route):
            for kind, index in (("T", T(j)), ("C", C(j)), ("B", B(j))):
                add(f"bound:{v}:{kind}:{j}:lower", [(index, -1)], -lower[index])
                add(f"bound:{v}:{kind}:{j}:upper", [(index, 1)], upper[index])
            raw = ins.nodes[node]
            lo = raw[4] + u["window_shift"]
            hi = lo + (raw[5] - raw[4]) * u["window_scale"]
            add(f"window:{v}:{j}:lower", [(T(j), -1)], -lo)
            add(f"window:{v}:{j}:upper", [(T(j), 1)], hi)
        add(f"initial:{v}:positive", [(B(0), 1)], ins.initial[v])
        add(f"initial:{v}:negative", [(B(0), -1)], -ins.initial[v])
        add(f"end_reserve:{v}", [(B(m - 1), -1)], -ins.reserve[v] * ins.battery[v])
        drive = Decimal(0)
        const = Decimal(0)
        for j, node in enumerate(route):
            rate = ins.alpha.get(node, Decimal(0)) * u["charge_multiplier"]
            add(f"charge_cap:{v}:{j}", [(B(j), 1), (C(j), rate)], ins.battery[v])
            if j + 1 == m:
                continue
            other = route[j + 1]
            travel = ins.travel[node - 1][other - 1] * u["travel_multiplier"]
            drive += travel
            service = ins.nodes[node][2]
            add(f"arc_time:{v}:{j}", [(T(j), 1), (C(j), 1), (T(j + 1), -1)],
                -service - travel)
            consumption = ins.beta * u["consumption_multiplier"] * travel
            add(f"arc_energy:{v}:{j}:positive", [(B(j + 1), 1), (B(j), -1), (C(j), -rate)], -consumption)
            add(f"arc_energy:{v}:{j}:negative", [(B(j + 1), -1), (B(j), 1), (C(j), rate)], consumption)
        cost = [Decimal(0)] * (3 * m)
        for node in route:
            if 1 <= node <= ins.users:
                p, d = pos[node], pos[node + ins.users]
                service = ins.nodes[node][2]
                direct = ins.travel[node - 1][node + ins.users - 1] * u["travel_multiplier"]
                add(f"ride_max:{v}:{node}", [(T(d), 1), (T(p), -1)], ins.ride[node - 1] + service)
                add(f"ride_min:{v}:{node}", [(T(p), 1), (T(d), -1)], -direct - service)
                cost[T(d)] += ins.weight[1]
                cost[T(p)] -= ins.weight[1]
                const += service + direct
        models.append(LP(v, route[:], rows, lower, upper, cost, drive, const))
    if counts != Counter(range(1, 2 * ins.users + 1)):
        raise ValueError("all pickups and dropoffs must occur exactly once")
    return models


def _float_rows(model: LP) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.zeros((len(model.rows), len(model.cost)))
    rhs = np.zeros(len(model.rows))
    for k, (_, terms, value) in enumerate(model.rows):
        rhs[k] = float(value)
        for j, a in terms.items():
            matrix[k, j] = float(a)
    if not np.isfinite(matrix).all() or not np.isfinite(rhs).all():
        raise ValueError("model exceeds floating solver numeric range")
    return matrix, rhs


def _row_violation(model: LP, values: list[Decimal]) -> Decimal:
    return max([Decimal(0)] + [sum((a * values[j] for j, a in terms.items()),
                                   Decimal(0)) - rhs
                              for _, terms, rhs in model.rows])


def _farkas(model: LP, matrix: np.ndarray, rhs: np.ndarray) -> dict[str, Any] | None:
    # Direct standard LP alternative: find y>=0, sum(y)=1, A^T y=0,
    # minimizing b^T y. The returned decimals are accepted only after a
    # conservative, bounded-residual check in original Decimal coefficients.
    eq = np.vstack((matrix.T, np.ones(len(rhs))))
    eq_rhs = np.zeros(eq.shape[0])
    eq_rhs[-1] = 1.0
    dual = linprog(rhs, A_eq=eq, b_eq=eq_rhs, bounds=(0, None), method="highs",
                   options={"dual_feasibility_tolerance": 1e-9,
                            "primal_feasibility_tolerance": 1e-9})
    if not dual.success or dual.fun >= -1e-9:
        return None
    ys = [decimal(format(max(0.0, float(x)), ".17g")) for x in dual.x]
    residual = [Decimal(0)] * len(model.cost)
    contradiction = Decimal(0)
    selected = []
    for (name, terms, bound), y in zip(model.rows, ys):
        if y == 0:
            continue
        contradiction += y * bound
        selected.append({"id": name, "multiplier": ds(y)})
        for j, a in terms.items():
            residual[j] += y * a
    lower_bound = sum((min(r * lo, r * hi)
                       for r, lo, hi in zip(residual, model.lower, model.upper)), Decimal(0))
    if contradiction >= lower_bound - Decimal("1e-9"):
        return None
    return {"type": "bounded-farkas/v1", "vehicle": model.vehicle, "rows": selected,
            "contradiction": ds(contradiction), "residual_lower_bound": ds(lower_bound)}


def solve(target: dict[str, Any], *, cache: bool = False) -> dict[str, Any]:
    try:
        task_hash = canonical_hash(target)
    except Exception:
        task_hash = hashlib.sha256(b"invalid-task").hexdigest()
    base: dict[str, Any] = {"schema": SCHEMA, "task_hash": task_hash,
                            "status": "UNRESOLVED", "vehicles": [], "objective": "0",
                            "witness": {}, "scope": SCOPE}
    if cache and task_hash in _EXACT_CACHE:
        return json.loads(json.dumps(_EXACT_CACHE[task_hash]))
    try:
        if not isinstance(target, dict):
            raise ValueError("task must be a JSON object")
        if target.get("adapter_id") != "eadarp-temporal/v1":
            raise ValueError("unsupported adapter")
        text = target["instance_text"]
        actual_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if actual_sha != target.get("instance_sha256"):
            raise ValueError("raw instance SHA256 mismatch")
        with localcontext() as ctx:
            ctx.prec = 50
            ins = parse(text)
            models = build(ins, target)
            certificates = []
            objective = Decimal(0)
            for model in models:
                matrix, rhs = _float_rows(model)
                optimization_cost = [float(c) for c in model.cost]
                m = len(model.route)
                for j in range(m, 2 * m):
                    optimization_cost[j] += 1e-9
                result = linprog(optimization_cost, A_ub=matrix, b_ub=rhs,
                                 bounds=[(None, None)] * len(model.cost), method="highs",
                                 options={"dual_feasibility_tolerance": 1e-9,
                                          "primal_feasibility_tolerance": 1e-9})
                if not result.success:
                    witness = _farkas(model, matrix, rhs) if result.status == 2 else None
                    if witness is not None:
                        base.update(status="INFEASIBLE", witness=witness)
                    else:
                        base["witness"] = {"type": "solver-unresolved/v1", "vehicle": model.vehicle,
                                           "solver_status": int(result.status), "message": str(result.message)}
                    return base
                values = [decimal(format(float(x), ".17g")) for x in result.x]
                violation = _row_violation(model, values)
                if violation > TOL:
                    base["witness"] = {"type": "numerical-unresolved/v1", "vehicle": model.vehicle,
                                       "max_violation": ds(violation)}
                    return base
                m = len(model.route)
                certificates.append({"vehicle": model.vehicle, "route": model.route,
                                     "start_min": [ds(x) for x in values[:m]],
                                     "charge_min": [ds(x) for x in values[m:2 * m]],
                                     "arrival_kwh": [ds(x) for x in values[2 * m:]]})
                excess = sum((model.cost[j] * values[j] for j in range(len(values))), Decimal(0))
                objective += ins.weight[0] * model.travel + excess - ins.weight[1] * model.ride_constant
            base.update(status="FEASIBLE", vehicles=certificates, objective=ds(objective),
                        witness={"type": "primal/v1", "algorithm": "standalone direct LP; SciPy HiGHS",
                                 "max_decimal_row_violation": ds(max(_row_violation(m, [decimal(s) for s in
                                     c["start_min"] + c["charge_min"] + c["arrival_kwh"]])
                                     for m, c in zip(models, certificates)))})
    except (ValueError, KeyError, TypeError, OverflowError, IndexError) as exc:
        base["witness"] = {"type": "input-unresolved/v1", "message": str(exc)}
    if cache and base["status"] in {"FEASIBLE", "INFEASIBLE"}:
        _EXACT_CACHE[task_hash] = json.loads(json.dumps(base))
    return base


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    target = json.loads(args.target.read_text()) if args.target else json.load(__import__("sys").stdin)
    result = solve(target)
    raw = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(raw)
    else:
        print(raw, end="")


if __name__ == "__main__":
    main()
