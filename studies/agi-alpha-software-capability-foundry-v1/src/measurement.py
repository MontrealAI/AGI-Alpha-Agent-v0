# SPDX-License-Identifier: Apache-2.0
"""Distinct wall, parent CPU and completed-child CPU accounts."""
from __future__ import annotations
import resource
import time

def stamp() -> tuple[float, float, float]:
    child = resource.getrusage(resource.RUSAGE_CHILDREN)
    return time.perf_counter(), time.process_time(), child.ru_utime + child.ru_stime

def delta(before: tuple[float, float, float]) -> dict[str, float]:
    after = stamp()
    return dict(zip(("wall_seconds", "parent_cpu_seconds", "child_cpu_seconds"),
                    (after[i] - before[i] for i in range(3))))

def measured(operation):
    before = stamp()
    value = operation()
    cost = delta(before)
    cost["total_cpu_seconds"] = cost["parent_cpu_seconds"] + cost["child_cpu_seconds"]
    return value, cost
