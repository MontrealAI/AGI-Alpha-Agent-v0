# SPDX-License-Identifier: Apache-2.0
"""Independent Decimal certificate checker for declared fixed-order Uber e-ADARP.

Reconstructs the TU Wien raw format and equations without importing the producer,
adaptation, solver, or its rows. This is a tolerance-qualified mathematical check
of a declared linear model, never a physical-fleet or uncertainty certificate.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import re
from typing import Any, Sequence

SCOPE = "declared-eADARP-linear-model-only"
TOL = Decimal("0.0000001")
FARKAS_MARGIN = Decimal("0.000000001")
UPDATES = {"travel_multiplier", "charge_multiplier", "consumption_multiplier", "window_shift", "window_scale"}
TARGET_KEYS = {"id", "adapter_id", "instance_text", "instance_sha256", "routes", "updates", "assumptions", "need"}
ARTIFACT_KEYS = {"schema", "task_hash", "status", "vehicles", "objective", "witness", "scope"}
ASSUMPTIONS = [
    "linear-charge-and-discharge", "fixed-orders-and-complete-passenger-pairs",
    "independent-vehicles-unlimited-station-concurrency", "declared-travel-times-not-real-dispatch",
    "numerical-tolerance-1e-7",
]


def _digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _exact(value: Any, keys: set[str]) -> None:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("unsupported or missing record fields")


def _dec(value: Any) -> Decimal:
    if not isinstance(value, str) or len(value) > 80 or not re.fullmatch(
        r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value
    ):
        raise ValueError("finite bounded decimal strings required")
    result = Decimal(value)
    exponent = result.as_tuple().exponent
    if not result.is_finite() or abs(result) > Decimal("1e12") or not isinstance(exponent, int) or exponent < -30:
        raise ValueError("decimal outside supported magnitude/precision")
    return result


def _str(value: Decimal) -> str:
    return format(value, "f") if value else "0"


def _integers(line: list[str]) -> list[int]:
    if any(not re.fullmatch(r"[1-9][0-9]{0,4}", token) for token in line):
        raise ValueError("positive integer node identifiers required")
    return [int(token) for token in line]


def _read(target: dict[str, Any]) -> dict[str, Any]:
    _exact(target, TARGET_KEYS)
    if target["adapter_id"] != "eadarp-temporal/v1":
        raise ValueError("unsupported adapter")
    if not isinstance(target["id"], str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", target["id"]):
        raise ValueError("bounded explicit task identity required")
    if not isinstance(target["need"], str) or not 1 <= len(target["need"].strip()) <= 2000:
        raise ValueError("explicit bounded target need required")
    assumptions = target["assumptions"]
    if not isinstance(assumptions, list) or not assumptions or len(assumptions) > 20 or any(
        not isinstance(item, str) or not item.strip() or len(item) > 1000 for item in assumptions
    ):
        raise ValueError("explicit bounded linear-model assumptions required")
    if len(set(assumptions)) != len(assumptions) or set(assumptions) != set(ASSUMPTIONS):
        raise ValueError("exact declared linear-model assumptions required; unsupported extensions rejected")
    raw = target["instance_text"]
    if not isinstance(raw, str) or not 0 < len(raw.encode()) <= 250000:
        raise ValueError("bounded raw UTF-8 instance text required")
    if hashlib.sha256(raw.encode("utf-8")).hexdigest() != target["instance_sha256"]:
        raise ValueError("raw instance SHA-256 mismatch (preserve original CR/LF bytes)")
    lines = [line.split() for line in raw.splitlines()]
    if not lines or any(not line for line in lines):
        raise ValueError("empty raw instance rows are unsupported")
    head = _integers(lines[0])
    if len(head) != 7:
        raise ValueError("seven-field header required")
    vehicles, users, common_origins, common_ends, station_count, replications, horizon_i = head
    if not (vehicles <= 20 and users <= 100 and station_count <= 100 and replications <= 10 and horizon_i <= 100000):
        raise ValueError("instance size exceeds supported bounds")
    nodes: dict[int, list[Decimal]] = {}
    position = 1
    while position < len(lines) and len(lines[position]) == 7:
        fields = lines[position]
        node = _integers(fields[:1])[0]
        if node in nodes:
            raise ValueError("duplicate node id")
        nodes[node] = [_dec(token) for token in fields[1:]]
        position += 1
    count = len(nodes)
    if not 2 * users + vehicles < count <= 400 or set(nodes) != set(range(1, count + 1)):
        raise ValueError("node set must be contiguous and include all service/depot nodes")
    data = lines[position:]
    if len(data) != 13 + count:
        raise ValueError("full explicit Uber travel matrix required; Euclidean inference is unsupported")
    origin_common, end_common, origins, destinations, stations = [_integers(line) for line in data[:5]]
    if len(origin_common) != common_origins or len(end_common) != common_ends or len(origins) != vehicles:
        raise ValueError("depot/header cardinality mismatch")
    if len(stations) != station_count * replications or not destinations:
        raise ValueError("station/header cardinality mismatch")
    groups = [set(range(1, 2 * users + 1)), set(origin_common), set(end_common), set(origins),
              set(destinations), set(stations)]
    all_ids = origin_common + end_common + origins + destinations + stations
    if any(len(group) != len(ids) for group, ids in zip(groups[1:],
           [origin_common, end_common, origins, destinations, stations])):
        raise ValueError("duplicate depot/station ids")
    if set(all_ids) | groups[0] != set(nodes) or sum(map(len, groups)) != count:
        raise ValueError("service, depot, station roles must partition raw nodes")
    ride, capacity, initial, battery, reserve, rates, discharge, weights = [
        [_dec(token) for token in line] for line in data[5:13]
    ]
    if [len(item) for item in (ride, capacity, initial, battery, reserve, rates, discharge, weights)] != [
        users, vehicles, vehicles, vehicles, vehicles, len(stations), 1, 2
    ]:
        raise ValueError("parameter cardinality mismatch")
    physical = (ride, capacity, initial, battery, reserve, rates, discharge, weights)
    if any(value < 0 for row in physical for value in row):
        raise ValueError("negative physical parameter")
    if any(value <= 0 for value in battery + rates + discharge) or any(value > 1 for value in reserve):
        raise ValueError("invalid battery/rate/reserve parameter")
    if any(initial[v] > battery[v] for v in range(vehicles)):
        raise ValueError("initial battery exceeds capacity")
    for node, values in nodes.items():
        _, _, service, seats, low, high = values
        expected = Decimal(1 if node <= users else -1 if node <= 2 * users else 0)
        if service < 0 or low < 0 or high < low or seats != expected:
            raise ValueError("unsupported node time/load declaration")
    matrix = [[_dec(token) for token in row] for row in data[13:]]
    if any(len(row) != count or any(value < 0 for value in row) for row in matrix):
        raise ValueError("nonnegative square travel matrix required")
    if any(matrix[j][j] != 0 for j in range(count)):
        raise ValueError("travel matrix diagonal must be zero")
    _exact(target["updates"], UPDATES)
    updates = {name: _dec(value) for name, value in target["updates"].items()}
    if any(updates[name] <= 0 for name in UPDATES - {"window_shift"}):
        raise ValueError("strictly positive update multipliers required")
    routes = target["routes"]
    if not isinstance(routes, list) or len(routes) != vehicles:
        raise ValueError("one fixed route per vehicle required")
    served: list[int] = []
    for v, route in enumerate(routes):
        if not isinstance(route, list) or not 2 <= len(route) <= count or any(type(node) is not int for node in route):
            raise ValueError("bounded integer route required")
        if len(set(route)) != len(route) or any(node not in nodes for node in route):
            raise ValueError("duplicate or unknown route node")
        if route[0] != origins[v] or route[-1] not in destinations:
            raise ValueError("incorrect vehicle origin or final depot")
        if any(node in set(origin_common + end_common + origins + destinations) for node in route[1:-1]):
            raise ValueError("interior depot visit unsupported")
        seats = Decimal(0)
        positions = {node: j for j, node in enumerate(route)}
        for j, node in enumerate(route):
            seats += nodes[node][3]
            if seats < 0 or seats > capacity[v] or (node in stations and seats != 0):
                raise ValueError("route violates seats/no-passenger-charging structural boundary")
            if node <= users:
                if node + users not in positions or positions[node + users] <= j:
                    raise ValueError("pickup must precede its matching drop on the same vehicle")
                served.append(node)
            elif node <= 2 * users and node - users not in positions:
                raise ValueError("drop has no pickup on this vehicle")
        if seats != 0:
            raise ValueError("vehicle ends with passengers")
    if sorted(served) != list(range(1, users + 1)):
        raise ValueError("serve every user exactly once across routes")
    return {"vehicles": vehicles, "users": users, "horizon": Decimal(horizon_i), "nodes": nodes,
            "routes": routes, "stations": dict(zip(stations, rates)), "ride": ride, "capacity": capacity,
            "initial": initial, "battery": battery, "reserve": reserve, "weights": weights,
            "travel": [[value * 2 * updates["travel_multiplier"] for value in row] for row in matrix],
            "discharge": discharge[0] * updates["consumption_multiplier"], "updates": updates}


def _model(ins: dict[str, Any]) -> dict[str, Any]:
    variables: list[dict[str, str]] = []
    rows: list[dict[str, Any]] = []
    indices: dict[str, int] = {}
    objective: dict[int, Decimal] = {}
    constant = Decimal(0)
    vehicle_constants = [Decimal(0)] * ins["vehicles"]

    def variable(name: str, upper: Decimal) -> int:
        index = len(variables)
        indices[name] = index
        variables.append({"name": name, "lower": "0", "upper": _str(upper)})
        return index

    def row(name: str, terms: Sequence[tuple[int, Decimal | int]], rhs: Decimal) -> None:
        coefficients: dict[int, Decimal] = {}
        for index, coefficient in terms:
            coefficients[index] = coefficients.get(index, Decimal(0)) + Decimal(coefficient)
        terms_out = [[index, _str(value)] for index, value in sorted(coefficients.items()) if value]
        rows.append({"name": name, "terms": terms_out, "rhs": _str(rhs)})

    def equality(name: str, terms: Sequence[tuple[int, Decimal | int]], rhs: Decimal) -> None:
        row(name + ":positive", terms, rhs)
        row(name + ":negative", [(index, -Decimal(coefficient)) for index, coefficient in terms], -rhs)

    for v, route in enumerate(ins["routes"]):
        for j in range(len(route)):
            variable(f"T:{v}:{j}", ins["horizon"])
        for j, node in enumerate(route):
            variable(f"C:{v}:{j}", ins["horizon"] if node in ins["stations"] else Decimal(0))
        for j in range(len(route)):
            variable(f"B:{v}:{j}", ins["battery"][v])
    # Every bound is included in Ax <= b, even though finite bounds are also
    # retained separately for a rigorous nonzero dual-residual certificate.
    for index, item in enumerate(variables):
        kind, vehicle, stop = item["name"].split(":")
        name = f"bound:{vehicle}:{kind}:{stop}"
        row(name + ":lower", [(index, -1)], Decimal(0))
        row(name + ":upper", [(index, 1)], Decimal(item["upper"]))
    for v, route in enumerate(ins["routes"]):
        def T(j: int) -> int:
            return indices[f"T:{v}:{j}"]

        def B(j: int) -> int:
            return indices[f"B:{v}:{j}"]

        def C(j: int) -> int:
            return indices[f"C:{v}:{j}"]

        positions = {node: j for j, node in enumerate(route)}
        equality(f"initial:{v}", [(B(0), 1)], ins["initial"][v])
        row(f"end_reserve:{v}", [(B(len(route) - 1), -1)], -ins["reserve"][v] * ins["battery"][v])
        for j, node in enumerate(route):
            low = ins["nodes"][node][4] + ins["updates"]["window_shift"]
            high = low + (ins["nodes"][node][5] - ins["nodes"][node][4]) * ins["updates"]["window_scale"]
            row(f"window:{v}:{j}:lower", [(T(j), -1)], -low)
            row(f"window:{v}:{j}:upper", [(T(j), 1)], high)
            rate = ins["stations"].get(node, Decimal(0)) * ins["updates"]["charge_multiplier"]
            charge = [(C(j), rate)]
            row(f"charge_cap:{v}:{j}", [(B(j), 1)] + charge, ins["battery"][v])
            if j + 1 < len(route):
                travel = ins["travel"][node - 1][route[j + 1] - 1]
                service = ins["nodes"][node][2]
                duration = [(C(j), 1)]
                row(f"arc_time:{v}:{j}", [(T(j), 1), (T(j + 1), -1)] + duration, -service - travel)
                equality(f"arc_energy:{v}:{j}", [(B(j + 1), 1), (B(j), -1)] +
                         [(index, -coefficient) for index, coefficient in charge], -ins["discharge"] * travel)
                constant += ins["weights"][0] * travel
                vehicle_constants[v] += ins["weights"][0] * travel
            if node <= ins["users"]:
                drop = positions[node + ins["users"]]
                direct = ins["travel"][node - 1][node + ins["users"] - 1]
                service = ins["nodes"][node][2]
                row(f"ride_max:{v}:{node}", [(T(drop), 1), (T(j), -1)], ins["ride"][node - 1] + service)
                row(f"ride_min:{v}:{node}", [(T(j), 1), (T(drop), -1)], -direct - service)
                objective[T(drop)] = objective.get(T(drop), Decimal(0)) + ins["weights"][1]
                objective[T(j)] = objective.get(T(j), Decimal(0)) - ins["weights"][1]
                constant -= ins["weights"][1] * (service + direct)
                vehicle_constants[v] -= ins["weights"][1] * (service + direct)
    return {"variables": variables, "rows": rows,
            "vehicle_constants": [_str(value) for value in vehicle_constants],
            "objective": {"terms": [[index, _str(value)] for index, value in sorted(objective.items()) if value],
                          "constant": _str(constant)}}


def _portable(model: dict[str, Any], vehicles: int) -> dict[str, Any]:
    result = []
    for vehicle in range(vehicles):
        selected = [index for index, item in enumerate(model["variables"])
                    if int(item["name"].split(":")[1]) == vehicle]
        local = {index: position for position, index in enumerate(selected)}
        rows = []
        for row in model["rows"]:
            if int(row["name"].split(":")[1]) == vehicle:
                rows.append({"name": row["name"], "terms": [[local[index], value] for index, value in row["terms"]],
                             "rhs": row["rhs"]})
        objective = [[local[index], value] for index, value in model["objective"]["terms"] if index in local]
        result.append({"vehicle": vehicle, "variables": [model["variables"][index] for index in selected], "rows": rows,
                       "objective": {"terms": objective, "constant": model["vehicle_constants"][vehicle]}})
    return {"vehicles": result}


def independent_model(target: dict[str, Any]) -> dict[str, Any]:
    """Rebuild finite-bounded named Ax<=b rows directly from the raw target."""
    with localcontext() as context:
        context.prec = 250
        ins = _read(target)
        return _portable(_model(ins), ins["vehicles"])


def _model_decimal(value: Any) -> Decimal:
    """Read finite model coefficients, including products of bounded inputs."""
    if not isinstance(value, str) or len(value) > 240 or not re.fullmatch(
        r"[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", value
    ):
        raise ValueError("finite decimal-string model coefficient required")
    result = Decimal(value)
    exponent = result.as_tuple().exponent
    if not result.is_finite() or abs(result) > Decimal("1e60") or not isinstance(exponent, int) or exponent < -120:
        raise ValueError("model coefficient exceeds supported product bounds")
    return result


def _normalize_model(model: Any, routes: list[list[int]]) -> dict[int, Any]:
    """Normalize portable models by semantic names, with exact Decimal values."""
    _exact(model, {"vehicles"})
    if not isinstance(model["vehicles"], list) or len(model["vehicles"]) != len(routes):
        raise ValueError("model must include each independent vehicle exactly once")
    normalized = {}
    for vehicle in model["vehicles"]:
        if not isinstance(vehicle, dict) or not {"vehicle", "variables", "rows", "objective"} <= set(vehicle) or (
            set(vehicle) - {"vehicle", "variables", "rows", "objective", "route"}
        ):
            raise ValueError("unknown or missing vehicle-model fields")
        ident = vehicle["vehicle"]
        if type(ident) is not int or not 0 <= ident < len(routes) or ident in normalized:
            raise ValueError("duplicate or unknown model vehicle")
        if "route" in vehicle:
            route = vehicle["route"]
            if (not isinstance(route, list) or any(type(node) is not int for node in route) or
                    route != routes[ident]):
                raise ValueError("model route metadata differs from the actual target route")
        if not isinstance(vehicle["variables"], list) or len(vehicle["variables"]) != 3 * len(routes[ident]):
            raise ValueError("model must contain exactly three variables per route position")
        names = []
        bounds = {}
        for variable in vehicle["variables"]:
            _exact(variable, {"name", "lower", "upper"})
            name = variable["name"]
            if not isinstance(name, str) or not 1 <= len(name) <= 120 or name in bounds:
                raise ValueError("duplicate or malformed model variable name")
            names.append(name)
            bounds[name] = (_model_decimal(variable["lower"]), _model_decimal(variable["upper"]))

        def terms(values: Any) -> dict[str, Decimal]:
            if not isinstance(values, list) or len(values) > 10000:
                raise ValueError("bounded sparse model terms required")
            coefficients: dict[str, Decimal] = {}
            for term in values:
                if (not isinstance(term, list) or len(term) != 2 or type(term[0]) is not int or
                        not 0 <= term[0] < len(names)):
                    raise ValueError("sparse model coefficient index outside variable order")
                name = names[term[0]]
                coefficients[name] = coefficients.get(name, Decimal(0)) + _model_decimal(term[1])
            return {name: value for name, value in coefficients.items() if value != 0}

        if not isinstance(vehicle["rows"], list) or len(vehicle["rows"]) > 20000:
            raise ValueError("bounded named model constraints required")
        rows = {}
        for row in vehicle["rows"]:
            _exact(row, {"name", "terms", "rhs"})
            name = row["name"]
            if not isinstance(name, str) or not 1 <= len(name) <= 120 or name in rows:
                raise ValueError("duplicate or malformed model row name")
            rows[name] = (terms(row["terms"]), _model_decimal(row["rhs"]))
        _exact(vehicle["objective"], {"terms", "constant"})
        objective = (terms(vehicle["objective"]["terms"]), _model_decimal(vehicle["objective"]["constant"]))
        normalized[ident] = {"bounds": bounds, "rows": rows, "objective": objective}
    return normalized


def semantic_model_equivalent(target: dict[str, Any], proposed: Any) -> bool:
    """Compare target-derived equations exactly, independent of model serialization.

    Known route metadata is checked against the target. Vehicle, variable, row
    and term ordering, harmless zero terms and equivalent decimal spelling do
    not affect correspondence. Any changed named equation/bound/objective does.
    """
    try:
        with localcontext() as context:
            context.prec = 250
            ins = _read(target)
            expected = _portable(_model(ins), ins["vehicles"])
            return _normalize_model(proposed, ins["routes"]) == _normalize_model(expected, ins["routes"])
    except (ValueError, TypeError, KeyError, InvalidOperation, OverflowError, IndexError):
        return False


def _feasible(ins: dict[str, Any], model: dict[str, Any], artifact: dict[str, Any]) -> list[str]:
    vehicles = artifact["vehicles"]
    if not isinstance(vehicles, list) or len(vehicles) != ins["vehicles"]:
        raise ValueError("one aligned vehicle certificate required per route")
    values: dict[str, Decimal] = {}
    for v, item in enumerate(vehicles):
        _exact(item, {"vehicle", "route", "start_min", "charge_min", "arrival_kwh"})
        route = ins["routes"][v]
        if (type(item["vehicle"]) is not int or item["vehicle"] != v or item["route"] != route or
                not isinstance(item["route"], list) or any(type(node) is not int for node in item["route"])):
            raise ValueError("certificate route/vehicle differs from target")
        for field, prefix in (("start_min", "T"), ("charge_min", "C"), ("arrival_kwh", "B")):
            if not isinstance(item[field], list) or len(item[field]) != len(route):
                raise ValueError("certificate arrays must align with every route position")
            for j, token in enumerate(item[field]):
                value = _dec(token)
                if prefix == "C" and route[j] not in ins["stations"]:
                    if value != 0:
                        raise ValueError("non-station charging is forbidden")
                values[f"{prefix}:{v}:{j}"] = value
    vector = [values[item["name"]] for item in model["variables"]]
    reasons = []
    for row in model["rows"]:
        left = sum((Decimal(coefficient) * vector[index] for index, coefficient in row["terms"]), Decimal(0))
        if left > Decimal(row["rhs"]) + TOL:
            reasons.append("violated " + row["name"])
            if len(reasons) >= 12:
                return reasons
    objective = Decimal(model["objective"]["constant"]) + sum(
        (Decimal(coefficient) * vector[index] for index, coefficient in model["objective"]["terms"]), Decimal(0)
    )
    if abs(objective - _dec(artifact["objective"])) > TOL:
        reasons.append("declared objective differs from independently reconstructed updated travel/excess ride")
    return reasons


def _infeasible(model: dict[str, Any], witness: Any) -> list[str]:
    allowed = {"type", "vehicle", "rows", "contradiction", "residual_lower_bound"}
    if not isinstance(witness, dict) or set(witness) - allowed or not {
        "type", "vehicle", "rows", "contradiction"
    } <= set(witness) or witness["type"] != "bounded-farkas/v1":
        raise ValueError("named nonnegative Farkas witness required")
    if type(witness["vehicle"]) is not int or not 0 <= witness["vehicle"] < len(model["vehicle_constants"]):
        raise ValueError("Farkas witness must identify a known vehicle")
    if not isinstance(witness["rows"], list) or not 1 <= len(witness["rows"]) <= len(model["rows"]):
        raise ValueError("bounded nonempty dual row list required")
    named = {row["name"]: row for row in model["rows"]}
    residual = [Decimal(0)] * len(model["variables"])
    weighted_rhs = Decimal(0)
    seen = set()
    for item in witness["rows"]:
        _exact(item, {"id", "multiplier"})
        if item["id"] not in named or item["id"] in seen:
            raise ValueError("unknown or repeated Farkas row id")
        seen.add(item["id"])
        if int(item["id"].split(":")[1]) != witness["vehicle"]:
            raise ValueError("Farkas rows must belong to the named independent vehicle")
        multiplier = _dec(item["multiplier"])
        if multiplier < 0:
            raise ValueError("negative Farkas multiplier")
        row = named[item["id"]]
        weighted_rhs += multiplier * Decimal(row["rhs"])
        for index, coefficient in row["terms"]:
            residual[index] += multiplier * Decimal(coefficient)
    residual_lower = sum((min(coefficient * Decimal(variable["lower"]), coefficient * Decimal(variable["upper"]))
                          for coefficient, variable in zip(residual, model["variables"])), Decimal(0))
    gap = residual_lower - weighted_rhs
    if "residual_lower_bound" in witness:
        # Equivalent frozen-control serialization: contradiction names y^T b,
        # while residual_lower_bound names min_{L<=x<=U} (A^T y)^T x.
        # Check both exact finite Decimal quantities, then independently test
        # their strictly positive separation; neither declaration supplies math.
        if (_dec(witness["contradiction"]) != weighted_rhs or
                _dec(witness["residual_lower_bound"]) != residual_lower):
            return ["declared weighted RHS or residual lower bound differs from independent reconstruction"]
    elif abs(_dec(witness["contradiction"]) - gap) > TOL:
        return ["declared dual contradiction differs from independently reconstructed bounded residual gap"]
    if gap <= FARKAS_MARGIN:
        return ["dual witness does not rigorously separate all finite-bounded feasible points"]
    return []


def check(target: dict[str, Any], artifact: dict[str, Any], constructed: Any = None) -> dict[str, Any]:
    """Return a strict bound-to-task verdict; reject uncertainty and unknown fields."""
    reasons: list[str] = []
    artifact_hash = ""
    task_id = target.get("id", "") if isinstance(target, dict) else ""
    decisive = False
    try:
        artifact_hash = _digest(artifact)
        with localcontext() as context:
            context.prec = 250
            ins = _read(target)
            _exact(artifact, ARTIFACT_KEYS)
            if artifact["schema"] != "agialpha/eadarp-certificate/v1" or artifact["scope"] != SCOPE:
                raise ValueError("certificate schema/scope mismatch")
            if artifact["task_hash"] != _digest(target):
                raise ValueError("certificate task hash mismatch")
            model = _model(ins)
            # Constructed rows never supply equations to this checker. Compare
            # their semantics exactly; incidental serialization is not a test.
            if (isinstance(constructed, dict) and "model" in constructed and
                    _normalize_model(constructed["model"], ins["routes"]) !=
                    _normalize_model(_portable(model, ins["vehicles"]), ins["routes"])):
                raise ValueError("constructed rows differ from independent raw-instance model")
            if artifact["status"] == "FEASIBLE":
                if artifact["witness"] not in ({}, None):
                    witness = artifact["witness"]
                    if (not isinstance(witness, dict) or witness.get("type") != "primal/v1" or
                            set(witness) - {"type", "algorithm", "max_decimal_row_violation"}):
                        raise ValueError("unknown primal witness metadata")
                    if "algorithm" in witness and (not isinstance(witness["algorithm"], str) or
                            not 1 <= len(witness["algorithm"]) <= 200):
                        raise ValueError("bounded inert algorithm description required")
                    if "max_decimal_row_violation" in witness and _dec(witness["max_decimal_row_violation"]) < 0:
                        raise ValueError("negative claimed residual")
                reasons = _feasible(ins, model, artifact)
                decisive = not reasons
            elif artifact["status"] == "INFEASIBLE":
                if artifact["vehicles"] != []:
                    raise ValueError("infeasible certificate must not contain primal vehicle values")
                _dec(artifact["objective"])
                reasons = _infeasible(model, artifact["witness"])
                decisive = not reasons
            elif artifact["status"] == "UNRESOLVED":
                reasons = ["solver could not provide an independently decisive certificate"]
            else:
                raise ValueError("unknown certificate status")
    except (ValueError, TypeError, KeyError, InvalidOperation, OverflowError, IndexError) as error:
        reasons = [str(error)]
    return {"accepted": bool(decisive and not reasons), "task_id": task_id, "artifact_hash": artifact_hash,
            "decisive": bool(decisive and not reasons), "reasons": reasons, "scope": SCOPE,
            "feasibility_tolerance": _str(TOL), "farkas_strict_margin": _str(FARKAS_MARGIN)}
