# SPDX-License-Identifier: Apache-2.0
import argparse, copy, csv, hashlib, json, math, random
from pathlib import Path

HERE = Path(__file__).resolve().parent


def expand_scenarios(data):
    result = {}
    for scenario in data["scenarios"]:
        row = (
            copy.deepcopy(result[scenario["inherits"]])
            if "inherits" in scenario
            else {}
        )
        row.update(scenario)
        row.pop("inherits", None)
        result[row["name"]] = row
    return result


def inputs(data, scenario):
    costs = data["costs"] | {k: v for k, v in scenario.items() if k in data["costs"]}
    return costs


def job_cost(data, scenario, outcome):
    row, rates, costs = (
        data["job_outcomes"][outcome],
        data["api"],
        inputs(data, scenario),
    )
    api = (
        scenario["baseline_input_tokens"] * rates["uncached_input_per_million"]
        + scenario["baseline_output_tokens"] * rates["output_per_million"]
    ) / 1e6
    multiplier = row["api_multiplier"]
    return {
        "api": api * multiplier,
        "tools": costs["baseline_tool_cost_per_job"] * multiplier,
        "artifact": costs["artifact_retention_per_job"],
        "support": row["support_hours"] * data["labor"]["usd_per_hour"],
        "exception": row["exception_hours"] * data["labor"]["usd_per_hour"],
    }


def expectations(data, scenario):
    probs, costs, wage = (
        scenario["outcome_probabilities"],
        inputs(data, scenario),
        data["labor"]["usd_per_hour"],
    )
    assert abs(sum(probs.values()) - 1) < 1e-10 and min(probs.values()) >= 0
    q = sum(probs[o] * data["job_outcomes"][o]["retained_acceptance"] for o in probs)
    initial = sum(probs[o] * data["job_outcomes"][o]["initial_payment"] for o in probs)
    refund = sum(probs[o] * data["job_outcomes"][o]["refund"] for o in probs)
    expense = {
        key: sum(probs[o] * job_cost(data, scenario, o)[key] for o in probs)
        for key in job_cost(data, scenario, "clean")
    }
    human_hours = sum(
        probs[o]
        * (
            data["job_outcomes"][o]["support_hours"]
            + data["job_outcomes"][o]["exception_hours"]
        )
        for o in probs
    )
    multiplier = sum(
        probs[o] * data["job_outcomes"][o]["api_multiplier"] for o in probs
    )
    sales_hours = (
        scenario["sales_hours_per_lead"] / scenario["purchase_conversion"]
        if scenario["purchase_conversion"]
        else 0
    )
    acquisition = (
        scenario["qualified_lead_cost"] / scenario["purchase_conversion"]
        if scenario["purchase_conversion"]
        else 0
    )
    failed_campaign = (
        scenario["qualified_inquiries_per_month"] * scenario["qualified_lead_cost"]
        if not scenario["purchase_conversion"]
        else 0
    )
    failed_sales_hours = (
        scenario["qualified_inquiries_per_month"] * scenario["sales_hours_per_lead"]
        if not scenario["purchase_conversion"]
        else 0
    )
    assert scenario["qualified_lead_cost"] >= scenario["sales_hours_per_lead"] * wage
    fixed = (
        wage
        * (
            costs["maintenance_hours_per_month"]
            + costs["administration_hours_per_month"]
        )
        + costs["hosting_software_per_month"]
        + costs["business_services_per_month"]
    )
    development = costs["development_hours"] * wage + costs["development_tooling"]
    capacity_human = max(
        0,
        data["capacity"]["available_human_hours_per_month"]
        - costs["maintenance_hours_per_month"]
        - costs["administration_hours_per_month"]
        - failed_sales_hours,
    ) / (human_hours + sales_hours)
    capacity_agent = (
        data["capacity"]["available_agent_hours_per_month"]
        * data["capacity"]["concurrent_agents"]
        / (data["capacity"]["baseline_agent_hours_per_job"] * multiplier)
    )
    capacity = min(capacity_human, capacity_agent)
    demand = scenario["qualified_inquiries_per_month"] * scenario["purchase_conversion"]
    attempts = min(demand, capacity)
    return {
        "q": q,
        "initial": initial,
        "refund": refund,
        "expense": expense,
        "delivery": sum(expense.values()),
        "human_hours": human_hours,
        "sales_hours": sales_hours,
        "acquisition": acquisition,
        "fixed": fixed,
        "development": development,
        "capacity": capacity,
        "capacity_human": capacity_human,
        "capacity_agent": capacity_agent,
        "demand": demand,
        "attempts": attempts,
        "failed_campaign": failed_campaign,
        "failed_sales_hours": failed_sales_hours,
    }


def accounting(data, scenario):
    e, c, price = (
        expectations(data, scenario),
        inputs(data, scenario),
        scenario["price"],
    )
    months = data["timing"]["selling_months"]
    n = e["attempts"] * months
    collected_after_warranty = (
        data["timing"]["collection_delay_days"]
        > data["timing"]["warranty_days_after_delivery"]
    )
    paid_rate = e["q"] if collected_after_warranty else e["initial"]
    refund_rate = 0 if collected_after_warranty else e["refund"]
    accepted, paid, refunded = n * e["q"], n * paid_rate, n * refund_rate
    gross_collections = paid * price
    refunds = refunded * price
    revenue = accepted * price
    fees = paid * (price * c["payment_fee_fraction"] + c["payment_fee_fixed"])
    delivery = n * e["delivery"]
    acquisition = n * e["acquisition"] + e["failed_campaign"] * months
    operating = revenue - delivery - fees - acquisition - e["fixed"] * months
    margin_per_attempt = (
        e["q"] * price
        - paid_rate * (price * c["payment_fee_fraction"] + c["payment_fee_fixed"])
        - e["delivery"]
        - e["acquisition"]
    )
    price_denominator = e["q"] - paid_rate * c["payment_fee_fraction"]
    base = e["delivery"] + e["acquisition"] + paid_rate * c["payment_fee_fixed"]
    be_price = (
        (base + e["fixed"] / e["attempts"]) / price_denominator
        if e["attempts"] and price_denominator > 0
        else None
    )
    be_full_price = (
        (base + (e["fixed"] + e["development"] / months) / e["attempts"])
        / price_denominator
        if e["attempts"] and price_denominator > 0
        else None
    )
    be_orders = (
        e["fixed"] / margin_per_attempt
        if margin_per_attempt > 0 and scenario["purchase_conversion"]
        else None
    )
    be_full_orders = (
        (e["fixed"] + e["development"] / months) / margin_per_attempt
        if margin_per_attempt > 0 and scenario["purchase_conversion"]
        else None
    )
    max_cac = (
        e["q"] * price
        - paid_rate * (price * c["payment_fee_fraction"] + c["payment_fee_fixed"])
        - e["delivery"]
        - e["fixed"] / e["attempts"]
        if e["attempts"]
        else None
    )
    per_attempt_before_acquisition = margin_per_attempt + e["acquisition"]
    inquiries = scenario["qualified_inquiries_per_month"]
    fixed_campaign_cost = inquiries * scenario["qualified_lead_cost"]
    conversion_be = (
        (fixed_campaign_cost + e["fixed"])
        / (inquiries * per_attempt_before_acquisition)
        if inquiries and per_attempt_before_acquisition > 0
        else None
    )
    project_conversion_be = (
        (fixed_campaign_cost + e["fixed"] + e["development"] / months)
        / (inquiries * per_attempt_before_acquisition)
        if inquiries and per_attempt_before_acquisition > 0
        else None
    )
    result = {
        "scenario": scenario["name"],
        "price": price,
        "attempted_orders_monthly": e["attempts"],
        "attempted_orders_annual": n,
        "final_acceptance_rate": e["q"],
        "initial_payment_rate": paid_rate,
        "late_refund_rate": refund_rate,
        "final_accepted_orders_annual": accepted,
        "final_rejected_orders_annual": n - accepted,
        "late_refunded_orders_annual": refunded,
        "modeled_gross_collections": gross_collections,
        "modeled_refunds": refunds,
        "accepted_revenue": revenue,
        "direct_delivery_cost": delivery,
        "payment_fees": fees,
        "direct_contribution": revenue - delivery - fees,
        "acquisition_cost": acquisition,
        "fixed_operating_cost": e["fixed"] * months,
        "operating_profit": operating,
        "additional_development": e["development"],
        "full_project_return": operating - e["development"],
        "delivery_cost_per_attempt": e["delivery"],
        "acquisition_cost_per_attempt": acquisition / n if n else None,
        "acquisition_cost_per_final_accepted_order": acquisition / accepted
        if accepted
        else None,
        "complete_operating_cost_per_final_accepted_order": (
            delivery + fees + acquisition + e["fixed"] * months
        )
        / accepted
        if accepted
        else None,
        "complete_project_cost_per_final_accepted_order": (
            delivery + fees + acquisition + e["fixed"] * months + e["development"]
        )
        / accepted
        if accepted
        else None,
        "operating_break_even_price": be_price,
        "project_break_even_price": be_full_price,
        "operating_break_even_attempts_monthly": be_orders,
        "project_break_even_attempts_monthly": be_full_orders,
        "operating_break_even_accepted_monthly": be_orders * e["q"]
        if be_orders is not None
        else None,
        "project_break_even_accepted_monthly": be_full_orders * e["q"]
        if be_full_orders is not None
        else None,
        "maximum_cac_per_attempt_at_operating_break_even": max_cac,
        "fixed_inquiry_campaign_operating_break_even_conversion": conversion_be,
        "fixed_inquiry_campaign_project_break_even_conversion": project_conversion_be,
        "available_capacity_attempts_monthly": e["capacity"],
        "human_capacity_attempts_monthly": e["capacity_human"],
        "agent_capacity_attempts_monthly": e["capacity_agent"],
        "human_hours_monthly": e["attempts"] * (e["human_hours"] + e["sales_hours"])
        + e["failed_sales_hours"]
        + c["maintenance_hours_per_month"]
        + c["administration_hours_per_month"],
        "interpretation": scenario["interpretation"],
    }
    assert abs(gross_collections - refunds - revenue) < 1e-7
    assert (
        abs(
            result["direct_contribution"]
            - acquisition
            - result["fixed_operating_cost"]
            - operating
        )
        < 1e-7
    )
    return result


def cash_ledger(data, scenario, mode="acceptance", monthly_scenarios=None):
    e, c, t, price = (
        expectations(data, scenario),
        inputs(data, scenario),
        data["timing"],
        scenario["price"],
    )
    events = []

    def event(day, kind, cash, reserved=0, month=None):
        events.append(
            {
                "day": day,
                "kind": kind,
                "cash_delta": cash,
                "reserve_delta": reserved,
                "selling_month": month,
            }
        )

    event(0, "additional_development", -e["development"])
    for month in range(t["selling_months"]):
        if monthly_scenarios is not None:
            current = monthly_scenarios[month]
            e, c, price = (
                expectations(data, current),
                inputs(data, current),
                current["price"],
            )
        day, n = month * t["days_per_month"], e["attempts"]
        event(day, "fixed_operations", -e["fixed"], month=month + 1)
        event(
            day,
            "acquisition",
            -n * e["acquisition"] - e["failed_campaign"],
            month=month + 1,
        )
        upfront = (
            e["expense"]["api"]
            + e["expense"]["tools"]
            + e["expense"]["artifact"]
            + e["expense"]["exception"]
        )
        event(day, "construction_tools_exceptions", -n * upfront, month=month + 1)
        close = day + t["delivery_calendar_days"] + t["warranty_days_after_delivery"]
        collect = day + t["delivery_calendar_days"] + t["collection_delay_days"]
        event(close, "warranty_support", -n * e["expense"]["support"], month=month + 1)
        if mode == "acceptance":
            if collect <= close:
                gross, fee = (
                    n * e["initial"] * price,
                    n
                    * e["initial"]
                    * (price * c["payment_fee_fraction"] + c["payment_fee_fixed"]),
                )
                event(collect, "initial_collection", gross, gross, month + 1)
                event(collect, "payment_fees", -fee, month=month + 1)
                event(
                    close,
                    "warranty_refunds",
                    -n * e["refund"] * price,
                    -n * e["refund"] * price,
                    month + 1,
                )
                event(
                    close, "warranty_reserve_release", 0, -n * e["q"] * price, month + 1
                )
            else:
                event(close, "cancel_uncollected_failed_invoices", 0, month=month + 1)
                event(
                    collect,
                    "final_accepted_late_collection",
                    n * e["q"] * price,
                    month=month + 1,
                )
                event(
                    collect,
                    "payment_fees",
                    -n
                    * e["q"]
                    * (price * c["payment_fee_fraction"] + c["payment_fee_fixed"]),
                    month=month + 1,
                )
        elif mode == "restricted_deposit":
            deposit = n * price / 2
            event(day, "refundable_deposit", deposit, deposit, month + 1)
            event(
                day,
                "deposit_processing_fees",
                -n * (price * c["payment_fee_fraction"] / 2 + c["payment_fee_fixed"]),
                month=month + 1,
            )
            event(
                close,
                "deposit_refund",
                -n * (1 - e["q"]) * price / 2,
                -n * (1 - e["q"]) * price / 2,
                month + 1,
            )
            event(
                close, "earned_deposit_release", 0, -n * e["q"] * price / 2, month + 1
            )
            balance = n * e["q"] * price / 2
            event(
                close + t["collection_delay_days"],
                "accepted_balance_collection",
                balance,
                month=month + 1,
            )
            event(
                close + t["collection_delay_days"],
                "accepted_balance_processing_fees",
                -n
                * e["q"]
                * (price * c["payment_fee_fraction"] / 2 + c["payment_fee_fixed"]),
                month=month + 1,
            )
        elif mode == "after_warranty":
            gross = n * e["q"] * price
            event(
                close + t["collection_delay_days"],
                "final_accepted_collection",
                gross,
                month=month + 1,
            )
            event(
                close + t["collection_delay_days"],
                "payment_fees",
                -n
                * e["q"]
                * (price * c["payment_fee_fraction"] + c["payment_fee_fixed"]),
                month=month + 1,
            )
        else:
            raise ValueError(mode)
    events.sort(key=lambda x: x["day"])
    cash = reserve = min_available = peak_reserve = 0
    for row in events:
        cash += row["cash_delta"]
        reserve += row["reserve_delta"]
        assert reserve > -1e-7
        available = cash - reserve
        min_available, peak_reserve = (
            min(min_available, available),
            max(peak_reserve, reserve),
        )
        row.update(
            {
                "cumulative_cash_before_financing": cash,
                "restricted_customer_funds": reserve,
                "unrestricted_cash_before_financing": available,
            }
        )
    assert abs(reserve) < 1e-7
    minimum_seed = -min_available
    for row in events:
        row["unrestricted_cash_with_minimum_seed"] = (
            row["unrestricted_cash_before_financing"] + minimum_seed
        )
        assert row["unrestricted_cash_with_minimum_seed"] > -1e-7
    if mode == "acceptance":
        expected = (
            accounting(data, scenario)["full_project_return"]
            if monthly_scenarios is None
            else sum(
                accounting(data, s)["operating_profit"] / t["selling_months"]
                for s in monthly_scenarios
            )
            - expectations(data, scenario)["development"]
        )
        assert abs(cash - expected) < 1e-6
    summary = {
        "mode": mode,
        "minimum_opening_cash": minimum_seed,
        "peak_restricted_customer_funds": peak_reserve,
        "final_net_cash_before_financing": cash,
        "remaining_customer_obligations": reserve,
        "last_event_day": max(r["day"] for r in events),
        "basis": "Expected-case cash schedule, not a stochastic stress quantile or measured liquidity requirement.",
    }
    return summary, events


def with_acceptance(scenario, q):
    s = copy.deepcopy(scenario)
    p = s["outcome_probabilities"]
    split = p["corrected"] / (p["clean"] + p["corrected"])
    refund = min(p["refunded"], 1 - q)
    s["outcome_probabilities"] = {
        "clean": q * (1 - split),
        "corrected": q * split,
        "rejected": 1 - q - refund,
        "refunded": refund,
    }
    return s


def threshold_grid(data, central):
    rows = []
    for price in range(500, 1501, 100):
        for attempts in range(3, 16):
            for q in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]:
                s = with_acceptance(central, q)
                s.update(
                    {
                        "price": price,
                        "qualified_inquiries_per_month": attempts
                        / s["purchase_conversion"],
                    }
                )
                a = accounting(data, s)
                rows.append(
                    {
                        k: a[k]
                        for k in [
                            "price",
                            "attempted_orders_monthly",
                            "final_acceptance_rate",
                            "accepted_revenue",
                            "operating_profit",
                            "full_project_return",
                            "delivery_cost_per_attempt",
                            "maximum_cac_per_attempt_at_operating_break_even",
                        ]
                    }
                )
    return rows


def root_acceptance(data, scenario, full_project=False):
    key = "full_project_return" if full_project else "operating_profit"
    if accounting(data, with_acceptance(scenario, 1))[key] < 0:
        return None
    low, high = 0.000001, 1
    for _ in range(60):
        mid = (low + high) / 2
        if accounting(data, with_acceptance(scenario, mid))[key] >= 0:
            high = mid
        else:
            low = mid
    return high


def sensitivities(data, central):
    result = []
    for parameter, values in [
        ("price", [500, 600, 750, 900, 1200, 1500]),
        ("qualified_lead_cost", [10, 25, 50, 75, 100]),
        ("development_hours", [20, 40, 80, 160]),
    ]:
        for value in values:
            s = copy.deepcopy(central)
            s[parameter] = value
            if (
                parameter == "qualified_lead_cost"
                and value < s["sales_hours_per_lead"] * data["labor"]["usd_per_hour"]
            ):
                continue
            a = accounting(data, s)
            result.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "operating_profit": a["operating_profit"],
                    "full_project_return": a["full_project_return"],
                }
            )
    for fee in [0.029, 0.044, 0.054]:
        d = copy.deepcopy(data)
        d["costs"]["payment_fee_fraction"] = fee
        a = accounting(d, central)
        result.append(
            {
                "parameter": "payment_fee_fraction",
                "value": fee,
                "operating_profit": a["operating_profit"],
                "full_project_return": a["full_project_return"],
            }
        )
    for factor in [0.25, 1, 3.75, 10]:
        s = copy.deepcopy(central)
        s["baseline_input_tokens"] *= factor
        s["baseline_output_tokens"] *= factor
        a = accounting(data, s)
        result.append(
            {
                "parameter": "api_budget_multiplier",
                "value": factor,
                "operating_profit": a["operating_profit"],
                "full_project_return": a["full_project_return"],
            }
        )
    base = accounting(data, central)
    for fraction in [0.01, 0.02, 0.05]:
        loss = base["accepted_revenue"] * fraction
        result.append(
            {
                "parameter": "accepted_invoice_bad_debt_fraction",
                "value": fraction,
                "operating_profit": base["operating_profit"] - loss,
                "full_project_return": base["full_project_return"] - loss,
            }
        )
    for fraction in [0.005, 0.02]:
        loss = base["final_accepted_orders_annual"] * fraction * (central["price"] + 15)
        result.append(
            {
                "parameter": "accepted_payment_chargeback_fraction",
                "value": fraction,
                "operating_profit": base["operating_profit"] - loss,
                "full_project_return": base["full_project_return"] - loss,
            }
        )
    return result


def participation(data, central):
    refs = {
        key: sum(p[key + "_hours"] for p in data["human_reference"]["phases"])
        * data["human_reference"]["rates"][key]
        for key in ["low", "central", "high"]
    }
    refs["high_unloaded_resource"] = refs.pop("high")
    refs["high_loaded_provider"] = data["human_reference"]["additional_loaded_high"][
        "amount"
    ]
    q = expectations(data, central)["q"]
    return [
        {
            "price": price,
            "human_reference_case": key,
            "human_outlay_reference": reference,
            "final_acceptance_assumption": q,
            "maximum_incremental_setup_delay_and_trust_cost": q * (reference - price),
            "basis": "Illustrative buyer first attempts capsule, pays only on retained acceptance, otherwise purchases human fallback. Relative expected saving q*(human price-capsule price)-extra setup/delay/trust cost. No willingness-to-pay or delay-value calibration.",
        }
        for price in range(500, 1501, 100)
        for key, reference in refs.items()
    ]


def token_partitions(data, scenarios):
    result = []
    a = data["api"]
    for scenario in scenarios.values():
        for name, outcome in data["job_outcomes"].items():
            total_input = int(
                round(scenario["baseline_input_tokens"] * outcome["api_multiplier"])
            )
            total_output = int(
                round(scenario["baseline_output_tokens"] * outcome["api_multiplier"])
            )
            count = max(
                math.ceil(total_input / a["partition_input_target"]),
                math.ceil(total_output / a["partition_output_target"]),
            )
            calls = [
                {
                    "call": i + 1,
                    "input_tokens": total_input // count + (i < total_input % count),
                    "output_tokens_including_reasoning": total_output // count
                    + (i < total_output % count),
                }
                for i in range(count)
            ]
            assert sum(c["input_tokens"] for c in calls) == total_input
            assert (
                sum(c["output_tokens_including_reasoning"] for c in calls)
                == total_output
            )
            assert all(
                c["input_tokens"] <= a["per_call_input_token_limit"]
                and c["output_tokens_including_reasoning"]
                <= a["per_call_output_token_limit"]
                for c in calls
            )
            result.append(
                {
                    "scenario": scenario["name"],
                    "outcome": name,
                    "planned_calls": count,
                    "total_input": total_input,
                    "total_output": total_output,
                    "calls": calls,
                    "basis": "Budget partition only; no paid API execution record.",
                }
            )
    return result


def ordinary_coordination(data, central):
    output = []
    price = central["price"]
    wage = data["labor"]["usd_per_hour"]
    for cohorts in [4, 8, 16]:
        for technical in [False, True]:
            for shared in [False, True]:
                if technical:
                    e = expectations(data, central)
                    delivery_per_attempt = e["delivery"]
                    q = e["q"]
                    initial = e["initial"]
                else:
                    delivery_per_attempt = 8 * wage
                    q = 0.95
                    initial = 0.97
                savings = 0.15 * delivery_per_attempt if shared else 0
                coordination = (0.5 * wage + 20) / cohorts if shared else 0
                common_failure = (
                    (0.05 * cohorts * delivery_per_attempt) / cohorts if shared else 0
                )
                shared_setup = (4 * wage) / cohorts if shared else 0
                final_cost = (
                    delivery_per_attempt
                    - savings
                    + coordination
                    + common_failure
                    + shared_setup
                )
                fees = initial * (
                    price * data["costs"]["payment_fee_fraction"]
                    + data["costs"]["payment_fee_fixed"]
                )
                contribution = q * price - final_cost - fees
                output.append(
                    {
                        "delivery": "frontier_assisted"
                        if technical
                        else "competent_human_at_loaded_resource_cost",
                        "shared": shared,
                        "cohort_size": cohorts,
                        "attempted_price": price,
                        "assumed_acceptance": q,
                        "delivery_and_coordination_per_attempt": final_cost,
                        "direct_contribution_per_attempt": contribution,
                        "basis": "Illustrative equal cohort, human 8h at $95 internal resource cost (not provider selling price), 15% reusable delivery work, $380 cohort setup, 0.5h+$20 coordination, 5% common rework exposure. Reuse requires customer permission. No measured reuse advantage; identical sharing assumptions for both arrangements.",
                    }
                )
    return output


def monte_carlo(data, central, trials=1000):
    rng = random.Random(20261027)
    profits = []
    counts = []
    costs = inputs(data, central)
    price = central["price"]
    e = expectations(data, central)
    for _ in range(trials):
        profit = -e["development"]
        accepted = 0
        for month in range(data["timing"]["selling_months"]):
            incident = rng.random() < 0.10
            attempts = 8 if not incident else 6
            s = with_acceptance(central, 0.70) if incident else central
            p = s["outcome_probabilities"]
            keys = list(p)
            weights = [p[k] for k in keys]
            profit -= e["fixed"] + attempts * e["acquisition"]
            for __ in range(attempts):
                outcome = rng.choices(keys, weights)[0]
                row = data["job_outcomes"][outcome]
                jc = job_cost(data, s, outcome)
                if incident:
                    jc["api"] *= 1.5
                profit -= sum(jc.values())
                profit += row["retained_acceptance"] * price
                profit -= row["initial_payment"] * (
                    price * costs["payment_fee_fraction"] + costs["payment_fee_fixed"]
                )
                accepted += row["retained_acceptance"]
        profits.append(profit)
        counts.append(accepted)
    profits.sort()
    counts.sort()

    def percentile(seq, q):
        return seq[round((len(seq) - 1) * q)]

    return {
        "trials": trials,
        "seed": 20261027,
        "assumed_monthly_common_incident_probability": 0.10,
        "incident_effect": "6 rather than 8 jobs; 70% rather than 85% final acceptance; 1.5x API cost. These parameters are uncalibrated scenario assumptions.",
        "full_project_return_p10": percentile(profits, 0.10),
        "full_project_return_median": percentile(profits, 0.50),
        "full_project_return_p90": percentile(profits, 0.90),
        "accepted_orders_p10": percentile(counts, 0.10),
        "accepted_orders_median": percentile(counts, 0.50),
        "accepted_orders_p90": percentile(counts, 0.90),
        "interpretation": "Quantiles under a deliberately specified conditional stochastic model, not estimated real-world probabilities, forecast confidence intervals or evidence of demand.",
    }


def write_csv(path, rows):
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, default=HERE / "inputs.json")
    parser.add_argument("--output", type=Path, default=HERE / "results")
    args = parser.parse_args()
    raw = args.inputs.read_bytes()
    data = json.loads(raw)
    scenarios = expand_scenarios(data)
    args.output.mkdir(parents=True, exist_ok=True)
    summary = []
    cash_summary = []
    for scenario in scenarios.values():
        result = accounting(data, scenario)
        cash, ledger = cash_ledger(data, scenario)
        result["minimum_opening_cash"] = cash["minimum_opening_cash"]
        result["operating_break_even_acceptance"] = root_acceptance(data, scenario)
        result["project_break_even_acceptance"] = root_acceptance(data, scenario, True)
        summary.append(result)
        cash_summary.append({"scenario": scenario["name"], **cash})
        write_csv(args.output / (scenario["name"] + "_cash_ledger.csv"), ledger)
    central = scenarios["central"]
    arrangements = []
    for mode in ["acceptance", "restricted_deposit", "after_warranty"]:
        cash, ledger = cash_ledger(data, central, mode)
        arrangements.append(cash)
        write_csv(args.output / ("central_" + mode + "_ledger.csv"), ledger)
    shock = copy.deepcopy(central)
    shock["outcome_probabilities"] = {
        "clean": 0,
        "corrected": 0,
        "rejected": 0,
        "refunded": 1,
    }
    shock_cash, shock_ledger = cash_ledger(
        data, central, monthly_scenarios=[shock] + [central] * 11
    )
    shock_cash["basis"] = (
        "Adverse deterministic first cohort: all eight initial payments refunded after failed correction; next eleven cohorts use central assumptions. Recovery is assumed, not established. Full customer funds remain reserved."
    )
    write_csv(
        args.output / "central_first_cohort_all_refunded_ledger.csv", shock_ledger
    )
    late_data = copy.deepcopy(data)
    late_data["timing"]["collection_delay_days"] = 35
    late_cash, late_ledger = cash_ledger(late_data, central)
    late_cash["basis"] = (
        "35-day delay after initial acceptance. Failed invoices canceled at warranty close before capture; only finally accepted invoices collected. All obligations run off by final event."
    )
    write_csv(args.output / "central_35_day_collection_delay_ledger.csv", late_ledger)
    refs = {
        key: sum(p[key + "_hours"] for p in data["human_reference"]["phases"])
        * data["human_reference"]["rates"][key]
        for key in ["low", "central", "high"]
    }
    result = {
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "evidence_level": data["evidence_level"],
        "actual": data["actual"],
        "human_reference": refs,
        "human_reference_labels": data["human_reference"]["rate_labels"],
        "loaded_high_provider_reference": data["human_reference"][
            "additional_loaded_high"
        ],
        "scenarios": summary,
        "cash": cash_summary,
        "payment_arrangements": arrangements,
        "first_cohort_all_refunded_stress": shock_cash,
        "35_day_collection_stress": late_cash,
        "conditional_stochastic_sensitivity": monte_carlo(data, central),
        "claim_boundary": data["claim_boundary"],
    }
    (args.output / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    (args.output / "api_token_budget_partitions.json").write_text(
        json.dumps(token_partitions(data, scenarios), indent=2) + "\n"
    )
    write_csv(args.output / "scenario_summary.csv", summary)
    write_csv(args.output / "threshold_grid.csv", threshold_grid(data, central))
    write_csv(args.output / "sensitivities.csv", sensitivities(data, central))
    write_csv(
        args.output / "participation_thresholds.csv", participation(data, central)
    )
    write_csv(
        args.output / "coordination_comparison.csv",
        ordinary_coordination(data, central),
    )
    print(
        json.dumps(
            {
                "human_reference": refs,
                "scenarios": [
                    {
                        k: r[k]
                        for k in [
                            "scenario",
                            "accepted_revenue",
                            "operating_profit",
                            "full_project_return",
                            "minimum_opening_cash",
                            "operating_break_even_price",
                            "project_break_even_price",
                        ]
                    }
                    for r in summary
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
