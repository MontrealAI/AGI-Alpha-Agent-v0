# SPDX-License-Identifier: Apache-2.0
"""Causal discovery dossiers, bottom-up scale and preserved rejection decisions."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from alpha_factory_v1.core.runtime.successor.protocol import Identifier, StrictModel, Text, canonical, digest

from .engine import ProductionBrief, Source, ablate, construct


class Link(StrictModel):
    link: Literal[
        "need-constraint", "constraint-construction", "construction-outcome", "outcome-buyer-value", "value-expansion"
    ]
    claim: Text
    sources: list[Identifier] = Field(min_length=1, max_length=16)
    counters: list[Identifier] = Field(max_length=16)
    status: Literal[
        "supported-public-context", "validated-specific-relationship", "assumed", "contradicted", "unmeasured"
    ]
    falsifier: Text


class Scale(StrictModel):
    currency: Literal["USD"] = "USD"
    metric: Literal["cumulative-incremental-customer-net-benefit"] = "cumulative-incremental-customer-net-benefit"
    horizon_years: int = Field(ge=1, le=20)
    reachable_organizations: int = Field(ge=0, le=100_000)
    active_organizations_by_year: list[Annotated[int, Field(ge=0, le=100_000)]] = Field(min_length=1, max_length=20)
    units_per_organization_per_year: int = Field(ge=0, le=1_000_000)
    production_capacity_units_by_year: list[Annotated[int, Field(ge=0, le=10**9)]] = Field(min_length=1, max_length=20)
    incremental_net_benefit_micro_usd_per_unit: int = Field(ge=0, le=10**12)
    capital_required_micro_usd: int = Field(ge=0, le=10**15)
    capital_committed_micro_usd: int = Field(ge=0, le=10**15)
    verified_inputs: bool
    basis: Text

    @model_validator(mode="after")
    def coherent(self) -> Scale:
        if (
            len(self.active_organizations_by_year) != self.horizon_years
            or len(self.production_capacity_units_by_year) != self.horizon_years
        ):
            raise ValueError("every year needs adoption and capacity")
        if any(n > self.reachable_organizations for n in self.active_organizations_by_year):
            raise ValueError("adoption cannot exceed the reachable population")
        return self


class Hypothesis(StrictModel):
    hypothesis_id: Identifier
    causal_core: Text
    beneficiaries: Text
    why_now: Text
    prior_approach: Text
    what_prior_approach_already_delivers: Text
    remaining_gap: Text
    links: list[Link] = Field(min_length=5, max_length=5)
    sources: list[Source] = Field(min_length=1, max_length=16)
    scale: Scale
    next_experiment: Text
    next_experiment_cap_micro_usd: int = Field(ge=1, le=10**12)
    stopping_condition: Text

    @model_validator(mode="after")
    def coherent(self) -> Hypothesis:
        if len({x.link for x in self.links}) != 5:
            raise ValueError("each causal relationship needs its own inspectable evidence")
        source_ids = {s.source_id for s in self.sources}
        if len(source_ids) != len(self.sources) or any(
            not set(link.sources + link.counters) <= source_ids for link in self.links
        ):
            raise ValueError("causal evidence must resolve to unique source identities")
        return self


def scale_audit(scale: Scale) -> dict[str, Any]:
    """Cap adoption by declared productive capacity; calculate thresholds, not TAM."""
    scale = Scale.model_validate_json(canonical(scale))
    served = [
        min(n * scale.units_per_organization_per_year, cap)
        for n, cap in zip(scale.active_organizations_by_year, scale.production_capacity_units_by_year)
    ]
    total_units = sum(served)
    net_value = total_units * scale.incremental_net_benefit_micro_usd_per_unit
    target = 10**15  # USD one billion, in micro-USD.
    threshold = (target + total_units - 1) // total_units if total_units else None
    capital_gap = max(0, scale.capital_required_micro_usd - scale.capital_committed_micro_usd)
    return {
        "currency": scale.currency,
        "metric": scale.metric,
        "horizon_years": scale.horizon_years,
        "served_units_by_year": served,
        "total_served_units": total_units,
        "conditional_net_benefit_micro_usd": str(net_value),
        "net_benefit_per_unit_required_for_billion_micro_usd": str(threshold) if threshold is not None else None,
        "capital_gap_micro_usd": capital_gap,
        "arithmetically_reaches_billion": net_value >= target,
        "scale_evidence_complete_as_declared": scale.verified_inputs and capital_gap == 0 and net_value >= target,
        "credible_billion_plus_established": False,
        "evidence_scope": "verified_inputs is the caller's declaration; no independent credibility adjudication is implemented",
        "scope": "Input-dependent arithmetic; no company revenue, provider profit or valuation follows",
    }


def discover(
    hypothesis: Hypothesis, brief: ProductionBrief, *, prior_rejections: list[dict[str, Any]]
) -> dict[str, Any]:
    """Generate combinations and challenge their causal links, not only rank names."""
    hypothesis = Hypothesis.model_validate_json(canonical(hypothesis))
    brief = ProductionBrief.model_validate_json(canonical(brief))
    core = digest("production-frontier-causal-core/v1", {"core": hypothesis.causal_core})
    prior = [r for r in prior_rejections if r.get("causal_core_digest") == core]
    if prior:
        return {
            "hypothesis_id": hypothesis.hypothesis_id,
            "causal_core_digest": core,
            "decision": "previously-rejected-requires-material-new-evidence",
            "previous": prior,
            "authority_granted": False,
        }
    construction = ablate(brief)
    conventional = construct(brief, conventional_only=True)
    scale = scale_audit(hypothesis.scale)
    gaps = [
        link.link + ":" + link.status for link in hypothesis.links if link.status != "validated-specific-relationship"
    ]
    if brief.input_mode == "authored-simulation":
        gaps.append("construction validated only in an authored finite model")
    if not construction["original"]["search_complete"]:
        gaps.append("construction search incomplete")
    if construction["original"]["best"] is None:
        gaps.append("no declared-model construction under the original requirements and budget")
    if not scale["scale_evidence_complete_as_declared"]:
        gaps.append("bottom-up billion-plus economics, adoption, capacity or capital unestablished")
    return {
        "hypothesis_id": hypothesis.hypothesis_id,
        "causal_core_digest": core,
        "hypothesis_digest": digest("production-frontier-hypothesis/v1", hypothesis),
        "decision": "HOLD-no-admitted-opportunity" if gaps else "research-case-eligible-for-independent-review",
        "reasons": gaps,
        "construction": construction,
        "conventional_component_control": conventional,
        "scale": scale,
        "next_experiment": hypothesis.next_experiment,
        "next_experiment_cap_micro_usd": hypothesis.next_experiment_cap_micro_usd,
        "stopping_condition": hypothesis.stopping_condition,
        "authority_granted": False,
        "qualification": "A research dossier cannot authorize production, enterprise admission, spending or buyer acceptance",
        "dossier_statuses": "Caller-declared interpretations, not independently adjudicated evidence",
    }
