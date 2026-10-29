# SPDX-License-Identifier: Apache-2.0
"""Competent conventional controls with equal predictions, actions and budgets."""

from __future__ import annotations
import time
from fractions import Fraction
from itertools import combinations
from typing import Any
from .checker import reference
from .instrument import digest, validate


def direct_plan(task: dict[str, Any]) -> dict[str, Any]:
    start = time.monotonic()
    ref = reference(task)
    witnesses = []
    unseparable = []
    for a, b in combinations(task["models"], 2):
        if a["decision"] == b["decision"]:
            continue
        separating = []
        for e in task["experiments"]:
            lo1, hi1 = map(Fraction, e["prediction"][a["id"]])
            lo2, hi2 = map(Fraction, e["prediction"][b["id"]])
            if max(lo1, lo2) > min(hi1, hi2):
                separating.append(e["id"])
        if not separating:
            unseparable.append([a["id"], b["id"]])
        witnesses.append({"models": [a["id"], b["id"]], "experiments": [e for e in ref["selected"] if e in separating]})
    return {
        "schema": "agialpha/experiment-plan/v1",
        "instrumentVersion": "conventional-enumeration-1",
        "taskHash": digest(task),
        "taskId": task["id"],
        **ref,
        "witnesses": witnesses,
        "unseparable": unseparable,
        "statesVisited": 2 ** len(task["experiments"]),
        "elapsedSeconds": time.monotonic() - start,
        "claimScope": "finite declared interval model only",
        "physicalQualified": False,
    }


def conventional_milp(task: dict[str, Any]) -> dict[str, Any]:
    import numpy as np
    from scipy.optimize import Bounds, LinearConstraint, milp  # type: ignore[import-untyped]

    validate(task)
    exps = task["experiments"]
    pairs = [(a, b) for a, b in combinations(task["models"], 2) if a["decision"] != b["decision"]]
    matrix = []
    for a, b in pairs:
        row = []
        for e in exps:
            pa = list(map(Fraction, e["prediction"][a["id"]]))
            pb = list(map(Fraction, e["prediction"][b["id"]]))
            row.append(int(max(pa[0], pb[0]) > min(pa[1], pb[1])))
        matrix.append(row)
    costs = np.array([e["cost"] for e in exps], dtype=float)
    if not matrix:
        return {"status": "GO", "cost": 0}
    result = milp(
        costs,
        integrality=np.ones(len(exps)),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(np.array(matrix), np.ones(len(matrix)), np.full(len(matrix), np.inf)),
        options={"time_limit": 5},
    )
    if result.status == 2:
        return {"status": "HOLD", "cost": None}
    if not result.success:
        return {"status": "INCONCLUSIVE", "cost": None}
    optimum = int(round(result.fun))
    return {
        "status": "GO" if optimum <= task["budget"] else "HOLD",
        "cost": optimum if optimum <= task["budget"] else None,
    }


def greedy_ablation(task: dict[str, Any]) -> dict[str, Any]:
    validate(task)
    pairs = {(a["id"], b["id"]) for a, b in combinations(task["models"], 2) if a["decision"] != b["decision"]}
    remaining = set(pairs)
    selected = []
    cost = 0
    while remaining:
        options = []
        for e in task["experiments"]:
            if e["id"] in selected or cost + e["cost"] > task["budget"]:
                continue
            separated = set()
            for a, b in remaining:
                pa = list(map(Fraction, e["prediction"][a]))
                pb = list(map(Fraction, e["prediction"][b]))
                if max(pa[0], pb[0]) > min(pa[1], pb[1]):
                    separated.add((a, b))
            if separated:
                options.append((Fraction(-len(separated), e["cost"]), e["id"], e, separated))
        if not options:
            break
        _, _, e, covered = min(options, key=lambda x: (x[0], x[1]))
        selected.append(e["id"])
        cost += e["cost"]
        remaining -= covered
    return {"status": "GO" if not remaining else "HOLD", "cost": cost if not remaining else None, "selected": selected}
