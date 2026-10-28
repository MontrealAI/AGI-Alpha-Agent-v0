# SPDX-License-Identifier: Apache-2.0
"""Finite construction of conditional access paths; no permission or tool execution."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field, model_validator

from .protocol import Identifier, StrictModel, Text, canonical, digest


class AccessStep(StrictModel):
    step_id: Identifier
    purpose: Text
    requires: list[Identifier] = Field(max_length=16)
    produces: list[Identifier] = Field(min_length=1, max_length=16)
    preserves: list[Identifier] = Field(min_length=1, max_length=16)
    permission: Literal["documented", "required", "denied"]
    permission_basis: Text
    estimated_cost_micro_usd: int = Field(ge=0, le=10**12)
    duration_seconds: int = Field(ge=1, le=43_200)

    @model_validator(mode="after")
    def distinct(self) -> AccessStep:
        for values in (self.requires, self.produces, self.preserves):
            if len(set(values)) != len(values):
                raise ValueError("access predicates must be distinct")
        return self


class AccessProblem(StrictModel):
    schema_name: Literal["flywheel-conditional-access/v1"] = "flywheel-conditional-access/v1"
    mission_id: Identifier
    useful_purpose: Text
    starting_facts: list[Identifier] = Field(max_length=32)
    required_outputs: list[Identifier] = Field(min_length=1, max_length=16)
    obligations: list[Identifier] = Field(min_length=1, max_length=16)
    steps: list[AccessStep] = Field(min_length=1, max_length=12)
    cost_cap_micro_usd: int = Field(ge=0, le=10**12)
    seconds_cap: int = Field(ge=1, le=43_200)
    search_node_cap: int = Field(default=20_000, ge=1, le=50_000)
    mode: Literal["live", "recorded", "synthetic", "calibrated"]
    limitations: Text

    @model_validator(mode="after")
    def coherent(self) -> AccessProblem:
        if len({step.step_id for step in self.steps}) != len(self.steps):
            raise ValueError("access step identities must be distinct")
        for values in (self.starting_facts, self.required_outputs, self.obligations):
            if len(set(values)) != len(values):
                raise ValueError("mission predicates must be distinct")
        if len(canonical(self)) > 120_000:
            raise ValueError("access problem exceeds its byte budget")
        return self


def construct_access(problem: AccessProblem) -> dict[str, Any]:
    """Search declared arrangements while retaining every original obligation."""
    problem = AccessProblem.model_validate_json(canonical(problem))
    obligations, goals = set(problem.obligations), set(problem.required_outputs)
    best: tuple[Any, ...] | None = None
    best_steps: list[AccessStep] = []
    visited = 0
    exhausted = False

    def visit(
        facts: set[str], selected: list[AccessStep], remaining: list[AccessStep], cost: int, seconds: int
    ) -> None:
        nonlocal best, best_steps, visited, exhausted
        if visited >= problem.search_node_cap:
            exhausted = True
            return
        visited += 1
        if goals <= facts:
            rank = (
                sum(step.permission == "required" for step in selected),
                cost,
                seconds,
                tuple(s.step_id for s in selected),
            )
            if best is None or rank < best:
                best, best_steps = rank, list(selected)
            return
        for step in remaining:
            if (
                step.permission == "denied"
                or not set(step.requires) <= facts
                or not obligations <= set(step.preserves)
                or set(step.produces) <= facts
                or cost + step.estimated_cost_micro_usd > problem.cost_cap_micro_usd
                or seconds + step.duration_seconds > problem.seconds_cap
            ):
                continue
            visit(
                facts | set(step.produces),
                selected + [step],
                [other for other in remaining if other.step_id != step.step_id],
                cost + step.estimated_cost_micro_usd,
                seconds + step.duration_seconds,
            )

    visit(set(problem.starting_facts), [], problem.steps, 0, 0)
    return {
        "schema": "flywheel-conditional-access-result/v1",
        "problem_digest": digest("insight-access-problem/v1", problem),
        "mission_id": problem.mission_id,
        "mode": problem.mode,
        "status": "incomplete"
        if exhausted
        else "no-plan"
        if best is None
        else "conditional-plan"
        if best[0]
        else "declared-plan",
        "steps": [step.model_dump() for step in best_steps],
        "pending_permissions": [step.step_id for step in best_steps if step.permission == "required"],
        "estimated_cost_micro_usd": best[1] if best else None,
        "duration_seconds": best[2] if best else None,
        "preserved_obligations": problem.obligations,
        "visited_nodes": visited,
        "ranking_policy": "fewest pending permissions, then estimated cost, duration and step identities",
        "scope": "finite declared monotone predicates; declaration correctness and external approval unverified",
        "actual_experiment_performed": False,
        "authority_granted": False,
        "customer_acceptance": False,
    }


def check_access(problem: AccessProblem, report: dict[str, Any]) -> bool:
    """Verify witness constraints without asserting search completeness or optimality."""
    problem = AccessProblem.model_validate_json(canonical(problem))
    if (
        report.get("schema") != "flywheel-conditional-access-result/v1"
        or report.get("mission_id") != problem.mission_id
        or report.get("mode") != problem.mode
        or report.get("customer_acceptance") is not False
    ):
        return False
    if report.get("problem_digest") != digest("insight-access-problem/v1", problem):
        return False
    if report.get("authority_granted") is not False or report.get("actual_experiment_performed") is not False:
        return False
    steps = {s.step_id: s for s in problem.steps}
    facts, seen, cost, seconds, pending = set(problem.starting_facts), set(), 0, 0, []
    for raw in report.get("steps", []):
        step = AccessStep.model_validate(raw)
        if (
            step.step_id not in steps
            or steps[step.step_id] != step
            or step.step_id in seen
            or step.permission == "denied"
            or not set(step.requires) <= facts
            or not set(problem.obligations) <= set(step.preserves)
        ):
            return False
        seen.add(step.step_id)
        facts.update(step.produces)
        cost += step.estimated_cost_micro_usd
        seconds += step.duration_seconds
        if step.permission == "required":
            pending.append(step.step_id)
    return bool(
        report.get("status") in {"declared-plan", "conditional-plan"}
        and set(problem.required_outputs) <= facts
        and cost <= problem.cost_cap_micro_usd
        and seconds <= problem.seconds_cap
        and report.get("estimated_cost_micro_usd") == cost
        and report.get("duration_seconds") == seconds
        and report.get("pending_permissions") == pending
        and report.get("preserved_obligations") == problem.obligations
        and report.get("status") == ("conditional-plan" if pending else "declared-plan")
    )
