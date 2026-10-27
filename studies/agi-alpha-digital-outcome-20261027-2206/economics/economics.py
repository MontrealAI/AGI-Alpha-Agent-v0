# SPDX-License-Identifier: Apache-2.0
"""Conditional service economics; stdlib only. No values are observed sales or bills.
Run: python economics.py --output economics_results.json
Unknown model cost M is retained symbolically; illustrative M=100 is a sensitivity,
not an estimate. Historical whole-study development D is unknown and subtracted once.
"""

from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from typing import Mapping, TypedDict, cast


class Scenario(TypedDict):
    """One explicit demand, effort, value and cost hypothesis."""

    n: int
    price: float
    rate: float
    pre_hours: float
    support_hours: float
    failed_attempt_probability: float
    failed_attempt_hours: float
    infra: float
    acquisition_hours: float
    acquisition_cash: float
    refund_fraction: float
    maintenance_hours: float
    fixed_cash: float
    setup_hours: float
    reserve_extra_hours: float
    buyer_self_hours: float
    buyer_rate: float
    buyer_delay_value: float
    buyer_participation_hours: float


class CashEvent(TypedDict):
    """A dated modeled cash event and its cumulative balance."""

    day: int
    event: str
    cash: float
    cumulative_cash: float


class CashPlan(TypedDict):
    """Expected cash requirements with unobserved funding left unknown."""

    model_cost_sensitivity: float
    staged_earned_milestone: bool
    expected_peak_deficit: float
    explicit_reserve_one_additional_full_refund_and_correction: float
    required_unrestricted_funding: float
    available_unrestricted_funds: None
    financing_feasible: None
    restricted_deposit_available_for_operations: int
    final_cash_before_historical_development: float
    additional_split_payment_fees: float
    cohort_duration_days: int
    events: list[CashEvent]
    caveat: str


class ScenarioSummary(TypedDict):
    """Financial conclusions conditional on one scenario and model-cost value."""

    scenario: str
    assumptions: Scenario
    components: dict[str, float]
    contribution_affine: dict[str, float]
    operating_profit_affine: dict[str, float]
    full_project_return_affine: dict[str, float]
    illustrative_M_not_estimate: float
    operating_profit_at_illustrative_M: float
    full_project_return_before_unknown_D_at_illustrative_M: float
    maximum_M_for_positive_operating_profit: float | None
    maximum_D_for_nonnegative_full_project_return_at_illustrative_M: float
    operating_break_even_price_at_illustrative_M: float | None
    break_even_price_including_additional_setup_but_not_D: float | None
    break_even_customer_count_at_price_and_M: int | None
    actual_sales: int
    actual_collections: int
    actual_signed_commitments: int
    demand_status: str
    financing: CashPlan
    staged_financing: CashPlan


SCENARIOS: dict[str, Scenario] = {
    "favorable": dict(
        n=8,
        price=2500.0,
        rate=100.0,
        pre_hours=1.75,
        support_hours=0.25,
        failed_attempt_probability=0.10,
        failed_attempt_hours=0.75,
        infra=3.0,
        acquisition_hours=0.5,
        acquisition_cash=10.0,
        refund_fraction=0.01,
        maintenance_hours=3.0,
        fixed_cash=200.0,
        setup_hours=3.0,
        reserve_extra_hours=2.0,
        buyer_self_hours=24.0,
        buyer_rate=175.0,
        buyer_delay_value=2000.0,
        buyer_participation_hours=1.0,
    ),
    "central": dict(
        n=4,
        price=1500.0,
        rate=125.0,
        pre_hours=2.5,
        support_hours=0.5,
        failed_attempt_probability=0.20,
        failed_attempt_hours=1.5,
        infra=5.0,
        acquisition_hours=0.75,
        acquisition_cash=25.0,
        refund_fraction=0.02,
        maintenance_hours=4.0,
        fixed_cash=300.0,
        setup_hours=4.0,
        reserve_extra_hours=3.0,
        buyer_self_hours=8.0,
        buyer_rate=150.0,
        buyer_delay_value=600.0,
        buyer_participation_hours=1.0,
    ),
    "adverse": dict(
        n=0,
        price=750.0,
        rate=175.0,
        pre_hours=5.5,
        support_hours=1.5,
        failed_attempt_probability=0.40,
        failed_attempt_hours=3.0,
        infra=15.0,
        acquisition_hours=2.0,
        acquisition_cash=75.0,
        refund_fraction=0.08,
        maintenance_hours=6.0,
        fixed_cash=600.0,
        setup_hours=8.0,
        reserve_extra_hours=4.0,
        buyer_self_hours=2.0,
        buyer_rate=125.0,
        buyer_delay_value=0.0,
        buyer_participation_hours=2.0,
    ),
}
FEE_RATE = 0.03
FEE_FIXED = 0.30


def r(v: float) -> float:
    """Round a reported amount without changing its underlying calculation."""
    return round(v, 6)


def components(s: Scenario) -> dict[str, float]:
    """Compute each attributable unit and cohort cost exactly once."""
    failures = s["failed_attempt_probability"] / (1 - s["failed_attempt_probability"])
    failed_hours = failures * s["failed_attempt_hours"]
    pre = (s["pre_hours"] + failed_hours) * s["rate"] + s["infra"]
    post = s["support_hours"] * s["rate"]
    acquisition = s["acquisition_hours"] * s["rate"] + s["acquisition_cash"]
    fee = FEE_RATE * s["price"] + FEE_FIXED
    net_revenue = (1 - s["refund_fraction"]) * s["price"]
    margin = net_revenue - fee - pre - post - acquisition
    fixed = s["maintenance_hours"] * s["rate"] + s["fixed_cash"]
    setup = s["setup_hours"] * s["rate"]
    buyer_value = max(
        0,
        (s["buyer_self_hours"] - s["buyer_participation_hours"]) * s["buyer_rate"] + s["buyer_delay_value"],
    )
    return dict(
        expected_failed_attempts_per_accepted=failures,
        expected_failed_hours_per_accepted=failed_hours,
        preacceptance_delivery=pre,
        postacceptance_support=post,
        acquisition=acquisition,
        payment_cost=fee,
        net_revenue_after_expected_refunds=net_revenue,
        contribution_intercept=margin,
        fixed_operating=fixed,
        additional_commercial_setup=setup,
        buyer_value_ceiling=buyer_value,
        buyer_surplus_at_price=buyer_value - s["price"],
    )


def cash_schedule(s: Scenario, m: float, staged: bool = False) -> CashPlan:
    """Expected cash, plus an explicit reserve for one extra refund + correction.
    Cohort starts every20days. Net30 final collections occur35days after start.
    Favorable8jobs collects byday175 and maintains throughday195; not an annual forecast.
    Maintenance paid20days after last receipt. No restricted deposit is used.
    Staged:30% of expected net fee earned/paid after an independently accepted
    useful qualification milestone atday3; remaining70% atday35. Both payments
    incur their proportional fees plus one fixed fee each. This is a conditional contract.
    """
    c = components(s)
    events: list[tuple[int, str, float]] = [
        (
            0,
            "commercial_setup_and_fixed_business",
            -c["additional_commercial_setup"] - s["fixed_cash"],
        )
    ]
    for j in range(s["n"]):
        t = 20 * j
        events.append(
            (
                t,
                f"job{j + 1}_acquisition_and_preacceptance",
                -c["acquisition"] - c["preacceptance_delivery"] - m,
            )
        )
        events.append((t + 7, f"job{j + 1}_support", -c["postacceptance_support"]))
        if staged:
            events.append(
                (
                    t + 3,
                    f"job{j + 1}_earned_accepted_qualification",
                    0.3 * c["net_revenue_after_expected_refunds"] - 0.3 * FEE_RATE * s["price"] - FEE_FIXED,
                )
            )
            events.append(
                (
                    t + 35,
                    f"job{j + 1}_final_collection",
                    0.7 * c["net_revenue_after_expected_refunds"] - 0.7 * FEE_RATE * s["price"] - FEE_FIXED,
                )
            )
        else:
            events.append(
                (
                    t + 35,
                    f"job{j + 1}_final_collection",
                    c["net_revenue_after_expected_refunds"] - c["payment_cost"],
                )
            )
    end = 20 * (max(s["n"], 1) - 1) + 55
    events.append((end, "cohort_maintenance", -s["maintenance_hours"] * s["rate"]))
    events.sort(key=lambda z: z[0])
    balance: float = 0
    lowest: float = 0
    rows: list[CashEvent] = []
    for day, label, amount in events:
        balance += amount
        lowest = min(lowest, balance)
        rows.append(dict(day=day, event=label, cash=r(amount), cumulative_cash=r(balance)))
    reserve = (s["price"] + s["reserve_extra_hours"] * s["rate"]) if s["n"] else 0.0
    return dict(
        model_cost_sensitivity=m,
        staged_earned_milestone=staged,
        expected_peak_deficit=r(-lowest),
        explicit_reserve_one_additional_full_refund_and_correction=r(reserve),
        required_unrestricted_funding=r(-lowest + reserve),
        available_unrestricted_funds=None,
        financing_feasible=None,
        restricted_deposit_available_for_operations=0,
        final_cash_before_historical_development=r(balance),
        additional_split_payment_fees=r(s["n"] * FEE_FIXED if staged else 0.0),
        cohort_duration_days=end,
        events=rows,
        caveat="Expected cash profile plus stated reserve, not an insolvency guarantee. Multiple correlated refunds/nonpayment can exceed the reserve. Actual funds, buyer signatures and finance commitments unverified.",
    )


def summarize(name: str, s: Scenario, m: float) -> ScenarioSummary:
    """Retain unknown costs symbolically and evaluate a stated sensitivity."""
    c = components(s)
    n = s["n"]
    pi = n * c["contribution_intercept"] - c["fixed_operating"]
    full = pi - c["additional_commercial_setup"]
    denom = 1 - s["refund_fraction"] - FEE_RATE
    breakprice = (
        (
            c["preacceptance_delivery"]
            + c["postacceptance_support"]
            + c["acquisition"]
            + m
            + FEE_FIXED
            + c["fixed_operating"] / n
        )
        / denom
        if n
        else None
    )
    bfull = (
        (
            c["preacceptance_delivery"]
            + c["postacceptance_support"]
            + c["acquisition"]
            + m
            + FEE_FIXED
            + (c["fixed_operating"] + c["additional_commercial_setup"]) / n
        )
        / denom
        if n
        else None
    )
    unit = c["contribution_intercept"] - m
    breakn = math.ceil(c["fixed_operating"] / unit) if unit > 0 else None
    return dict(
        scenario=name,
        assumptions=s,
        components={k: r(v) for k, v in c.items()},
        contribution_affine=dict(intercept=r(c["contribution_intercept"]), model_cost_coefficient=-1),
        operating_profit_affine=dict(intercept=r(pi), model_cost_coefficient=-n),
        full_project_return_affine=dict(
            intercept=r(full),
            model_cost_coefficient=-n,
            historical_development_coefficient=-1,
        ),
        illustrative_M_not_estimate=m,
        operating_profit_at_illustrative_M=r(pi - n * m),
        full_project_return_before_unknown_D_at_illustrative_M=r(full - n * m),
        maximum_M_for_positive_operating_profit=r(pi / n) if n else None,
        maximum_D_for_nonnegative_full_project_return_at_illustrative_M=r(full - n * m),
        operating_break_even_price_at_illustrative_M=r(breakprice) if breakprice else None,
        break_even_price_including_additional_setup_but_not_D=r(bfull) if bfull else None,
        break_even_customer_count_at_price_and_M=breakn,
        actual_sales=0,
        actual_collections=0,
        actual_signed_commitments=0,
        demand_status="Assumed cohort, not a demand estimate or forecast"
        if n
        else "Value assumptions support zero purchases; no inconsistent sale forced",
        financing=cash_schedule(s, m),
        staged_financing=cash_schedule(s, m, True),
    )


def main() -> None:
    """Write deterministic scenario evidence for the requested model-cost value."""
    p = argparse.ArgumentParser()
    p.add_argument("--model-cost", type=float, default=100.0)
    p.add_argument("--output", default=str(Path(__file__).with_name("economics_results.json")))
    a = p.parse_args()
    if a.model_cost < 0 or not math.isfinite(a.model_cost):
        p.error("model cost must be finite and nonnegative")
    out: dict[str, object] = {
        "edition": "DIGITAL-20261027-R1",
        "currency": "USD nominal",
        "all_financial_amounts": "conditional estimates, not actual profit or quotations",
        "model_cost_M": "Unknown total attributable model/tool charge per accepted buyer engagement, including failed attempts; common across arms. Default100 is sensitivity only.",
        "historical_development_D": "Unknown complete whole-study development and publication resource cost; charge once for full-project return, never again per customer.",
        "cohort_horizon": "Favorable195days including maintenance for8buyers; central115days for4buyers. Counts are not annual sales forecasts.",
        "acceptance_link": "Source/CLI/tests/evidence accepted as one public mission. Buyer-specific qualification/integration and paid support are proposed commercial extensions, not accepted customer deliveries.",
        "scenario_results": [summarize(k, v, a.model_cost) for k, v in SCENARIOS.items()],
    }
    scenario_results = cast(list[ScenarioSummary], out["scenario_results"])
    s = SCENARIOS["central"]
    c = components(s)
    n = s["n"]
    u = c["contribution_intercept"] - a.model_cost
    isolated = n * (u - c["fixed_operating"] - c["additional_commercial_setup"])
    shared = n * u - c["fixed_operating"] - c["additional_commercial_setup"]
    out["conditional_matched_arrangements"] = {
        "scope": "Same competent delivered package and hypothetical central buyers; only ordinary reuse of cohort setup/maintenance changes. No technical productivity or price premium assigned.",
        "conventional_isolated": r(isolated),
        "expert_operation_alone_isolated": r(isolated),
        "conventional_shared": r(shared),
        "expert_plus_shared": r(shared),
        "positive_interaction": 0,
        "all_values_before_unknown_historical_D": "If one development asset is reused, subtract D once for both capable shared arrangements; no double bill.",
        "meaning": "Sharing ordinary fixed costs can help; it is not a transformation, novelty result or measured commercial experiment.",
    }
    out["sensitivity"] = [
        {
            "M": m,
            "central_operating_profit": r(s["n"] * (c["contribution_intercept"] - m) - c["fixed_operating"]),
            "central_full_project_before_D": r(
                s["n"] * (c["contribution_intercept"] - m) - c["fixed_operating"] - c["additional_commercial_setup"]
            ),
            "central_funding": cash_schedule(s, m)["required_unrestricted_funding"],
            "central_staged_funding": cash_schedule(s, m, True)["required_unrestricted_funding"],
        }
        for m in (0, 50, 100, 250, 500, 750)
    ]
    out["pricing_grid_central"] = [
        {
            "price": price,
            "conditional_buyer_surplus": r(c["buyer_value_ceiling"] - price),
            "operating_profit_at_M": r(
                s["n"]
                * (
                    (1 - s["refund_fraction"] - FEE_RATE) * price
                    - FEE_FIXED
                    - c["preacceptance_delivery"]
                    - c["postacceptance_support"]
                    - c["acquisition"]
                    - a.model_cost
                )
                - c["fixed_operating"]
            ),
            "demand_inferred": False,
        }
        for price in (800, 1000, 1500, 1800)
    ]
    out["buyer_participation_test"] = {
        "change": "Customer supplies one additional accepted setup hour, replacing one provider hour; final verification and all acceptance requirements retained",
        "provider_hour_cost": 125.0,
        "buyer_hour_cost": 150.0,
        "provider_max_cost_neutral_discount_before_fees": 125.0,
        "buyer_min_compensating_discount": 150.0,
        "pareto_improving_discount_exists_under_central_assumptions": False,
        "measured": False,
        "interpretation": "Discounts and unpaid buyer work do not create value automatically.",
    }
    out["failure_correlation_stress"] = {
        "one_extra_full_refund_reserved": True,
        "two_extra_central_refunds_above_expected": 3000.0,
        "extra_cash_beyond_one_refund_reserve": 1500.0,
        "no_probability_claim": True,
    }
    Path(a.output).write_text(json.dumps(out, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "output": a.output,
                "scenarios": [
                    {
                        k: cast(Mapping[str, object], r)[k]
                        for k in [
                            "scenario",
                            "operating_profit_at_illustrative_M",
                            "full_project_return_before_unknown_D_at_illustrative_M",
                            "maximum_M_for_positive_operating_profit",
                            "operating_break_even_price_at_illustrative_M",
                        ]
                    }
                    for r in scenario_results
                ],
                "central_funding": scenario_results[1]["financing"]["required_unrestricted_funding"],
                "central_staged_funding": scenario_results[1]["staged_financing"]["required_unrestricted_funding"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
