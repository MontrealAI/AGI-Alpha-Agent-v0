# SPDX-License-Identifier: Apache-2.0
"""Frozen fresh-confirmation generator; generation is authorized only after arm freeze."""

from __future__ import annotations

import copy
import math
import random
from typing import Any

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


def _base() -> dict[str, Any]:
    return {
        "schema": "reuse-gate-input.v1",
        "id": "fresh-base",
        "use": "industrial_nonpotable",
        "request": "screening",
        "currency": "EUR",
        "capex": [8000, 8000],
        "annual_savings": [5000, 5000],
        "cash_opex": {"operations": [1000, 1000]},
        "annual_depreciation": 800,
        "discount_rate": 0.08,
        "years": 5,
        "quality_unit": "mg/L",
        "product_quality": {"sodium": [80, 100], "chloride": [90, 120]},
        "buyer_limits": {"sodium": 150, "chloride": 200},
        "buyer_limit_kind": "process_specification",
        "evidence": {field: True for field in EVIDENCE_FIELDS},
    }


def generate_cases(seed: int = 2026102701) -> list[dict[str, Any]]:
    """Generate exactly 64 prespecified probes, without evaluating any arm."""
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []

    def add(
        name: str,
        category: str,
        expected: str,
        changes: dict[str, Any] | None = None,
        checks: dict[str, Any] | None = None,
        status: str = "clear_protocol_requirement",
    ) -> dict[str, Any]:
        case = _base()
        case.update(copy.deepcopy(changes or {}))
        case["id"] = name
        cases.append(
            {
                "id": name,
                "category": category,
                "protocol_status": status,
                "case": case,
                "expected_decision": expected,
                "checks": checks or {},
            }
        )
        return case

    yes, defer, stop, invalid, outside = "CONDITIONAL_NEXT_MILESTONE", "DEFER", "STOP", "INVALID_INPUT", "OUT_OF_SCOPE"
    add("valid_reference", "valid", yes)
    add(
        "zero_rate_exact_oracle",
        "valid_decimal_benchmark",
        yes,
        {"discount_rate": 0},
        {
            "decimal_expected": {
                "cash_margin": ["4000", "4000"],
                "accounting_margin": ["3200", "3200"],
                "npv": ["12000", "12000"],
                "simple_payback": ["2", "2"],
                "annuity": "5",
            }
        },
    )
    add("maximum_discount", "valid", yes, {"discount_rate": 1, "capex": [100, 100]})
    add("maximum_horizon", "valid", yes, {"years": 50})
    add("zero_capital", "valid", yes, {"capex": [0, 0]})
    add(
        "empty_cash_costs",
        "valid_boundary",
        yes,
        {"cash_opex": {}},
        {"interpretation": "Schema requires an object, not a nonempty object; completeness remains separate."},
    )
    add("zero_depreciation", "valid", yes, {"annual_depreciation": 0})
    add(
        "profitable_intervals",
        "valid",
        yes,
        {"capex": [5000, 9000], "annual_savings": [4800, 6500], "cash_opex": {"operations": [900, 1200]}},
    )
    add(
        "quality_equal_limits",
        "valid_boundary",
        yes,
        {"product_quality": {"sodium": [150, 150], "chloride": [200, 200]}},
    )
    add(
        "zero_cash_zero_capital",
        "valid_boundary",
        yes,
        {"capex": [0, 0], "annual_savings": [1000, 1000]},
        {"decimal_expected": {"cash_margin": ["0", "0"], "npv": ["0", "0"], "simple_payback": [None, None]}},
    )
    add(
        "published_cash_transferred_assumptions",
        "valid_transfer",
        yes,
        {
            "capex": [180000, 180000],
            "annual_savings": [82000, 82000],
            "cash_opex": {
                "energy": [7730, 7730],
                "chemicals": [3900, 3900],
                "labour": [11000, 11000],
                "discharge": [6000, 6000],
            },
            "annual_depreciation": 18000,
            "years": 10,
            "discount_rate": 0.12,
        },
        {"interpretation": "Only cash magnitudes transfer; all supplied evidence and buyer limits are synthetic."},
    )
    add(
        "irrelevant_metadata",
        "valid_metamorphic",
        yes,
        {"provenance": {"note": "Untrusted metadata grants no authority."}},
        {"same_numeric_as": "valid_reference"},
    )

    add("missing_process_limits", "unresolved_evidence", defer, {"buyer_limits": None})
    add("discharge_is_not_process", "unresolved_evidence", defer, {"buyer_limit_kind": "discharge_only"})
    add("unknown_specification_kind", "unresolved_evidence", defer, {"buyer_limit_kind": "unknown"})
    missing = add("missing_evidence_container", "unresolved_evidence", defer)
    del missing["evidence"]
    for field in EVIDENCE_FIELDS:
        evidence = {name: name != field for name in EVIDENCE_FIELDS}
        add(f"unresolved_{field}", "unresolved_evidence", defer, {"evidence": evidence}, {"must_name_gap": field})

    loss = {"capex": [1000, 1100], "annual_savings": [10, 20]}
    add("optimistic_economic_loss", "adverse", stop, loss)
    add("uncertain_economic_value", "adverse", defer, {"capex": [1000, 20000], "annual_savings": [1000, 5000]})
    add(
        "certain_quality_incompatibility",
        "adverse",
        stop,
        {"product_quality": {"sodium": [151, 160], "chloride": [90, 120]}},
    )
    add(
        "uncertain_quality_compatibility",
        "adverse",
        defer,
        {"product_quality": {"sodium": [149, 151], "chloride": [90, 120]}},
    )
    add("no_margin_with_capital", "adverse", stop, {"annual_savings": [1000, 1000]})
    add("negative_margin_without_capital", "adverse", stop, {"capex": [0, 0], "annual_savings": [999, 999]})
    add("loss_precedes_evidence_gaps", "adverse_ordering", stop, {**loss, "buyer_limits": None, "evidence": {}})
    evidence = {field: field != "buyer_spec_confirmed" for field in EVIDENCE_FIELDS}
    add(
        "incompatibility_precedes_confirmation_gap",
        "adverse_ordering",
        stop,
        {"product_quality": {"sodium": [151, 151], "chloride": [90, 120]}, "evidence": evidence},
        {"interpretation": "Incompatibility is conditional on the supplied process specification."},
    )
    add("potable_request", "out_of_scope", outside, {"use": "potable"})
    add("operation_request", "out_of_scope", outside, {"request": "operation"})
    add("mixing_request", "out_of_scope", outside, {"request": "mixing"})
    add("control_request", "out_of_scope", outside, {"request": "control"})

    add("boolean_capital", "malformed", invalid, {"capex": [False, 8000]})
    add("boolean_savings", "malformed", invalid, {"annual_savings": [True, 5000]})
    add("boolean_operating_cost", "malformed", invalid, {"cash_opex": {"operations": [False, 1000]}})
    add("boolean_depreciation", "malformed", invalid, {"annual_depreciation": False})
    add("boolean_discount", "malformed", invalid, {"discount_rate": False})
    add("boolean_horizon", "malformed", invalid, {"years": True})
    add("boolean_quality", "malformed", invalid, {"product_quality": {"sodium": [False, 100], "chloride": [90, 120]}})
    add("boolean_buyer_limit", "malformed", invalid, {"buyer_limits": {"sodium": True, "chloride": 200}})
    nonboolean_evidence: dict[str, Any] = {field: True for field in EVIDENCE_FIELDS}
    nonboolean_evidence["offtake"] = 1
    add("nonboolean_evidence", "malformed", invalid, {"evidence": nonboolean_evidence})
    add("nan_capital", "malformed_nonfinite", invalid, {"capex": [float("nan"), 8000]})
    add("infinite_savings", "malformed_nonfinite", invalid, {"annual_savings": [5000, float("inf")]})
    add("negative_cost_interval", "malformed", invalid, {"cash_opex": {"operations": [-1, 1000]}})
    add("unordered_capital", "malformed", invalid, {"capex": [8001, 8000]})
    add("zero_horizon", "malformed", invalid, {"years": 0})
    missing = add("missing_mandatory_costs", "malformed", invalid)
    del missing["cash_opex"]
    add("mismatched_analytes", "malformed", invalid, {"buyer_limits": {"sodium": 150}})

    add("near_zero_discount_18", "numerical_boundary", yes, {"discount_rate": 1e-18})
    add("near_zero_discount_12", "numerical_boundary", yes, {"discount_rate": 1e-12})
    add(
        "near_unit_discount",
        "numerical_boundary",
        yes,
        {"discount_rate": math.nextafter(1.0, 0.0), "capex": [100, 100]},
    )
    add(
        "tiny_negative_npv_sign",
        "numerical_boundary",
        stop,
        {
            "capex": [50, 50],
            "annual_savings": [2, 2],
            "cash_opex": {"operations": [1, 1]},
            "discount_rate": 1e-18,
            "years": 50,
        },
        {"strict_sign": "Discounted fifty unit receipts are strictly less than fifty for any positive discount."},
    )
    above = math.nextafter(150.0, math.inf)
    add(
        "quality_one_ulp_above_upper",
        "numerical_boundary",
        defer,
        {"product_quality": {"sodium": [150, above], "chloride": [90, 120]}},
    )
    add(
        "quality_one_ulp_above_lower",
        "numerical_boundary",
        stop,
        {"product_quality": {"sodium": [above, above], "chloride": [90, 120]}},
    )
    add(
        "decimal_literal_cancellation",
        "decimal_interpretation_diagnostic",
        yes,
        {
            "capex": [0, 0],
            "annual_savings": [0.3, 0.3],
            "cash_opex": {"first": [0.1, 0.1], "second": [0.2, 0.2]},
            "discount_rate": 0,
            "years": 1,
        },
        {
            "decimal_expected": {"cash_margin": ["0", "0"], "npv": ["0", "0"]},
            "diagnostic": "Decimal JSON-literal arithmetic versus binary64 representation; report separately.",
        },
        status="protocol_gap:input_number_representation_not_explicit",
    )
    multiplier = rng.choice([10, 100, 1000])
    add(
        "monetary_scale_metamorphic",
        "metamorphic",
        yes,
        {
            "capex": [8000 * multiplier, 8000 * multiplier],
            "annual_savings": [5000 * multiplier, 5000 * multiplier],
            "cash_opex": {"operations": [1000 * multiplier, 1000 * multiplier]},
            "annual_depreciation": 800 * multiplier,
        },
        {"scaled_numeric_from": "valid_reference", "factor": multiplier, "unchanged": ["simple_payback", "decision"]},
    )
    add(
        "depreciation_does_not_change_cash",
        "metamorphic",
        yes,
        {"annual_depreciation": 999999},
        {"same_as": "valid_reference", "fields": ["cash_margin", "npv", "simple_payback", "decision"]},
    )
    split = rng.randint(1, 999)
    add(
        "cost_partition_metamorphic",
        "metamorphic",
        yes,
        {"cash_opex": {"part_a": [split, split], "part_b": [1000 - split, 1000 - split]}},
        {"same_numeric_as": "valid_reference"},
    )
    add(
        "analyte_order_metamorphic",
        "metamorphic",
        yes,
        {
            "product_quality": {"chloride": [90, 120], "sodium": [80, 100]},
            "buyer_limits": {"chloride": 200, "sodium": 150},
        },
        {"same_numeric_as": "valid_reference"},
    )
    add(
        "uncertainty_widening_metamorphic",
        "metamorphic",
        defer,
        {"capex": [8000, 40000], "annual_savings": [1000, 5000]},
        {"must_not_improve_from": "valid_reference", "preserve_optimistic_bound": True},
    )
    if len(cases) != 64:
        raise RuntimeError(f"Frozen confirmation design requires 64 cases, received {len(cases)}")
    return cases


def encode_cases(value: Any) -> Any:
    """Encode invalid nonfinite probes in standard JSON without losing their types."""
    if isinstance(value, float) and not math.isfinite(value):
        return {"__test_nonfinite_float__": "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")}
    if isinstance(value, list):
        return [encode_cases(item) for item in value]
    if isinstance(value, dict):
        return {key: encode_cases(item) for key, item in value.items()}
    return value


def decode_cases(value: Any) -> Any:
    """Restore explicit invalid numeric probes after standard-JSON deserialization."""
    if isinstance(value, dict):
        if set(value) == {"__test_nonfinite_float__"}:
            return float(value["__test_nonfinite_float__"])
        return {key: decode_cases(item) for key, item in value.items()}
    if isinstance(value, list):
        return [decode_cases(item) for item in value]
    return value
