# SPDX-License-Identifier: Apache-2.0
"""Closed executable placement workflows and common capability descriptions.

Capsules contain data for an installed interpreter, never Python, shell commands,
imports or scorer code. The initial supported form is an executable workflow.
Model assets and remotely served specialists remain explicitly unsupported.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal

from pydantic import Field, model_validator

from .flywheel_experiments import PlacementProblem
from .protocol import Digest, StrictModel, canonical, digest


class CapabilityDescription(StrictModel):
    form: Literal["executable-skill", "trained-component", "specialist-service"]
    runtime: str = Field(min_length=1, max_length=200)
    input_contract: Digest
    output_contract: Digest
    tests_digest: Digest
    provenance_digest: Digest
    permissions: list[Literal["bounded-local-compute"]] = Field(max_length=1)
    dependencies: list[Digest] = Field(max_length=16)
    limitations: str = Field(min_length=1, max_length=4000)

    @property
    def supported(self) -> bool:
        return self.form == "executable-skill" and self.runtime == "resilient-placement/v1"


class PlacementWorkflow(StrictModel):
    schema_name: Literal["placement-workflow/v1"] = "placement-workflow/v1"
    version: int = Field(ge=1, le=1_000_000)
    order: Literal["given", "largest-demand", "scarcity", "regret"] = "given"
    bound: Literal["static", "residual"] = "static"
    capacity_pruning: bool = False


def execute_workflow(
    problem: PlacementProblem, workflow: PlacementWorkflow, charge: Callable[[int], None]
) -> dict[str, Any]:
    """Exact search with explicit work, interruption and an honest proof budget.

    Both the learned ordering and complementary capacity/bounding procedures are
    closed installed algorithms. Every comparison, constraint probe and visit is
    charged; changing the representation does not remove the original constraints.
    """
    problem = PlacementProblem.model_validate_json(canonical(problem))
    workflow = PlacementWorkflow.model_validate_json(canonical(workflow))
    hosts, count = len(problem.capacities), len(problem.demands)
    used, nodes, exhausted = 0, 0, False

    def tick() -> None:
        nonlocal used
        used += 1
        charge(1)

    pairs = []
    for a in range(hosts):
        for b in range(a + 1, hosts):
            tick()
            if problem.failure_domains[a] != problem.failure_domains[b]:
                pairs.append((a, b))
    choices = []
    for service in range(count):
        row = []
        for a, b in pairs:
            tick()
            row.append((problem.costs[service][a] + problem.costs[service][b], a, b))
        choices.append(sorted(row))
    services = list(range(count))
    if workflow.order == "largest-demand":
        services.sort(key=lambda s: (-problem.demands[s], s))
    elif workflow.order == "scarcity":
        services.sort(
            key=lambda s: (
                sum(
                    problem.capacities[a] >= problem.demands[s] and problem.capacities[b] >= problem.demands[s]
                    for _, a, b in choices[s]
                ),
                -problem.demands[s],
                s,
            )
        )
    elif workflow.order == "regret":
        services.sort(key=lambda s: (-(choices[s][1][0] - choices[s][0][0]) if len(choices[s]) > 1 else -(10**12), s))
    # Account for a conservative ordering envelope uniformly across all arms.
    charge(count * max(1, len(pairs)) * max(1, count.bit_length()))
    used += count * max(1, len(pairs)) * max(1, count.bit_length())
    capacity = list(problem.capacities)
    selected: dict[int, list[int]] = {}
    best, best_cost = None, 10**15

    def visit(offset: int, cost: int) -> None:
        nonlocal nodes, exhausted, best, best_cost
        if nodes >= problem.node_budget:
            exhausted = True
            return
        tick()
        nodes += 1
        remaining = services[offset:]
        if workflow.capacity_pruning:
            tick()
            if sum(capacity) < 2 * sum(problem.demands[s] for s in remaining):
                return
        lower = 0
        for service in remaining:
            cheapest = None
            for amount, a, b in choices[service]:
                tick()
                if workflow.bound == "static" or (
                    capacity[a] >= problem.demands[service] and capacity[b] >= problem.demands[service]
                ):
                    cheapest = amount
                    break
            if cheapest is None:
                return
            lower += cheapest
        if cost + lower >= best_cost:
            return
        if offset == count:
            best, best_cost = [selected[s][:] for s in range(count)], cost
            return
        service = services[offset]
        demand = problem.demands[service]
        for amount, a, b in choices[service]:
            tick()
            if capacity[a] < demand or capacity[b] < demand:
                continue
            capacity[a] -= demand
            capacity[b] -= demand
            selected[service] = [a, b]
            visit(offset + 1, cost + amount)
            capacity[a] += demand
            capacity[b] += demand
            del selected[service]
            if exhausted:
                return

    visit(0, 0)
    return {
        "status": "incomplete" if exhausted else "optimal" if best is not None else "infeasible",
        "placement": best,
        "cost": best_cost if best is not None else None,
        "search_nodes": nodes,
        "logical_units": used,
        "workflow_digest": digest("flywheel-program", workflow),
        "scope": "finite synthetic planning; no infrastructure deployment",
    }


class PlacementInvocation(StrictModel):
    mission_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$")
    problem: PlacementProblem
    beta_digest: Digest
    policy_digest: Digest
    recipient_capabilities_digest: Digest
    prerequisite_digests: list[Digest] = Field(max_length=32)
    logical_limit: int = Field(ge=1, le=100_000)
    cost_cap_micro_usd: int = Field(ge=0, le=10**12)

    @model_validator(mode="after")
    def affordable_independent_scope(self) -> PlacementInvocation:
        # This first protected adapter requires an independently affordable oracle.
        hosts = len(self.problem.capacities)
        if (hosts * (hosts - 1) // 2) ** len(self.problem.demands) > 100_000:
            raise ValueError("placement invocation exceeds qualified independent-check scope")
        return self


def capability_forms() -> list[dict[str, Any]]:
    return [
        {"form": "executable-skill", "supported": True, "runtime": "resilient-placement/v1"},
        {"form": "trained-component", "supported": False, "reason": "No qualified loader or model assets"},
        {"form": "specialist-service", "supported": False, "reason": "No qualified remote serving adapter"},
    ]


def placement_fingerprint(problem: PlacementProblem) -> str:
    """Conservatively exclude host/service permutations and renamed domains.

    The projection can conflate different instances. False exclusions are safer
    than treating a cosmetic rewrap of an exposed problem as fresh evidence.
    """
    groups = sorted(set(problem.failure_domains))
    capacities = sorted(
        sorted(problem.capacities[h] for h, label in enumerate(problem.failure_domains) if label == g) for g in groups
    )
    rows = []
    for s, demand in enumerate(problem.demands):
        grouped = sorted(
            sorted(
                [problem.capacities[h], problem.costs[s][h]]
                for h, label in enumerate(problem.failure_domains)
                if label == g
            )
            for g in groups
        )
        rows.append([demand, grouped])
    return digest("placement-semantic-exposure", {"capacity_groups": capacities, "services": sorted(rows)})
