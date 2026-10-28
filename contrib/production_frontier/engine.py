# SPDX-License-Identifier: Apache-2.0
"""Backward relevance and forward construction with consumable, typed resources.

This compiler executes a finite declared model, never the proposed real-world
actions. Facts, performance, prices and permissions remain declarations. Existing
SUCCESSOR records and authority services retain their roles.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from alpha_factory_v1.core.runtime.successor.protocol import (
    Digest,
    Identifier,
    StrictModel,
    Text,
    canonical,
    digest,
)

Quantity = Annotated[int, Field(ge=0, le=100_000)]
Money = Annotated[int, Field(ge=0, le=10**12)]


class Source(StrictModel):
    source_id: Identifier
    uri: Text
    sha256: Digest
    kind: Literal["public-primary", "measurement", "authorized-brief", "authored-assumption"]
    supports: Text
    does_not_establish: Text


class Resource(StrictModel):
    resource_id: Identifier
    unit: Text
    meaning: Text


class Recipe(StrictModel):
    recipe_id: Identifier
    description: Text
    consumes: dict[Identifier, Quantity] = Field(max_length=24)
    produces: dict[Identifier, Quantity] = Field(max_length=24)
    requires: list[Identifier] = Field(max_length=24)
    provides: list[Identifier] = Field(max_length=24)
    preserves: list[Identifier] = Field(min_length=1, max_length=24)
    permission: Literal["research-cleared", "required", "denied"]
    permission_basis: Text
    origin: Literal["conventional", "proposed-construction"]
    estimated_cost_micro_usd: Money
    seconds: int = Field(ge=1, le=43_200)
    sources: list[Identifier] = Field(min_length=1, max_length=16)
    acceptance: Text
    failure: Text

    @model_validator(mode="after")
    def coherent(self) -> Recipe:
        for values in (self.requires, self.provides, self.preserves, self.sources):
            if len(values) != len(set(values)):
                raise ValueError("recipe references must be distinct")
        if not self.produces and not self.provides:
            raise ValueError("a construction must produce a resource or capability")
        if any(v == 0 for v in [*self.consumes.values(), *self.produces.values()]):
            raise ValueError("omit zero resource flows")
        return self


class ProductionBrief(StrictModel):
    schema_name: Literal["production-frontier/v1"] = "production-frontier/v1"
    brief_id: Identifier
    beneficiary: Text
    useful_outcome: Text
    binding_constraint: Text
    input_mode: Literal["authored-simulation", "public-requirements", "authorized-measurements"]
    resources: list[Resource] = Field(min_length=1, max_length=24)
    stock: dict[Identifier, Quantity] = Field(max_length=24)
    capabilities: list[Identifier] = Field(max_length=24)
    required_stock: dict[Identifier, Quantity] = Field(min_length=1, max_length=24)
    required_capabilities: list[Identifier] = Field(max_length=24)
    obligations: list[Identifier] = Field(min_length=1, max_length=24)
    recipes: list[Recipe] = Field(min_length=1, max_length=12)
    sources: list[Source] = Field(min_length=1, max_length=24)
    cost_cap_micro_usd: Money
    seconds_cap: int = Field(ge=1, le=43_200)
    state_cap: int = Field(default=4096, ge=1, le=4096)
    limitations: list[Text] = Field(min_length=1, max_length=24)

    @model_validator(mode="after")
    def coherent(self) -> ProductionBrief:
        resources = {r.resource_id for r in self.resources}
        sources = {s.source_id for s in self.sources}
        if len(resources) != len(self.resources) or len(sources) != len(self.sources):
            raise ValueError("resource and source identities must be unique")
        if len({r.recipe_id for r in self.recipes}) != len(self.recipes):
            raise ValueError("recipe identities must be unique")
        for values in (self.capabilities, self.required_capabilities, self.obligations):
            if len(values) != len(set(values)):
                raise ValueError("brief predicates must be distinct")
        if not (self.stock.keys() | self.required_stock.keys()) <= resources:
            raise ValueError("stock and requirements must bind declared resource units")
        if any(v == 0 for v in self.required_stock.values()):
            raise ValueError("required stock must be positive")
        for recipe in self.recipes:
            if not (recipe.consumes.keys() | recipe.produces.keys()) <= resources or not set(recipe.sources) <= sources:
                raise ValueError("every flow and source must be declared")
        if len(canonical(self)) > 160_000:
            raise ValueError("brief exceeds its byte budget")
        return self


class ConstructionPolicy(StrictModel):
    schema_name: Literal["production-frontier-policy/v1"] = "production-frontier-policy/v1"
    ranking: Literal["permissions-cost-new-components-time-length-identities"] = (
        "permissions-cost-new-components-time-length-identities"
    )
    acceptance: Literal["typed-conservation-final-requirements-obligations-budgets"] = (
        "typed-conservation-final-requirements-obligations-budgets"
    )
    model_scope: Literal["finite-single-use-sequential-recipes"] = "finite-single-use-sequential-recipes"


def binding(brief: ProductionBrief, policy: ConstructionPolicy) -> str:
    return digest("production-frontier-exact-input-and-policy/v1", {"brief": brief, "policy": policy})


def _relevant(brief: ProductionBrief) -> set[str]:
    """Trace unmet outputs backwards; do not insert domain-specific answers."""
    resources, capabilities = set(brief.required_stock), set(brief.required_capabilities)
    selected: set[str] = set()
    changed = True
    while changed:
        changed = False
        for recipe in brief.recipes:
            if recipe.recipe_id not in selected and (
                recipe.produces.keys() & resources or set(recipe.provides) & capabilities
            ):
                selected.add(recipe.recipe_id)
                resources.update(recipe.consumes)
                capabilities.update(recipe.requires)
                changed = True
    return selected


def construct(
    brief: ProductionBrief,
    policy: ConstructionPolicy | None = None,
    *,
    disabled: frozenset[str] = frozenset(),
    conventional_only: bool = False,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Generate feasible complementary systems; all resource use is simulated."""
    brief = ProductionBrief.model_validate_json(canonical(brief))
    policy = ConstructionPolicy.model_validate_json(canonical(policy or ConstructionPolicy()))
    if not disabled <= {r.recipe_id for r in brief.recipes}:
        raise ValueError("disabled recipes must belong to the exact brief")
    relevant = _relevant(brief)
    recipes = sorted(
        [
            r
            for r in brief.recipes
            if r.recipe_id in relevant
            and r.recipe_id not in disabled
            and r.permission != "denied"
            and (not conventional_only or r.origin == "conventional")
            and set(brief.obligations) <= set(r.preserves)
        ],
        key=lambda r: r.recipe_id,
    )
    # For a subset, balances, capabilities, cost and elapsed time are independent
    # of its feasible ordering. Keep one ordering, not factorial duplicates.
    queue: deque[tuple[int, list[int], dict[str, int], set[str], int, int]] = deque(
        [
            (
                0,
                [],
                {r.resource_id: brief.stock.get(r.resource_id, 0) for r in brief.resources},
                set(brief.capabilities),
                0,
                0,
            )
        ]
    )
    seen = {0}
    candidates: list[dict[str, Any]] = []
    visited, incomplete, interrupted = 0, False, False
    while queue:
        if cancelled and cancelled():
            interrupted = True
            break
        if visited >= brief.state_cap:
            incomplete = True
            break
        mask, route, stock, capabilities, cost, seconds = queue.popleft()
        visited += 1
        if (
            all(stock.get(k, 0) >= v for k, v in brief.required_stock.items())
            and set(brief.required_capabilities) <= capabilities
        ):
            steps = [brief.recipes[i] for i in route]
            pending = [r.recipe_id for r in steps if r.permission == "required"]
            rank = [
                len(pending),
                cost,
                sum(r.origin == "proposed-construction" for r in steps),
                seconds,
                len(steps),
                [r.recipe_id for r in steps],
            ]
            candidates.append(
                {
                    "steps": [r.recipe_id for r in steps],
                    "pending_permissions": pending,
                    "stock": stock,
                    "capabilities": sorted(capabilities),
                    "estimated_cost_micro_usd": cost,
                    "seconds": seconds,
                    "rank": rank,
                }
            )
        for recipe in recipes:
            i = next(i for i, r in enumerate(brief.recipes) if r.recipe_id == recipe.recipe_id)
            next_mask = mask | (1 << i)
            if next_mask == mask or next_mask in seen or not set(recipe.requires) <= capabilities:
                continue
            if any(stock.get(k, 0) < v for k, v in recipe.consumes.items()):
                continue
            if cost + recipe.estimated_cost_micro_usd > brief.cost_cap_micro_usd or seconds + recipe.seconds > (
                brief.seconds_cap
            ):
                continue
            updated = dict(stock)
            for k, v in recipe.consumes.items():
                updated[k] = updated.get(k, 0) - v
            for k, v in recipe.produces.items():
                updated[k] = updated.get(k, 0) + v
            seen.add(next_mask)
            queue.append(
                (
                    next_mask,
                    route + [i],
                    updated,
                    capabilities | set(recipe.provides),
                    cost + recipe.estimated_cost_micro_usd,
                    seconds + recipe.seconds,
                )
            )
    candidates.sort(key=lambda x: x["rank"])
    return {
        "schema": "production-frontier-result/v1",
        "binding": binding(brief, policy),
        "brief_id": brief.brief_id,
        "adapter": "declared-model-simulation",
        "input_mode": brief.input_mode,
        "policy": policy.model_dump(),
        "disabled": sorted(disabled),
        "conventional_only": conventional_only,
        "status": "cancelled"
        if interrupted
        else "incomplete"
        if incomplete
        else "feasible"
        if candidates
        else "no-plan",
        "search_complete": not incomplete and not interrupted,
        "states": visited,
        "candidate_count": len(candidates),
        "candidates": candidates[:8],
        "best": candidates[0] if candidates else None,
        "authority_granted": False,
        "real_actions_executed": False,
        "scientific_or_commercial_acceptance": False,
        "scope": "finite declared recipes; no physical truth, optimality outside this grammar or real approval inferred",
    }


def ablate(brief: ProductionBrief, policy: ConstructionPolicy | None = None) -> dict[str, Any]:
    """Test each selected dependency rather than declaring it indispensable."""
    original = construct(brief, policy)
    results = []
    if original["best"]:
        for recipe_id in original["best"]["steps"]:
            removed = construct(brief, policy, disabled=frozenset({recipe_id}))
            if not original["search_complete"] or not removed["search_complete"]:
                verdict = "unknown"
            elif removed["best"] is None:
                verdict = "necessary-in-declared-model"
            elif removed["best"]["rank"][:5] > original["best"]["rank"][:5]:
                verdict = "improves-declared-objective"
            else:
                verdict = "not-necessary"
            results.append({"removed": recipe_id, "verdict": verdict, "result": removed})
    return {"original": original, "ablations": results}
