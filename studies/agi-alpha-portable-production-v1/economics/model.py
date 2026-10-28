# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import copy
import csv
import gzip
import hashlib
import io
import itertools
import json
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
F = Fraction

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def validate_freeze() -> dict[str, str]:
    frozen = json.loads((ROOT / "freeze.json").read_text())
    for name, expected in frozen["sha256"].items():
        if digest(ROOT / name) != expected:
            raise ValueError("Frozen source or input changed: " + name)
    return frozen["sha256"]

def money(value: Fraction | int) -> dict[str, Any]:
    v = F(value)
    return {"exact_cents": str(v), "usd": round(float(v / 100), 6)}

def pjson(value: Fraction) -> dict[str, Any]:
    return {"exact": str(value), "decimal": round(float(value), 10)}

@dataclass(frozen=True)
class Event:
    key: str
    outcome: str
    value: int = 0

@dataclass
class Account:
    bank: int
    initial: int
    setup_ready: bool = False
    restricted: int = 0
    support_reserve: int = 0
    receivable: int = 0
    revenue: int = 0
    cost: int = 0
    bad_debt: int = 0
    collected: int = 0
    refunded: int = 0
    customer_value: int = 0
    customer_benefit: int = 0
    leads: int = 0
    booked: int = 0
    accepted: int = 0
    corrected: int = 0
    failures: int = 0
    defaults: int = 0
    setups: int = 0
    expanded: int = 0
    refusals: int = 0
    finance_blocks: int = 0
    min_unrestricted: int = 0
    shortfall: int = 0
    observations: tuple[str, ...] = ()
    trace: list[dict[str, Any]] = field(default_factory=list)

    @property
    def profit(self) -> int:
        return self.revenue - self.cost - self.bad_debt

    def observe_cash(self, label: str) -> None:
        free = self.bank - self.restricted - self.support_reserve
        self.min_unrestricted = min(self.min_unrestricted, free)
        if free < 0:
            raise AssertionError("Restricted money used")
        self.trace.append({"event": label, "bank": self.bank, "restricted_deposits": self.restricted,
                           "support_reserve": self.support_reserve, "unrestricted": free,
                           "receivable": self.receivable, "recognized_revenue": self.revenue})

    def pay(self, amount: int, label: str) -> None:
        self.bank -= amount
        self.cost += amount
        self.observe_cash(label)

def base_account(capital: int) -> Account:
    return Account(bank=capital, initial=capital, min_unrestricted=capital)

def acceptance_prior(scenario: dict[str, Any]) -> Fraction:
    weights = list(map(F, scenario["common_state_probabilities"]))
    delivery = scenario["delivery_probabilities"]
    return (weights[0] + weights[1]) * (F(delivery["clean"]) + F(delivery["corrected"]))

def event_tables(config: dict[str, Any], scenario: dict[str, Any], price: int) -> list[list[tuple[Event, Fraction]]]:
    acceptance = acceptance_prior(scenario)
    buyer = config["labor_reference"]
    result = []
    for state in range(3):
        outcomes: list[tuple[Event, Fraction]] = []
        refusal = F(1)
        procurement = F(scenario["procurement_probabilities"][state])
        for kind, (value, type_mass) in enumerate(zip(scenario["outside_option_values_cents"],
                                                    scenario["buyer_type_probabilities"])):
            expected_benefit = (acceptance * (value - price - buyer["buyer_integration_cents"])
                                - (1 - acceptance) * buyer["buyer_failed_attempt_loss_cents"])
            if expected_benefit < 0:
                continue
            buy = F(type_mass) * procurement
            refusal -= buy
            deliveries = {"clean": F(0), "corrected": F(0), "failed": F(1)} if state == 2 else {
                key: F(value) for key, value in scenario["delivery_probabilities"].items()}
            for outcome, probability in deliveries.items():
                if not probability:
                    continue
                if outcome == "failed":
                    outcomes.append((Event(f"failed_t{kind}", "failed", value), buy * probability))
                else:
                    paid = F(scenario["balance_collection_probability"])
                    for label, share in [("paid", paid), ("default", 1 - paid)]:
                        if share:
                            outcomes.append((Event(f"{outcome}_{label}_t{kind}", f"{outcome}_{label}", value),
                                             buy * probability * share))
        if refusal:
            outcomes.append((Event("refused", "refused"), refusal))
        if sum(p for _, p in outcomes) != 1 or any(p < 0 for _, p in outcomes):
            raise AssertionError("Outcome probabilities invalid")
        result.append(outcomes)
    return result

def unit_cost(config: dict[str, Any]) -> int:
    costs = config["costs_cents"]
    return sum(costs[k] for k in ("source_intake", "construction", "independent_digital_validation",
                                 "handoff", "compute_storage", "permissions_administration"))

def run_order(account: Account, event: Event, config: dict[str, Any], arrangement: str, price: int) -> str:
    costs, terms = config["costs_cents"], config["offer"]
    reserve = terms["minimum_unrestricted_reserve_cents"]
    if account.bank - costs["lead_acquisition"] < reserve:
        account.finance_blocks += 1
        account.observations += ("lead_financing_blocked",)
        return "lead_financing_blocked"
    account.pay(costs["lead_acquisition"], "acquire_lead")
    account.leads += 1
    if event.outcome == "refused":
        account.refusals += 1
        account.observations += ("refused",)
        return "refused"
    setup = costs["additional_commercial_setup"] if arrangement == "separate_preparation" or not account.setup_ready else 0
    deposit = int(price * F(terms["deposit_fraction"]))
    fee = int(deposit * F(config["payment_fee_fraction"]))
    needed = setup + unit_cost(config) + costs["one_correction"] + fee + costs["failed_refund_administration"] + reserve
    if account.bank < needed:
        account.shortfall = max(account.shortfall, needed - account.bank)
        account.finance_blocks += 1
        account.observations += ("financing_blocked",)
        return "financing_blocked"
    if setup:
        account.pay(setup, "commercial_preparation")
        account.setups += 1
        account.setup_ready = True
    account.bank += deposit
    account.restricted += deposit
    account.collected += deposit
    account.booked += 1
    account.observe_cash("refundable_deposit_received")
    account.pay(fee, "deposit_processing_fee")
    account.pay(unit_cost(config), "complete_digital_execution")
    if event.outcome.startswith("corrected") or event.outcome == "failed":
        account.pay(costs["one_correction"], "one_correction")
        account.corrected += 1
    if event.outcome == "failed":
        account.failures += 1
        account.bank -= deposit
        account.restricted -= deposit
        account.collected -= deposit
        account.refunded += deposit
        account.observe_cash("full_deposit_refund_day_26")
        account.pay(costs["failed_refund_administration"], "refund_administration")
        account.customer_benefit -= config["labor_reference"]["buyer_failed_attempt_loss_cents"]
    else:
        account.accepted += 1
        account.revenue += price
        account.restricted -= deposit
        account.receivable += price - deposit
        account.support_reserve += costs["accepted_support"]
        account.observe_cash("digital_acceptance_day_21")
        if "_default" in event.outcome:
            account.defaults += 1
            account.bad_debt += price - deposit
            account.receivable -= price - deposit
            account.observe_cash("unpaid_balance_written_off_day_66")
        else:
            account.bank += price - deposit
            account.collected += price - deposit
            account.receivable -= price - deposit
            account.observe_cash("final_balance_collected_day_51")
            account.pay(int((price - deposit) * F(config["payment_fee_fraction"])), "balance_processing_fee")
        account.support_reserve -= costs["accepted_support"]
        account.pay(costs["accepted_support"], "support_completed_day_66")
        account.customer_value += event.value
        account.customer_benefit += event.value - price - config["labor_reference"]["buyer_integration_cents"]
    account.observations += (event.key,)
    if account.restricted or account.support_reserve or account.receivable:
        raise AssertionError("Order ended with unsettled modeled obligation")
    if account.bank - account.initial != account.profit:
        raise AssertionError("Accrual/cash reconciliation failed")
    return event.key

def posterior(scenario: dict[str, Any], tables: list[list[tuple[Event, Fraction]]], observation: str) -> list[Fraction]:
    weights = list(map(F, scenario["common_state_probabilities"]))
    likelihood = []
    for table in tables:
        if observation in ("financing_blocked", "lead_financing_blocked"):
            chance = sum(p for e, p in table if e.outcome != "refused")
        else:
            chance = sum(p for e, p in table if e.key == observation)
        likelihood.append(chance)
    total = sum(w * p for w, p in zip(weights, likelihood))
    return [w * p / total for w, p in zip(weights, likelihood)] if total else weights

def continuation_values(account: Account, config: dict[str, Any], scenario: dict[str, Any],
                        arrangement: str, price: int, tables: list[list[tuple[Event, Fraction]]],
                        observation: str) -> tuple[Fraction, list[Fraction]]:
    weights = posterior(scenario, tables, observation)
    coordination = config["costs_cents"]["selective_continuation_coordination"]
    if account.bank - coordination < config["offer"]["minimum_unrestricted_reserve_cents"]:
        return F(-coordination), weights
    value = F(0)
    for state, w in enumerate(weights):
        for pair in itertools.product(tables[state], repeat=2):
            trial = copy.deepcopy(account)
            trial.trace = []
            trial.pay(coordination, "continuation_coordination")
            for event, _ in pair:
                run_order(trial, event, config, arrangement, price)
            probability = w * pair[0][1] * pair[1][1]
            value += probability * (trial.profit - account.profit)
    return value, weights

FIELDS = ["scenario", "arrangement", "policy", "price_cents", "capital_cents", "common_state",
          "probability", "observations", "leads", "booked", "accepted", "corrected", "failures",
          "defaults", "setups", "expanded", "refusals", "finance_blocks", "revenue_cents", "cost_cents",
          "bad_debt_cents", "net_collections_cents", "refunds_cents", "prospective_profit_cents",
          "illustrative_full_history_profit_cents", "end_cash_cents", "min_unrestricted_cents",
          "funding_shortfall_cents", "customer_reference_value_cents", "customer_net_benefit_cents"]

def evaluate(config: dict[str, Any], scenario: dict[str, Any], arrangement: str, policy: str,
             price: int, capital: int, writer: Any = None) -> dict[str, Any]:
    weights = list(map(F, scenario["common_state_probabilities"]))
    tables = event_tables(config, scenario, price)
    sums = {key: F(0) for key in ("revenue", "cost", "bad_debt", "collected", "refunded",
                                  "profit", "customer_value", "customer_benefit", "accepted", "booked",
                                  "leads", "finance_blocks", "setups")}
    mass = F(0)
    loss = F(0)
    full_loss = F(0)
    finance_probability = F(0)
    expansion_probability = F(0)
    minimum_profit = 0
    maximum_profit = 0
    min_cash = capital
    max_shortfall = 0
    worlds = 0
    decisions: dict[str, Any] = {}
    samples: dict[str, Any] = {}
    build = config["costs_cents"]["illustrative_historical_build_once"]

    def record(state: int, probability: Fraction, account: Account) -> None:
        nonlocal mass, loss, full_loss, finance_probability, expansion_probability
        nonlocal worlds, minimum_profit, maximum_profit, min_cash, max_shortfall
        if not probability:
            return
        worlds += 1
        mass += probability
        for key in sums:
            sums[key] += probability * getattr(account, key)
        loss += probability * (account.profit < 0)
        full_loss += probability * (account.profit - build < 0)
        finance_probability += probability * bool(account.finance_blocks)
        expansion_probability += probability * bool(account.expanded)
        minimum_profit = min(minimum_profit, account.profit)
        maximum_profit = max(maximum_profit, account.profit)
        min_cash = min(min_cash, account.min_unrestricted)
        max_shortfall = max(max_shortfall, account.shortfall)
        label = "default" if account.defaults else "failed" if account.failures else "accepted" if account.accepted else "refused"
        samples.setdefault(label, {"observations": account.observations, "trace": account.trace,
                                   "profit_cents": account.profit, "final_cash_cents": account.bank})
        if writer:
            writer.writerow([scenario["name"], arrangement, policy, price, capital,
                             config["common_states"][state], str(probability), "|".join(account.observations),
                             account.leads, account.booked, account.accepted, account.corrected, account.failures,
                             account.defaults, account.setups, account.expanded, account.refusals, account.finance_blocks,
                             account.revenue, account.cost, account.bad_debt, account.collected, account.refunded,
                             account.profit, account.profit - build, account.bank, account.min_unrestricted,
                             account.shortfall, account.customer_value, account.customer_benefit])

    if policy == "stop_now":
        record(0, F(1), base_account(capital))
    else:
        for state, w in enumerate(weights):
            for event, chance in tables[state]:
                account = base_account(capital)
                observed = run_order(account, event, config, arrangement, price)
                probability = w * chance
                expand = False
                if policy == "deliver_selectively" and not observed.endswith("financing_blocked"):
                    cache_key = observed
                    if cache_key not in decisions:
                        value, post = continuation_values(account, config, scenario, arrangement, price, tables, observed)
                        decisions[cache_key] = {"incremental_expected_profit": money(value),
                                                "posterior": [str(v) for v in post], "expand": value > 0}
                    expand = decisions[cache_key]["expand"]
                if expand:
                    for pair in itertools.product(tables[state], repeat=2):
                        trial = copy.deepcopy(account)
                        trial.expanded = 1
                        trial.pay(config["costs_cents"]["selective_continuation_coordination"], "continuation_coordination")
                        for later, _ in pair:
                            run_order(trial, later, config, arrangement, price)
                        record(state, probability * pair[0][1] * pair[1][1], trial)
                else:
                    record(state, probability, account)
    if mass != 1:
        raise AssertionError("History mass is not one")
    financial = {key: money(sums[key]) for key in ("revenue", "cost", "bad_debt", "collected", "refunded",
                                                  "profit", "customer_value", "customer_benefit")}
    financial["illustrative_full_history_profit"] = money(sums["profit"] - build)
    financial["expected_end_cash"] = money(capital + sums["profit"])
    return {"scenario": scenario["name"], "arrangement": arrangement, "policy": policy,
            "price_cents": price, "capital_cents": capital, "finite_history_count": worlds,
            "probability_mass": str(mass), "expected": financial,
            "expected_counts": {key: str(sums[key]) for key in ("accepted", "booked", "leads", "finance_blocks", "setups")},
            "prospective_loss_probability": pjson(loss), "illustrative_full_history_loss_probability": pjson(full_loss),
            "finance_refusal_probability": pjson(finance_probability), "expansion_probability": pjson(expansion_probability),
            "minimum_prospective_profit": money(minimum_profit), "maximum_prospective_profit": money(maximum_profit),
            "minimum_unrestricted_cash": money(min_cash), "maximum_additional_funding_shortfall": money(max_shortfall),
            "continuation_decisions": decisions, "cash_trace_examples": samples}

def information_value(config: dict[str, Any], scenario: dict[str, Any], price: int) -> dict[str, Any]:
    tables = event_tables(config, scenario, price)
    prior = list(map(F, scenario["common_state_probabilities"]))
    coordination = config["costs_cents"]["selective_continuation_coordination"]
    values = []
    for table in tables:
        mean = F(0)
        for event, probability in table:
            account = base_account(10000000)
            account.setup_ready = True
            run_order(account, event, config, "conventional_shared", price)
            mean += probability * account.profit
        values.append(2 * mean - coordination)
    without = max(F(0), sum(p * v for p, v in zip(prior, values)))
    signal_keys = sorted({e.key for table in tables for e, _ in table})
    with_signal = F(0)
    for key in signal_keys:
        probabilities = [sum(p for e, p in table if e.key == key) for table in tables]
        mass = sum(p * q for p, q in zip(prior, probabilities))
        if mass:
            conditional = sum(p * q * v for p, q, v in zip(prior, probabilities, values)) / mass
            with_signal += mass * max(F(0), conditional)
    evsi = with_signal - without
    if evsi < 0:
        raise AssertionError("Free information decreased the optimal decision value")
    return {"scenario": scenario["name"], "scope": "Two future prospects; same ready asset and sufficient capital in every comparison; no signal cost included",
            "continue_values_by_common_state": [money(v) for v in values],
            "best_decision_without_signal": money(without), "best_decision_with_pilot_signal": money(with_signal),
            "maximum_additional_information_fee": money(evsi),
            "note": "Do not subtract the paid-work pilot cost again as research. Full pilot economics appear in the policy comparison; this is only the ceiling for additional information collection."}

def scale_and_retention(config: dict[str, Any]) -> dict[str, Any]:
    x = config["expansion"]
    population, years = x["population"], x["horizon_years"]
    target, benefit = x["target_net_customer_benefit_cents"], x["illustrative_net_value_per_accepted_outcome_cents"]
    exposure = sum(map(F, x["annual_adoption_fractions"]))
    jobs = x["illustrative_jobs_per_active_shop_year"]
    required = F(target, population * benefit) / exposure
    r = config["retention"]
    retained_cost = r["extra_extraction_validation_cents"] + r["months"] * r["maintenance_per_month_cents"]
    threshold = F(retained_cost, r["fresh_reuses"] * config["labor_reference"]["assumed_loaded_hourly_cents"]) / F(r["usable_probability"])
    return {"population": population, "horizon_years": years, "cumulative_adoption_years": str(exposure),
            "target_metric": "USD1 billion cumulative NET CUSTOMER BENEFIT after service price and buyer integration over 10 years",
            "illustrative_ramp_net_customer_benefit": money(population * exposure * jobs * benefit),
            "required_jobs_per_active_shop_year_at_frozen_ramp": float(required),
            "required_jobs_per_shop_year_at_100_percent_adoption_all_ten_years": float(F(target, population * years * benefit)),
            "accepted_jobs_needed_for_target": str(F(target, benefit)),
            "conditional_provider_revenue_at_target_volume": money(F(target, benefit) * config["offer"]["price_cents"]),
            "obtainable_revenue": "Not estimated from population; only the finite scenario cohort is modeled.",
            "valuation": "Not estimated.", "admission": "No defensible billion-plus venture admission: eligibility, adoption and realized customer benefit are unvalidated.",
            "retention_extra_cost": money(retained_cost), "retention_incremental_value_vs_same_library": money(0),
            "retention_net_increment": money(-retained_cost), "retention_decision": "REJECT",
            "retention_break_even_incremental_hours_saved_per_usable_fresh_reuse": str(threshold),
            "gym_status": "NOT RUN", "live_ens_authentication": "NOT RUN; no fixture grants live authority"}

def run(output: Path) -> None:
    frozen = validate_freeze()
    config = json.loads((ROOT / "inputs.json").read_text())
    output.mkdir(parents=True, exist_ok=False)
    stream = io.StringIO()
    writer = csv.writer(stream)
    writer.writerow(FIELDS)
    results = []
    price = config["offer"]["price_cents"]
    capital = config["offer"]["initial_unrestricted_capital_cents"]
    for scenario, arrangement, policy in itertools.product(config["scenarios"], config["arrangements"], config["policies"]):
        results.append(evaluate(config, scenario, arrangement, policy, price, capital, writer))
    with (output / "histories.csv.gz").open("wb") as target:
        with gzip.GzipFile(fileobj=target, mode="wb", mtime=0) as compressed:
            compressed.write(stream.getvalue().encode())
    sensitivity = []
    for scenario in config["scenarios"]:
        for candidate_price in config["offer"]["price_grid_cents"]:
            for candidate_capital in config["offer"]["capital_grid_cents"]:
                item = evaluate(config, scenario, "conventional_shared", "deliver_selectively", candidate_price, candidate_capital)
                item.pop("cash_trace_examples")
                sensitivity.append(item)
    summaries = {"edition": config["edition"], "frozen_sha256": frozen, "actual": config["actual"],
                 "results": results, "sensitivity": sensitivity,
                 "information_value": [information_value(config, s, price) for s in config["scenarios"]],
                 "scale_and_retention": scale_and_retention(config)}
    (output / "results.json").write_text(json.dumps(summaries, indent=2) + "\n")
    max_first = (config["costs_cents"]["lead_acquisition"] + config["costs_cents"]["additional_commercial_setup"]
                 + unit_cost(config) + config["costs_cents"]["one_correction"]
                 + int(price * F(config["offer"]["deposit_fraction"]) * F(config["payment_fee_fraction"]))
                 + config["costs_cents"]["failed_refund_administration"] + config["offer"]["minimum_unrestricted_reserve_cents"])
    (output / "financing.json").write_text(json.dumps({
        "first_booked_order_minimum_initial_unrestricted_capital": money(max_first),
        "refundable_deposit_does_not_reduce_this_requirement": True,
        "funding_alternatives": [{"kind": "owner equity", "cost": "No cash financing charge modeled; opportunity cost unmeasured."},
                                 {"kind": "committed external credit", "status": "Not available or authorized",
                                  "illustrative_90_day_interest_on_first_order_requirement": [
                                      {"annual_rate": rate, "interest": money(F(max_first) * F(rate) * F(90,365))}
                                      for rate in config["financing"]["debt_interest_rate_grid"]]},
                                 {"kind": "customer acceptance of a separate paid preparation milestone",
                                  "status": "Requires a separately scoped useful delivery and new buyer agreement; not assumed here."}]
    }, indent=2) + "\n")
    print(json.dumps({"output": str(output), "main_cells": len(results), "sensitivity_cells": len(sensitivity),
                      "world_rows": sum(x["finite_history_count"] for x in results)}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    run(args.output)

