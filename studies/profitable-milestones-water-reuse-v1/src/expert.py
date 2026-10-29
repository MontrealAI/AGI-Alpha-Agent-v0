# SPDX-License-Identifier: Apache-2.0
"""Bounded, evidence-aware screening of a specified water-reuse milestone."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
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
ACTIONS = {
    "buyer_spec_confirmed": "Obtain the named buyer's process-water specification; discharge limits are insufficient.",
    "long_run_pilot": "Measure quality, flux, cleaning duty and downtime over representative feed variability.",
    "pretreatment": "Validate the proposed pretreatment and its changes to feed chemistry at the intended site.",
    "residuals_route": "Establish an authorized residuals route and its full unit cost.",
    "nonchemical_hazards": "Assess nonchemical hazards relevant to the intended use; the two-ion screen cannot do this.",
    "hydraulic_fit": "Verify actual source flow, buyer demand, storage, conveyance and hydraulic fit.",
    "offtake": "Confirm the buyer's intended quantity, reliability requirement and commercial participation.",
    "complete_costs": "Complete engineering, replacement, downtime, conveyance, permitting and funding cost inputs.",
}


def number(value: Any, label: str, positive: bool = False) -> float:
    """Reject silent coercion, including booleans and nonfinite input."""
    if type(value) not in (int, float):
        raise ValueError(f"{label}: a finite numeric value is required")
    try:
        result = float(value)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{label}: outside supported numeric range") from error
    if not math.isfinite(result) or result < 0 or (positive and result <= 0):
        raise ValueError(f"{label}: invalid nonnegative/positive bound")
    return result


def interval(value: Any, label: str) -> tuple[float, float]:
    """Read a closed concentration or currency interval."""
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{label}: a two-element interval is required")
    lo, hi = number(value[0], label), number(value[1], label)
    if lo > hi:
        raise ValueError(f"{label}: lower bound exceeds upper bound")
    return lo, hi


def validate(case: Any) -> dict[str, Any]:
    """Validate the original scope before deriving any claim."""
    if not isinstance(case, dict):
        raise ValueError("input must be an object")
    if case.get("schema") != "reuse-gate-input.v1":
        raise ValueError("unsupported schema")
    if not isinstance(case.get("id"), str) or not case["id"].strip():
        raise ValueError("id must be a nonempty string")
    if not isinstance(case.get("use"), str) or not isinstance(case.get("request"), str):
        raise ValueError("use and request must be strings")
    if case.get("currency") != "EUR" or case.get("quality_unit") != "mg/L":
        raise ValueError("currency must be EUR and concentration unit must be mg/L")
    capital = interval(case.get("capex"), "capex")
    savings = interval(case.get("annual_savings"), "annual_savings")
    costs = case.get("cash_opex")
    if not isinstance(costs, dict) or any(not isinstance(k, str) or not k for k in costs):
        raise ValueError("cash_opex must be an object of named cash costs")
    if any("depreciation" in k.casefold() or "amortization" in k.casefold() for k in costs):
        raise ValueError("noncash depreciation/amortization must not be charged again as cash opex")
    cost_intervals = [interval(v, f"cash_opex.{k}") for k, v in costs.items()]
    depreciation = number(case.get("annual_depreciation"), "annual_depreciation")
    rate = number(case.get("discount_rate"), "discount_rate")
    if rate > 1:
        raise ValueError("discount_rate exceeds one")
    years = case.get("years")
    if type(years) is not int or not 1 <= years <= 50:
        raise ValueError("years must be an integer from one through fifty")
    quality = case.get("product_quality")
    if not isinstance(quality, dict) or not quality or any(not isinstance(k, str) or not k for k in quality):
        raise ValueError("product_quality must name at least one analyte")
    products = {k: interval(v, f"product_quality.{k}") for k, v in quality.items()}
    if "buyer_limits" not in case:
        raise ValueError("buyer_limits must be explicitly provided, including null when unknown")
    limits = case["buyer_limits"]
    if limits is not None:
        if not isinstance(limits, dict) or set(limits) != set(products):
            raise ValueError("buyer_limits must name exactly the supplied product analytes")
        limits = {k: number(v, f"buyer_limits.{k}", positive=True) for k, v in limits.items()}
    if case.get("buyer_limit_kind") not in ("process_specification", "discharge_only", "unknown"):
        raise ValueError("invalid buyer_limit_kind")
    evidence = case.get("evidence", {})
    if not isinstance(evidence, dict) or any(type(v) is not bool for v in evidence.values()):
        raise ValueError("provided evidence flags must be booleans")
    return {
        "capital": capital,
        "savings": savings,
        "cost_intervals": cost_intervals,
        "depreciation": depreciation,
        "rate": rate,
        "years": years,
        "products": products,
        "limits": limits,
        "evidence": evidence,
    }


def refusal(decision: str, reason: str) -> dict[str, Any]:
    """Refuse without producing partial numerical reassurance."""
    return {
        "decision": decision,
        "reasons": [reason],
        "cash_margin": None,
        "accounting_margin": None,
        "npv": None,
        "simple_payback": None,
        "next_measurements": [],
        "evidence_level": "executed_screening_model_only",
        "operating_authorization": False,
    }


def evaluate(case: dict[str, Any]) -> dict[str, Any]:
    """Return a conditional screen, with separate cash, profit and evidence gates."""
    try:
        data = validate(case)
        if case["use"] != "industrial_nonpotable" or case["request"] != "screening":
            return refusal("OUT_OF_SCOPE", "This instrument supports non-potable industrial screening only.")
        r, years = data["rate"], data["years"]
        annuity = float(years) if r == 0 else -math.expm1(-years * math.log1p(r)) / r
        costs_lo = math.fsum(v[0] for v in data["cost_intervals"])
        costs_hi = math.fsum(v[1] for v in data["cost_intervals"])
        cash_lo = data["savings"][0] - costs_hi
        cash_hi = data["savings"][1] - costs_lo
        npv = [cash_lo * annuity - data["capital"][1], cash_hi * annuity - data["capital"][0]]
        accounting = [cash_lo - data["depreciation"], cash_hi - data["depreciation"]]
        if not all(math.isfinite(v) for v in [cash_lo, cash_hi, *npv, *accounting]):
            raise ValueError("derived quantity exceeds finite arithmetic range")
        payback = [
            data["capital"][0] / cash_hi if cash_hi > 0 else None,
            data["capital"][1] / cash_lo if cash_lo > 0 else None,
        ]
        if any(v is not None and not math.isfinite(v) for v in payback):
            raise ValueError("payback exceeds finite arithmetic range")
        missing = [k for k in EVIDENCE if not data["evidence"].get(k, False)]
        gaps = [f"unresolved:{k}" for k in missing]
        actual_spec = data["limits"] is not None and case["buyer_limit_kind"] == "process_specification"
        incompatible: list[str] = []
        if actual_spec:
            for analyte, bounds in data["products"].items():
                if bounds[0] > data["limits"][analyte]:
                    incompatible.append(analyte)
                if bounds[1] > data["limits"][analyte]:
                    gaps.append(f"uncertain_quality:{analyte}")
        else:
            gaps.append("missing_process_specification")
        if npv[0] < 0:
            gaps.append("negative_robust_npv")
        if npv[1] < 0:
            decision, reasons = "STOP", ["Even optimistic stated-cost NPV is negative."]
        elif incompatible:
            decision, reasons = (
                "STOP",
                [f"Minimum product concentration exceeds the process limit: {k}" for k in incompatible],
            )
        elif gaps:
            decision, reasons = "DEFER", gaps
        else:
            decision, reasons = (
                "CONDITIONAL_NEXT_MILESTONE",
                ["The bounded screen passes; regrant authority for the next milestone."],
            )
        next_measurements = [ACTIONS[k] for k in missing]
        if not actual_spec and ACTIONS["buyer_spec_confirmed"] not in next_measurements:
            next_measurements.insert(0, ACTIONS["buyer_spec_confirmed"])
        if npv[0] < 0:
            next_measurements.append(
                "Resolve the cost or savings interval only if the result can change the next decision."
            )
        if any(x.startswith("uncertain_quality:") for x in gaps):
            next_measurements.append("Measure the identified product analytes against the actual buyer specification.")
        return {
            "decision": decision,
            "reasons": reasons,
            "cash_margin": [cash_lo, cash_hi],
            "accounting_margin": accounting,
            "npv": npv,
            "simple_payback": payback,
            "next_measurements": next_measurements,
            "evidence_level": "executed_screening_model_only",
            "operating_authorization": False,
            "currency": "EUR",
            "annuity_factor": annuity,
            "annual_omitted_cost_headroom": cash_lo - data["capital"][1] / annuity,
            "unresolved_evidence": missing,
            "conditional_on_input_accuracy": True,
        }
    except (ValueError, OverflowError, TypeError) as error:
        return refusal("INVALID_INPUT", str(error))


def main() -> None:
    """Read one authorized local JSON record and print its deterministic screen."""
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python src/expert.py inputs/published_case.json")
    source = Path(sys.argv[1])
    if source.stat().st_size > 1_000_000:
        raise SystemExit("Input exceeds the one-megabyte local screening bound")
    print(json.dumps(evaluate(json.loads(source.read_text())), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
