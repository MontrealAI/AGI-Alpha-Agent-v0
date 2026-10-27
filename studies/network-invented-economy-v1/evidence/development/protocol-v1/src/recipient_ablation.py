# SPDX-License-Identifier: Apache-2.0
"""Deterministic modeled recipient-cost probes against competent, frozen Beta.

This module executes accounting comparisons, not frontier models or customer jobs.
It reuses the simulator's priced Work catalogs. No witness operation count is
converted to dollars, and no quality multiplier or random synthetic gain is used.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any

from .alpha_assessment import AlphaAssessment, AlphaCosts, BetaBaseline, evaluate_alpha
from .simulator import (
    CONSTRUCTION, CORRECTION, EVALUATION, INTAKE, INTEGRATION, KINDS, PACKAGING,
    PRODUCTION, RECONSTRUCTION, REVALIDATE, VALIDATION, Scenario, Work,
)


SCHEMA = "beyond-beta.recipient-ablation.v1"
PROTOCOL_ID = "frozen-recipient-required-cost-v1"
OUTCOMES = ("success", "failed", "harmful")


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def _number(value: float, name: str, *, minimum: float = 0, maximum: float | None = None) -> None:
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < minimum or (maximum is not None and value > maximum)):
        raise ValueError(f"invalid {name}")


def _integer(value: int, name: str, *, minimum: int = 0, maximum: int = 10000) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"invalid {name}")


def _work(value: Work) -> None:
    if not isinstance(value, Work):
        raise ValueError("an explicit Work record is required")
    for name, amount in asdict(value).items():
        _number(amount, "work " + name)


def _components(values: tuple[int, ...], *, allow_empty: bool = False) -> None:
    if (not isinstance(values, tuple) or (not values and not allow_empty)
            or len(set(values)) != len(values)
            or any(type(v) is not int or not 0 <= v < len(KINDS) for v in values)):
        raise ValueError("components must be an immutable unique tuple of known kinds")


def _sum_work(values: Any) -> Work:
    result = Work()
    for value in values:
        result = result + value
    return result


def _round(value: float) -> float:
    return round(value, 8)


@dataclass(frozen=True)
class RecipientSnapshot:
    """Ordinary experience and equivalent methods survive candidate removal.

ordinary_factors model how much of the standard reconstruction workload remains.
They change effort, not intelligence, correctness or acceptance probabilities.
equivalents are already held, eligible methods with their complete marginal Work.
"""

    name: str
    beta: BetaBaseline
    ordinary_factors: tuple[float, float, float] = (1.0, 1.0, 1.0)
    equivalents: tuple[Work | None, Work | None, Work | None] = (None, None, None)

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.beta, BetaBaseline):
            raise ValueError("described recipient and Beta baseline required")
        if (not isinstance(self.ordinary_factors, tuple) or len(self.ordinary_factors) != len(KINDS)
                or not isinstance(self.equivalents, tuple) or len(self.equivalents) != len(KINDS)):
            raise ValueError("one immutable ordinary/equivalent entry per component is required")
        for amount in self.ordinary_factors:
            _number(amount, "ordinary reconstruction factor", maximum=1)
        for value in self.equivalents:
            if value is not None:
                _work(value)

    @property
    def hash(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class FrozenMission:
    mission_id: str
    domain: int
    components: tuple[int, ...]
    common_work: Work
    week: int = 0
    available_cash: float = 10000.0
    input_limit_m: float = 2400.0
    output_limit_m: float = 480.0
    deadline_weeks: float = 12.0

    def __post_init__(self) -> None:
        if not self.mission_id:
            raise ValueError("mission identity required")
        _integer(self.domain, "domain", maximum=2)
        _components(self.components)
        _work(self.common_work)
        _integer(self.week, "week")
        for name in ("available_cash", "input_limit_m", "output_limit_m", "deadline_weeks"):
            _number(getattr(self, name), name)


@dataclass(frozen=True)
class CandidateBundle:
    """One removable artifact or jointly assessed bundle; this is not a permit."""

    candidate_id: str
    beta_id: str
    components: tuple[int, ...] = (0, 1, 2)
    residual_work: tuple[Work, Work, Work] = field(
        default_factory=lambda: tuple(w.scale(0.22) for w in RECONSTRUCTION))
    domain: int = 0
    status: str = "admitted"
    expires_week: int = 10000
    validation_due_week: int = 12

    def __post_init__(self) -> None:
        if not self.candidate_id or not self.beta_id:
            raise ValueError("candidate and assessment baseline identities required")
        _components(self.components)
        if not isinstance(self.residual_work, tuple) or len(self.residual_work) != len(KINDS):
            raise ValueError("explicit residual work per component required")
        for value in self.residual_work:
            _work(value)
        _integer(self.domain, "candidate domain", maximum=2)
        _integer(self.expires_week, "expiry")
        _integer(self.validation_due_week, "validation due")
        if self.status not in {"admitted", "candidate", "revoked", "retired", "superseded"}:
            raise ValueError("unknown candidate status")

    @property
    def hash(self) -> str:
        return _hash(asdict(self))


@dataclass(frozen=True)
class LifecyclePlan:
    """All values are assumed USD totals/rates, not measured venture expenses.

The construction amount includes failed attempts; failed_construction_cost is a
disclosed subset, never an extra charge. Historical costs remain in project
profitability but cannot make prospective reconstruction unaffordable a second time.
"""

    upfront: AlphaCosts = field(default_factory=AlphaCosts)
    failed_construction_cost: float = 0.0
    historical_cost: float = 0.0
    weekly_upkeep: float = 0.0
    revalidation_cost: float = 0.0
    revalidation_period_weeks: int = 12
    beta_reassessment_cost: float = 0.0
    useful_lifetime_weeks: int = 40
    uses_per_week: int = 2
    available_investment_cash: float = 50000.0
    uncertainty_margin_per_use: float = 0.0
    reassess_moving_beta: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.upfront, AlphaCosts):
            raise ValueError("complete explicit upfront costs required")
        for name in ("failed_construction_cost", "historical_cost", "weekly_upkeep", "revalidation_cost",
                     "beta_reassessment_cost", "available_investment_cash", "uncertainty_margin_per_use"):
            _number(getattr(self, name), name)
        if self.failed_construction_cost > self.upfront.construction + 1e-9:
            raise ValueError("failed construction must be a subset of construction cost")
        _integer(self.revalidation_period_weeks, "revalidation period", minimum=1)
        _integer(self.useful_lifetime_weeks, "useful lifetime", minimum=1, maximum=1040)
        _integer(self.uses_per_week, "uses per week", maximum=10000)
        if type(self.reassess_moving_beta) is not bool:
            raise ValueError("explicit reassessment choice required")


def default_beta(version: str = "competent-beta-cost-probe-v1") -> BetaBaseline:
    description = ("Astra Pro reasoning, Terra execution, ordinary theory/solvers, source grounding, "
                   "critique/correction and accumulated experience; no missing-file incapacity.")
    return BetaBaseline(version, _hash({"description": description, "effort_catalog": "simulator.Work",
                                        "version": version}), description, "simulation")


def standard_mission(scenario: Scenario, components: tuple[int, ...] = (0, 1, 2)) -> FrozenMission:
    _components(components)
    depth = max(components) + 1
    return FrozenMission("frozen-bounded-mechanism", 0, components,
                         INTAKE + PRODUCTION[depth - 1] + VALIDATION[depth - 1] + PACKAGING,
                         input_limit_m=scenario.quota_input_m * 12,
                         output_limit_m=scenario.quota_output_m * 12)


def standard_lifecycle(scenario: Scenario, bundle: CandidateBundle, *, failed_attempts: int = 1) -> LifecyclePlan:
    _integer(failed_attempts, "failed attempts", maximum=100)
    construction = sum(CONSTRUCTION[k].cost(scenario) for k in bundle.components) * scenario.construction_cost_factor
    return LifecyclePlan(
        upfront=AlphaCosts(construction=construction * (1 + failed_attempts),
                           validation=EVALUATION.cost(scenario) + REVALIDATE.cost(scenario),
                           acquisition=len(bundle.components) * scenario.sharing_bounty),
        failed_construction_cost=construction * failed_attempts,
        weekly_upkeep=(len(bundle.components) * scenario.maintenance_per_skill + scenario.distribution_fixed
                       + scenario.membership_count * scenario.member_overhead),
        revalidation_cost=REVALIDATE.cost(scenario), revalidation_period_weeks=scenario.revalidation_period,
        beta_reassessment_cost=EVALUATION.cost(scenario), useful_lifetime_weeks=scenario.useful_lifetime,
    )


def _route(work: Work, scenario: Scenario, mission: FrozenMission) -> dict[str, Any]:
    cost = work.cost(scenario)
    limits = {"cash": cost <= mission.available_cash + 1e-9,
              "input_quota": work.input_m <= mission.input_limit_m + 1e-9,
              "output_quota": work.output_m <= mission.output_limit_m + 1e-9,
              "deadline": work.latency <= mission.deadline_weeks + 1e-9}
    return {"cost_usd": _round(cost), "input_m": _round(work.input_m), "output_m": _round(work.output_m),
            "serial_latency_weeks": _round(work.latency), "feasible": all(limits.values()),
            "constraints": limits, "work": asdict(work)}


def probe_recipient(
    scenario: Scenario, recipient: RecipientSnapshot, mission: FrozenMission, bundle: CandidateBundle,
    *, validation_overhead: float = 1.0, frontier_factor: float = 1.0,
) -> dict[str, Any]:
    """Compare required full routes; optional use is chosen before transfer outcome.

Failure/harm branches pay the full attempted route, competent reconstruction and
recovery. They are defined to recover the same functional scope if resources
suffice. No claim about real correctness, acceptance or failure rates follows.
"""
    _number(validation_overhead, "validation overhead")
    _number(frontier_factor, "frontier factor", maximum=1)
    for name in ("transfer_success", "harmful_transfer"):
        _number(getattr(scenario, name), name, maximum=1)
    ordinary: dict[int, Work] = {}
    routes: dict[str, str] = {}
    for kind in mission.components:
        reconstruction = RECONSTRUCTION[kind].scale(recipient.ordinary_factors[kind] * frontier_factor)
        equivalent = recipient.equivalents[kind]
        use_existing = equivalent is not None and equivalent.cost(scenario) <= reconstruction.cost(scenario)
        ordinary[kind] = equivalent if use_existing else reconstruction
        routes[str(kind)] = "existing-equivalent" if use_existing else "competent-reconstruction"
    beta_work = mission.common_work + _sum_work(ordinary.values())
    beta_route = _route(beta_work, scenario, mission)
    reasons = []
    if bundle.status != "admitted":
        reasons.append("not-currently-admitted")
    if bundle.beta_id != recipient.beta.beta_id:
        reasons.append("stale-beta-assessment")
    if bundle.domain != mission.domain:
        reasons.append("outside-scope")
    if mission.week >= bundle.expires_week:
        reasons.append("expired")
    if mission.week >= bundle.validation_due_week:
        reasons.append("revalidation-due")
    probabilities = {
        "success": scenario.transfer_success * (1 - scenario.harmful_transfer),
        "failed": 1 - scenario.transfer_success,
        "harmful": scenario.transfer_success * scenario.harmful_transfer,
    }
    selected: tuple[int, ...] = ()
    best_cost = beta_work.cost(scenario)
    best_branches = {key: beta_work for key in OUTCOMES}
    best_breakdown: dict[str, Any] = {}
    eligible = tuple(k for k in bundle.components if k in mission.components) if not reasons else ()
    for count in range(1, len(eligible) + 1):
        for subset in itertools.combinations(eligible, count):
            retained_ordinary = _sum_work(work for k, work in ordinary.items() if k not in subset)
            residual = _sum_work(bundle.residual_work[k] for k in subset)
            integration = INTEGRATION.scale(len(subset) * validation_overhead)
            checking = REVALIDATE.scale(validation_overhead)
            attempted = residual + integration + checking
            success = mission.common_work + retained_ordinary + attempted
            failed = beta_work + attempted + CORRECTION
            harmful = failed + VALIDATION[max(mission.components)]
            branches = {"success": success, "failed": failed, "harmful": harmful}
            expected = math.fsum(probabilities[key] * work.cost(scenario) for key, work in branches.items())
            if expected < best_cost - 1e-9:
                selected, best_cost, best_branches = subset, expected, branches
                best_breakdown = {"residual_work": asdict(residual), "integration_work": asdict(integration),
                                  "receiving_validation_work": asdict(checking),
                                  "failed_recovery_work": asdict(CORRECTION),
                                  "harmful_additional_validation_work": asdict(VALIDATION[max(mission.components)])}
    conditional = {key: {"probability": _round(probabilities[key]), **_route(work, scenario, mission)}
                   for key, work in best_branches.items()}
    if not selected:
        conditional = {"ordinary": {"probability": 1.0, **beta_route}}
    feasibility = math.fsum(row["probability"] for row in conditional.values() if row["feasible"])
    state = {"scenario": asdict(scenario), "recipient": asdict(recipient), "mission": asdict(mission),
             "candidate": asdict(bundle), "validation_overhead": validation_overhead,
             "frontier_factor": frontier_factor}
    return {
        "schema": SCHEMA, "source_kind": "simulation", "state_hash": _hash(state),
        "beta_id": recipient.beta.beta_id, "comparator_capability_set_hash": recipient.hash,
        "candidate_hash": bundle.hash, "recipient": recipient.name, "mission": mission.mission_id,
        "ordinary_component_routes": routes, "preserved_equivalents": [k for k in mission.components
                                                                        if recipient.equivalents[k] is not None],
        "beta": beta_route, "selected_components": list(selected), "eligibility_rejections": reasons,
        "shared_conditional_routes": conditional, "transfer_cost_breakdown": best_breakdown,
        "shared_expected_cost_usd": _round(best_cost),
        "expected_delivery_saving_usd": _round(beta_work.cost(scenario) - best_cost),
        "shared_feasible_probability": _round(feasibility),
        "newly_feasible_probability": _round(feasibility if not beta_route["feasible"] else 0.0),
        "lost_feasibility_probability": _round(1 - feasibility if beta_route["feasible"] else 0.0),
        "interpretation": "Required modeled complete mission costs; no cash spent, sale, correctness trial or measured frontier outcome.",
    }


def required_reuses(fixed_cost: float, saving_per_use: float, uncertainty_per_use: float = 0.0) -> int | None:
    """Smallest integer count with strictly positive net; None means no crossing."""
    _number(fixed_cost, "fixed cost")
    _number(uncertainty_per_use, "uncertainty")
    _number(saving_per_use, "saving", minimum=-1e100)
    margin = saving_per_use - uncertainty_per_use
    return None if margin <= 0 else math.floor(fixed_cost / margin) + 1


def assess_lifecycle(
    scenario: Scenario, recipients: tuple[RecipientSnapshot, ...], mission: FrozenMission,
    bundle: CandidateBundle, plan: LifecyclePlan, *, weights: tuple[float, ...] | None = None,
    validation_overhead: float = 1.0, frontier_improvement: float | None = None,
) -> dict[str, Any]:
    """Project required reuse/life with per-week paired costs and all lifecycle costs.

This is a prospective cost surface, not the enterprise's finite-cash event ledger.
Upfront affordability is checked independently of any projected future savings.
Revalidation and (if chosen) moving-Beta reassessment are assumed to succeed and
are charged. Their failure probabilities belong in the enterprise simulator.
"""
    if not isinstance(recipients, tuple) or not recipients:
        raise ValueError("an immutable nonempty recipient population is required")
    if len({p.name for p in recipients}) != len(recipients):
        raise ValueError("recipient identities must be unique")
    if weights is None:
        weights = tuple(1 / len(recipients) for _ in recipients)
    if not isinstance(weights, tuple) or len(weights) != len(recipients):
        raise ValueError("one immutable population weight per recipient required")
    for weight in weights:
        _number(weight, "recipient weight")
    total_weight = math.fsum(weights)
    if total_weight <= 0:
        raise ValueError("positive population weight required")
    normalized = tuple(w / total_weight for w in weights)
    improvement = scenario.external_improvement if frontier_improvement is None else frontier_improvement
    _number(improvement, "annual frontier improvement", maximum=4)
    _integer(scenario.beta_epoch_weeks, "Beta epoch", minimum=1)
    initial = plan.upfront.total
    cumulative_delivery = cumulative_beta = cumulative_shared = 0.0
    upkeep = revalidation = reassessment = 0.0
    previous_epoch = mission.week // scenario.beta_epoch_weeks
    rows = []
    weekly_gains = []
    all_routes_feasible = True
    any_selected = False
    for elapsed in range(1, plan.useful_lifetime_weeks + 1):
        week = mission.week + elapsed
        epoch = week // scenario.beta_epoch_weeks if improvement else previous_epoch
        beta_changed = improvement > 0 and epoch != previous_epoch
        if beta_changed and plan.reassess_moving_beta:
            reassessment += plan.beta_reassessment_cost
        previous_epoch = epoch
        if elapsed % plan.revalidation_period_weeks == 0:
            revalidation += plan.revalidation_cost
        upkeep += plan.weekly_upkeep
        factor = max(0.15, 1 - improvement * elapsed / 52)
        probes = []
        for recipient in recipients:
            version = recipient.beta.beta_id if not improvement or epoch == mission.week // scenario.beta_epoch_weeks else (
                recipient.beta.beta_id + f"/epoch-{epoch}")
            current_beta = replace(recipient.beta, beta_id=version,
                                   configuration_hash=_hash({"base": recipient.beta.configuration_hash,
                                                             "week": week, "factor": factor}))
            current_recipient = replace(recipient, beta=current_beta)
            initially_current = bundle.beta_id == recipient.beta.beta_id
            candidate_version = version if initially_current and plan.reassess_moving_beta else bundle.beta_id
            initial_evidence_current = mission.week < bundle.validation_due_week
            next_check = (mission.week + (elapsed // plan.revalidation_period_weeks + 1)
                          * plan.revalidation_period_weeks) if initial_evidence_current else bundle.validation_due_week
            maintained = replace(bundle, beta_id=candidate_version, validation_due_week=next_check)
            probes.append(probe_recipient(scenario, current_recipient, replace(mission, week=week), maintained,
                                          validation_overhead=validation_overhead, frontier_factor=factor))
        gain = math.fsum(weight * probe["expected_delivery_saving_usd"] for weight, probe in zip(normalized, probes))
        beta_cost = math.fsum(weight * probe["beta"]["cost_usd"] for weight, probe in zip(normalized, probes))
        shared_cost = math.fsum(weight * probe["shared_expected_cost_usd"] for weight, probe in zip(normalized, probes))
        weekly_gains.append(gain)
        cumulative_delivery += gain * plan.uses_per_week
        cumulative_beta += beta_cost * plan.uses_per_week
        cumulative_shared += shared_cost * plan.uses_per_week
        if plan.uses_per_week:
            all_routes_feasible &= all(probe["shared_feasible_probability"] >= 1 - 1e-8
                                       for weight, probe in zip(normalized, probes) if weight > 0)
            any_selected |= any(probe["selected_components"] for weight, probe in zip(normalized, probes) if weight > 0)
        complete_lifecycle = initial + plan.historical_cost + upkeep + revalidation + reassessment
        uses = elapsed * plan.uses_per_week
        net = cumulative_delivery - complete_lifecycle
        rows.append({"week": elapsed, "baseline_versions": sorted({p["beta_id"] for p in probes}),
                     "frontier_factor": _round(factor), "uses": uses,
                     "expected_saving_per_use": _round(gain), "cumulative_delivery_saving": _round(cumulative_delivery),
                     "complete_lifecycle_cost": _round(complete_lifecycle), "project_net": _round(net),
                     "lower_project_net": _round(net - uses * plan.uncertainty_margin_per_use),
                     "prospective_net": _round(net + plan.historical_cost),
                     "revalidation_cost_to_date": _round(revalidation),
                     "beta_reassessment_cost_to_date": _round(reassessment)})
    planned_reuse = plan.useful_lifetime_weeks * plan.uses_per_week
    alpha_cost_values = asdict(plan.upfront)
    alpha_cost_values["acquisition"] += plan.historical_cost
    alpha_cost_values["maintenance"] += upkeep + revalidation + reassessment
    costs = AlphaCosts(**alpha_cost_values)
    evidence = {"protocol": PROTOCOL_ID, "scenario": asdict(scenario), "recipients": [asdict(p) for p in recipients],
                "weights": normalized, "mission": asdict(mission), "bundle": asdict(bundle),
                "plan": asdict(plan), "validation_overhead": validation_overhead,
                "frontier_improvement": improvement, "rows": rows}
    path_id = "declared-beta-path-" + _hash({"recipients": [p.beta.hash for p in recipients], "improvement": improvement,
                                            "epoch_weeks": scenario.beta_epoch_weeks, "start_week": mission.week})[:20]
    assessment = decision = None
    if len(weekly_gains) >= 2:
        alpha = AlphaAssessment(
            beta_id=path_id, comparator_capability_set_hash=_hash([p.hash for p in recipients]),
            scope=("bounded-mechanism-required-cost", "declared-beta-path", "joint-bundle" if len(bundle.components) > 1 else "single-component"),
            paired_gains=tuple(weekly_gains), planned_reuse=planned_reuse, costs=costs,
            uncertainty_margin_per_use=plan.uncertainty_margin_per_use, source_kind="simulation",
            protocol_id=PROTOCOL_ID, evidence_hash=_hash(evidence),
            dependency_hashes=tuple(_hash({"kind": k, "residual": asdict(bundle.residual_work[k])}) for k in bundle.components),
            redundant=not any_selected,
        )
        assessment, decision = asdict(alpha), asdict(evaluate_alpha(alpha))
    positive = [r["week"] for r in rows if r["lower_project_net"] > 0]
    durable = next((r["week"] for r in rows if all(x["lower_project_net"] > 0 for x in rows[r["week"] - 1:])), None)
    average_gain = math.fsum(weekly_gains) / len(weekly_gains)
    affordable = initial <= plan.available_investment_cash + 1e-9
    return {
        "schema": SCHEMA, "source_kind": "simulation", "protocol_id": PROTOCOL_ID,
        "input_and_evidence_hash": _hash(evidence), "baseline_path_id": path_id,
        "assumptions": {"outcomes_are_declared_model_branches": True, "functional_fallback_is_assumed": True,
                        "same_ordinary_models_tools_and_experience": True, "no_quality_multiplier": True,
                        "revalidation_reassessment_success_assumed": True, "all_fresh_uses_pay_receiving_costs": True,
                        "interval_is_not_a_statistical_confidence_interval": True},
        "population": {p.name: _round(w) for p, w in zip(recipients, normalized)},
        "planned_reuse": planned_reuse, "mean_delivery_saving_per_use": _round(average_gain),
        "beta_complete_delivery_cost": _round(cumulative_beta), "shared_complete_delivery_cost": _round(cumulative_shared),
        "upfront_cost": _round(initial), "failed_construction_subset": _round(plan.failed_construction_cost),
        "historical_cost": plan.historical_cost, "upkeep_cost": _round(upkeep),
        "revalidation_cost": _round(revalidation), "beta_reassessment_cost": _round(reassessment),
        "complete_lifecycle_cost": _round(costs.total), "project_net": rows[-1]["project_net"],
        "prospective_net": rows[-1]["prospective_net"], "lower_project_net": rows[-1]["lower_project_net"],
        "required_reuses_at_declared_lifetime": required_reuses(costs.total, average_gain, plan.uncertainty_margin_per_use),
        "first_positive_lifetime_weeks": positive[0] if positive else None,
        "durable_positive_lifetime_weeks_within_range": durable,
        "upfront_affordable_without_future_receipts": affordable,
        "additional_upfront_cash_required": _round(max(0, initial - plan.available_investment_cash)),
        "all_modeled_delivery_routes_feasible": all_routes_feasible,
        "candidate_is_recommended_now": bool(decision and decision["accepted"] and affordable and all_routes_feasible),
        "assessment": assessment, "decision": decision, "weekly": rows,
        "limitation": "Modeled cost and constraint comparisons, not realized receipts, measured invention, graph authorization or a financing schedule.",
    }


def run_recipient_ablation(scenario: Scenario | None = None) -> dict[str, Any]:
    """Declared deterministic examples and one-factor sweeps; no policy tuning."""
    scenario = scenario or Scenario()
    beta = default_beta()
    missing = RecipientSnapshot("competent-frontier-reconstructor", beta)
    experienced = RecipientSnapshot("ordinary-experienced", beta, (0.60, 0.60, 0.60))
    specialist = RecipientSnapshot("ordinary-specialist", beta, (0.33, 0.33, 0.33))
    equivalents = tuple(work.scale(0.10) for work in RECONSTRUCTION)
    duplicate = RecipientSnapshot("already-equivalent", beta, equivalents=equivalents)
    partial = RecipientSnapshot("partial-equivalent", beta, equivalents=(equivalents[0], None, None))
    bundle = CandidateBundle("compiled-coordination-bundle", beta.beta_id)
    mission = standard_mission(scenario)
    plan = standard_lifecycle(scenario, bundle)
    probes = [probe_recipient(scenario, p, mission, bundle) for p in (missing, experienced, specialist, partial, duplicate)]
    grid = {
        "overlap": (0.0, 0.25, 0.5, 0.75, 1.0),
        "uses_per_week": (0, 1, 2, 4, 8),
        "validation_overhead": (0.5, 1.0, 2.0, 4.0, 8.0),
        "frontier_improvement": (0.0, 0.18, 0.5, 1.0),
        "useful_lifetime_weeks": (4, 12, 26, 40, 64, 104),
    }
    sweeps = []
    keep = ("input_and_evidence_hash", "planned_reuse", "mean_delivery_saving_per_use", "complete_lifecycle_cost",
            "project_net", "lower_project_net", "required_reuses_at_declared_lifetime", "first_positive_lifetime_weeks",
            "durable_positive_lifetime_weeks_within_range", "upfront_affordable_without_future_receipts",
            "all_modeled_delivery_routes_feasible", "candidate_is_recommended_now", "baseline_path_id")
    for parameter, values in grid.items():
        for value in values:
            changed = plan
            weights = (0.75, 0.25)
            overhead = 1.0
            improvement = scenario.external_improvement
            if parameter == "overlap":
                weights = (1 - value, value)
            elif parameter in {"uses_per_week", "useful_lifetime_weeks"}:
                changed = replace(plan, **{parameter: value})
            elif parameter == "validation_overhead":
                overhead = value
            else:
                improvement = value
            result = assess_lifecycle(scenario, (missing, duplicate), mission, bundle, changed, weights=weights,
                                      validation_overhead=overhead, frontier_improvement=improvement)
            sweeps.append({"parameter": parameter, "value": value, **{k: result[k] for k in keep}})
    central = assess_lifecycle(scenario, (missing, duplicate), mission, bundle, plan, weights=(0.75, 0.25))
    return {"schema": SCHEMA, "protocol_id": PROTOCOL_ID, "evidence_kind": "deterministic-modeled-cost-comparison",
            "protocol": {"grid": grid, "scenario": asdict(scenario), "plan": asdict(plan),
                         "recipients": [asdict(p) for p in (missing, experienced, specialist, partial, duplicate)],
                         "candidate": asdict(bundle), "mission": asdict(mission)},
            "frozen_recipient_probes": probes, "lifecycle": central, "sensitivity": sweeps,
            "actual_activity": {"live_role_model_calls": 0, "customer_jobs": 0, "collections_usd": 0,
                                "live_ens_enforcement": False},
            "interpretation": "These are assumed workload/resource economics. Exact witness operation counts are never dollar-calibrated here."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/recipient_ablation.json"))
    args = parser.parse_args()
    result = run_recipient_ablation()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.out), "source_kind": result["evidence_kind"],
                      "probes": len(result["frozen_recipient_probes"]), "sensitivity_rows": len(result["sensitivity"]),
                      "modeled_project_net": result["lifecycle"]["project_net"]}))


if __name__ == "__main__":
    main()
