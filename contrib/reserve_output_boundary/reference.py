# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import itertools
from typing import Any


def relational_audit(rows: list[dict[str, Any]], minimum: int) -> tuple[bool, int]:
    counts = []
    for left in rows:
        alternatives = {
            right["secret_value"]
            for right in rows
            if right["observer_view"] == left["observer_view"] and right["outputs"] == left["outputs"]
        }
        counts.append(len(alternatives))
    return min(counts) >= minimum, min(counts)


def assignment_bit(owners: list[dict[str, Any]], scenarios: list[dict[str, Any]], index: int) -> int:
    for scenario_index, scenario in enumerate(scenarios):
        demands = scenario["demand_clients"]
        found = False
        for allocation in itertools.permutations(range(6), len(demands)):
            works = True
            for demand, asset in zip(demands, allocation, strict=True):
                world = owners[asset // 2]["worlds"][index]
                row = asset % 2
                if not (
                    world["eligibility"][row][demand]
                    and world["availability"][row][scenario_index]
                    and not world["retention"][row][scenario_index]
                ):
                    works = False
                    break
            if works:
                found = True
                break
        if not found:
            return 0
    return 1
