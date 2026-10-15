# SPDX-License-Identifier: Apache-2.0
"""Exact bounded portfolio planning over operator-supplied assumptions."""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "agialpha.bounded-plan.v1"


def validate(spec: Any) -> dict[str, Any]:
    """Reject ambiguous, unbounded and cyclic inputs before optimization."""

    def keys(value: Any, expected: set[str]) -> None:
        if not isinstance(value, dict) or set(value) != expected:
            raise ValueError("Unexpected or missing fields")

    def integer(value: Any, maximum: int = 1_000_000) -> None:
        if type(value) is not int or not 0 <= value <= maximum:  # noqa: E721
            raise ValueError("Expected bounded nonnegative integer")

    def label(value: Any, maximum: int) -> None:
        if not isinstance(value, str) or not value.strip() or value != value.strip() or len(value) > maximum:
            raise ValueError("Expected nonempty trimmed text")

    keys(spec, {"schema", "goal", "budget", "effort_capacity", "max_risk", "tasks"})
    if spec["schema"] != SCHEMA:
        raise ValueError("Unsupported schema")
    label(spec["goal"], 500)
    integer(spec["budget"])
    integer(spec["effort_capacity"])
    integer(spec["max_risk"], 100)
    tasks = spec["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 16:
        raise ValueError("Expected 1..16 tasks")
    ids: set[str] = set()
    for task in tasks:
        keys(task, {"id", "label", "cost", "effort", "value", "risk", "requires"})
        name = task["id"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", name) or name in ids:
            raise ValueError("Invalid or duplicate task ID")
        ids.add(name)
        label(task["label"], 120)
        for field in ("cost", "effort", "value"):
            integer(task[field])
        integer(task["risk"], 100)
        deps = task["requires"]
        if (
            not isinstance(deps, list)
            or len(deps) > 15
            or any(not isinstance(d, str) for d in deps)
            or len(set(deps)) != len(deps)
            or name in deps
        ):
            raise ValueError("Invalid dependencies")
    pending = {t["id"]: set(t["requires"]) for t in tasks}
    if any(not deps <= ids for deps in pending.values()):
        raise ValueError("Unknown dependency")
    done: set[str] = set()
    while pending:
        ready = sorted(name for name, deps in pending.items() if deps <= done)
        if not ready:
            raise ValueError("Dependency cycle")
        done.update(ready)
        for name in ready:
            del pending[name]
    return spec


def solve(spec: Any) -> dict[str, Any]:
    """Return the globally optimal feasible subset with reproducible tie breaks."""
    validate(spec)
    tasks = sorted(spec["tasks"], key=lambda task: task["id"])
    best: tuple[Any, ...] | None = None
    chosen: list[dict[str, Any]] = []
    feasible = 0
    for mask in range(1 << len(tasks)):
        subset = [task for index, task in enumerate(tasks) if mask & (1 << index)]
        ids = tuple(task["id"] for task in subset)
        selected = set(ids)
        if any(task["risk"] > spec["max_risk"] or not set(task["requires"]) <= selected for task in subset):
            continue
        cost = sum(task["cost"] for task in subset)
        effort = sum(task["effort"] for task in subset)
        if cost > spec["budget"] or effort > spec["effort_capacity"]:
            continue
        feasible += 1
        rank = (-sum(task["value"] for task in subset), cost, effort, ids)
        if best is None or rank < best:
            best, chosen = rank, subset
    ordered: list[str] = []
    pending = {task["id"]: task for task in chosen}
    while pending:
        name = min(name for name, task in pending.items() if set(task["requires"]) <= set(ordered))
        ordered.append(name)
        del pending[name]
    ids = [task["id"] for task in chosen]
    return {
        "schema": "agialpha.bounded-plan-result.v1",
        "goal": spec["goal"],
        "selected_ids": ids,
        "steps": ordered,
        "totals": {
            "cost": sum(t["cost"] for t in chosen),
            "effort": sum(t["effort"] for t in chosen),
            "value": sum(t["value"] for t in chosen),
            "max_risk": max((t["risk"] for t in chosen), default=0),
        },
        "omitted_ids": [t["id"] for t in tasks if t["id"] not in ids],
        "feasible_subsets": feasible,
    }
