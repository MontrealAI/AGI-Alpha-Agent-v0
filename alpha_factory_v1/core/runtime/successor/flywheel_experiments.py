# SPDX-License-Identifier: Apache-2.0
"""Bounded executable systems-R&D workload, not simulated frontier competence.

Choose two replicas per service across distinct failure domains while respecting
host capacity and minimizing service-specific placement costs. The independent
small-instance enumerator does not use the production search or its bounds.
"""

from __future__ import annotations

import itertools
from typing import Any

from pydantic import Field, model_validator

from .protocol import StrictModel, canonical
from .transformation_library import _is_exact_type


class PlacementProblem(StrictModel):
    capacities: list[int] = Field(min_length=2, max_length=10)
    failure_domains: list[str] = Field(min_length=2, max_length=10)
    demands: list[int] = Field(min_length=1, max_length=16)
    costs: list[list[int]] = Field(min_length=1, max_length=16)
    node_budget: int = Field(default=250_000, ge=1, le=1_000_000)

    @model_validator(mode="after")
    def dimensions(self) -> PlacementProblem:
        hosts = len(self.capacities)
        if len(self.failure_domains) != hosts or len(self.costs) != len(self.demands):
            raise ValueError("inconsistent host/service dimensions")
        if any(len(row) != hosts for row in self.costs):
            raise ValueError("each service requires one cost for each host")
        if any(not 1 <= n <= 1000 for n in self.capacities + self.demands):
            raise ValueError("demands and capacities must be positive bounded integers")
        if any(not 0 <= n <= 1_000_000 for row in self.costs for n in row):
            raise ValueError("costs must be nonnegative bounded integers")
        if any(not 1 <= len(label) <= 80 for label in self.failure_domains):
            raise ValueError("failure-domain labels must be bounded")
        canonical(self)
        return self


def solve_placement(problem: PlacementProblem) -> dict[str, Any]:
    """Exact branch and bound with a finite node cap and an honest incomplete result."""
    problem = PlacementProblem.model_validate_json(canonical(problem))
    hosts, services = len(problem.capacities), len(problem.demands)
    pairs = [
        (a, b)
        for a in range(hosts)
        for b in range(a + 1, hosts)
        if problem.failure_domains[a] != problem.failure_domains[b]
    ]
    choices = [
        sorted(pairs, key=lambda pair: (problem.costs[s][pair[0]] + problem.costs[s][pair[1]], pair))
        for s in range(services)
    ]
    lower = [
        min((problem.costs[s][a] + problem.costs[s][b] for a, b in choices[s]), default=10**12) for s in range(services)
    ]
    suffix = [0] * (services + 1)
    for s in reversed(range(services)):
        suffix[s] = suffix[s + 1] + lower[s]
    capacity = list(problem.capacities)
    selected: list[tuple[int, int]] = []
    best: list[list[int]] | None = None
    best_cost, nodes, exhausted = 10**15, 0, False

    def visit(service: int, cost: int) -> None:
        nonlocal best, best_cost, nodes, exhausted
        if nodes >= problem.node_budget:
            exhausted = True
            return
        nodes += 1
        if cost + suffix[service] >= best_cost:
            return
        if service == services:
            best, best_cost = [list(pair) for pair in selected], cost
            return
        demand = problem.demands[service]
        for a, b in choices[service]:
            if capacity[a] >= demand and capacity[b] >= demand:
                capacity[a] -= demand
                capacity[b] -= demand
                selected.append((a, b))
                visit(service + 1, cost + problem.costs[service][a] + problem.costs[service][b])
                selected.pop()
                capacity[a] += demand
                capacity[b] += demand
                if exhausted:
                    return

    visit(0, 0)
    return {
        "status": "incomplete" if exhausted else "optimal" if best is not None else "infeasible",
        "placement": best,
        "cost": best_cost if best is not None else None,
        "search_nodes": nodes,
        "scope": "finite synthetic planning; no infrastructure deployment",
    }


def verify_placement(problem: PlacementProblem, result: dict[str, Any]) -> dict[str, Any]:
    """Recompute constraints and use an independent exhaustive oracle when affordable."""
    problem = PlacementProblem.model_validate_json(canonical(problem))
    hosts, services = len(problem.capacities), len(problem.demands)
    placement = result.get("placement")
    feasible = isinstance(placement, list) and len(placement) == services
    loads = [0] * hosts
    cost = 0
    if feasible and isinstance(placement, list):
        for service, pair in enumerate(placement):
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or any(not _is_exact_type(h, int) or not 0 <= h < hosts for h in pair)
            ):
                feasible = False
                break
            a, b = pair
            if a == b or problem.failure_domains[a] == problem.failure_domains[b]:
                feasible = False
                break
            for host in pair:
                loads[host] += problem.demands[service]
                cost += problem.costs[service][host]
        feasible = feasible and all(load <= cap for load, cap in zip(loads, problem.capacities))
    feasible = feasible and result.get("cost") == cost
    options = list(itertools.combinations(range(hosts), 2))
    combinations = len(options) ** services
    oracle_cost = None
    if combinations <= 100_000:
        for assignment in itertools.product(options, repeat=services):
            if any(problem.failure_domains[a] == problem.failure_domains[b] for a, b in assignment):
                continue
            used = [sum(problem.demands[s] for s, pair in enumerate(assignment) if h in pair) for h in range(hosts)]
            if any(n > limit for n, limit in zip(used, problem.capacities)):
                continue
            value = sum(problem.costs[s][h] for s, pair in enumerate(assignment) for h in pair)
            oracle_cost = value if oracle_cost is None else min(oracle_cost, value)
    accepted = combinations <= 100_000 and (
        feasible
        and result.get("status") == "optimal"
        and result.get("cost") == oracle_cost
        or oracle_cost is None
        and placement is None
        and result.get("status") == "infeasible"
    )
    return {
        "accepted_finite_result": accepted,
        "feasible": feasible,
        "oracle_cost": oracle_cost,
        "oracle_enumerated": combinations <= 100_000,
        "oracle_assignments": combinations,
        "actual_customer_acceptance": False,
        "frontier_model_advantage": "unmeasured",
    }
