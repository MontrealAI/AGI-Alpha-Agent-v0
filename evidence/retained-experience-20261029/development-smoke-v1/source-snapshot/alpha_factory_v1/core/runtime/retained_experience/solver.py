# SPDX-License-Identifier: Apache-2.0
"""Construct fresh LP certificates from verified historical constraint sets.

The retained objects are numerical methods, not remembered task answers. Every
application checks the current inequalities and dual bound before reuse. This is
standard parametric optimization in a bounded model, not an invention claim.
"""

from __future__ import annotations

from copy import deepcopy
from decimal import Decimal
from typing import Any

import numpy as np
from scipy.linalg import qr
from scipy.optimize import linprog

from ..structural_transfer import eadarp, eadarp_check
from ..structural_transfer.contracts import digest
from ..compounding_discovery.programs import canonical_decimal

TOL = 1e-7
GAP = 1e-5


def arrays(item: dict[str, Any]) -> tuple[Any, Any, Any]:
    """Materialize the complete finite-bounded Ax<=b model."""
    matrix = np.zeros((len(item["rows"]), len(item["variables"])))
    objective = np.zeros(len(item["variables"]))
    for r, row in enumerate(item["rows"]):
        for index, coefficient in row["terms"]:
            matrix[r, index] = float(coefficient)
    for index, coefficient in item["objective"]["terms"]:
        objective[index] = float(coefficient)
    return matrix, np.array([float(row["rhs"]) for row in item["rows"]]), objective


def signature(item: dict[str, Any]) -> str:
    """Bind actual coefficients, row order, objective and variable identities."""
    return digest(
        {
            "variables": item["variables"],
            "rows": [{"name": r["name"], "terms": r["terms"]} for r in item["rows"]],
            "objective": item["objective"]["terms"],
        }
    )


def primal_artifact(target: dict[str, Any], model: dict[str, Any], points: list[Any]) -> dict[str, Any]:
    schedules, total = [], Decimal(0)
    for item, point in zip(model["vehicles"], points):
        values = [format(float(x), ".15g") for x in point]
        size = len(item["route"])
        schedules.append(
            {
                "vehicle": item["vehicle"], "route": item["route"], "start_min": values[:size],
                "charge_min": values[size:2 * size], "arrival_kwh": values[2 * size:],
            }
        )
        total += Decimal(item["objective"]["constant"]) + sum(
            (Decimal(c) * Decimal(values[i]) for i, c in item["objective"]["terms"]), Decimal(0)
        )
    return {
        "schema": "agialpha/eadarp-certificate/v1", "task_hash": digest(target), "status": "FEASIBLE",
        "vehicles": schedules, "objective": canonical_decimal(total), "witness": {},
        "scope": "declared-eADARP-linear-model-only",
    }


def ray_artifact(target: dict[str, Any], item: dict[str, Any], weights: list[dict[str, str]]) -> dict[str, Any] | None:
    """Recompute the rigorous bounded-residual Farkas gap for the NEW right side."""
    rows = {row["name"]: row for row in item["rows"]}
    residual = [Decimal(0)] * len(item["variables"])
    rhs = Decimal(0)
    for entry in weights:
        if entry["id"] not in rows:
            return None
        weight = Decimal(entry["multiplier"])
        if not weight.is_finite() or weight < 0:
            return None
        row = rows[entry["id"]]
        rhs += weight * Decimal(row["rhs"])
        for index, coefficient in row["terms"]:
            residual[index] += weight * Decimal(coefficient)
    lower = sum(
        (min(r * Decimal(v["lower"]), r * Decimal(v["upper"])) for r, v in zip(residual, item["variables"])),
        Decimal(0),
    )
    if lower - rhs <= Decimal("1e-9"):
        return None
    return {
        "schema": "agialpha/eadarp-certificate/v1", "task_hash": digest(target), "status": "INFEASIBLE",
        "vehicles": [], "objective": "0", "scope": "declared-eADARP-linear-model-only",
        "witness": {"type": "bounded-farkas/v1", "vehicle": item["vehicle"], "rows": deepcopy(weights),
                    "contradiction": canonical_decimal(lower - rhs)},
    }


def solve(
    target: dict[str, Any], model: dict[str, Any], method: str = "highs", presolve: bool = True,
    templates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a complete competent LP reference, including infeasibility certificates."""
    points, duals, calls = [], [], 0
    for item in model["vehicles"]:
        cached = templates.get(signature(item)) if templates is not None else None
        if cached is None:
            matrix, rhs, objective = arrays(item)
        else:
            matrix, objective = cached
            rhs = np.array([float(row["rhs"]) for row in item["rows"]])
        calls += 1
        result = linprog(objective, A_ub=matrix, b_ub=rhs, bounds=(None, None), method=method,
                         options={"presolve": presolve, "time_limit": 10})
        if not result.success:
            calls += 1
            ray = linprog(rhs, A_eq=np.vstack([matrix.T, np.ones(len(rhs))]),
                          b_eq=np.r_[np.zeros(len(objective)), 1], bounds=(0, None), method=method,
                          options={"presolve": presolve, "time_limit": 10})
            artifact = None
            if ray.success:
                weights = [{"id": row["name"], "multiplier": format(float(value), ".15g")}
                           for row, value in zip(item["rows"], ray.x) if value > 0]
                artifact = ray_artifact(target, item, weights)
            if artifact is None:
                raise ValueError("reference did not construct a valid certificate")
            return {"artifact": artifact, "duals": [], "solver_calls": calls, "reuse": []}
        points.append(result.x)
        duals.append({row["name"]: format(float(y), ".15g")
                      for row, y in zip(item["rows"], result.ineqlin.marginals) if y != 0})
    return {"artifact": primal_artifact(target, model, points), "duals": duals, "solver_calls": calls, "reuse": []}


def learn(history: list[dict[str, Any]], *, points_only: bool = False) -> dict[str, Any]:
    """Compile checked experience only; history contains no future target or label."""
    assets, failures = [], []
    for record in history:
        target, output = record["target"], record["output"]
        artifact = output["artifact"]
        if eadarp_check.check(target, artifact, {}).get("accepted") is not True:
            raise ValueError("unverified history cannot be retained")
        model = eadarp.compile_model(target)
        if artifact["status"] == "INFEASIBLE":
            witness = artifact["witness"]
            if not points_only:
                assets.append({"kind": "ray", "source": digest(target), "vehicle": witness["vehicle"],
                               "weights": deepcopy(witness["rows"])})
            continue
        for item, schedule, dual in zip(model["vehicles"], artifact["vehicles"], output["duals"]):
            matrix, rhs, _ = arrays(item)
            point = np.array([float(x) for key in ("start_min", "charge_min", "arrival_kwh") for x in schedule[key]])
            if points_only:
                assets.append({"kind": "basis", "source": digest(target), "vehicle": item["vehicle"],
                               "signature": signature(item), "rows": [], "inverse": [], "duals": deepcopy(dual),
                               "point": [format(float(x), ".15g") for x in point]})
                continue
            active = np.flatnonzero(abs(matrix @ point - rhs) <= TOL)
            _, triangular, pivots = qr(matrix[active].T, pivoting=True, mode="economic")
            size = len(point)
            if len(active) < size or np.linalg.matrix_rank(triangular) < size:
                failures.append({"source": digest(target), "vehicle": item["vehicle"], "reason": "rank-deficient"})
                continue
            selected = active[pivots[:size]]
            inverse = np.linalg.inv(matrix[selected])
            assets.append({"kind": "basis", "source": digest(target), "vehicle": item["vehicle"],
                           "signature": signature(item), "rows": selected.tolist(),
                           "inverse": [[format(float(x), ".17g") for x in row] for row in inverse],
                           "duals": deepcopy(dual), "point": [format(float(x), ".15g") for x in point]})
    memory = {"schema": "agialpha/retained-lp-memory/v1", "training": [digest(x["target"]) for x in history],
              "assets": assets, "failed_constructions": failures}
    return {**memory, "memory_hash": digest(memory)}


def apply(
    target: dict[str, Any], model: dict[str, Any], memory: dict[str, Any], *, method: str = "highs",
    presolve: bool = True, ordinary_cache: bool = False,
) -> dict[str, Any]:
    """Construct an unqualified output; the caller MUST independently accept it."""
    return PreparedExperience(memory).run(target, model, method=method, presolve=presolve, ordinary_cache=ordinary_cache)


class PreparedExperience:
    """Validate and decode a frozen memory once; charge this setup in comparisons."""

    def __init__(self, memory: dict[str, Any]) -> None:
        if memory.get("memory_hash") != digest({k: v for k, v in memory.items() if k != "memory_hash"}):
            raise ValueError("retained memory changed")
        self.memory = deepcopy(memory)
        self.assets = deepcopy(memory["assets"])
        for asset in self.assets:
            if asset["kind"] == "basis":
                asset["inverse"] = np.array(asset["inverse"], dtype=float)
                asset["point"] = np.array(asset["point"], dtype=float)

    def run(
        self, target: dict[str, Any], model: dict[str, Any], *, method: str = "highs",
        presolve: bool = True, ordinary_cache: bool = False,
    ) -> dict[str, Any]:
        """Produce a current-task certificate without changing historical memory."""
        return _apply(target, model, self.assets, method, presolve, ordinary_cache)


def _apply(
    target: dict[str, Any], model: dict[str, Any], assets: list[Any], method: str, presolve: bool, ordinary_cache: bool,
) -> dict[str, Any]:
    points, duals, used, rejected = [], [], [], []
    if not ordinary_cache:
        for index, asset in enumerate(assets):
            if asset["kind"] != "ray":
                continue
            artifact = ray_artifact(target, model["vehicles"][asset["vehicle"]], asset["weights"])
            if artifact is not None:
                return {"artifact": artifact, "duals": [], "solver_calls": 0, "reuse": [index], "rejected": rejected}
            rejected.append({"asset": index, "reason": "current-ray-does-not-prove-infeasibility"})
    for item in model["vehicles"]:
        matrix, rhs, objective = arrays(item)
        current = signature(item)
        found = False
        for index, asset in enumerate(assets):
            if asset["kind"] != "basis" or asset["vehicle"] != item["vehicle"] or asset["signature"] != current:
                continue
            point = asset["point"] if ordinary_cache else asset["inverse"] @ rhs[asset["rows"]]
            dual = np.array([float(asset["duals"].get(row["name"], "0")) for row in item["rows"]])
            if (not np.all(np.isfinite(point)) or np.max(matrix @ point - rhs) > TOL or
                    np.max(dual) > 0 or np.max(abs(objective - matrix.T @ dual)) > 1e-9 or
                    abs(float(objective @ point - rhs @ dual)) > GAP / 4):
                rejected.append({"asset": index, "reason": "current-primal-or-dual-check-refused"})
                continue
            points.append(point)
            duals.append(deepcopy(asset["duals"]))
            used.append(index)
            found = True
            break
        if not found:
            output = solve(target, model, method, presolve)
            return {**output, "rejected": rejected, "partial_reuse_discarded": used}
    artifact = primal_artifact(target, model, points)
    return {"artifact": artifact, "duals": duals, "solver_calls": 0, "reuse": used, "rejected": rejected}
