# SPDX-License-Identifier: Apache-2.0
"""Probe design preserves original outcomes and refuses ambiguous observations."""

from __future__ import annotations

import itertools
import random

import pytest

from alpha_factory_v1.core.runtime.successor.flywheel_observations import (
    ObservationPlan,
    ObservationProblem,
    Probe,
    World,
    compile_observations,
    interpret_observations,
)


def problem(seed: int = 0, probes: int = 4) -> ObservationProblem:
    rng = random.Random(seed)
    worlds = [World(world_id=f"s{i}", outcome_satisfied=i < 2, meaning=f"Declared outcome state {i}") for i in range(6)]
    return ObservationProblem(
        mission_id=f"fresh-{seed}",
        purpose_digest="a" * 64,
        environment_digest="b" * 64,
        worlds=worlds,
        probes=[
            Probe(
                probe_id=f"p{i}",
                resource_units=rng.randint(1, 4),
                outcomes={w.world_id: str(rng.randint(0, 2)) for w in worlds},
                semantics="Authored read-only fixture",
            )
            for i in range(probes)
        ],
        max_resource_units=5,
        coverage_limitations="Finite supplied worlds; no live effect or retry authority",
    )


def independent_reference(instance: ObservationProblem) -> tuple[int, int, tuple[str, ...]]:
    scores = []
    for bits in itertools.product((0, 1), repeat=len(instance.probes)):
        probes = [p for bit, p in zip(bits, instance.probes) if bit]
        cost = sum(p.resource_units for p in probes)
        if cost > instance.max_resource_units:
            continue
        partitions: dict[tuple[str, ...], list[World]] = {}
        for w in instance.worlds:
            partitions.setdefault(tuple(p.outcomes[w.world_id] for p in probes), []).append(w)
        ambiguity = sum(
            sum(w.outcome_satisfied for w in group) * sum(not w.outcome_satisfied for w in group)
            for group in partitions.values()
        )
        scores.append((ambiguity, cost, tuple(sorted(p.probe_id for p in probes))))
    return min(scores)


@pytest.mark.parametrize("seed", range(32))
def test_exact_design_matches_independent_partition_oracle(seed: int) -> None:
    instance = problem(seed)
    plan = compile_observations(instance)
    assert (len(plan.unresolved_pairs), plan.resource_units, tuple(plan.probes)) == independent_reference(instance)
    assert plan.subsets_examined == 16 and plan.authority == []
    probes = {p.probe_id: p for p in instance.probes}
    for world in instance.worlds:
        finding = interpret_observations(
            instance, plan, {name: probes[name].outcomes[world.world_id] for name in plan.probes}
        )
        assert world.world_id in finding.compatible_worlds and finding.authority == []
        if finding.outcome != "hold":
            assert (finding.outcome == "satisfied-in-model") is world.outcome_satisfied


def test_uninformative_and_unfunded_probes_preserve_hold() -> None:
    raw = problem().model_dump()
    raw["max_resource_units"] = 0
    instance = ObservationProblem.model_validate(raw)
    plan = compile_observations(instance)
    assert plan.probes == [] and len(plan.unresolved_pairs) == 8
    assert interpret_observations(instance, plan, {}).outcome == "hold"
    raw["max_resource_units"] = 5
    for p in raw["probes"]:
        p["outcomes"] = {w["world_id"]: "same" for w in raw["worlds"]}
    instance = ObservationProblem.model_validate(raw)
    assert compile_observations(instance).probes == []


def test_same_outcome_states_need_not_be_distinguished() -> None:
    raw = problem().model_dump()
    raw["probes"] = [
        {
            **raw["probes"][0],
            "resource_units": 1,
            "outcomes": {w["world_id"]: "yes" if w["outcome_satisfied"] else "no" for w in raw["worlds"]},
        }
    ]
    instance = ObservationProblem.model_validate(raw)
    plan = compile_observations(instance)
    assert not plan.unresolved_pairs
    finding = interpret_observations(instance, plan, {"p0": "yes"})
    assert finding.outcome == "satisfied-in-model" and len(finding.compatible_worlds) == 2
    assert interpret_observations(instance, plan, {"p0": "unexpected"}).outcome == "hold"


@pytest.mark.parametrize("change", ["purpose_digest", "environment_digest", "mission_id"])
def test_transfer_requires_fresh_mission_binding(change: str) -> None:
    original = problem()
    plan = compile_observations(original)
    raw = original.model_dump()
    raw[change] = "c" * 64 if change.endswith("digest") else "different-mission"
    with pytest.raises(ValueError, match="exact current"):
        interpret_observations(ObservationProblem.model_validate(raw), plan, {})


def test_tampered_plan_and_incomplete_observation_refuse() -> None:
    original = problem()
    plan = compile_observations(original)
    raw = plan.model_dump()
    raw["resource_units"] += 1
    with pytest.raises(ValueError):
        interpret_observations(original, ObservationPlan.model_validate(raw), {})
    with pytest.raises(ValueError):
        interpret_observations(original, plan, {"unauthorized": "read"})
    with pytest.raises(ValueError):
        ObservationPlan.model_validate({**plan.model_dump(), "authority": ["retry"]})


@pytest.mark.parametrize("defect", ["missing-world", "duplicate-world", "duplicate-probe", "oversize", "bool-cost"])
def test_malformed_world_models_are_refused(defect: str) -> None:
    raw = problem().model_dump()
    if defect == "missing-world":
        raw["probes"][0]["outcomes"].pop("s0")
    elif defect == "duplicate-world":
        raw["worlds"][0] = raw["worlds"][1]
    elif defect == "duplicate-probe":
        raw["probes"][0] = raw["probes"][1]
    elif defect == "bool-cost":
        raw["probes"][0]["resource_units"] = True
    else:
        raw["probes"] = raw["probes"] * 4
    with pytest.raises(ValueError):
        ObservationProblem.model_validate(raw)
