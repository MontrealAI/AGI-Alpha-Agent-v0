# SPDX-License-Identifier: Apache-2.0
"""Independent Decimal reference evaluator for the frozen reuse-gate protocol."""

from __future__ import annotations

import math
from decimal import Decimal, localcontext
from typing import Any, cast

EVIDENCE_FIELDS = (
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
    "buyer_spec_confirmed": "Obtain the customer's dated, use-specific product-water acceptance specification.",
    "long_run_pilot": "Measure sustained flux, cleaning frequency, uptime and permeate quality across operating states.",
    "pretreatment": "Validate pretreatment under representative source variability and chemical additions.",
    "residuals_route": "Confirm concentrate and cleaning-residual disposal routes, acceptance and full costs.",
    "nonchemical_hazards": "Assess microbial, aerosol, worker-contact and other nonchemical hazards for the intended use.",
    "hydraulic_fit": "Measure source availability, demand, storage, hydraulic capacity and downtime compatibility.",
    "offtake": "Confirm the receiving process's demand, operational acceptance and contractual offtake conditions.",
    "complete_costs": "Obtain complete engineering, installation, replacement, downtime, permitting and funding costs.",
}


def _number(value: Any) -> Decimal:
    if type(value) not in (int, float):
        raise ValueError("not a nonboolean JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("nonfinite number")
    result = Decimal(value) if isinstance(value, int) else Decimal(str(value))
    if not result.is_finite():
        raise ValueError("nonfinite number")
    return result


def _interval(value: Any) -> tuple[Decimal, Decimal]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError("expected two-element interval")
    lower, upper = (_number(part) for part in value)
    if lower < 0 or upper < lower:
        raise ValueError("negative or unordered interval")
    return lower, upper


def _empty(decision: str, reasons: list[str]) -> dict[str, Any]:
    return {
        "decision": decision,
        "reasons": reasons,
        "cash_margin": None,
        "accounting_margin": None,
        "npv": None,
        "simple_payback": None,
        "next_measurements": [],
        "evidence_level": "SOFTWARE_SCREEN_ONLY",
        "operational_authorization": False,
    }


def evaluate(case: Any) -> dict[str, Any]:
    """Evaluate supplied assumptions without authorizing physical operation."""
    if not isinstance(case, dict):
        return _empty("INVALID_INPUT", ["invalid:input_object"])
    errors: list[str] = []
    numbers: dict[str, Any] = {}
    for field, expected in (("schema", "reuse-gate-input.v1"), ("currency", "EUR"), ("quality_unit", "mg/L")):
        if case.get(field) != expected:
            errors.append(f"invalid:{field}")
    for field in ("id", "use", "request"):
        if not isinstance(case.get(field), str) or not case[field].strip():
            errors.append(f"invalid:{field}")
    for field in ("capex", "annual_savings"):
        try:
            numbers[field] = _interval(case.get(field))
        except (ValueError, TypeError, OverflowError):
            errors.append(f"invalid:{field}")
    for field in ("annual_depreciation", "discount_rate"):
        try:
            number = _number(case.get(field))
            if number < 0 or (field == "discount_rate" and number > 1):
                raise ValueError("outside permitted range")
            numbers[field] = number
        except (ValueError, TypeError, OverflowError):
            errors.append(f"invalid:{field}")
    years = case.get("years")
    if type(years) is not int or not 1 <= years <= 50:
        errors.append("invalid:years")
    costs = case.get("cash_opex")
    cash_costs: list[tuple[Decimal, Decimal]] = []
    if not isinstance(costs, dict):
        errors.append("invalid:cash_opex")
    else:
        for name, value in costs.items():
            if not isinstance(name, str) or not name.strip() or "depreciation" in name.lower():
                errors.append("invalid:cash_opex_name_or_noncash_depreciation")
            try:
                cash_costs.append(_interval(value))
            except (ValueError, TypeError, OverflowError):
                errors.append(f"invalid:cash_opex:{name}")
    quality = case.get("product_quality")
    quality_bounds: dict[str, tuple[Decimal, Decimal]] = {}
    if not isinstance(quality, dict) or not quality:
        errors.append("invalid:product_quality")
    else:
        for name, value in quality.items():
            if not isinstance(name, str) or not name.strip():
                errors.append("invalid:product_quality_analyte")
            try:
                quality_bounds[name] = _interval(value)
            except (ValueError, TypeError, OverflowError):
                errors.append(f"invalid:product_quality:{name}")
    limits = case.get("buyer_limits")
    buyer_limits: dict[str, Decimal] = {}
    if limits is not None:
        if not isinstance(limits, dict):
            errors.append("invalid:buyer_limits")
        else:
            if not isinstance(quality, dict) or set(limits) != set(quality):
                errors.append("invalid:buyer_limit_analytes")
            for name, value in limits.items():
                try:
                    number = _number(value)
                    if number <= 0:
                        raise ValueError("nonpositive buyer limit")
                    buyer_limits[name] = number
                except (ValueError, TypeError, OverflowError):
                    errors.append(f"invalid:buyer_limit:{name}")
    kind = case.get("buyer_limit_kind")
    if kind not in ("process_specification", "discharge_only", "unknown"):
        errors.append("invalid:buyer_limit_kind")
    evidence = case.get("evidence", {})
    if not isinstance(evidence, dict):
        errors.append("invalid:evidence_object")
        evidence = {}
    else:
        for name, value in evidence.items():
            if type(value) is not bool:
                errors.append(f"invalid:evidence:{name}")
    if errors:
        return _empty("INVALID_INPUT", errors)
    if case["use"] != "industrial_nonpotable" or case["request"] != "screening":
        return _empty("OUT_OF_SCOPE", ["only_nonpotable_industrial_screening_supported"])
    values = list(numbers["capex"]) + list(numbers["annual_savings"])
    values += [numbers["annual_depreciation"], numbers["discount_rate"]]
    values += [value for pair in cash_costs for value in pair]
    significant = [value for value in values if value != 0]
    precision = 96
    if significant:
        precision = max(
            precision,
            max(value.adjusted() for value in significant)
            - min(value.as_tuple().exponent for value in significant)
            + 96,
        )
    with localcontext() as context:
        context.prec = precision
        zero = Decimal(0)
        annual_low = numbers["annual_savings"][0] - sum((part[1] for part in cash_costs), zero)
        annual_high = numbers["annual_savings"][1] - sum((part[0] for part in cash_costs), zero)
        discount = Decimal(1) + numbers["discount_rate"]
        factors = [Decimal(1) / (discount**year) for year in range(1, cast(int, years) + 1)]
        annuity = sum(factors, zero)
        npv_low = sum((annual_low * factor for factor in factors), zero) - numbers["capex"][1]
        npv_high = sum((annual_high * factor for factor in factors), zero) - numbers["capex"][0]
        payback_low = numbers["capex"][0] / annual_high if annual_high > 0 else None
        payback_high = numbers["capex"][1] / annual_low if annual_low > 0 else None
        accounting = (annual_low - numbers["annual_depreciation"], annual_high - numbers["annual_depreciation"])
        output_values = [annual_low, annual_high, npv_low, npv_high, annuity, *accounting]
        output_values += [value for value in (payback_low, payback_high) if value is not None]
        if any(not math.isfinite(float(value)) for value in output_values):
            result = _empty("INVALID_INPUT", ["derived_numeric_representation_overflow"])
            result["diagnostics"] = ["protocol_gap:finite_inputs_have_no_explicit_derived_output_range"]
            return result
        result = {
            "decision": "CONDITIONAL_NEXT_MILESTONE",
            "reasons": [],
            "cash_margin": [float(annual_low), float(annual_high)],
            "accounting_margin": [float(accounting[0]), float(accounting[1])],
            "npv": [float(npv_low), float(npv_high)],
            "simple_payback": [None if value is None else float(value) for value in (payback_low, payback_high)],
            "annuity": float(annuity),
            "next_measurements": [],
            "evidence_level": "SOFTWARE_SCREEN_ONLY",
            "operational_authorization": False,
            "decimal_oracle": {
                "cash_margin": [str(annual_low), str(annual_high)],
                "accounting_margin": [str(accounting[0]), str(accounting[1])],
                "npv": [str(npv_low), str(npv_high)],
                "annuity": str(annuity),
                "simple_payback": [None if value is None else str(value) for value in (payback_low, payback_high)],
                "precision": precision,
            },
        }
        process_spec = bool(buyer_limits) and kind == "process_specification"
        stop_reasons = []
        if npv_high < 0:
            stop_reasons.append("optimistic_npv_negative")
        if process_spec:
            stop_reasons.extend(
                f"quality_incompatible:{name}"
                for name, bounds in quality_bounds.items()
                if bounds[0] > buyer_limits[name]
            )
        if stop_reasons:
            result["decision"] = "STOP"
            result["reasons"] = stop_reasons
            return result
        gaps = []
        measurements = []
        if limits is None:
            gaps.append("buyer_limits_missing")
            measurements.append(MEASUREMENTS["buyer_spec_confirmed"])
        if kind != "process_specification":
            gaps.append(f"buyer_limit_kind:{kind}")
            measurements.append(MEASUREMENTS["buyer_spec_confirmed"])
        for name in EVIDENCE_FIELDS:
            if evidence.get(name) is not True:
                gaps.append(f"unresolved:{name}")
                measurements.append(MEASUREMENTS[name])
        if npv_low < 0:
            gaps.append("robust_npv_negative")
            measurements.append(
                "Resolve the cost, savings, availability or capital uncertainty that changes the decision."
            )
        if process_spec:
            for name, bounds in quality_bounds.items():
                if bounds[1] > buyer_limits[name]:
                    gaps.append(f"quality_uncertain:{name}")
                    measurements.append(f"Measure representative product {name} against the customer's maximum.")
        if gaps:
            result["decision"] = "DEFER"
            result["reasons"] = gaps
            result["next_measurements"] = list(dict.fromkeys(measurements))
        else:
            result["reasons"] = ["all_supplied_bounded_screening_conditions_met;no_operational_permission"]
        return result
