# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
F = Fraction


def money(value: float) -> int:
    return round(value * 100)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def csv_write(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)


def fraction(value: Any) -> Fraction:
    return F(str(value))


def state_parameters(config: dict[str, Any], scenario: dict[str, Any], shock: bool) -> dict[str, Any]:
    s = deepcopy(scenario)
    s["cost_multiplier"] = 1.0
    if shock:
        shock_config = config["common_shock"]
        s["trust_booking_probability"] *= shock_config["booking_multiplier"]
        s["cost_multiplier"] = shock_config["cost_multiplier"]
        for key, multiplier in [
            ("first_pass_delivery_probability", "first_pass_multiplier"),
            ("acceptance_given_delivery_probability", "acceptance_multiplier"),
            ("collection_given_acceptance_probability", "collection_multiplier"),
        ]:
            s[key] *= shock_config[multiplier]
    return s


def booking_probability(config: dict[str, Any], s: dict[str, Any], price: float) -> float:
    h = config["human_comparator"]
    comparator = h["hours"] * h["hourly_rate_usd"] * h["overhead_factor"]
    if price + s["switching_cost_usd"] > comparator:
        return 0.0
    lo, hi = s["buyer_reservation_min_usd"], s["buyer_reservation_max_usd"]
    tail = min(1.0, max(0.0, (hi - price) / (hi - lo)))
    return tail * s["trust_booking_probability"]


def job_costs(s: dict[str, Any], saving: float = 0.0) -> tuple[int, int, int]:
    labor = max(0.0, s["labor_hours"] * s["labor_rate_usd"] - saving)
    base = labor + s["model_allowance_usd"] + s["infrastructure_usd"] + s["packaging_usd"]
    return (
        money(base * s["cost_multiplier"]),
        money(s["correction_usd"] * s["cost_multiplier"]),
        money(s["support_usd"] * s["cost_multiplier"]),
    )


def unit_economics(config: dict[str, Any], s: dict[str, Any], price: float) -> dict[str, Any]:
    p, a, k = [
        fraction(s[key])
        for key in [
            "first_pass_delivery_probability",
            "acceptance_given_delivery_probability",
            "collection_given_acceptance_probability",
        ]
    ]
    rescue = fraction(s["correction_rescue_probability"])
    delivered = p + (1 - p) * rescue
    accepted = delivered * a
    price_f, deposit, rate = (
        fraction(price),
        fraction(config["deposit_fraction"]),
        fraction(config["payment_fee_fraction"]),
    )
    revenue = accepted * price_f
    collections = accepted * price_f * (deposit + (1 - deposit) * k)
    bad_debt = revenue - collections
    fees = rate * price_f * (deposit + accepted * (1 - deposit) * k)
    base, correction, support = [F(x, 100) for x in job_costs(s)]
    cost = base + (1 - p) * correction + support + fees + bad_debt
    booked = booking_probability(config, s, price)
    acquisition = fraction(s["lead_cost_usd"]) / fraction(booked) if booked else None
    contribution = revenue - cost - acquisition if acquisition is not None else None
    return {
        "price_usd": price,
        "booking_probability_per_qualified_lead": booked,
        "technical_artifact_delivery_probability": float(delivered),
        "accepted_probability": float(accepted),
        "expected_earned_revenue_usd": float(revenue),
        "expected_collections_usd": float(collections),
        "expected_bad_debt_usd": float(bad_debt),
        "base_delivery_cost_usd": float(base),
        "expected_correction_usd": float((1 - p) * correction),
        "support_usd": float(support),
        "payment_fees_usd": float(fees),
        "expected_job_expense_usd": float(cost),
        "acquisition_per_booking_usd": float(acquisition) if acquisition is not None else None,
        "expected_contribution_usd": float(contribution) if contribution is not None else None,
        "exact_contribution_fraction_usd": str(contribution) if contribution is not None else None,
        "exact_revenue_fraction_usd": str(revenue),
        "exact_job_cost_fraction_usd": str(cost),
    }


def minimum_seed(config: dict[str, Any], s: dict[str, Any], price: float) -> float:
    base, correction, support = job_costs(s)
    return (
        sum(config["startup_costs_usd"].values())
        + config["horizon_weeks"] * config["weekly_overhead_usd"]
        + config["operating_buffer_usd"]
        + s["lead_cost_usd"]
        + (base + correction + support) / 100
        + price * config["payment_fee_fraction"]
    )


def planning_profit(config: dict[str, Any], s: dict[str, Any], price: float) -> dict[str, float]:
    unit = unit_economics(config, s, price)
    weeks = config["horizon_weeks"]
    leads = weeks * s["leads_per_week"]
    mean_service_weeks = 2 - s["first_pass_delivery_probability"]
    capacity = weeks * config["slots"] / mean_service_weeks
    attempts = min(leads * unit["booking_probability_per_qualified_lead"], capacity)
    job_profit = unit["expected_earned_revenue_usd"] - unit["expected_job_expense_usd"]
    acquisitions = leads * s["lead_cost_usd"]
    fixed_and_acquisition = (
        acquisitions + weeks * config["weekly_overhead_usd"] + sum(config["startup_costs_usd"].values())
    )
    break_even_booking_probability = fixed_and_acquisition / (leads * job_profit) if job_profit > 0 and leads else None
    operating = attempts * job_profit - acquisitions - weeks * config["weekly_overhead_usd"]
    return {
        "expected_attempts": attempts,
        "expected_accepted": attempts * unit["accepted_probability"],
        "capacity_attempts": capacity,
        "acquisition_spend_usd": acquisitions,
        "break_even_booking_probability_per_lead": break_even_booking_probability,
        "operating_profit_usd": operating,
        "full_project_profit_usd": operating - sum(config["startup_costs_usd"].values()),
        "first_job_seed_needed_usd": minimum_seed(config, s, price),
    }


def plant_and_evsi(
    config: dict[str, Any],
    prior: float | None = None,
    sensitivity: float | None = None,
    specificity: float | None = None,
) -> dict[str, Any]:
    plant, test = config["plant"], config["information_experiment"]
    p = test["prior_viable"] if prior is None else prior
    sn = test["sensitivity"] if sensitivity is None else sensitivity
    sp = test["specificity"] if specificity is None else specificity
    annual = plant["annual_gross_saving_eur"] - plant["annual_cash_opex_eur"]
    annuity = sum((1 + plant["discount_rate"]) ** -year for year in range(1, plant["horizon_years"] + 1))
    good = annual * annuity - plant["capex_eur"]
    bad = -test["nonviable_loss_eur"]
    no_test_invest = p * good + (1 - p) * bad
    no_test = max(0.0, no_test_invest)
    branches = []
    for label, joint_good, joint_bad in [
        ("positive", p * sn, (1 - p) * (1 - sp)),
        ("negative", p * (1 - sn), (1 - p) * sp),
    ]:
        probability = joint_good + joint_bad
        posterior = joint_good / probability if probability else 0.0
        invest = posterior * good + (1 - posterior) * bad
        branches.append(
            {
                "signal": label,
                "probability": probability,
                "posterior_viable": posterior,
                "invest_value_eur": invest,
                "action": "INVEST" if invest > 0 else "STOP",
                "best_value_eur": max(0.0, invest),
            }
        )
    after = sum(row["probability"] * row["best_value_eur"] for row in branches)
    fee = test["fee_usd"] / test["usd_per_eur_fixed_scenario"]
    gross = after - no_test
    net = gross - fee - test["delay_cost_eur"]
    return {
        "prior_viable": p,
        "sensitivity": sn,
        "specificity": sp,
        "annual_net_cash_saving_eur": annual,
        "simple_payback_years": plant["capex_eur"] / annual,
        "viable_case_partial_npv_eur": good,
        "nonviable_payoff_eur": bad,
        "no_test_invest_value_eur": no_test_invest,
        "no_test_best_value_eur": no_test,
        "no_test_action": "INVEST" if no_test_invest > 0 else "STOP",
        "signal_branches": branches,
        "expected_best_post_signal_value_eur": after,
        "gross_evsi_eur": gross,
        "fee_eur": fee,
        "delay_cost_eur": test["delay_cost_eur"],
        "net_evsi_eur": net,
        "buy_experiment": net > 0,
        "current_plant_decision": "DEFER: missing specification, long-run pilot and full costs",
        "scope": test["scope"],
        "actual_customer_value_measured": False,
    }


class Campaign:
    def __init__(
        self,
        config: dict[str, Any],
        scenario: dict[str, Any],
        price: float,
        seed: int,
        opening: float | None = None,
        retention: bool = True,
    ) -> None:
        self.c, self.original, self.price = config, scenario, money(price)
        self.rng = random.Random(seed)
        self.shock = self.rng.random() < scenario["common_shock_probability"]
        self.s = state_parameters(config, scenario, self.shock)
        self.opening = money(config["opening_seed_usd"] if opening is None else opening)
        self.cash, self.earned, self.expenses, self.receivables = self.opening, 0, 0, 0
        self.deposits, self.payables, self.module_reserve = 0, 0, 0
        self.fixed = money(config["horizon_weeks"] * config["weekly_overhead_usd"])
        self.buffer = money(config["operating_buffer_usd"])
        self.jobs: list[dict[str, Any]] = []
        self.pending: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.categories: dict[str, int] = {}
        self.counters = dict(
            leads=0,
            bookings=0,
            delivered=0,
            accepted=0,
            collected=0,
            defaults=0,
            refused=0,
            corrected=0,
            adopted=0,
            capacity_declines=0,
            liquidity_declines=0,
            acquisition_stops=0,
        )
        self.week, self.module = 0, None
        self.retention_enabled = retention
        self.minimum_available = 10**18
        self.started = False
        self.retention_decisions: list[dict[str, Any]] = []

    def job_reserve(self) -> int:
        return sum(job["reserve"] for job in self.jobs)

    def available(self) -> int:
        return (
            self.cash
            - self.deposits
            - self.payables
            - self.job_reserve()
            - self.fixed
            - self.buffer
            - self.module_reserve
        )

    def event(
        self,
        label: str,
        cash: int = 0,
        expense: int = 0,
        revenue: int = 0,
        receivable: int = 0,
        category: str = "",
        job_id: str = "",
    ) -> None:
        self.cash += cash
        self.expenses += expense
        self.earned += revenue
        self.receivables += receivable
        if category:
            self.categories[category] = self.categories.get(category, 0) + expense
        available = self.available()
        self.minimum_available = min(self.minimum_available, available)
        self.events.append(
            {
                "week": self.week,
                "event": label,
                "job_id": job_id,
                "cash_delta_usd": cash / 100,
                "expense_delta_usd": expense / 100,
                "earned_revenue_delta_usd": revenue / 100,
                "receivable_delta_usd": receivable / 100,
                "category": category,
                "cash_usd": self.cash / 100,
                "earned_revenue_usd": self.earned / 100,
                "expenses_usd": self.expenses / 100,
                "receivables_usd": self.receivables / 100,
                "refundable_deposits_usd": self.deposits / 100,
                "payables_usd": self.payables / 100,
                "completion_support_reserve_usd": self.job_reserve() / 100,
                "remaining_fixed_obligations_usd": self.fixed / 100,
                "operating_buffer_usd": self.buffer / 100,
                "module_maintenance_reserve_usd": self.module_reserve / 100,
                "available_funds_usd": available / 100,
            }
        )
        if self.started and available < 0:
            raise AssertionError(f"Unfunded cash prefix {self.week} {label}: {available}")

    def book(self) -> None:
        first = self.rng.random() < self.s["first_pass_delivery_probability"]
        rescue = self.rng.random() < self.s["correction_rescue_probability"]
        delivered = first or rescue
        accepted = delivered and self.rng.random() < self.s["acceptance_given_delivery_probability"]
        collected = accepted and self.rng.random() < self.s["collection_given_acceptance_probability"]
        adopted = accepted and self.rng.random() < self.s["buyer_adoption_given_acceptance_probability"]
        fits = self.rng.random() < self.c["retention"]["module_fit_probability"]
        saving = 0.0
        if self.module and self.module["successful"] and self.week >= self.module["ready_week"] and fits:
            saving = self.module["option"]["labor_saving_usd_per_fit_attempt"]
        base, correction, support = job_costs(self.s, saving)
        fee_all = money(self.price / 100 * self.c["payment_fee_fraction"])
        maximum_cost = base + correction + support + fee_all
        if self.available() < maximum_cost:
            self.counters["liquidity_declines"] += 1
            return
        self.counters["bookings"] += 1
        job_id = f"J{self.counters['bookings']:03d}"
        deposit = round(self.price * self.c["deposit_fraction"])
        fee_deposit = round(deposit * self.c["payment_fee_fraction"])
        fee_balance = fee_all - fee_deposit
        first_cost = base // 2
        job = {
            "id": job_id,
            "completion": self.week + (1 if first else 2),
            "first": first,
            "delivered": delivered,
            "accepted": accepted,
            "collected": collected,
            "adopted": adopted,
            "base_due": base - first_cost,
            "correction": correction,
            "support": support,
            "deposit": deposit,
            "fee_balance": fee_balance,
            "reserve": base - first_cost + correction + support + fee_balance,
            "done": False,
            "support_done": False,
            "balance_done": False,
        }
        self.jobs.append(job)
        self.deposits += deposit
        self.event("deposit_received_unearned", cash=deposit, job_id=job_id)
        self.event("delivery_start", cash=-first_cost, expense=first_cost, category="delivery_base", job_id=job_id)
        self.event(
            "deposit_processing_fee", cash=-fee_deposit, expense=fee_deposit, category="payment_fees", job_id=job_id
        )

    def complete(self, job: dict[str, Any]) -> None:
        job["done"] = True
        job_id = job["id"]
        base = job["base_due"]
        job["reserve"] -= base
        self.payables += base
        self.pending.append({"week": self.week + 1, "amount": base, "job_id": job_id})
        self.event("delivery_balance_accrued", expense=base, category="delivery_base", job_id=job_id)
        correction = job["correction"] if not job["first"] else 0
        job["reserve"] -= job["correction"]
        if correction:
            self.counters["corrected"] += 1
            self.event("correction", cash=-correction, expense=correction, category="correction", job_id=job_id)
        else:
            self.event("unused_correction_reserve_released", job_id=job_id)
        self.counters["delivered"] += int(job["delivered"])
        self.deposits -= job["deposit"]
        if job["accepted"]:
            self.counters["accepted"] += 1
            self.counters["adopted"] += int(job["adopted"])
            self.event("accepted_fee_earned", revenue=self.price, receivable=self.price - job["deposit"], job_id=job_id)
        else:
            self.counters["refused"] += 1
            job["reserve"] -= job["fee_balance"]
            job["balance_done"] = True
            self.event("unaccepted_deposit_refunded", cash=-job["deposit"], job_id=job_id)

    def settle(self) -> None:
        for item in self.pending[:]:
            if item["week"] == self.week:
                self.payables -= item["amount"]
                self.event("payable_paid", cash=-item["amount"], job_id=item["job_id"])
                self.pending.remove(item)
        for job in self.jobs:
            if not job["done"] and job["completion"] == self.week:
                self.complete(job)
            if (
                job["done"]
                and not job["balance_done"]
                and self.week == job["completion"] + self.c["collection_delay_weeks"]
            ):
                balance = self.price - job["deposit"]
                job["balance_done"] = True
                job["reserve"] -= job["fee_balance"]
                if job["collected"]:
                    self.counters["collected"] += 1
                    self.event("balance_collected", cash=balance, receivable=-balance, job_id=job["id"])
                    self.event(
                        "balance_processing_fee",
                        cash=-job["fee_balance"],
                        expense=job["fee_balance"],
                        category="payment_fees",
                        job_id=job["id"],
                    )
                else:
                    self.counters["defaults"] += 1
                    self.event(
                        "receivable_written_off",
                        expense=balance,
                        receivable=-balance,
                        category="bad_debt",
                        job_id=job["id"],
                    )
            if (
                job["done"]
                and not job["support_done"]
                and self.week == job["completion"] + self.c["support_delay_weeks"]
            ):
                job["support_done"] = True
                job["reserve"] -= job["support"]
                self.event(
                    "support_obligation_completed",
                    cash=-job["support"],
                    expense=job["support"],
                    category="support",
                    job_id=job["id"],
                )

    def maybe_retain(self) -> None:
        if not self.retention_enabled or self.module or not self.counters["adopted"]:
            return
        if plant_and_evsi(self.c)["net_evsi_eur"] <= 0:
            return
        remaining = self.c["horizon_weeks"] - self.week - self.c["retention"]["build_weeks"]
        if remaining <= 0:
            return
        arrivals = self.s["leads_per_week"] * booking_probability(self.c, self.s, self.price / 100)
        capacity = self.c["slots"] / (2 - self.s["first_pass_delivery_probability"])
        uses = remaining * min(arrivals, capacity) * self.c["retention"]["module_fit_probability"]
        free_surplus = self.available() - self.opening
        unit = unit_economics(self.c, self.s, self.price / 100)
        lost_bookings = (
            max(0, arrivals - (self.c["slots"] - 1) / (2 - self.s["first_pass_delivery_probability"]))
            * self.c["retention"]["build_weeks"]
        )
        foregone_margin = lost_bookings * max(0, unit["expected_earned_revenue_usd"] - unit["expected_job_expense_usd"])
        alternatives = []
        for option in self.c["retention"]["options"]:
            bill = option["construction_ceiling_usd"] + option["maintenance_ceiling_usd"]
            expected_benefit = (
                uses * option["labor_saving_usd_per_fit_attempt"] * option["technical_success_probability"]
                - bill
                - foregone_margin
            )
            self.retention_decisions.append(
                {
                    "week": self.week,
                    "option": option["id"],
                    "assumed_fit_uses": uses,
                    "foregone_capacity_margin_usd": foregone_margin,
                    "expected_incremental_benefit_usd": expected_benefit,
                    "required_funds_usd": bill,
                    "available_surplus_usd": free_surplus / 100,
                    "financeable": free_surplus >= money(bill),
                    "positive_expected_benefit": expected_benefit > 0,
                }
            )
            if expected_benefit > 0 and free_surplus >= money(bill):
                alternatives.append((expected_benefit, option))
        if not alternatives:
            return
        benefit, option = max(alternatives, key=lambda item: (item[0], -item[1]["construction_ceiling_usd"]))
        self.module = {
            "option": option,
            "ready_week": self.week + self.c["retention"]["build_weeks"],
            "successful": self.rng.random() < option["technical_success_probability"],
            "admission_week": self.week,
            "assumed_remaining_fit_uses": uses,
            "expected_incremental_benefit_usd": benefit,
            "surplus_before_usd": free_surplus / 100,
        }
        cost = money(option["construction_ceiling_usd"])
        self.module_reserve = money(option["maintenance_ceiling_usd"])
        self.event("optional_module_construction", cash=-cost, expense=cost, category="optional_construction")

    def run(self) -> dict[str, Any]:
        startup = money(sum(self.c["startup_costs_usd"].values()))
        if self.opening < startup + self.fixed + self.buffer:
            self.fixed = 0
            self.event("REFUSE_UNFUNDED_CAMPAIGN")
            return self.summary(refused=True)
        self.started = True
        self.event("opening_cash_and_obligations")
        self.event("commercial_startup", cash=-startup, expense=startup, category="startup")
        for self.week in range(self.c["horizon_weeks"] + 7):
            self.settle()
            if self.week < self.c["horizon_weeks"]:
                fixed = money(self.c["weekly_overhead_usd"])
                self.fixed -= fixed
                self.event("weekly_committed_overhead", cash=-fixed, expense=fixed, category="overhead")
                self.maybe_retain()
                slots = self.c["slots"]
                if self.module and self.week < self.module["ready_week"]:
                    slots -= 1
                for _ in range(self.s["leads_per_week"]):
                    lead = money(self.s["lead_cost_usd"])
                    if self.available() < lead:
                        self.counters["acquisition_stops"] += 1
                        continue
                    self.counters["leads"] += 1
                    self.event("qualified_lead_acquisition", cash=-lead, expense=lead, category="acquisition")
                    if self.rng.random() >= booking_probability(self.c, self.s, self.price / 100):
                        continue
                    active = sum(not job["done"] for job in self.jobs)
                    if active >= slots:
                        self.counters["capacity_declines"] += 1
                        continue
                    self.book()
        if self.module_reserve:
            cost, self.module_reserve = self.module_reserve, 0
            self.event("incremental_module_maintenance", cash=-cost, expense=cost, category="optional_maintenance")
        assert self.payables == self.deposits == self.receivables == self.fixed == self.job_reserve() == 0
        assert self.cash - self.opening == self.earned - self.expenses
        assert sum(self.categories.values()) == self.expenses
        assert self.cash >= self.buffer
        self.event("complete_winddown")
        return self.summary()

    def summary(self, refused: bool = False) -> dict[str, Any]:
        profit = (self.earned - self.expenses) / 100
        startup = self.categories.get("startup", 0) / 100
        fixed = self.categories.get("overhead", 0) / 100
        optional = (
            self.categories.get("optional_construction", 0) + self.categories.get("optional_maintenance", 0)
        ) / 100
        return {
            "scenario": self.original["id"],
            "common_shock": self.shock,
            "price_usd": self.price / 100,
            "opening_seed_usd": self.opening / 100,
            "unfunded_refusal": refused,
            **self.counters,
            "earned_revenue_usd": self.earned / 100,
            "complete_expenses_usd": self.expenses / 100,
            "full_project_profit_usd": profit,
            "operating_before_startup_and_optional_usd": profit + startup + optional,
            "contribution_before_fixed_and_startup_usd": profit + startup + fixed + optional,
            "terminal_cash_usd": self.cash / 100,
            "terminal_available_funds_usd": self.available() / 100,
            "available_above_seed_and_reserves_usd": max(0, self.available() - self.opening) / 100,
            "minimum_available_funds_usd": self.minimum_available / 100,
            "full_project_return_on_seed": profit / (self.opening / 100) if self.opening else None,
            "optional_module": self.module["option"]["id"] if self.module else "STOP",
            "optional_module_success": self.module["successful"] if self.module else None,
            "optional_admission_week": self.module["admission_week"] if self.module else None,
            "categories_usd": {key: value / 100 for key, value in self.categories.items()},
        }


def develop(config: dict[str, Any], out: Path) -> None:
    price_rows, unit_rows = [], []
    candidates = []
    for price in config["price_candidates_usd"]:
        weighted = 0.0
        eligible = True
        for scenario in config["scenarios"]:
            sp = scenario["common_shock_probability"]
            scenario_profit = 0.0
            for shock in (False, True):
                s = state_parameters(config, scenario, shock)
                weight = sp if shock else 1 - sp
                plan = planning_profit(config, s, price)
                scenario_profit += weight * plan["full_project_profit_usd"]
                eligible &= minimum_seed(config, s, price) <= config["opening_seed_usd"]
                price_rows.append({"scenario": scenario["id"], "shock": shock, "price_usd": price, **plan})
                unit_rows.append({"scenario": scenario["id"], "shock": shock, **unit_economics(config, s, price)})
            weighted += scenario["development_weight"] * scenario_profit
        candidates.append(
            {
                "price_usd": price,
                "weighted_expected_full_project_profit_usd": weighted,
                "first_job_financeable_all_declared_states": eligible,
            }
        )
    valid = [
        candidate
        for candidate in candidates
        if candidate["first_job_financeable_all_declared_states"]
        and candidate["weighted_expected_full_project_profit_usd"] > 0
    ]
    selected = (
        max(valid, key=lambda row: (row["weighted_expected_full_project_profit_usd"], -row["price_usd"]))
        if valid
        else None
    )
    policy = {
        "schema": "agialpha.price-policy.v1",
        "selected_price_usd": selected["price_usd"] if selected else None,
        "candidates": candidates,
        "rule": config["price_policy"],
        "limitations": "Analytical planning uses expected load and capacity, and full planned acquisition. Fresh campaigns enforce every cash prefix and may curtail acquisition; these development estimates are not observed operating outcomes.",
    }
    write_json(out / "economics_policy.json", policy)
    csv_write(out / "economics_development.csv", price_rows)
    csv_write(out / "economics_unit.csv", unit_rows)
    write_json(out / "economics_customer_evsi.json", plant_and_evsi(config))
    evsi_rows = []
    test = config["information_experiment"]
    for p in test["priors"]:
        for sn in test["sensitivities"]:
            for sp in test["specificities"]:
                row = plant_and_evsi(config, p, sn, sp)
                evsi_rows.append(
                    {
                        key: value
                        for key, value in row.items()
                        if key not in ["signal_branches", "scope", "current_plant_decision"]
                    }
                )
    csv_write(out / "economics_evsi_sensitivity.csv", evsi_rows)
    print(json.dumps(policy, indent=2))


def freeze(config_path: Path, out: Path) -> None:
    paths = [Path(__file__).resolve(), config_path.resolve(), out / "economics_policy.json"]
    payload = {
        "schema": "agialpha.economics.freeze.v1",
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "after deterministic policy selection and before fresh confirmation histories",
        "source_and_input_sha256": {str(path.relative_to(ROOT)): digest(path) for path in paths},
        "claim": "Byte commitment and recorded workflow ordering; not independent timestamp certification.",
    }
    write_json(out / "economics_FREEZE.json", payload)
    print(json.dumps(payload, indent=2))


def quantile(values: list[float], q: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * q
    low, high = math.floor(index), math.ceil(index)
    return values[low] * (high - index) + values[high] * (index - low) if high > low else values[low]


def confirm(config: dict[str, Any], out: Path) -> None:
    frozen = json.loads((out / "economics_FREEZE.json").read_text())
    for path, expected in frozen["source_and_input_sha256"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen source/input changed: " + path)
    policy = json.loads((out / "economics_policy.json").read_text())
    price = policy["selected_price_usd"]
    if price is None:
        write_json(out / "economics_summary.json", {"decision": "STOP_NO_ELIGIBLE_PRICE"})
        return
    worlds, events, optional_controls, retention_decisions = [], [], [], []
    for scenario_index, scenario in enumerate(config["scenarios"]):
        for world in range(config["confirmation_worlds_per_scenario"]):
            seed = config["confirmation_seed"] + scenario_index * 100000 + world
            campaign = Campaign(config, scenario, price, seed)
            result = campaign.run()
            retention_decisions.extend(
                {"scenario": scenario["id"], "world_id": world, **row} for row in campaign.retention_decisions
            )
            result["world_id"] = world
            worlds.append(result)
            for index, event in enumerate(campaign.events):
                events.append({"scenario": scenario["id"], "world_id": world, "event_index": index, **event})
            baseline = Campaign(config, scenario, price, seed, retention=False)
            base = baseline.run()
            optional_controls.append(
                {
                    "scenario": scenario["id"],
                    "world_id": world,
                    "with_optional_profit_usd": result["full_project_profit_usd"],
                    "without_optional_profit_usd": base["full_project_profit_usd"],
                    "difference_usd": result["full_project_profit_usd"] - base["full_project_profit_usd"],
                    "note": "Shared seed, but module RNG and capacity alter later paths; not paired causal efficacy evidence.",
                }
            )
    summary = {
        "selected_price_usd": price,
        "world_count": len(worlds),
        "weeks": config["horizon_weeks"],
        "external_seed_usd": config["opening_seed_usd"],
        "actual_collections_usd": 0,
        "actual_complete_cost_usd": None,
        "actual_profit_usd": None,
        "maximum_capital_at_risk_usd": config["opening_seed_usd"] - config["operating_buffer_usd"],
        "customer_field_experiment": plant_and_evsi(config),
        "scenarios": {},
        "cash_conservation_checks": len(worlds),
        "minimum_available_all_worlds_usd": min(row["minimum_available_funds_usd"] for row in worlds),
        "retention_evidence": "Assumed savings only. Ordinary-library identical-asset economics are exactly equal by specification; no measured retained Alpha.",
        "observations": config["observation_boundaries"],
    }
    for scenario in config["scenarios"]:
        subset = [row for row in worlds if row["scenario"] == scenario["id"]]
        profit = [row["full_project_profit_usd"] for row in subset]
        result = {
            "mean_profit_usd": statistics.mean(profit),
            "median_profit_usd": statistics.median(profit),
            "p05_profit_usd": quantile(profit, 0.05),
            "p95_profit_usd": quantile(profit, 0.95),
            "minimum_profit_usd": min(profit),
            "maximum_profit_usd": max(profit),
            "profitable_fraction": sum(value > 0 for value in profit) / len(profit),
            "mean_bookings": statistics.mean(row["bookings"] for row in subset),
            "mean_accepted": statistics.mean(row["accepted"] for row in subset),
            "mean_collected_full_balances": statistics.mean(row["collected"] for row in subset),
            "mean_terminal_cash_usd": statistics.mean(row["terminal_cash_usd"] for row in subset),
            "mean_available_funds_usd": statistics.mean(row["terminal_available_funds_usd"] for row in subset),
            "mean_available_surplus_above_seed_and_reserves_usd": statistics.mean(
                row["available_above_seed_and_reserves_usd"] for row in subset
            ),
            "optional_investments": sum(row["optional_module"] != "STOP" for row in subset),
            "optional_technical_failures": sum(row["optional_module_success"] is False for row in subset),
            "minimum_seed_first_job_no_shock_usd": minimum_seed(
                config, state_parameters(config, scenario, False), price
            ),
            "minimum_seed_first_job_common_shock_usd": minimum_seed(
                config, state_parameters(config, scenario, True), price
            ),
            "zero_seed_decision": Campaign(config, scenario, price, 1, opening=0).run()["unfunded_refusal"],
        }
        controls = [row["difference_usd"] for row in optional_controls if row["scenario"] == scenario["id"]]
        result["optional_vs_disabled_mean_difference_usd"] = statistics.mean(controls)
        summary["scenarios"][scenario["id"]] = result
    csv_write(out / "economics_worlds.csv", [{k: v for k, v in row.items() if k != "categories_usd"} for row in worlds])
    csv_write(out / "economics_cash_ledgers.csv", events)
    csv_write(out / "economics_optional_controls.csv", optional_controls)
    csv_write(out / "economics_retention_decisions.csv", retention_decisions)
    write_json(out / "economics_full_world_records.json", worlds)
    write_json(out / "economics_summary.json", summary)
    sensitivity(config, price, out)
    print(json.dumps(summary, indent=2))


def sensitivity(config: dict[str, Any], price: float, out: Path) -> None:
    center = config["scenarios"][1]
    rows = []
    changes = {
        "labor_hours": [0, 4, 8, 12, 16, 24],
        "leads_per_week": [1, 2, 3, 4, 6],
        "acceptance_given_delivery_probability": [0.6, 0.75, 0.85, 0.95, 0.99],
        "collection_given_acceptance_probability": [0.6, 0.8, 0.9, 0.97, 1.0],
        "lead_cost_usd": [40, 80, 160, 320, 640],
        "model_allowance_usd": [25, 100, 300, 700, 1500],
    }
    for parameter, values in changes.items():
        for value in values:
            s = deepcopy(center)
            s[parameter] = value
            s = state_parameters(config, s, False)
            unit, plan = unit_economics(config, s, price), planning_profit(config, s, price)
            rows.append(
                {
                    "parameter": parameter,
                    "value": value,
                    "price_usd": price,
                    "expected_unit_contribution_usd": unit["expected_contribution_usd"],
                    **plan,
                }
            )
    csv_write(out / "economics_sensitivity.csv", rows)


def selfcheck(config: dict[str, Any], out: Path) -> None:
    checks = []
    report = plant_and_evsi(config)
    checks.append(
        {
            "name": "payback_depreciation_not_double_counted",
            "pass": abs(report["simple_payback_years"] - 180000 / 53370) < 1e-12,
        }
    )
    checks.append(
        {
            "name": "perfect_information_bound",
            "pass": 0 <= report["gross_evsi_eur"] <= 0.5 * report["viable_case_partial_npv_eur"],
        }
    )
    for scenario in config["scenarios"]:
        campaign = Campaign(config, scenario, 2500, config["development_seed"])
        result = campaign.run()
        checks.append(
            {
                "name": scenario["id"] + "_cash_and_expense_conservation",
                "pass": result["minimum_available_funds_usd"] >= 0,
            }
        )
        refused = Campaign(config, scenario, 2500, 1, opening=0).run()
        checks.append(
            {
                "name": scenario["id"] + "_zero_seed_refusal",
                "pass": refused["unfunded_refusal"] and refused["earned_revenue_usd"] == 0,
            }
        )
    write_json(
        out / "economics_development_checks.json", {"checks": checks, "all_passed": all(row["pass"] for row in checks)}
    )
    if not all(row["pass"] for row in checks):
        raise AssertionError("Development check failed")
    print(json.dumps({"checks": len(checks), "all_passed": True}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["selfcheck", "develop", "freeze", "confirm"])
    parser.add_argument("--config", type=Path, default=ROOT / "inputs/economics.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = json.loads(args.config.read_text())
    if args.phase == "freeze":
        freeze(args.config, args.output)
    elif args.phase == "develop":
        develop(config, args.output)
    elif args.phase == "confirm":
        confirm(config, args.output)
    else:
        selfcheck(config, args.output)


if __name__ == "__main__":
    main()
