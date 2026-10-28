# SPDX-License-Identifier: Apache-2.0
"""Independent witness replay and conventional exhaustive tiny-instance oracle."""

from __future__ import annotations

from collections.abc import Iterator
from itertools import permutations
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from alpha_factory_v1.core.runtime.successor.protocol import Digest, Identifier, StrictModel, canonical

from .engine import ConstructionPolicy, ProductionBrief, binding


class Witness(StrictModel):
    steps: list[Identifier] = Field(max_length=12)
    pending_permissions: list[Identifier] = Field(max_length=12)
    stock: dict[Identifier, Annotated[int, Field(ge=0, le=1_300_000)]] = Field(max_length=24)
    capabilities: list[Identifier] = Field(max_length=312)
    estimated_cost_micro_usd: int = Field(ge=0, le=10**12)
    seconds: int = Field(ge=0, le=43_200)
    rank: list[Any] = Field(min_length=6, max_length=6)


class Result(StrictModel):
    schema_name: Literal["production-frontier-result/v1"] = Field(alias="schema")
    binding: Digest
    brief_id: Identifier
    adapter: Literal["declared-model-simulation"]
    input_mode: Literal["authored-simulation", "public-requirements", "authorized-measurements"]
    policy: ConstructionPolicy
    disabled: list[Identifier] = Field(max_length=12)
    conventional_only: bool
    status: Literal["feasible", "incomplete", "cancelled"]
    search_complete: bool
    states: int = Field(ge=1, le=4096)
    candidate_count: int = Field(ge=1, le=4096)
    candidates: list[Witness] = Field(min_length=1, max_length=8)
    best: Witness
    authority_granted: Literal[False]
    real_actions_executed: Literal[False]
    scientific_or_commercial_acceptance: Literal[False]
    scope: Literal[
        "finite declared recipes; no physical truth, optimality outside this grammar or real approval inferred"
    ]

    @model_validator(mode="after")
    def coherent(self) -> Result:
        if len(self.candidates) != min(8, self.candidate_count) or self.candidate_count > self.states:
            raise ValueError("inconsistent candidate inventory")
        routes = [tuple(c.steps) for c in self.candidates]
        if len(routes) != len(set(routes)) or self.best != self.candidates[0]:
            raise ValueError("duplicate candidates or inconsistent best witness")
        ranks = [c.rank for c in self.candidates]
        if ranks != sorted(ranks):
            raise ValueError("the offered candidates must be ranked consistently")
        if len(self.disabled) != len(set(self.disabled)):
            raise ValueError("disabled controls must be distinct")
        return self


def replay(brief: ProductionBrief, steps: list[str], *, disabled: list[str], conventional_only: bool) -> dict[str, Any]:
    """Replay without the compiler's search, relevance pruning or subset cache."""
    brief = ProductionBrief.model_validate_json(canonical(brief))
    if type(steps) is not list or any(type(step) is not str for step in steps):
        raise ValueError("witness steps must be an explicit string list")
    return _replay_validated(brief, steps, disabled=disabled, conventional_only=conventional_only)


def _replay_validated(
    brief: ProductionBrief, steps: list[str], *, disabled: list[str], conventional_only: bool
) -> dict[str, Any]:
    stock = {r.resource_id: brief.stock.get(r.resource_id, 0) for r in brief.resources}
    capabilities, seen, pending = set(brief.capabilities), set(), []
    cost, seconds, new_components = 0, 0, 0
    recipes = {r.recipe_id: r for r in brief.recipes}
    for identity in steps:
        if identity in seen or identity not in recipes or identity in disabled:
            raise ValueError("unknown, duplicate or disabled step")
        recipe = recipes[identity]
        if recipe.permission == "denied" or (conventional_only and recipe.origin != "conventional"):
            raise ValueError("forbidden construction")
        if any(x not in recipe.preserves for x in brief.obligations) or any(
            x not in capabilities for x in recipe.requires
        ):
            raise ValueError("capability or original obligation missing")
        for resource, amount in recipe.consumes.items():
            stock[resource] -= amount
            if stock[resource] < 0:
                raise ValueError("a scarce input was reused")
        for resource, amount in recipe.produces.items():
            stock[resource] += amount
        capabilities.update(recipe.provides)
        cost += recipe.estimated_cost_micro_usd
        seconds += recipe.seconds
        new_components += int(recipe.origin == "proposed-construction")
        if cost > brief.cost_cap_micro_usd or seconds > brief.seconds_cap:
            raise ValueError("resource budget exceeded")
        if recipe.permission == "required":
            pending.append(identity)
        seen.add(identity)
    if any(stock[x] < q for x, q in brief.required_stock.items()) or any(
        x not in capabilities for x in brief.required_capabilities
    ):
        raise ValueError("the useful outcome is not delivered")
    return {
        "stock": stock,
        "capabilities": sorted(capabilities),
        "estimated_cost_micro_usd": cost,
        "seconds": seconds,
        "pending_permissions": pending,
        "rank": [len(pending), cost, new_components, seconds, len(steps), steps],
    }


def verify(
    brief: ProductionBrief,
    policy: ConstructionPolicy,
    report: dict[str, Any],
    *,
    disabled: frozenset[str] = frozenset(),
    conventional_only: bool = False,
) -> bool:
    """Check each offered witness; this does not certify a no-plan or optimum."""
    try:
        brief = ProductionBrief.model_validate_json(canonical(brief))
        policy = ConstructionPolicy.model_validate_json(canonical(policy))
        Result.model_validate_json(canonical(report))
        if (
            report["schema"] != "production-frontier-result/v1"
            or report["binding"] != binding(brief, policy)
            or report["brief_id"] != brief.brief_id
            or report["input_mode"] != brief.input_mode
            or report["adapter"] != "declared-model-simulation"
            or report["policy"] != policy.model_dump()
            or any(
                report[k] is not False
                for k in ("authority_granted", "real_actions_executed", "scientific_or_commercial_acceptance")
            )
            or report["conventional_only"] is not conventional_only
            or report["disabled"] != sorted(disabled)
            or not disabled <= {r.recipe_id for r in brief.recipes}
            or report["status"] not in {"feasible", "incomplete", "cancelled"}
            or type(report["states"]) is not int
            or not 1 <= report["states"] <= brief.state_cap
            or type(report["search_complete"]) is not bool
            or (report["status"] == "feasible") != report["search_complete"]
        ):
            return False
        candidates = report["candidates"]
        if not candidates or report["best"] != candidates[0]:
            return False
        for candidate in candidates:
            outcome = _replay_validated(
                brief,
                candidate["steps"],
                disabled=report["disabled"],
                conventional_only=report["conventional_only"],
            )
            if canonical(candidate) != canonical({"steps": candidate["steps"], **outcome}):
                return False
        return True
    except (ValueError, KeyError, TypeError, AttributeError):
        return False


def exhaustive(brief: ProductionBrief) -> dict[str, Any] | None:
    """Strong conventional full-grammar comparison; at most seven steps."""
    brief = ProductionBrief.model_validate_json(canonical(brief))
    if len(brief.recipes) > 7:
        raise ValueError("factorial oracle is limited to seven steps")

    def paths() -> Iterator[tuple[str, ...]]:
        identities = [r.recipe_id for r in brief.recipes]
        for length in range(len(identities) + 1):
            yield from permutations(identities, length)

    best = None
    for path in paths():
        try:
            outcome = _replay_validated(brief, list(path), disabled=[], conventional_only=False)
        except ValueError:
            continue
        if best is None or outcome["rank"] < best["rank"]:
            best = outcome
    return best
