# SPDX-License-Identifier: Apache-2.0
"""Bounded engineering repair objective; the frozen research specialist is unchanged."""
from __future__ import annotations

import math
import re
import time
from typing import Any, Sequence

import numpy as np
from scipy import __version__ as scipy_version
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def _integer(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


def solve(task: dict[str, Any], upper_bound: int | None = None, time_limit: float = 2.0) -> dict[str, Any]:
    start, cpu = time.perf_counter(), time.process_time()
    if not isinstance(task, dict) or task.get("schema") != "release-plan/v1" or task.get("kind") != "repair":
        raise ValueError("ENGINEERING_REPAIR_TASK")
    if not isinstance(task.get("id"), str) or not 1 <= len(task["id"]) <= 128:
        raise ValueError("TASK_ID")
    if task.get("planning_only") is not True or task.get("public_or_synthetic") not in ("synthetic", "public"):
        raise ValueError("PLANNING_INPUT_SCOPE")
    jobs, capacity = task.get("jobs"), task.get("capacity")
    if not isinstance(jobs, list) or not 1 <= len(jobs) <= 18:
        raise ValueError("JOB_COUNT")
    if not isinstance(capacity, list) or not 1 <= len(capacity) <= 128 or not all(_integer(x, 0, 4) for x in capacity):
        raise ValueError("CAPACITY_SCOPE")
    horizon = len(capacity)
    deadline = task.get("deadline", horizon)
    if not _integer(deadline, 1, horizon):
        raise ValueError("DEADLINE_SCOPE")
    if upper_bound is not None and not _integer(upper_bound, 1, horizon):
        raise ValueError("UPPER_BOUND_SCOPE")
    if type(time_limit) not in (int, float) or not math.isfinite(time_limit) or not 0 < time_limit <= 2:
        raise ValueError("SOLVE_ALLOWANCE_SCOPE")
    effective = min(deadline, upper_bound if upper_bound is not None else horizon)
    ids: dict[str, int] = {}
    for index, job in enumerate(jobs):
        if (
            not isinstance(job, dict)
            or not isinstance(job.get("id"), str)
            or not re.fullmatch(r"J[1-9][0-9]{0,2}", job["id"])
        ):
            raise ValueError("JOB_ID")
        if job["id"] in ids or not _integer(job.get("duration"), 1, 12) or not _integer(job.get("crew"), 1, 4):
            raise ValueError("JOB_SCOPE")
        if (
            not isinstance(job.get("deps"), list)
            or not all(isinstance(x, str) for x in job["deps"])
            or len(set(job["deps"])) != len(job["deps"])
        ):
            raise ValueError("DEPENDENCY_SCOPE")
        ids[job["id"]] = index
    visited: set[str] = set()
    active: set[str] = set()

    def visit(jid: str) -> None:
        if jid not in ids or jid in active:
            raise ValueError("DEPENDENCY_GRAPH")
        if jid in visited:
            return
        active.add(jid)
        for parent in jobs[ids[jid]]["deps"]:
            visit(parent)
        active.remove(jid)
        visited.add(jid)

    for jid in ids:
        visit(jid)
    release, locked, baseline = task.get("release", {}), task.get("locked", {}), task.get("baseline")
    if not isinstance(baseline, dict) or set(baseline) != set(ids):
        raise ValueError("BASELINE_SCOPE")
    for field, mapping in (("release", release), ("locked", locked), ("baseline", baseline)):
        if not isinstance(mapping, dict) or not set(mapping) <= set(ids):
            raise ValueError("MAPPING_SCOPE")
        for jid, value in mapping.items():
            bound = horizon - 1 if field == "release" else horizon - jobs[ids[jid]]["duration"]
            if not _integer(value, 0, bound):
                raise ValueError("MAPPING_BOUNDS")
    for jid, value in locked.items():
        if value != baseline[jid] or value < release.get(jid, 0):
            raise ValueError("LOCK_BASELINE_RELEASE")
    movement_limit = task.get("movement_limit", 2304)
    if not _integer(movement_limit, 0, 2304):
        raise ValueError("MOVEMENT_SCOPE")
    options: list[tuple[str, int]] = []
    columns: list[list[int]] = []
    for job in jobs:
        starts = (
            [locked[job["id"]]]
            if job["id"] in locked
            else range(release.get(job["id"], 0), effective - job["duration"] + 1)
        )
        eligible = []
        for tick in starts:
            if (
                tick < release.get(job["id"], 0)
                or tick + job["duration"] > effective
                or any(capacity[x] < job["crew"] for x in range(tick, tick + job["duration"]))
            ):
                continue
            eligible.append(len(options))
            options.append((job["id"], tick))
        columns.append(eligible)
    n = len(options)
    ri: list[int] = []
    ci: list[int] = []
    values: list[float] = []
    lower: list[float] = []
    upper: list[float] = []

    def row(entries: Sequence[tuple[int, float]], lo: float, hi: float) -> None:
        index = len(lower)
        lower.append(lo)
        upper.append(hi)
        for col, value in entries:
            ri.append(index)
            ci.append(col)
            values.append(float(value))

    for selected in columns:
        row([(col, 1) for col in selected], 1, 1)
    for job, selected in zip(jobs, columns):
        for parent in job["deps"]:
            row(
                [(col, options[col][1]) for col in selected]
                + [(col, -options[col][1]) for col in columns[ids[parent]]],
                jobs[ids[parent]]["duration"],
                np.inf,
            )
    for tick in range(effective):
        row(
            [
                (col, jobs[ids[jid]]["crew"])
                for col, (jid, begin) in enumerate(options)
                if begin <= tick < begin + jobs[ids[jid]]["duration"]
            ],
            -np.inf,
            capacity[tick],
        )
    for job, selected in zip(jobs, columns):
        row([(col, options[col][1] + job["duration"]) for col in selected] + [(n, -1)], -np.inf, 0)
    row([(col, abs(tick - baseline[jid])) for col, (jid, tick) in enumerate(options)], -np.inf, movement_limit)
    objective = np.array([(effective + 1) * abs(tick - baseline[jid]) for jid, tick in options] + [1.0])
    matrix = coo_matrix((values, (ri, ci)), shape=(len(lower), n + 1)).tocsc()
    lb, ub = np.zeros(n + 1), np.ones(n + 1)
    ub[n] = effective
    build_ms = (time.perf_counter() - start) * 1000
    solved_at = time.perf_counter()
    result = milp(
        objective,
        integrality=np.ones(n + 1),
        bounds=Bounds(lb, ub),
        constraints=LinearConstraint(matrix, np.asarray(lower), np.asarray(upper)),
        options={"time_limit": float(time_limit), "mip_rel_gap": 0.0, "presolve": True},
    )
    solver_wall_ms = (time.perf_counter() - solved_at) * 1000
    schedule = None
    if result.x is not None:
        schedule = []
        for job, selected in zip(jobs, columns):
            chosen = [options[col][1] for col in selected if result.x[col] > 0.5]
            if len(chosen) != 1:
                raise ValueError("NONINTEGRAL_REPAIR_RESULT")
            schedule.append({"id": job["id"], "start": chosen[0], "end": chosen[0] + job["duration"]})
        schedule.sort(key=lambda x: (x["start"], x["id"]))
    return {
        "schema": "engineering-highs-repair/v1",
        "task_id": task["id"],
        "mode": "repair",
        "status": str(result.message),
        "status_code": int(result.status),
        "success": bool(result.success),
        "schedule": schedule,
        "makespan": max(x["end"] for x in schedule) if schedule else None,
        "movement": sum(abs(x["start"] - baseline[x["id"]]) for x in schedule) if schedule else None,
        "objective": float(result.fun) if result.fun is not None else None,
        "objective_semantics": "Within the explicit deadline, minimize total movement first, makespan second. Integer weight effective_horizon+1 makes every one-unit movement change dominate the full makespan range.",
        "mip_gap": float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None,
        "mip_nodes": int(result.mip_node_count) if getattr(result, "mip_node_count", None) is not None else None,
        "model_binary_variables": n,
        "model_rows": len(lower),
        "model_build_ms": build_ms,
        "model_solve_ms": solver_wall_ms,
        "model_solve_timing_scope": "Wall interval around the SciPy milp call; no solver CPU or primitive count is inferred.",
        "wall_ms": (time.perf_counter() - start) * 1000,
        "cpu_ms": (time.process_time() - cpu) * 1000,
        "time_limit_seconds": float(time_limit),
        "scipy_version": scipy_version,
        "numpy_version": np.__version__,
        "internal_primitive_count": None,
        "proof": [],
        "authority": [],
    }
