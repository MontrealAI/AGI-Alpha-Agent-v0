# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import json, math, sys, time
import numpy as np
from scipy import __version__ as scipy_version
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


def solve(task, upper_bound=None, time_limit=2.0, mode="makespan"):
    if mode not in ("makespan", "deadline"):
        raise ValueError("SPECIALIST_MODE")
    start = time.perf_counter()
    cpu = time.process_time()
    jobs = task["jobs"]
    ids = {j["id"]: i for i, j in enumerate(jobs)}
    capacity = task["capacity"]
    H = len(capacity)
    if upper_bound is not None:
        H = min(H, int(upper_bound))
    if mode == "deadline":
        H = min(H, task.get("deadline", H))
    options = []
    cols_by_job = []
    release = task.get("release", {})
    locked = task.get("locked", {})
    baseline = task.get("baseline", {})
    for j in jobs:
        cols = []
        starts = [locked[j["id"]]] if j["id"] in locked else range(release.get(j["id"], 0), H - j["duration"] + 1)
        for t in starts:
            if (
                t < release.get(j["id"], 0)
                or t + j["duration"] > H
                or any(capacity[s] < j["crew"] for s in range(t, t + j["duration"]))
            ):
                continue
            cols.append(len(options))
            options.append((j["id"], t))
        if not cols:
            return {
                "schema": "highs-specialist/v1",
                "status": "INFEASIBLE_MODEL",
                "schedule": None,
                "wall_ms": (time.perf_counter() - start) * 1000,
                "cpu_ms": (time.process_time() - cpu) * 1000,
                "scipy_version": scipy_version,
            }
        cols_by_job.append(cols)
    n = len(options)
    cmax = n
    row_i = []
    col_i = []
    values = []
    lower = []
    upper = []

    def row(entries, lo, hi):
        r = len(lower)
        lower.append(lo)
        upper.append(hi)
        for col, value in entries:
            row_i.append(r)
            col_i.append(col)
            values.append(float(value))

    for cols in cols_by_job:
        row([(col, 1) for col in cols], 1, 1)
    for j, cols in zip(jobs, cols_by_job):
        for p in j["deps"]:
            previous = cols_by_job[ids[p]]
            duration = jobs[ids[p]]["duration"]
            row(
                [(col, options[col][1]) for col in cols] + [(col, -options[col][1]) for col in previous],
                duration,
                np.inf,
            )
    for t in range(H):
        entries = []
        for j, cols in zip(jobs, cols_by_job):
            for col in cols:
                if options[col][1] <= t < options[col][1] + j["duration"]:
                    entries.append((col, j["crew"]))
        row(entries, -np.inf, capacity[t])
    for j, cols in zip(jobs, cols_by_job):
        row([(col, options[col][1] + j["duration"]) for col in cols] + [(cmax, -1)], -np.inf, 0)
    if "movement_limit" in task:
        row(
            [(col, abs(t - baseline.get(id, t))) for col, (id, t) in enumerate(options)],
            -np.inf,
            task["movement_limit"],
        )
    objective = np.zeros(n + 1)
    objective[cmax] = 0.0 if mode == "deadline" else 1.0
    if baseline and mode == "makespan":
        scale = 1 / (len(jobs) * len(capacity) + 1)
        for col, (id, t) in enumerate(options):
            objective[col] = scale * abs(t - baseline.get(id, t))
    matrix = coo_matrix((values, (row_i, col_i)), shape=(len(lower), n + 1)).tocsc()
    lb = np.zeros(n + 1)
    ub = np.ones(n + 1)
    ub[cmax] = H
    build_ms = (time.perf_counter() - start) * 1000
    result = milp(
        objective,
        integrality=np.ones(n + 1),
        bounds=Bounds(lb, ub),
        constraints=LinearConstraint(matrix, np.asarray(lower), np.asarray(upper)),
        options={"time_limit": float(time_limit), "mip_rel_gap": 0.0, "presolve": True},
    )
    schedule = None
    if result.x is not None:
        schedule = []
        for j, cols in zip(jobs, cols_by_job):
            selected = [options[col][1] for col in cols if result.x[col] > 0.5]
            if len(selected) != 1:
                raise ValueError("NONINTEGRAL_SPECIALIST_RESULT")
            t = selected[0]
            schedule.append({"id": j["id"], "start": t, "end": t + j["duration"]})
        schedule.sort(key=lambda x: (x["start"], x["id"]))
    output = {
        "schema": "highs-specialist/v1",
        "task_id": task["id"],
        "status": str(result.message),
        "status_code": int(result.status),
        "success": bool(result.success),
        "schedule": schedule,
        "makespan": max((j["end"] for j in schedule), default=None) if schedule else None,
        "movement": sum(abs(j["start"] - baseline.get(j["id"], j["start"])) for j in schedule) if schedule else None,
        "objective": float(result.fun) if result.fun is not None else None,
        "mip_gap": float(result.mip_gap) if getattr(result, "mip_gap", None) is not None else None,
        "mip_dual_bound": float(result.mip_dual_bound) if getattr(result, "mip_dual_bound", None) is not None else None,
        "mip_nodes": int(result.mip_node_count) if getattr(result, "mip_node_count", None) is not None else None,
        "model_binary_variables": n,
        "model_rows": len(lower),
        "model_nonzeros": len(values),
        "model_build_ms": build_ms,
        "wall_ms": (time.perf_counter() - start) * 1000,
        "cpu_ms": (time.process_time() - cpu) * 1000,
        "time_limit_seconds": time_limit,
        "scipy_version": scipy_version,
        "numpy_version": np.__version__,
        "internal_primitive_count": None,
        "internal_primitive_count_note": "Opaque solver internals are not converted into declared JavaScript work units.",
    }
    output.update(
        mode=mode,
        objective_semantics=(
            "Feasibility objective 0 under the user deadline; optimal status DOES NOT establish optimal makespan."
            if mode == "deadline"
            else "Minimize makespan; on repair, movement is a strictly subordinate bounded tie-breaker."
        ),
    )
    output["model_solve_ms"] = output["wall_ms"] - build_ms
    return output


if __name__ == "__main__":
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if request.get("op") == "metadata":
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "scipy": scipy_version,
                            "numpy": np.__version__,
                            "python": sys.version,
                            "solver": "scipy.optimize.milp / bundled HiGHS",
                        }
                    ),
                    flush=True,
                )
            else:
                print(
                    json.dumps(
                        {
                            "ok": True,
                            "result": solve(
                                request["task"],
                                request.get("upper_bound"),
                                request.get("time_limit", 2.0),
                                request.get("mode", "makespan"),
                            ),
                        }
                    ),
                    flush=True,
                )
        except Exception as e:
            print(json.dumps({"ok": False, "error": type(e).__name__ + ": " + str(e)}), flush=True)
