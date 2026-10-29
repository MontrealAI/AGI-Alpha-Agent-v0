# SPDX-License-Identifier: Apache-2.0
"""Seed-funded fixed-order construction for a shared physical charging port.

The wrapped independent-station contract is a per-vehicle relaxation only. This
contract replaces its concurrency assumption with one port per physical station.
Numerical feasibility is checked; global optimality and physical operation are not.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, InvalidOperation, localcontext
import itertools
from pathlib import Path
import re
import time
from typing import Any

from ..structural_transfer import eadarp, eadarp_check
from ..structural_transfer.contracts import digest, read, write_new

TASK_SCHEMA = "agialpha/shared-charger-task/v1"
RESULT_SCHEMA = "agialpha/shared-charger-result/v1"
SCOPE = "declared-fixed-order-linear-charge-shared-port-model-only"
TOL = Decimal("0.0000001")


def _stations(base: dict[str, Any]) -> tuple[list[int], dict[int, tuple[Decimal, Decimal]]]:
    lines = [line.split() for line in base["instance_text"].splitlines()]
    cursor = 1
    locations = {}
    while len(lines[cursor]) == 7:
        row = lines[cursor]
        locations[int(row[0])] = (Decimal(row[1]), Decimal(row[2]))
        cursor += 1
    return [int(node) for node in lines[cursor + 4]], locations


def wrap_target(base: dict[str, Any], *, task_id: str = "shared-charger") -> dict[str, Any]:
    """Group co-located declared station copies, without inventing new geometry."""
    eadarp_check.independent_model(base)
    stations, locations = _stations(base)
    groups: dict[tuple[Decimal, Decimal], list[int]] = {}
    for node in stations:
        groups.setdefault(locations[node], []).append(node)
    return {
        "schema": TASK_SCHEMA,
        "id": task_id,
        "base_target": base,
        "physical_stations": [
            {"id": f"station-{min(nodes)}", "nodes": nodes, "capacity": 1} for nodes in groups.values()
        ],
        "occupancy": "service-start-through-positive-charge-end",
        "funding": "initial-seed-funded-research",
        "time_limit_seconds": 30,
    }


def _validate(request: dict[str, Any]) -> tuple[dict[str, Any], dict[int, str]]:
    required = {"schema", "id", "base_target", "physical_stations", "occupancy", "funding", "time_limit_seconds"}
    if not isinstance(request, dict) or set(request) != required or request["schema"] != TASK_SCHEMA:
        raise ValueError("exact shared-charger task contract required")
    if not isinstance(request["id"], str) or not re.fullmatch(r"[A-Za-z0-9_.:/-]{1,120}", request["id"]):
        raise ValueError("bounded task identity required")
    if request["occupancy"] != "service-start-through-positive-charge-end":
        raise ValueError("unsupported occupancy semantics")
    if request["funding"] != "initial-seed-funded-research":
        raise ValueError("this construction has no earned-funding attribution")
    if type(request["time_limit_seconds"]) is not int or not 1 <= request["time_limit_seconds"] <= 60:
        raise ValueError("integer solver time ceiling from 1 through 60 seconds required")
    base = request["base_target"]
    eadarp_check.independent_model(base)
    stations, locations = _stations(base)
    groups = request["physical_stations"]
    if not isinstance(groups, list) or not 1 <= len(groups) <= 100:
        raise ValueError("complete bounded station partition required")
    node_group: dict[int, str] = {}
    ids = set()
    for group in groups:
        if not isinstance(group, dict) or set(group) != {"id", "nodes", "capacity"}:
            raise ValueError("exact physical station fields required")
        ident, nodes = group["id"], group["nodes"]
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", ident) or ident in ids:
            raise ValueError("unique bounded physical station identity required")
        ids.add(ident)
        if type(group["capacity"]) is not int or group["capacity"] != 1:
            raise ValueError("only one physical port per station is supported")
        if not isinstance(nodes, list) or not nodes or any(type(node) is not int for node in nodes):
            raise ValueError("explicit station-node list required")
        for node in nodes:
            if node not in stations or node in node_group:
                raise ValueError("station partition must cover each raw station exactly once")
            node_group[node] = ident
        if len({locations[node] for node in nodes}) != 1:
            raise ValueError("distinct physical locations cannot be called station replicas")
    if set(node_group) != set(stations):
        raise ValueError("unmapped raw station")
    # Equal raw station coordinates identify replicas in this declared contract.
    for left, right in itertools.combinations(stations, 2):
        if locations[left] == locations[right] and node_group[left] != node_group[right]:
            raise ValueError("co-located raw station replicas must share one physical port")
    events = [
        (vehicle, j)
        for vehicle, route in enumerate(base["routes"])
        for j, node in enumerate(route)
        if node in node_group
    ]
    if len(events) > 8:
        raise ValueError("at most eight charger visits are supported")
    return base, node_group


def _decimal(value: Any) -> Decimal:
    if not isinstance(value, str) or len(value) > 80:
        raise ValueError("bounded decimal string required")
    result = Decimal(value)
    if not result.is_finite() or abs(result) > Decimal("1e12"):
        raise ValueError("nonfinite or unbounded occupancy")
    return result


def check(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Independently reconstruct base equations and shared-port occupied intervals."""
    reasons: list[str] = []
    intervals = []
    try:
        base, node_group = _validate(request)
        if not isinstance(result, dict) or set(result) != {
            "schema",
            "task_hash",
            "status",
            "base_artifact",
            "resources",
            "scope",
        }:
            raise ValueError("exact shared-charger artifact required")
        if result["schema"] != RESULT_SCHEMA or result["task_hash"] != digest(request) or result["scope"] != SCOPE:
            raise ValueError("artifact task/schema/scope mismatch")
        if result["status"] != "FEASIBLE":
            raise ValueError("no independently checked feasible shared-port certificate")
        artifact = result["base_artifact"]
        verdict = eadarp_check.check(base, artifact)
        if not verdict["accepted"] or artifact["status"] != "FEASIBLE":
            raise ValueError("independent base acceptance failed: " + "; ".join(verdict["reasons"]))
        with localcontext() as context:
            context.prec = 100
            for vehicle in artifact["vehicles"]:
                for position, node in enumerate(vehicle["route"]):
                    if node not in node_group:
                        continue
                    start = _decimal(vehicle["start_min"][position])
                    duration = _decimal(vehicle["charge_min"][position])
                    if duration > TOL:
                        intervals.append(
                            {
                                "station": node_group[node],
                                "vehicle": vehicle["vehicle"],
                                "position": position,
                                "start_min": str(start),
                                "end_min": str(start + duration),
                            }
                        )
            for left, right in itertools.combinations(intervals, 2):
                if left["station"] != right["station"]:
                    continue
                overlap = min(Decimal(left["end_min"]), Decimal(right["end_min"])) - max(
                    Decimal(left["start_min"]), Decimal(right["start_min"])
                )
                if overlap > TOL:
                    reasons.append(
                        f"shared-port overlap: {left['vehicle']}:{left['position']} / "
                        f"{right['vehicle']}:{right['position']}"
                    )
    except (ValueError, TypeError, KeyError, IndexError, InvalidOperation) as error:
        reasons.append(str(error))
    return {
        "accepted": not reasons,
        "reasons": reasons,
        "occupied_intervals": intervals,
        "scope": SCOPE,
        "feasibility_tolerance": str(TOL),
        "global_optimality_checked": False,
    }


def solve(request: dict[str, Any]) -> dict[str, Any]:
    """Solve a joint bounded MILP; unsuccessful search remains unresolved, not proved infeasible."""
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp

    base, node_group = _validate(request)
    model = eadarp.compile_model(base)
    started, cpu = time.perf_counter(), time.process_time()
    variables: list[dict[str, Any]] = []
    offsets: list[int] = []
    rows: list[dict[int, float]] = []
    rhs: list[float] = []
    objective: list[float] = []
    for item in model["vehicles"]:
        offset = len(variables)
        offsets.append(offset)
        variables.extend(item["variables"])
        objective.extend([0.0] * len(item["variables"]))
        for index, coefficient in item["objective"]["terms"]:
            objective[offset + index] = float(coefficient)
        for row in item["rows"]:
            rows.append({offset + index: float(coefficient) for index, coefficient in row["terms"]})
            rhs.append(float(row["rhs"]))
    continuous_count = len(variables)
    events = []
    for item, offset in zip(model["vehicles"], offsets):
        length = len(item["route"])
        for position, node in enumerate(item["route"]):
            if node in node_group:
                events.append(
                    {
                        "station": node_group[node],
                        "time": offset + position,
                        "charge": offset + length + position,
                        "vehicle": item["vehicle"],
                    }
                )
    horizon = float(eadarp.parse(base)["horizon"])
    big_m = 2 * horizon

    def binary(name: str) -> int:
        index = len(variables)
        variables.append({"name": name, "lower": "0", "upper": "1"})
        objective.append(0.0)
        return index

    for index, event in enumerate(events):
        event["active"] = binary(f"active:{index}")
        rows.append({event["charge"]: 1, event["active"]: -horizon})
        rhs.append(0.0)
    for left, right in itertools.combinations(events, 2):
        if left["station"] != right["station"] or left["vehicle"] == right["vehicle"]:
            continue
        order = binary(f"precedence:{left['time']}:{right['time']}")
        rows.append(
            {
                left["time"]: 1,
                left["charge"]: 1,
                right["time"]: -1,
                order: big_m,
                left["active"]: big_m,
                right["active"]: big_m,
            }
        )
        rhs.append(3 * big_m)
        rows.append(
            {
                right["time"]: 1,
                right["charge"]: 1,
                left["time"]: -1,
                order: -big_m,
                left["active"]: big_m,
                right["active"]: big_m,
            }
        )
        rhs.append(2 * big_m)
    matrix = np.zeros((len(rows), len(variables)))
    for row, terms in enumerate(rows):
        for index, coefficient in terms.items():
            matrix[row, index] = coefficient
    result = milp(
        np.array(objective),
        integrality=np.r_[np.zeros(continuous_count), np.ones(len(variables) - continuous_count)],
        bounds=Bounds([float(v["lower"]) for v in variables], [float(v["upper"]) for v in variables]),
        constraints=LinearConstraint(matrix, -np.inf, rhs),
        options={"time_limit": request["time_limit_seconds"], "mip_rel_gap": 0.0},
    )
    artifact: dict[str, Any] = {}
    if result.x is not None:
        schedules, total = [], Decimal(0)
        for item, offset in zip(model["vehicles"], offsets):
            length = len(item["route"])
            values = [format(float(x), ".15g") for x in result.x[offset : offset + 3 * length]]
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
                (Decimal(coefficient) * Decimal(values[index]) for index, coefficient in item["objective"]["terms"]),
                Decimal(0),
            )
        artifact = {
            "schema": "agialpha/eadarp-certificate/v1",
            "task_hash": digest(base),
            "status": "FEASIBLE",
            "vehicles": schedules,
            "objective": str(total),
            "witness": {},
            "scope": "declared-eADARP-linear-model-only",
        }
    return {
        "schema": RESULT_SCHEMA,
        "task_hash": digest(request),
        "status": "FEASIBLE" if artifact else "UNRESOLVED",
        "base_artifact": artifact,
        "resources": {
            "solver_calls": 1,
            "charger_visits": len(events),
            "binary_variables": len(variables) - continuous_count,
            "wall_seconds": format(time.perf_counter() - started, ".9f"),
            "cpu_seconds": format(time.process_time() - cpu, ".9f"),
            "solver_status": int(result.status),
            "solver_optimality_claim": bool(result.success),
            "funding": "initial-seed-funded-research",
        },
        "scope": SCOPE,
    }


def add_commands(commands: Any) -> None:
    """Register an additive mission command without granting native or spending authority."""
    command = commands.add_parser("shared-charger", help="Check jointly occupied fixed-order charging schedules")
    _arguments(command)


def _arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("action", choices=["solve", "check"])
    parser.add_argument("file", type=Path)
    parser.add_argument("--output", type=Path)


def handle(args: argparse.Namespace) -> dict[str, Any]:
    """Write new result artifacts exclusively, or replay a retained result."""
    if args.action == "check":
        return check(read(args.file / "request.json"), read(args.file / "result.json"))
    if args.output is None:
        raise ValueError("solve requires --output NEW_DIRECTORY")
    request = read(args.file)
    if any(path.is_symlink() for path in (args.output, *args.output.parents)):
        raise ValueError("symlinked output paths are unsupported")
    args.output.mkdir(parents=True, exist_ok=False)
    write_new(args.output / "request.json", request)
    try:
        result = solve(request)
        write_new(args.output / "result.json", result)
        verdict = check(request, result)
        write_new(args.output / "acceptance.json", verdict)
    except Exception as error:
        write_new(args.output / "failure.json", {"error": type(error).__name__, "task_hash": digest(request)})
        raise
    return verdict


def main() -> int:
    """Provide an exclusive-output command for explicit shared-resource mission inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    _arguments(parser)
    verdict = handle(parser.parse_args())
    import json

    print(json.dumps(verdict, sort_keys=True))
    return 0 if verdict["accepted"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
