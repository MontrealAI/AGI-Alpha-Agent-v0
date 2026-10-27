# SPDX-License-Identifier: Apache-2.0
"""Finite manufacturing scheduling laboratory; no model, market, or ENS calls."""

from __future__ import annotations

import hashlib
import json
import math
import time
from typing import Any

import numpy as np

STRATA = ("producer", "recipient", "scale", "shift")
RULES = np.array(
    [
        [1.0, 0.5, 1.0, 1.0, 1.0, -0.6, 0.1],
        [1.0, 0.2, 1.0, 0.5, 0.5, -0.3, 0.0],
        [1.0, 1.0, 1.0, 1.5, 0.5, -0.6, 0.0],
        [1.0, 0.0, 1.0, 0.0, 0.2, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.1, 0.5, -1.0, 0.1],
        [0.0, 0.4, 1.0, 2.0, 0.5, -0.4, 0.0],
        [1.0, 0.0, 0.0, 0.1, 0.5, 0.0, 0.0],
        [0.5, 0.5, 1.5, 1.0, 1.5, -0.5, 0.2],
    ], dtype=float,
)


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def make_instance(seed: int, stratum: str = "producer", small: bool = False) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    n, m = {"producer": (32, 3), "recipient": (40, 4), "scale": (64, 4), "shift": (48, 3)}[stratum]
    if small:
        n = 10
    families = 4 if stratum != "shift" else 6
    family = rng.integers(0, families, n)
    base = rng.integers(4, 25, n)
    speed = rng.uniform(0.7, 1.35, m)
    p = np.maximum(1, np.rint(base[:, None] * speed[None, :] * rng.uniform(0.8, 1.25, (n, m)))).astype(int)
    eligible = rng.random((n, m)) > (0.12 if stratum != "shift" else 0.32)
    for j in range(n):
        eligible[j, rng.integers(m)] = True
    workload = float(np.mean(p) * n / m)
    releases = rng.integers(0, max(2, int(workload * (0.25 if stratum != "shift" else 0.5))), n)
    tightness = 0.75 if stratum in ("producer", "scale") else 0.62
    due = releases + np.rint(workload * rng.uniform(0.1, tightness, n) + np.min(p, axis=1)).astype(int)
    weights = rng.integers(1, 6 if stratum != "recipient" else 10, n)
    setup = np.abs(np.arange(families)[:, None] - np.arange(families)[None, :]) * (2 if stratum != "shift" else 4)
    sigmas = rng.uniform(0.08, 0.38 if stratum != "shift" else 0.65, m)
    histories = rng.lognormal(-0.5 * sigmas**2, sigmas, (60, m))
    estimates = np.std(np.log(histories), axis=0, ddof=1)
    return {
        "case_id": f"{stratum}-{seed}", "seed": seed, "stratum": stratum,
        "n": n, "m": m, "p": p.tolist(), "eligible": eligible.tolist(), "family": family.tolist(),
        "release": releases.tolist(), "due": due.tolist(), "weight": weights.tolist(), "setup": setup.tolist(),
        "duration_sigma_true": sigmas.tolist(), "duration_sigma_estimate": estimates.tolist(),
        "measurement_history": histories.tolist(),
    }


def _arrays(instance: dict[str, Any]) -> dict[str, np.ndarray]:
    return {key: np.asarray(instance[key]) for key in ("p", "eligible", "family", "release", "due", "weight", "setup")}


def dispatch(instance: dict[str, Any], theta: np.ndarray, risk: float = 0.0) -> dict[str, Any]:
    a = _arrays(instance)
    n, m = instance["n"], instance["m"]
    available = np.zeros(m)
    last = np.full(m, -1, dtype=int)
    remaining = np.ones(n, dtype=bool)
    scale = float(np.mean(a["p"]))
    plan = []
    planned_p = a["p"] * (1.0 + risk * np.asarray(instance["duration_sigma_estimate"])[None, :])
    for _ in range(n):
        setups = a["setup"][a["family"][:, None], np.maximum(last, 0)[None, :]].astype(float)
        setups[:, last < 0] = 0
        start = np.maximum(available[None, :] + setups, a["release"][:, None])
        finish = start + planned_p
        score = (
            theta[0] * np.log(planned_p / scale)
            + theta[1] * np.maximum(a["due"][:, None] - finish, 0) / scale
            - theta[2] * np.log(a["weight"][:, None])
            + theta[3] * setups / scale
            + theta[4] * np.maximum(a["release"][:, None] - available[None, :], 0) / scale
            + theta[5] * np.maximum(finish - a["due"][:, None], 0) / scale
            + theta[6] * finish / scale
        )
        score[~a["eligible"] | ~remaining[:, None]] = np.inf
        j, k = np.unravel_index(np.argmin(score), score.shape)
        real_start = max(float(available[k] + setups[j, k]), float(a["release"][j]))
        real_finish = real_start + float(a["p"][j, k])
        plan.append({"job": int(j), "machine": int(k), "start": real_start, "finish": real_finish})
        available[k] = real_finish
        last[k] = a["family"][j]
        remaining[j] = False
    return {"jobs": plan, "theta": theta.tolist(), "risk": risk}


def incumbent(instance: dict[str, Any]) -> dict[str, Any]:
    a = _arrays(instance)
    available = np.zeros(instance["m"])
    last = np.full(instance["m"], -1, dtype=int)
    plan = []
    for j in np.argsort(a["due"], kind="stable"):
        setup = np.where(last < 0, 0, a["setup"][a["family"][j], np.maximum(last, 0)])
        starts = np.maximum(a["release"][j], available + setup)
        finishes = np.where(a["eligible"][j], starts + a["p"][j], np.inf)
        k = int(np.argmin(finishes))
        plan.append({"job": int(j), "machine": k, "start": float(starts[k]), "finish": float(finishes[k])})
        available[k] = finishes[k]
        last[k] = a["family"][j]
    return {"jobs": plan, "rule": "EDD-earliest-feasible-finish"}


def verify(instance: dict[str, Any], schedule: dict[str, Any]) -> dict[str, Any]:
    """Independently recompute assignment, processing, release, setup and objective."""
    records = schedule["jobs"]
    errors = []
    ids = [r["job"] for r in records]
    if sorted(ids) != list(range(instance["n"])):
        return {"valid": False, "errors": ["missing, duplicate or unknown job"]}
    completion = [0.0] * instance["n"]
    for k in range(instance["m"]):
        previous = None
        previous_end = 0.0
        for row in sorted((r for r in records if r["machine"] == k), key=lambda r: (r["start"], r["job"])):
            j = row["job"]
            start, end = row["start"], row["finish"]
            if not math.isfinite(start) or not math.isfinite(end):
                errors.append("non-finite time")
            setup = 0 if previous is None else instance["setup"][instance["family"][previous]][instance["family"][j]]
            if not instance["eligible"][j][k]:
                errors.append("ineligible machine")
            if start < instance["release"][j] - 1e-8 or start < previous_end + setup - 1e-8:
                errors.append("release/setup/overlap")
            if abs(end - start - instance["p"][j][k]) > 1e-8:
                errors.append("wrong processing duration")
            completion[j] = end
            previous, previous_end = j, end
    if any(r["machine"] not in range(instance["m"]) for r in records):
        errors.append("unknown machine")
    tardiness = sum(instance["weight"][j] * max(0, completion[j] - instance["due"][j]) for j in range(instance["n"]))
    makespan = max(completion)
    normalizer = sum(instance["weight"]) * float(np.mean(instance["p"]))
    objective = (tardiness + 0.1 * sum(instance["weight"]) * makespan) / normalizer
    return {"valid": not errors, "errors": errors, "weighted_tardiness": tardiness, "makespan": makespan, "objective": objective}


def scenario_factors(instance: dict[str, Any], seed: int, count: int = 24, truth: bool = False) -> np.ndarray:
    rng = np.random.default_rng(seed)
    sigma = np.asarray(instance["duration_sigma_true" if truth else "duration_sigma_estimate"])
    common = rng.normal(size=(count, 1, 1)) * 0.10
    eps = rng.normal(size=(count, instance["n"], instance["m"])) * sigma[None, None, :]
    return np.exp(eps + common - 0.5 * (sigma[None, None, :] ** 2 + 0.01))


def risk_score(instance: dict[str, Any], schedule: dict[str, Any], factors: np.ndarray) -> dict[str, float]:
    count = len(factors)
    endings = np.zeros((count, instance["n"]))
    for k in range(instance["m"]):
        end = np.zeros(count)
        previous = None
        for row in sorted((r for r in schedule["jobs"] if r["machine"] == k), key=lambda r: (r["start"], r["job"])):
            j = row["job"]
            setup = 0 if previous is None else instance["setup"][instance["family"][previous]][instance["family"][j]]
            start = np.maximum(instance["release"][j], end + setup)
            end = start + instance["p"][j][k] * factors[:, j, k]
            endings[:, j] = end
            previous = j
    tardiness = (np.maximum(endings - np.asarray(instance["due"])[None, :], 0) * np.asarray(instance["weight"])[None, :]).sum(axis=1)
    makespan = endings.max(axis=1)
    normalizer = sum(instance["weight"]) * float(np.mean(instance["p"]))
    scores = (tardiness + 0.1 * sum(instance["weight"]) * makespan) / normalizer
    tail = np.sort(scores)[max(0, math.floor(0.9 * count)):]
    return {"objective": float(0.5 * scores.mean() + 0.5 * tail.mean()), "mean": float(scores.mean()), "cvar90": float(tail.mean())}


def solve(instance: dict[str, Any], policy: dict[str, Any] | None, mode: str, offering: str, budget: int = 48) -> dict[str, Any]:
    started = time.perf_counter()
    instance = {key: value for key, value in instance.items() if key != "duration_sigma_true"}
    rng = np.random.default_rng(instance["seed"] + 717)
    scenarios = scenario_factors(instance, instance["seed"] + 800_000, 24) if offering == "robust" else None
    learned = np.asarray(policy["theta"], dtype=float) if policy is not None else None
    rules = [r.copy() for r in RULES]
    if mode == "beta_plus":
        rules.extend([r * np.array([1, f, 1, g, 1, f, 1]) for r in RULES[:3] for f, g in ((0.5, 2), (2, 0.5))])
    if learned is not None:
        rules.append(learned)
    candidate_scores = []
    best = None
    best_theta = RULES[0]
    best_score = math.inf
    for step in range(budget):
        if step < len(rules):
            theta = rules[step]
        else:
            center = best_theta if step % 3 else RULES[rng.integers(len(RULES))]
            theta = np.clip(center + rng.normal(0, 0.35 if step % 2 else 0.9, 7), -3, 5)
        risk = 0.0 if offering == "nominal" or mode == "v2" else (0.5 if step % 3 else 1.0)
        schedule = dispatch(instance, theta, risk=risk)
        nominal = verify(instance, schedule)
        if not nominal["valid"]:
            raise AssertionError(nominal)
        score = nominal["objective"] if scenarios is None or mode == "v2" else risk_score(instance, schedule, scenarios)["objective"]
        candidate_scores.append(float(score))
        if score < best_score:
            best_score, best, best_theta = score, schedule, theta.copy()
    assert best is not None
    return {"schedule": best, "training_objective": float(best_score), "candidate_scores": candidate_scores,
            "evals": budget, "scenario_evals": budget * (0 if scenarios is None or mode == "v2" else len(scenarios)),
            "solve_seconds": time.perf_counter() - started}


def cp_sat(instance: dict[str, Any], warm: dict[str, Any], deterministic_budget: float = 0.08) -> dict[str, Any]:
    """Optional independently developed solver comparator, never a training oracle."""
    from ortools.sat.python import cp_model

    started = time.perf_counter()
    model = cp_model.CpModel()
    n, m = instance["n"], instance["m"]
    horizon = max(instance["release"]) + sum(max(p) for p in instance["p"]) + n * max(max(s) for s in instance["setup"])
    starts = [model.new_int_var(0, horizon, f"s{j}") for j in range(n)]
    ends = [model.new_int_var(0, horizon, f"e{j}") for j in range(n)]
    assignments = {}
    for j in range(n):
        choices = []
        for k in range(m):
            if instance["eligible"][j][k]:
                assignments[j, k] = model.new_bool_var(f"x{j}_{k}")
                choices.append(assignments[j, k])
                model.add(ends[j] == starts[j] + instance["p"][j][k]).only_enforce_if(assignments[j, k])
        model.add_exactly_one(choices)
        model.add(starts[j] >= instance["release"][j])
    ordered = {}
    for j in range(n):
        for q in range(j + 1, n):
            y = model.new_bool_var(f"before{j}_{q}")
            ordered[j, q] = y
            setup = instance["setup"][instance["family"][j]][instance["family"][q]]
            for k in range(m):
                if (j, k) in assignments and (q, k) in assignments:
                    model.add(starts[q] >= ends[j] + setup).only_enforce_if([assignments[j, k], assignments[q, k], y])
                    model.add(starts[j] >= ends[q] + setup).only_enforce_if([assignments[j, k], assignments[q, k], ~y])
    late = [model.new_int_var(0, horizon, f"late{j}") for j in range(n)]
    for j in range(n):
        model.add_max_equality(late[j], [0, ends[j] - instance["due"][j]])
    makespan = model.new_int_var(0, horizon, "makespan")
    model.add_max_equality(makespan, ends)
    objective = 10 * sum(instance["weight"][j] * late[j] for j in range(n)) + sum(instance["weight"]) * makespan
    model.minimize(objective)
    byid = {r["job"]: r for r in warm["jobs"]}
    for j in range(n):
        row = byid[j]
        model.add_hint(starts[j], int(round(row["start"])))
        model.add_hint(ends[j], int(round(row["finish"])))
        model.add_hint(late[j], int(max(0, row["finish"] - instance["due"][j])))
        for k in range(m):
            if (j, k) in assignments:
                model.add_hint(assignments[j, k], int(row["machine"] == k))
    for (j, q), var in ordered.items():
        model.add_hint(var, int(byid[j]["start"] <= byid[q]["start"]))
    model.add_hint(makespan, int(max(row["finish"] for row in warm["jobs"])))
    solver = cp_model.CpSolver()
    solver.parameters.max_deterministic_time = deterministic_budget
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 20261027
    status = solver.solve(model)
    schedule = warm
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        schedule = {"jobs": [{"job": j, "machine": next(k for k in range(m) if (j, k) in assignments and solver.value(assignments[j, k])),
                               "start": float(solver.value(starts[j])), "finish": float(solver.value(ends[j]))} for j in range(n)]}
    result = verify(instance, schedule)
    warm_result = verify(instance, warm)
    if not result["valid"]:
        raise AssertionError(result)
    if result["objective"] > warm_result["objective"]:
        schedule, result = warm, warm_result
    normalizer = sum(instance["weight"]) * float(np.mean(instance["p"])) * 10
    return {"schedule": schedule, "verification": result, "status": solver.status_name(status),
            "best_bound": solver.best_objective_bound / normalizer, "deterministic_budget": deterministic_budget,
            "solve_seconds": time.perf_counter() - started, "ortools_version": "9.14.6206"}
