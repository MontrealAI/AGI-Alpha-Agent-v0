# SPDX-License-Identifier: Apache-2.0
"""Pre-assay feasibility for the unchanged research Alpha gate."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Callable


def _nonnegative(value: int | float | str, name: str) -> Fraction:
    if isinstance(value, bool):
        raise ValueError(name + " must be a finite nonnegative number")
    try:
        number = Fraction(str(value))
    except (ValueError, ZeroDivisionError) as exc:
        raise ValueError(name + " must be a finite nonnegative number") from exc
    if number < 0:
        raise ValueError(name + " must be nonnegative")
    return number


def research_gate_envelope(spec: dict[str, Any]) -> dict[str, Any]:
    """Reject an assay whose allowed observations cannot clear the current gate."""
    maximum = _nonnegative(spec["maximum_per_use_delta_cents"], "maximum_per_use_delta_cents")
    uses = _nonnegative(spec["forecast_eligible_uses"], "forecast_eligible_uses")
    costs = []
    for name in ("lifecycle_cost_cents", "evaluation_cost_cents"):
        value = spec[name]
        if type(value) is not int or value < 0:
            raise ValueError(name + " must be nonnegative integer cents")
        costs.append(value)
    clusters = spec["maximum_independent_clusters"]
    if type(clusters) is not int or not 0 <= clusters <= 24:
        raise ValueError("maximum_independent_clusters must be an integer from 0 through 24")
    upper = maximum * uses - sum(costs)
    floored = upper.numerator // upper.denominator
    reasons = []
    if clusters < 6:
        reasons.append("existing-gate-needs-six-independent-clusters")
    if maximum <= 0:
        reasons.append("nonpositive-upper-per-use-advantage")
    if floored < 1:
        reasons.append("maximum-lifetime-net-cannot-reach-one-cent")
    return {
        "schema": "operational-alpha-admission-envelope/v1",
        "reachable": not reasons,
        "reasons": reasons,
        "maximum_lifetime_net_cents": floored,
        "exact_unfloored_net": {"numerator": upper.numerator, "denominator": upper.denominator},
        "inputs": spec.copy(),
        "gate": "unchanged beyond-beta-alpha-policy-v1 / assessAlpha",
        "decision_information": "declared pre-assay bounds and prior-use forecast only",
        "grants_admission": False,
        "grants_execution_authority": False,
        "limitation": "Bounds must be justified; reachability alone establishes no useful skill or economic value.",
    }


def assess_if_reachable(spec: dict[str, Any], evaluator: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    """Buy the declared assessment only after its result could affect eligibility."""
    envelope = research_gate_envelope(spec)
    if not envelope["reachable"]:
        return {
            "envelope": envelope,
            "assessment_purchased": False,
            "assessment_cost_cents": 0,
            "assessment": None,
            "decision": "hold-no-assessment",
        }
    try:
        assessment = evaluator()
    except Exception as exc:
        assessment = {"verdict": "assessment-failed", "error_type": type(exc).__name__, "error": str(exc)}
    return {
        "envelope": envelope,
        "assessment_purchased": True,
        "assessment_cost_cents": spec["evaluation_cost_cents"],
        "assessment": assessment,
        "decision": "defer-to-unchanged-admission-and-authority-gates",
    }


def historical_hurdle_envelope(spec: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct the previous author edition's direct-value reachability theorem."""
    uses = _nonnegative(spec["uses"], "uses")
    transfer = _nonnegative(spec["transfer"], "transfer")
    if transfer > 1:
        raise ValueError("transfer must not exceed one")
    cap = _nonnegative(spec["cap"], "cap")
    fee = _nonnegative(spec["fee"], "fee")
    fixed = _nonnegative(spec["fixed"], "fixed")
    hurdle = _nonnegative(spec["hurdle"], "hurdle")
    if hurdle < 1:
        raise ValueError("hurdle must be at least one")
    gross, costs = uses * transfer * cap, uses * fee + fixed
    return {
        "reachable": gross >= hurdle * costs and gross > costs,
        "maximum_gross": float(gross),
        "remaining_costs": float(costs),
        "hurdle_costs": float(hurdle * costs),
        "strict_positive_net": gross > costs,
        "historical_diagnostic_only": True,
    }
