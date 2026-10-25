# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import copy
import importlib.util
import itertools
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from native_repair import solve

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("independent_development_checker", ROOT / "scientific/review/check.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


def task():
    return {
        "schema": "release-plan/v1",
        "id": "authored-native-repair",
        "kind": "repair",
        "public_or_synthetic": "synthetic",
        "planning_only": True,
        "jobs": [
            {"id": "J1", "duration": 2, "crew": 1, "deps": []},
            {"id": "J2", "duration": 1, "crew": 1, "deps": []},
        ],
        "capacity": [1] * 4,
        "baseline": {"J1": 2, "J2": 0},
        "deadline": 4,
        "release": {},
        "locked": {},
    }


def enumerated(t):
    feasible = []
    jobs = {j["id"]: j for j in t["jobs"]}
    for values in itertools.product(
        *(range(t.get("release", {}).get(j["id"], 0), len(t["capacity"]) - j["duration"] + 1) for j in t["jobs"])
    ):
        starts = dict(zip(jobs, values))
        if any(starts[k] != v for k, v in t.get("locked", {}).items()):
            continue
        if any(starts[p] + jobs[p]["duration"] > starts[j["id"]] for j in t["jobs"] for p in j["deps"]):
            continue
        if any(
            sum(j["crew"] for j in t["jobs"] if starts[j["id"]] <= tick < starts[j["id"]] + j["duration"]) > capacity
            for tick, capacity in enumerate(t["capacity"])
        ):
            continue
        movement = sum(abs(starts[k] - v) for k, v in t["baseline"].items())
        makespan = max(starts[j["id"]] + j["duration"] for j in t["jobs"])
        if makespan <= t["deadline"] and movement <= t.get("movement_limit", 2304):
            feasible.append((movement, makespan))
    return sorted(feasible)


def independent_check(t, r):
    bound = checker.check({"task": t, "result": None})["lower_bound"]
    result = {
        "schema": "release-plan-result/v1",
        "task_id": t["id"],
        "schedule": r["schedule"],
        "makespan": r["makespan"],
        "movement": r["movement"],
        "lower_bound": bound,
        "optimal_by_lower_bound": r["makespan"] == bound["value"],
        "dispatch_order": [j["id"] for j in r["schedule"] if j["id"] not in t.get("locked", {})],
        "lookahead_steps": 0,
        "proof": [],
        "authority": [],
    }
    checked = checker.check({"task": t, "result": result})
    assert checked["valid"] and checked["qualified"]


def test_movement_first_selects_four_zero_over_three_one():
    t = task()
    r = solve(t)
    assert r["status_code"] == 0 and (r["movement"], r["makespan"]) == (0, 4) == enumerated(t)[0]
    independent_check(t, r)


def test_infeasible_original_baseline_requires_minimum_movement():
    t = task()
    t.update(capacity=[1, 0, 1, 1, 1], baseline={"J1": 0, "J2": 2}, deadline=5)
    r = solve(t)
    assert r["status_code"] == 0 and (r["movement"], r["makespan"]) == (3, 5) == enumerated(t)[0]
    independent_check(t, r)


def test_movement_constraint_reports_infeasible_without_schedule():
    t = task()
    t.update(capacity=[1, 0, 1, 1, 1], baseline={"J1": 0, "J2": 2}, deadline=5, movement_limit=2)
    r = solve(t)
    assert not enumerated(t) and r["status_code"] == 2 and not r["success"] and r["schedule"] is None


def test_locked_prefix_precedence_and_releases():
    t = task()
    t.update(capacity=[1] * 7, baseline={"J1": 0, "J2": 2}, locked={"J1": 0}, release={"J2": 4}, deadline=7)
    t["jobs"][1]["deps"] = ["J1"]
    r = solve(t)
    assert r["status_code"] == 0 and (r["movement"], r["makespan"]) == enumerated(t)[0]
    assert next(j for j in r["schedule"] if j["id"] == "J1")["start"] == 0
    independent_check(t, r)


def test_backend_timeout_status_is_not_success_or_proof():
    backend = SimpleNamespace(
        message="Authored backend limit fixture",
        status=1,
        success=False,
        x=None,
        fun=None,
        mip_gap=None,
        mip_node_count=None,
    )
    with patch("native_repair.milp", return_value=backend):
        r = solve(task())
    assert r["status_code"] == 1 and not r["success"] and r["schedule"] is None and r["authority"] == []


@pytest.mark.parametrize("field,value", [("deadline", 0), ("deadline", True), ("movement_limit", -1)])
def test_invalid_bounds_refuse_before_model(field, value):
    t = copy.deepcopy(task())
    t[field] = value
    with pytest.raises(ValueError):
        solve(t)
