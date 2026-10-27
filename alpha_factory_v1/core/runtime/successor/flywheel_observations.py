# SPDX-License-Identifier: Apache-2.0
"""Finite observation design for an unchanged outcome; no execution authority.

The supplied world table is a model, not a certificate of real-world coverage.
This bounded exact search uses ordinary distinguishing-set enumeration.
"""

from __future__ import annotations

from itertools import combinations
from typing import Literal

from pydantic import Field, model_validator

from .protocol import Digest, Identifier, StrictModel, Text, digest


class World(StrictModel):
    world_id: Identifier
    outcome_satisfied: bool
    meaning: Text


class Probe(StrictModel):
    probe_id: Identifier
    resource_units: int = Field(ge=1, le=1_000_000)
    outcomes: dict[str, str]
    semantics: Text


class ObservationProblem(StrictModel):
    schema_name: Literal["mission-observation-problem/v1"] = "mission-observation-problem/v1"
    mission_id: Identifier
    purpose_digest: Digest
    environment_digest: Digest
    worlds: list[World] = Field(min_length=2, max_length=64)
    probes: list[Probe] = Field(min_length=1, max_length=12)
    max_resource_units: int = Field(ge=0, le=12_000_000)
    coverage_limitations: Text

    @model_validator(mode="after")
    def finite_table(self) -> ObservationProblem:
        identities = {world.world_id for world in self.worlds}
        if len(identities) != len(self.worlds) or {w.outcome_satisfied for w in self.worlds} != {True, False}:
            raise ValueError("distinct worlds must contain satisfied and unsatisfied outcomes")
        if len({probe.probe_id for probe in self.probes}) != len(self.probes):
            raise ValueError("distinct read-only probe identities required")
        for probe in self.probes:
            if set(probe.outcomes) != identities or any(
                not isinstance(v, str) or not 1 <= len(v) <= 256 for v in probe.outcomes.values()
            ):
                raise ValueError("every probe must cover every declared world with bounded exact observations")
        return self


class ObservationPlan(StrictModel):
    problem_digest: Digest
    probes: list[Identifier] = Field(max_length=12)
    resource_units: int = Field(ge=0, le=12_000_000)
    unresolved_pairs: list[list[Identifier]] = Field(max_length=1024)
    subsets_examined: int = Field(ge=1, le=4096)
    authority: list[Identifier] = Field(default_factory=list, max_length=0)


class ObservationFinding(StrictModel):
    problem_digest: Digest
    plan_digest: Digest
    compatible_worlds: list[Identifier] = Field(max_length=64)
    outcome: Literal["satisfied-in-model", "unsatisfied-in-model", "hold"]
    limitations: Text
    authority: list[Identifier] = Field(default_factory=list, max_length=0)


def compile_observations(problem: ObservationProblem) -> ObservationPlan:
    problem = ObservationProblem.model_validate_json(problem.model_dump_json())
    pairs = [
        (a.world_id, b.world_id)
        for a in problem.worlds
        for b in problem.worlds
        if a.outcome_satisfied and not b.outcome_satisfied
    ]
    best: tuple[int, int, tuple[str, ...]] | None = None
    selected: tuple[int, ...] = ()
    unresolved = pairs
    examined = 0
    for count in range(len(problem.probes) + 1):
        for indices in combinations(range(len(problem.probes)), count):
            examined += 1
            probes = [problem.probes[index] for index in indices]
            cost = sum(probe.resource_units for probe in probes)
            if cost > problem.max_resource_units:
                continue
            remaining = [(a, b) for a, b in pairs if all(p.outcomes[a] == p.outcomes[b] for p in probes)]
            score = (len(remaining), cost, tuple(sorted(probe.probe_id for probe in probes)))
            if best is None or score < best:
                best, selected, unresolved = score, indices, remaining
    return ObservationPlan(
        problem_digest=digest("observation-problem", problem),
        probes=sorted(problem.probes[index].probe_id for index in selected),
        resource_units=sum(problem.probes[index].resource_units for index in selected),
        unresolved_pairs=[list(pair) for pair in unresolved],
        subsets_examined=examined,
    )


def interpret_observations(
    problem: ObservationProblem, plan: ObservationPlan, observations: dict[str, str]
) -> ObservationFinding:
    problem = ObservationProblem.model_validate_json(problem.model_dump_json())
    plan = ObservationPlan.model_validate_json(plan.model_dump_json())
    if plan.problem_digest != digest("observation-problem", problem) or plan != compile_observations(problem):
        raise ValueError("use the exact current problem and its bounded canonical plan")
    if set(observations) != set(plan.probes) or any(
        not isinstance(value, str) or not 1 <= len(value) <= 256 for value in observations.values()
    ):
        raise ValueError("supply exactly the executed authorized observations")
    probes = {probe.probe_id: probe for probe in problem.probes}
    worlds = [
        world
        for world in problem.worlds
        if all(probes[name].outcomes[world.world_id] == observed for name, observed in observations.items())
    ]
    outcomes = {world.outcome_satisfied for world in worlds}
    return ObservationFinding(
        problem_digest=plan.problem_digest,
        plan_digest=digest("observation-plan", plan),
        compatible_worlds=[world.world_id for world in worlds],
        outcome="satisfied-in-model"
        if outcomes == {True}
        else "unsatisfied-in-model"
        if outcomes == {False}
        else "hold",
        limitations=problem.coverage_limitations,
    )
