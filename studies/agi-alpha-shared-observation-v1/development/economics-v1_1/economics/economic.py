# SPDX-License-Identifier: Apache-2.0
"""Finite conditional-order economics; every receipt and buyer is simulated."""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any


def load_operators(technical: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate technical costs; acquisition is excluded from both alternatives."""
    operators = technical["operators"]
    if not 1 <= len(operators) <= 6:
        raise ValueError("Finite event tree supports one to six operators")
    if len({x["id"] for x in operators}) != len(operators):
        raise ValueError("Duplicate operator")
    for op in operators:
        for key in ("baseline_cost", "contingent_cost", "value_of_information", "peak_action_reserve"):
            if not math.isfinite(op[key]):
                raise ValueError(f"Nonfinite {key}")
        if min(op["baseline_cost"], op["contingent_cost"], op["peak_action_reserve"]) < 0:
            raise ValueError("Negative expense or reserve")
        delta = op["baseline_cost"] - op["contingent_cost"]
        if not math.isclose(delta, op["value_of_information"], rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError("Technical information value must equal baseline minus contingent expense")
    return operators


def tariff_cost(inputs: int, outputs: int, tariff: dict[str, Any]) -> float:
    """Uncached Standard workload estimate, including the long-context tier."""
    long_context = inputs > 272_000
    return (
        inputs * tariff["input_per_million"] * (2 if long_context else 1)
        + outputs * tariff["output_per_million"] * (1.5 if long_context else 1)
    ) / 1_000_000


def select_participants(
    available: list[dict[str, Any]], assumptions: dict[str, Any], constructed: bool, shared: bool
) -> list[dict[str, Any]]:
    """Decline negative-value offers; recompute the equal share after withdrawals."""
    selected = [op for op in available if constructed and op["valid"]]
    a = assumptions
    q = a["first_pass_acceptance"]["E"]
    while selected:
        share = a["acquisition_cost"] / len(selected) if shared else a["acquisition_cost"]
        keep = []
        for op in selected:
            surplus = (1 - a["common_package_failure_probability"]) * (
                q * (op["value_of_information"] - a["package_fee"]) - share
            ) - a["customer_adaptation_cost"]
            required_cash = share + a["package_fee"]
            required_cash += a["customer_adaptation_cost"] + op["peak_action_reserve"]
            budget = op.get("customer_cash_available")
            if surplus >= -1e-10 and (budget is None or required_cash <= budget):
                keep.append(op)
        if len(keep) == len(selected):
            break
        selected = keep
    return selected


def cash_path(
    a: dict[str, Any], offered: int, selected: list[dict[str, Any]], shared: bool,
    common_failure: bool, statuses: tuple[str, ...], saving: float = 0.0,
) -> dict[str, Any]:
    """Settle acquisition pass-through, refundable fees, default and support."""
    n = len(selected)
    quote = a["per_operator_quote_cost"] * offered
    acquisition = a["acquisition_cost"] * (1 if shared and n else n)
    fee_deposit = a["package_fee"] * a["fee_deposit_fraction"] * n
    accepted = sum(s in ("paid", "default") for s in statuses) if not common_failure else 0
    paid = sum(s == "paid" for s in statuses) if not common_failure else 0
    defaults = accepted - paid
    preparation = max(0.0, a["fixed_A_delivery_cost"] - quote - saving) if n else 0.0
    delivery = preparation + a["per_operator_A_delivery_cost"] * n
    handling = a["failure_handling_per_operator"] * (n - accepted)
    support = a["support_per_accepted_operator"] * accepted
    balance = a["package_fee"] * (1 - a["fee_deposit_fraction"]) * paid
    refunds = fee_deposit if common_failure else a["package_fee"] * a["fee_deposit_fraction"] * (n - accepted)
    if common_failure:
        refunds += acquisition
    collected_service = accepted * a["package_fee"] * a["fee_deposit_fraction"] + balance
    sensor_loss = acquisition if common_failure else 0.0
    profit = collected_service - quote - delivery - handling - support - sensor_loss
    stages = []
    cash = a["seed_capital"]

    def record(day: int, label: str, change: float, refundable: float, obligations: float) -> None:
        nonlocal cash
        cash += change
        stages.append({"day": day, "event": label, "cash": cash, "cash_change": change,
                       "refundable_liability": refundable, "unpaid_obligations": obligations,
                       "reserve": a["provider_reserve"],
                       "available_funds": cash - refundable - obligations - a["provider_reserve"]})

    record(0, "quote", -quote, 0.0, 0.0)
    if n:
        record(1, "conditional_deposits", acquisition + fee_deposit, acquisition + fee_deposit, delivery)
        record(2, "acquire_and_prepare", -acquisition - delivery,
               acquisition + fee_deposit, handling + support)
        record(3, "accept_default_or_refund", balance - refunds - handling, 0.0, support)
        record(4, "support_settled", -support, 0.0, 0.0)
    customer_value = sum(op["value_of_information"] for op, s in zip(selected, statuses) if s in ("paid", "default"))
    if common_failure:
        customer_value = 0.0
    customer_cost = collected_service + (0.0 if common_failure else acquisition)
    customer_cost += a["customer_adaptation_cost"] * n
    return {"participants": n, "accepted": accepted, "defaults": defaults,
            "common_failure": common_failure, "statuses": list(statuses),
            "earned_gross_service_revenue": accepted * a["package_fee"],
            "collected_service_revenue": collected_service,
            "bad_debt": defaults * a["package_fee"] * (1 - a["fee_deposit_fraction"]),
            "pass_through_collected": acquisition, "pass_through_refunded": sensor_loss,
            "gross_customer_cash_receipts": acquisition + fee_deposit + balance,
            "sensor_paid": acquisition, "refunds": refunds,
            "A_cash_cost": quote + delivery + handling + support + sensor_loss,
            "operating_profit_before_BC": profit, "end_cash": cash,
            "end_available_funds": cash - a["provider_reserve"],
            "minimum_available_funds": min(x["available_funds"] for x in stages),
            "extra_financing_required": max(0.0, -min(x["available_funds"] for x in stages)),
            "customer_expected_action_savings": customer_value,
            "customer_net_value": customer_value - customer_cost,
            "required_buyer_cash": [op["peak_action_reserve"] + acquisition / n
                                    + a["package_fee"]
                                    + a["customer_adaptation_cost"] for op in selected],
            "buyer_liquidity_verified": all("customer_cash_available" in op for op in selected) and bool(n),
            "cash_path": stages}


def evaluate(
    technical: dict[str, Any], a: dict[str, Any], constructed: bool = True,
    shared: bool = True, retain_paths: bool = False, saving: float = 0.0,
) -> dict[str, Any]:
    """Exactly enumerate withdrawals, common failure, rejection and default."""
    operators = load_operators(technical)
    probability_keys = ("precommit_withdrawal_probability", "common_package_failure_probability",
                        "conditional_payment_default_probability", "fee_deposit_fraction")
    if any(not 0 <= a[key] <= 1 for key in probability_keys):
        raise ValueError("Probability or deposit fraction outside [0,1]")
    if any(not 0 <= value <= 1 for value in a["first_pass_acceptance"].values()):
        raise ValueError("Acceptance probability outside [0,1]")
    if min(a["acquisition_cost"], a["package_fee"], a["seed_capital"], a["provider_reserve"]) < 0:
        raise ValueError("Negative money input")
    w = a["precommit_withdrawal_probability"]
    common = a["common_package_failure_probability"]
    q = a["first_pass_acceptance"]["E"]
    d = a["conditional_payment_default_probability"]
    metrics = ("participants", "accepted", "defaults", "earned_gross_service_revenue",
               "collected_service_revenue", "bad_debt", "pass_through_collected",
               "pass_through_refunded", "sensor_paid", "refunds", "A_cash_cost",
               "operating_profit_before_BC", "end_cash", "end_available_funds",
               "customer_expected_action_savings", "customer_net_value", "extra_financing_required")
    totals = dict.fromkeys(metrics, 0.0)
    total_probability = launch_probability = liquidity_failure = positive_profit = 0.0
    worst_cash = math.inf
    worst_profit = math.inf
    largest_financing = 0.0
    paths = []
    outcomes = 0
    for present in itertools.product((False, True), repeat=len(operators)):
        probability = math.prod((1 - w) if x else w for x in present)
        selected = select_participants([op for op, yes in zip(operators, present) if yes], a, constructed, shared)
        n = len(selected)
        launch_probability += probability * bool(n)
        branches = [(1.0, False, ())] if not n else [(common, True, tuple("reject" for _ in selected))]
        if n:
            for statuses in itertools.product(("paid", "default", "reject"), repeat=n):
                chance = (1 - common) * math.prod({"paid": q * (1 - d), "default": q * d,
                                                "reject": 1 - q}[s] for s in statuses)
                branches.append((chance, False, statuses))
        for conditional, failure, statuses in branches:
            weight = probability * conditional
            if weight <= 0:
                continue
            result = cash_path(a, len(operators), selected, shared, failure, statuses, saving)
            total_probability += weight
            outcomes += 1
            for key in metrics:
                totals[key] += weight * result[key]
            liquid = result["minimum_available_funds"] >= -1e-9
            liquidity_failure += weight * (not liquid)
            positive_profit += weight * (result["operating_profit_before_BC"] > 0)
            worst_cash = min(worst_cash, result["minimum_available_funds"])
            worst_profit = min(worst_profit, result["operating_profit_before_BC"])
            largest_financing = max(largest_financing, result["extra_financing_required"])
            if retain_paths:
                paths.append({"probability": weight, "available_operators": list(present), **result})
    if not math.isclose(total_probability, 1.0, abs_tol=1e-9):
        raise ArithmeticError("Event probabilities do not sum to one")
    if not math.isclose(totals["end_cash"], a["seed_capital"] + totals["operating_profit_before_BC"], abs_tol=1e-7):
        raise ArithmeticError("Cash and recognized net collections do not reconcile")
    return {"evidence": "enumerated_conditional_simulation", "constructed": constructed, "shared": shared,
            "expected": totals, "launch_probability": launch_probability, "outcome_count": outcomes,
            "probability_sum": total_probability, "liquidity_failure_probability": liquidity_failure,
            "positive_profit_probability": positive_profit, "worst_operating_profit": worst_profit,
            "worst_available_funds": worst_cash, "maximum_extra_financing": largest_financing,
            "unfunded_paths_are_not_executed": True,
            "paths": paths if retain_paths else None}


def expertise_grid(a: dict[str, Any]) -> list[dict[str, Any]]:
    """Unknown U/E/E+ effects include equal and worse outcomes at matched budgets."""
    grid = a["U_E_grid"]
    base = a["fixed_A_delivery_cost"] + 4 * a["per_operator_A_delivery_cost"]
    rows = []
    for q, de, dp, mult, attempts in itertools.product(
        grid["baseline_acceptance"], grid["delta_E"], grid["delta_Eplus"],
        grid["cost_multipliers"], grid["maximum_attempts"],
    ):
        probs = [q, max(0.0, min(1.0, q + de)), max(0.0, min(1.0, q + de + dp))]
        costs = [base, base * mult, base * mult]
        row: dict[str, Any] = {"q_U": q, "delta_E": de, "delta_Eplus": dp,
                               "expert_cost_multiplier": mult, "maximum_attempts": attempts}
        for name, prob, cost in zip(("U", "E", "Eplus"), probs, costs):
            retry = prob * grid["retry_success_fraction"]
            accepted = prob + ((1 - prob) * retry if attempts == 2 else 0.0)
            expected_cost = cost * (1 + (1 - prob) if attempts == 2 else 1)
            row[name] = {"assumed_first_pass_acceptance": prob,
                         "acceptance_after_retries": accepted,
                         "expected_attempts": 1 + (1 - prob) if attempts == 2 else 1,
                         "expected_cost": expected_cost,
                         "cost_per_accepted_outcome": expected_cost / accepted if accepted else None}
        collectible = 4 * a["package_fee"] * (1 - a["conditional_payment_default_probability"])
        row["required_acceptance_gain_E_vs_U"] = (costs[1] - costs[0]) / collectible if collectible else None
        row["matched_resource_budget_row"] = mult == 1
        rows.append(row)
    return rows


def retention_grid(a: dict[str, Any]) -> list[dict[str, Any]]:
    """No retention gains are observed; report prospective investment thresholds."""
    rows = []
    for saving, extra_C in itertools.product(a["Eplus_cash_saving_range"], (0.0, a["C_optional_calibration_cost"])):
        net = saving - a["B_upkeep_per_use"]
        cost = a["B_retention_admission_cost"] + extra_C
        rows.append({"assumed_cash_saving_per_fresh_use": saving, "B_initial": a["B_retention_admission_cost"],
                     "C_optional": extra_C, "net_per_use_after_upkeep": net,
                     "minimum_uses_for_strict_positive_increment": math.floor(cost / net) + 1 if net > 0 else None,
                     "gain_observed": False, "admission_reachable": net > 0,
                     "admission_decision": "hold_pending_fresh_cost_evidence" if net > 0 else "reject_before_assessment"})
    return rows


def run(technical: dict[str, Any], assumptions: dict[str, Any]) -> dict[str, Any]:
    """Return factorial ablations, competent parity, sensitivity and investment thresholds."""
    a = assumptions
    cases = {"T0_A0_ablation": (False, False), "T0_A1_ablation": (False, True),
             "T1_A0_individual": (True, False), "T1_A1_joint": (True, True),
             "competent_unrestricted_E": (True, True)}
    factorial = {name: evaluate(technical, a, *flags) for name, flags in cases.items()}
    assert factorial["T1_A1_joint"] == factorial["competent_unrestricted_E"]
    sensitivity = []
    for acquisition, price in itertools.product(a["acquisition_cost_range"], a["package_fee_range"]):
        changed = {**a, "acquisition_cost": acquisition, "package_fee": price}
        result = evaluate(technical, changed)
        sensitivity.append({"acquisition": acquisition, "package_fee": price,
                            "launch_probability": result["launch_probability"],
                            "profit": result["expected"]["operating_profit_before_BC"],
                            "customer_net_value": result["expected"]["customer_net_value"],
                            "maximum_extra_financing": result["maximum_extra_financing"]})
    human = a["human_service"]
    hourly = human["annual_wage"] / human["annual_hours_divisor"]
    references = [{"hours": h, "burden": b, "estimated_cost": h * b * hourly}
                  for h, b in itertools.product(human["hours"], human["burden_multipliers"])]
    workload = a["modeled_Astra_workload"]
    no_value = {"operators": [{**x, "contingent_cost": x["baseline_cost"], "value_of_information": 0.}
                              for x in technical["operators"]]}
    return {"schema": "shared-observation-economics-results-v1", "actual_customer_collections": 0,
            "actual_complete_research_cost": None, "actual_frontier_billing": None,
            "assumptions_sha256": hashlib.sha256(json.dumps(a, sort_keys=True).encode()).hexdigest(),
            "factorial": factorial, "sensitivity": sensitivity,
            "seed_zero_stress": evaluate(technical, {**a, "seed_capital": 0.0}),
            "default_stress": evaluate(technical, {**a, "conditional_payment_default_probability": 1.0}),
            "withdrawal_stress": evaluate(technical, {**a, "precommit_withdrawal_probability": 1.0}),
            "no_value_stress": evaluate(no_value, a),
            "human_reference": {"hourly_wage_proxy": hourly, "scenarios": references,
                                "market_quote": False, "source": human["source"]},
            "tariff_workload_estimate_included_in_A": tariff_cost(workload["uncached_input_tokens"],
                                                                 workload["output_tokens"], a["tariffs"]["Astra"]),
            "expertise_assumption_grid": expertise_grid(a), "retention_thresholds": retention_grid(a),
            "boundaries": ["T0 is a component ablation, never ordinary model U or competent expert E.",
                           "E with identical algebra and coordination rights ties joint E+ before extra retention cost.",
                           "Customer action savings are simulated value, never enterprise revenue.",
                           "A funds delivery-required learning; B and C are additional optional investments.",
                           "Zero-seed paths are counterfactual funding requirements, not executable sales.",
                           "Common package failure refunds all deposits; acquisition cost is then provider loss."]}


def compact_summary(result: dict[str, Any], technical: dict[str, Any], a: dict[str, Any]) -> dict[str, Any]:
    """Small manuscript-facing table with cash and opportunity costs kept distinct."""
    joint = result["factorial"]["T1_A1_joint"]
    e = joint["expected"]
    quote = a["per_operator_quote_cost"] * len(technical["operators"])
    rows = {name: {"launch_probability": x["launch_probability"],
                   "service_collections": x["expected"]["collected_service_revenue"],
                   "A_cash_cost": x["expected"]["A_cash_cost"],
                   "operating_profit_before_BC": x["expected"]["operating_profit_before_BC"],
                   "buyer_net_value": x["expected"]["customer_net_value"]}
            for name, x in result["factorial"].items()}
    all_success = cash_path(a, len(technical["operators"]), technical["operators"], True, False,
                            tuple("paid" for _ in technical["operators"]))
    withdrawal = cash_path(a, len(technical["operators"]), technical["operators"], True, False,
                           tuple("withdraw_after_commit" if i == 0 else "paid"
                                 for i in range(len(technical["operators"]))))
    return {"evidence": "conditional_simulation_only", "factorial": rows,
            "expected_A_components": {"quotes_all_invitations": quote,
                                      "construction_preparation_correction": (a["fixed_A_delivery_cost"] - quote)
                                      * joint["launch_probability"],
                                      "per_operator_delivery": a["per_operator_A_delivery_cost"] * e["participants"],
                                      "failed_or_rejected_handling": a["failure_handling_per_operator"]
                                      * (e["participants"] - e["accepted"]),
                                      "support": a["support_per_accepted_operator"] * e["accepted"],
                                      "common_failure_sunk_acquisition": e["pass_through_refunded"]},
            "all_commit_accept_pay_branch": all_success, "postcommit_withdrawal_diagnostic": withdrawal,
            "positive_profit_probability": joint["positive_profit_probability"],
            "worst_operating_profit": joint["worst_operating_profit"],
            "zero_seed_extra_financing_maximum": result["seed_zero_stress"]["maximum_extra_financing"],
            "zero_seed_liquidity_failure_probability": result["seed_zero_stress"]["liquidity_failure_probability"],
            "no_value_acquisition_order": result["no_value_stress"]["expected"]["sensor_paid"],
            "no_value_quote_loss": result["no_value_stress"]["expected"]["operating_profit_before_BC"],
            "human_reference": result["human_reference"], "retention_thresholds": result["retention_thresholds"],
            "opportunity_costs": {"actual_unpaid_provider_engineering": None,
                                  "required_residual_customer_attention": None,
                                  "modeled_A_paid_effort": "included in 60 fixed plus 20 per participating operator",
                                  "provider_unpriced_opportunity_cost_erasing_expected_profit": e["operating_profit_before_BC"]},
            "actual_customer_collections": 0, "actual_complete_research_cost": None,
            "buyer_liquidity": "required full fee and fallback reserves reported; financing unverified",
            "primary_Operational_Alpha": "unmeasured; q_U=q_E=q_Eplus=0.90; competent E ties E+",
            "pricing": "80 USD illustrative fixed fee; not optimized and not a discount from human wage proxy"}


def main() -> None:
    """Run from an independently generated technical JSON and frozen assumptions."""
    parser = argparse.ArgumentParser()
    parser.add_argument("technical", type=Path)
    parser.add_argument("--assumptions", type=Path, default=Path(__file__).with_name("assumptions-v1.json"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    a = json.loads(args.assumptions.read_text())
    technical = json.loads(args.technical.read_text())
    result = run(technical, a)
    result["technical_sha256"] = hashlib.sha256(args.technical.read_bytes()).hexdigest()
    result["assumptions_file_sha256"] = hashlib.sha256(args.assumptions.read_bytes()).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "economic_results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    summary = compact_summary(result, technical, a)
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with (args.output / "sensitivity.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(result["sensitivity"][0]))
        writer.writeheader()
        writer.writerows(result["sensitivity"])
    paths = evaluate(technical, a, retain_paths=True)
    (args.output / "event_tree.json").write_text(json.dumps(paths, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"cases": len(result["factorial"]), "technical_sha256": result["technical_sha256"],
                      "joint": result["factorial"]["T1_A1_joint"]["expected"]}, indent=2))


if __name__ == "__main__":
    main()
