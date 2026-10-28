# SPDX-License-Identifier: Apache-2.0
"""Bounded conventional cash-flow and process-specification screen."""

from __future__ import annotations

import math
from typing import Any


EVIDENCE = (
    "buyer_spec_confirmed",
    "long_run_pilot",
    "pretreatment",
    "residuals_route",
    "nonchemical_hazards",
    "hydraulic_fit",
    "offtake",
    "complete_costs",
)
MEASUREMENTS = {
    "buyer_spec_confirmed": "Obtain the buyer's signed process-water specification for every reported analyte.",
    "long_run_pilot": "Measure long-run performance, fouling, cleaning, uptime and repeatability in an authorized pilot.",
    "pretreatment": "Validate the proposed pretreatment against representative source-water conditions.",
    "residuals_route": "Confirm residuals quantities, treatment route, acceptance and associated costs.",
    "nonchemical_hazards": "Evaluate biological, particulate and other nonchemical hazards for the intended process.",
    "hydraulic_fit": "Confirm flow, storage, pressure, timing and system compatibility at the intended site.",
    "offtake": "Obtain a bounded offtake commitment specifying volume, availability, responsibility and payment.",
    "complete_costs": "Resolve omitted engineering, replacement, downtime, support and other incremental cash costs.",
}
EVIDENCE_LEVEL = (
    "Executed bounded software screen; field validation, customer acceptance and collections unestablished."
)


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}: a finite number is required; booleans are not numbers")
    try:
        result = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{name}: number is outside finite supported range") from exc
    if not math.isfinite(result) or result < 0 or (positive and result == 0):
        requirement = "positive" if positive else "nonnegative"
        raise ValueError(f"{name}: a finite {requirement} number is required")
    return result


def _interval(value: Any, name: str) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{name}: a two-element lower/upper list is required")
    lower, upper = (_number(value[0], name + "[0]"), _number(value[1], name + "[1]"))
    if lower > upper:
        raise ValueError(f"{name}: lower bound exceeds upper bound")
    return lower, upper


def _named_intervals(value: Any, name: str, *, nonempty: bool = False) -> dict[str, tuple[float, float]]:
    if not isinstance(value, dict) or (nonempty and not value):
        raise ValueError(f"{name}: a {'nonempty ' if nonempty else ''}named object is required")
    result = {}
    for key, interval in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{name}: all names must be nonempty strings")
        if name == "cash_opex" and "depreciation" in key.lower():
            raise ValueError("cash_opex: depreciation must be reported separately from cash costs")
        result[key] = _interval(interval, f"{name}.{key}")
    return result


def _empty(decision: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "decision": decision,
        "reasons": reasons,
        "cash_margin": None,
        "accounting_margin": None,
        "npv": None,
        "simple_payback": None,
        "next_measurements": [],
        "evidence_level": EVIDENCE_LEVEL,
    }


def evaluate(case: dict[str, Any]) -> dict[str, Any]:
    """Apply the frozen screening contract without granting operational authority."""
    try:
        if not isinstance(case, dict):
            raise ValueError("case: a JSON object is required")
        if case.get("schema") != "reuse-gate-input.v1":
            raise ValueError("schema: reuse-gate-input.v1 is required")
        if not isinstance(case.get("id"), str) or not case["id"].strip():
            raise ValueError("id: a nonempty string is required")
        for field in ("use", "request"):
            if not isinstance(case.get(field), str) or not case[field].strip():
                raise ValueError(f"{field}: a nonempty string is required")
        if case.get("currency") != "EUR":
            raise ValueError("currency: EUR is required; automatic currency conversion is unsupported")
        if case.get("quality_unit") != "mg/L":
            raise ValueError("quality_unit: mg/L is required")
        capex = _interval(case.get("capex"), "capex")
        savings = _interval(case.get("annual_savings"), "annual_savings")
        opex = _named_intervals(case.get("cash_opex"), "cash_opex")
        depreciation = _number(case.get("annual_depreciation"), "annual_depreciation")
        rate = _number(case.get("discount_rate"), "discount_rate")
        if rate > 1:
            raise ValueError("discount_rate: must be between zero and one")
        years = case.get("years")
        if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 50:
            raise ValueError("years: an integer from 1 through 50 is required")
        quality = _named_intervals(case.get("product_quality"), "product_quality", nonempty=True)
        if "buyer_limits" not in case:
            raise ValueError("buyer_limits: specify null when the process limits are unavailable")
        limits = case["buyer_limits"]
        if limits is not None:
            if not isinstance(limits, dict) or set(limits) != set(quality):
                raise ValueError("buyer_limits: must contain exactly the same analytes as product_quality")
            limits = {name: _number(value, f"buyer_limits.{name}", positive=True) for name, value in limits.items()}
        kind = case.get("buyer_limit_kind")
        if kind not in ("process_specification", "discharge_only", "unknown"):
            raise ValueError("buyer_limit_kind: process_specification, discharge_only or unknown is required")
        evidence = case.get("evidence", {})
        if not isinstance(evidence, dict):
            raise ValueError("evidence: a boolean-valued object is required; absent keys remain unresolved")
        if any(not isinstance(key, str) or type(value) is not bool for key, value in evidence.items()):
            raise ValueError("evidence: every provided value must be boolean; missing keys remain unresolved")
    except (TypeError, ValueError, OverflowError) as exc:
        return _empty("INVALID_INPUT", [str(exc)])

    if case["use"] != "industrial_nonpotable" or case["request"] != "screening":
        return _empty(
            "OUT_OF_SCOPE",
            ["Only industrial nonpotable screening is supported; no operation, mixing or control authorization."],
        )

    try:
        annuity = float(years) if rate == 0 else -math.expm1(-years * math.log1p(rate)) / rate
        cost_lower = math.fsum(interval[0] for interval in opex.values())
        cost_upper = math.fsum(interval[1] for interval in opex.values())
        margin = [savings[0] - cost_upper, savings[1] - cost_lower]
        accounting = [endpoint - depreciation for endpoint in margin]
        npv = [margin[0] * annuity - capex[1], margin[1] * annuity - capex[0]]
        payback = [capex[0] / margin[1] if margin[1] > 0 else None, capex[1] / margin[0] if margin[0] > 0 else None]
        if any(
            not math.isfinite(value)
            for value in [
                annuity,
                cost_lower,
                cost_upper,
                *margin,
                *accounting,
                *npv,
                *[x for x in payback if x is not None],
            ]
        ):
            raise ValueError("derived numeric results exceed the finite supported range")
    except (ValueError, OverflowError, ZeroDivisionError) as exc:
        return _empty("INVALID_INPUT", [f"calculation: {exc}"])

    result = {
        "decision": "CONDITIONAL_NEXT_MILESTONE",
        "reasons": [],
        "cash_margin": margin,
        "accounting_margin": accounting,
        "npv": npv,
        "simple_payback": payback,
        "next_measurements": [],
        "evidence_level": EVIDENCE_LEVEL,
    }
    process_spec = limits is not None and kind == "process_specification"
    stop_reasons = []
    if npv[1] < 0:
        stop_reasons.append(f"Optimistic NPV is negative ({npv[1]:.12g} EUR) under the stated cash-flow bounds.")
    if process_spec:
        for analyte, interval in quality.items():
            if interval[0] > limits[analyte]:
                stop_reasons.append(
                    f"{analyte}: lower product bound {interval[0]:.12g} mg/L exceeds specified process limit {limits[analyte]:.12g} mg/L."
                )
    if stop_reasons:
        result["decision"] = "STOP"
        result["reasons"] = stop_reasons
        result["next_measurements"] = [
            "Reopen only if new authorized evidence materially changes the incompatible quality or economic bounds."
        ]
        return result

    gaps, measurements = [], []
    if not process_spec:
        gaps.append(
            "A buyer process specification is missing; discharge limits do not establish process-water acceptance."
        )
        measurements.append(MEASUREMENTS["buyer_spec_confirmed"])
    for item in EVIDENCE:
        if evidence.get(item) is not True:
            gaps.append(f"Unresolved required evidence: {item}.")
            if MEASUREMENTS[item] not in measurements:
                measurements.append(MEASUREMENTS[item])
    if npv[0] < 0:
        gaps.append(f"Robust NPV is negative ({npv[0]:.12g} EUR); favorable assumptions are required for viability.")
        measurements.append(
            "Narrow uncertain capital, savings and recurring cash-cost bounds before committing to the next investment."
        )
    if process_spec:
        for analyte, interval in quality.items():
            if interval[1] > limits[analyte]:
                gaps.append(
                    f"{analyte}: upper product bound {interval[1]:.12g} mg/L exceeds specified process limit {limits[analyte]:.12g} mg/L."
                )
                measurements.append(
                    f"Measure representative {analyte} variability and validate a process-compatible product bound."
                )
    if gaps:
        result["decision"] = "DEFER"
        result["reasons"] = gaps
        result["next_measurements"] = measurements
    else:
        result["reasons"] = [
            "The specified bounded quality, evidence and cash-flow screen supports only the next conditional engineering milestone."
        ]
        result["next_measurements"] = [
            "Define the next milestone's acceptance, budget and authority separately; this screen does not authorize construction or operation."
        ]
    return result
