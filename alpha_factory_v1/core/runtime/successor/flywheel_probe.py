# SPDX-License-Identifier: Apache-2.0
"""Construct a bounded information request; never retry or authorize an action.

This instrument reasons over an explicitly supplied finite hypothesis set. Its
certificate is conditional on that set and the observation contract. Imported
probe descriptions are data, never executable tools or current acceptance.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Literal

from pydantic import Field, model_validator

from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest
from .transformation_library import _is_exact_type


class ReadOnlyProbe(StrictModel):
    probe_id: Identifier
    observation_contract: Text
    source_digest: Digest
    query_units: int = Field(ge=1, le=1_000_000)


class EffectHypothesis(StrictModel):
    hypothesis_id: Identifier
    result: Literal["not-applied", "applied", "partially-applied"]
    observations: dict[str, str] = Field(min_length=1, max_length=32)


class ProbeProblem(StrictModel):
    schema_name: Literal["flywheel-information-probe/v1"] = "flywheel-information-probe/v1"
    mission_digest: Digest
    purpose_digest: Digest
    input_semantics: Text
    required_output_semantics: Text
    observation_epoch: Digest
    coverage_basis: Text
    probes: list[ReadOnlyProbe] = Field(min_length=1, max_length=32)
    hypotheses: list[EffectHypothesis] = Field(min_length=1, max_length=128)
    query_budget: int = Field(ge=0, le=1_000_000)

    @model_validator(mode="after")
    def coherent(self) -> ProbeProblem:
        ids = {probe.probe_id for probe in self.probes}
        if len(ids) != len(self.probes):
            raise ValueError("probe identities must be unique")
        if len({world.hypothesis_id for world in self.hypotheses}) != len(self.hypotheses):
            raise ValueError("hypothesis identities must be unique")
        for world in self.hypotheses:
            if set(world.observations) != ids or any(
                not value or len(value) > 2000 for value in world.observations.values()
            ):
                raise ValueError("every finite hypothesis must specify every bounded observation")
        if len(canonical(self)) > 250_000:
            raise ValueError("finite information problem exceeds its byte budget")
        return self


class ProbeObservation(StrictModel):
    probe_id: Identifier
    value: str = Field(min_length=1, max_length=2000)
    observation_epoch: Digest
    source_digest: Digest


def inspect_information(problem: ProbeProblem, observations: list[ProbeObservation]) -> dict[str, Any]:
    """Partition the supplied worlds and request a discriminating approved read."""
    if not _is_exact_type(observations, list) or len(observations) > 32:
        raise ValueError("observation transcript exceeds its finite contract")
    problem = ProbeProblem.model_validate_json(canonical(problem))
    observations = [ProbeObservation.model_validate_json(canonical(row)) for row in observations]
    probes = {probe.probe_id: probe for probe in problem.probes}
    seen: set[str] = set()
    spent = 0
    possible = list(problem.hypotheses)
    for row in observations:
        probe = probes.get(row.probe_id)
        if probe is None or row.probe_id in seen:
            raise ValueError("observations require distinct declared probes")
        if row.observation_epoch != problem.observation_epoch or row.source_digest != probe.source_digest:
            raise ValueError("observation contract or epoch changed; reassess the mission")
        spent += probe.query_units
        if spent > problem.query_budget:
            raise ValueError("actual observation transcript exceeds its declared budget")
        seen.add(row.probe_id)
        possible = [world for world in possible if world.observations[row.probe_id] == row.value]

    conclusions = {world.result for world in possible}
    next_probe = None
    reason = "resolved-in-declared-model"
    if not possible:
        reason = "observation-outside-declared-model"
    elif len(conclusions) > 1:
        reason = "no-affordable-distinguishing-observation"
        choices = []
        for probe in problem.probes:
            if probe.probe_id in seen or spent + probe.query_units > problem.query_budget:
                continue
            separated = sum(
                left.result != right.result and left.observations[probe.probe_id] != right.observations[probe.probe_id]
                for index, left in enumerate(possible)
                for right in possible[index + 1 :]
            )
            if separated:
                choices.append((Fraction(-separated, probe.query_units), probe.query_units, probe.probe_id))
        if choices:
            next_probe = min(choices)[2]
            reason = "request-separating-read"
    result = next(iter(conclusions)) if len(conclusions) == 1 else None
    return {
        "schema": "flywheel-information-result/v1",
        "problem_digest": digest("flywheel-information-problem", problem),
        "transcript_digest": digest("flywheel-information-transcript", observations),
        "remaining_hypotheses": sorted(world.hypothesis_id for world in possible),
        "result": result,
        "next_probe": next_probe,
        "query_units_spent": spent,
        "reason": reason,
        "evidence_type": "conditional-finite-model-computation",
        "coverage_qualified": False,
        "actual_effect_accepted": False,
        "authority_granted": False,
        "retry_permitted": False,
    }


def verify_information(problem: ProbeProblem, observations: list[ProbeObservation], report: dict[str, Any]) -> bool:
    """Check the finite result independently by direct consistency enumeration."""
    if not _is_exact_type(observations, list) or len(observations) > 32:
        raise ValueError("observation transcript exceeds its finite contract")
    problem = ProbeProblem.model_validate_json(canonical(problem))
    rows = [ProbeObservation.model_validate_json(canonical(row)) for row in observations]
    candidate = inspect_information(problem, rows)
    if canonical(candidate) != canonical(report):
        return False
    consistent = {
        world.hypothesis_id: world.result
        for world in problem.hypotheses
        if all(world.observations[row.probe_id] == row.value for row in rows)
    }
    if report["remaining_hypotheses"] != sorted(consistent):
        return False
    results = set(consistent.values())
    if report["result"] is not None:
        return results == {report["result"]}
    if report["next_probe"] is not None:
        probe_id = report["next_probe"]
        return any(
            left.result != right.result and left.observations[probe_id] != right.observations[probe_id]
            for left in problem.hypotheses
            if left.hypothesis_id in consistent
            for right in problem.hypotheses
            if right.hypothesis_id in consistent
        )
    return not consistent or len(results) > 1
