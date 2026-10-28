# SPDX-License-Identifier: Apache-2.0
"""Frozen, stateful commercial hypotheses; never actual money or customer evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

Json = dict[str, Any]
ACCOUNTS = ("cash", "ar", "asset", "custody", "payable", "debt")


def uniform(seed: int, *labels: object) -> float:
    """Keyed exogenous draws preserve common random numbers across policies."""
    key = "|".join(map(str, (seed, *labels))).encode()
    return (int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big") + 0.5) / 2**64


def normal(seed: int, *labels: object) -> float:
    a = max(uniform(seed, *labels, "n1"), 1e-15)
    return math.sqrt(-2 * math.log(a)) * math.cos(2 * math.pi * uniform(seed, *labels, "n2"))


def money(value: float) -> int:
    return int(round(value))


def read_config(path: Path) -> Json:
    value: Json = json.loads(path.read_text())
    if value["currency"] != "USD" or value["months"] != 24:
        raise ValueError("This frozen protocol requires USD and a 24-month operating horizon")
    return value


class Books:
    """Integer-cent double-entry events with distinct refundable custody."""

    def __init__(self, initial_equity: int, credit_limit: int, trace: bool) -> None:
        self.balances = dict.fromkeys(ACCOUNTS, 0)
        self.equity = 0
        self.profit = 0
        self.revenue = 0
        self.expense = 0
        self.month = 0
        self.credit_limit = credit_limit
        self.insolvent_month: int | None = None
        self.peak_unfunded = 0
        self.minimum_available = initial_equity
        self.trace = trace
        self.events: list[Json] = []
        self.monthly: list[Json] = []
        self.flows: defaultdict[str, int] = defaultdict(int)
        self.categories: defaultdict[str, int] = defaultdict(int)
        self.opening = self.balances.copy()
        self.book("owner_equity", cash=initial_equity, equity=initial_equity)

    @property
    def available(self) -> int:
        return self.balances["cash"] - self.balances["custody"]

    def book(self, kind: str, revenue: int = 0, expense: int = 0, equity: int = 0, **delta: int) -> None:
        if not all(type(x) is int for x in (*delta.values(), revenue, expense, equity)):
            raise ValueError("All money must be exact integer cents")
        for account, amount in delta.items():
            if account not in ACCOUNTS:
                raise ValueError("Unknown account")
            self.balances[account] += amount
            self.flows[account + "_change"] += amount
        self.profit += revenue - expense
        self.revenue += revenue
        self.expense += expense
        self.equity += equity
        self.flows["revenue"] += revenue
        self.flows["expense"] += expense
        self.flows["equity"] += equity
        self.categories[kind] += expense
        net_assets = sum(self.balances[x] for x in ("cash", "ar", "asset"))
        liabilities = sum(self.balances[x] for x in ("custody", "payable", "debt"))
        if net_assets - liabilities != self.equity + self.profit:
            raise ArithmeticError(f"Balance-sheet disagreement at {kind}")
        if min(self.balances.values()) < 0 or self.available < 0:
            raise ArithmeticError(f"Negative balance or spending of custody at {kind}")
        self.minimum_available = min(self.minimum_available, self.available)
        if self.trace:
            self.events.append({"month": self.month, "kind": kind, "delta": delta, "revenue": revenue,
                                "expense": expense, "equity": equity, "balances": self.balances.copy()})

    def fund(self, due: int) -> int:
        gap = max(0, due - self.available)
        draw = min(gap, max(0, self.credit_limit - self.balances["debt"]))
        if draw:
            self.book("finite_credit_draw", cash=draw, debt=draw)
        gap = max(0, due - self.available)
        self.peak_unfunded = max(self.peak_unfunded, gap)
        if gap and self.insolvent_month is None:
            self.insolvent_month = self.month
        return min(due, self.available)

    def charge(self, kind: str, amount: int, capitalize: bool = False) -> None:
        if amount < 0:
            raise ValueError("Negative charge")
        paid = self.fund(amount)
        self.book(kind, expense=0 if capitalize else amount, cash=-paid, payable=amount - paid,
                  asset=amount if capitalize else 0)

    def collect(self, amount: int, processor_fraction: float, processor_fixed: int) -> None:
        self.book("invoice_collection", cash=amount, ar=-amount)
        self.charge("payment_processing", money(amount * processor_fraction) + processor_fixed)

    def refund(self, invoice: Json) -> None:
        outstanding = invoice["outstanding"]
        cash_due = invoice["price"] - outstanding
        paid = self.fund(cash_due)
        self.book("accepted_delivery_refund", revenue=-invoice["price"], ar=-outstanding,
                  cash=-paid, payable=cash_due - paid)
        invoice["outstanding"] = 0
        invoice["refunded"] = True

    def settle_payable(self) -> None:
        payment = min(self.available, self.balances["payable"])
        if payment:
            self.book("past_due_obligation_payment", cash=-payment, payable=-payment)

    def close_month(self, **extra: Any) -> None:
        row: Json = {"month": self.month, **extra, **self.flows, "cumulative_profit": self.profit}
        for account in ACCOUNTS:
            row[account + "_open"] = self.opening[account]
            row[account + "_close"] = self.balances[account]
            row.setdefault(account + "_change", 0)
        for field in ("revenue", "expense", "equity"):
            row.setdefault(field, 0)
        self.monthly.append(row)
        self.opening = self.balances.copy()
        self.flows.clear()


def buyers(config: Json, seed: int) -> list[Json]:
    result = []
    for group, segment in enumerate(config["segments"]):
        count = money(config["market_buyers"] * segment["fraction"])
        for i in range(count):
            identity = f"{segment['prefix']}-{i + 1:03d}"
            factor = math.exp(config["buyer_log_dispersion"] * normal(seed, identity, "resources"))
            result.append({"id": identity, "segment": group,
                           "value": money(segment["value_cents"] * factor),
                           "budget": money(segment["budget_cents"] * factor),
                           "diy_cost": money(segment["diy_cost_cents"] * factor),
                           "aware": uniform(seed, identity, "aware") < config["initial_awareness_fraction"],
                           "last_choice": "none", "accepted": 0, "failed": 0})
    return result


def run_world(config: Json, policy: Json, scenario_name: str, seed: int, trace: bool = False) -> Json:
    """Operate one economy; all participant preferences are authored hypotheses."""
    scenario = config["scenarios"][scenario_name]
    books = Books(config["equity_cents"], config["credit_limit_cents"], trace)
    identities = buyers(config, seed)
    decisions: list[Json] = []
    invoices: list[Json] = []
    counters: defaultdict[str, int] = defaultdict(int)
    operational = policy["mode"] != "stop"
    closed_month: int | None = 0 if not operational else None
    labor = scenario.get("labor_cost_multiplier", 1.0)
    engineering_rate = config["engineering_hour_cents"] * labor
    ops_rate = config["operations_hour_cents"] * labor
    fixed = money(config["maintenance_hours_month"] * engineering_rate
                  + (config["administration_hours_month"] + config["sales_hours_month"]) * ops_rate
                  + config["hosting_cents_month"] + config["accounting_insurance_cents_month"])
    startup = money(config["startup_development_hours"] * engineering_rate + config["startup_administration_cents"])
    if operational:
        books.charge("startup_development_and_administration", startup)
        books.charge("equipment_purchase", config["equipment_cents"], capitalize=True)
    books.close_month(active=int(operational), **dict(counters))
    competitor_price = money(config["competitor_initial_price_cents"]
                             * scenario.get("competitor_initial_price_multiplier", 1.0))
    competitor_coverage = scenario.get("competitor_initial_coverage", config["competitor_initial_coverage"])
    competitor_distribution = config["competitor_initial_distribution"]
    competitor_quality = config["competitor_initial_quality"]
    prior_share = 0.0
    direct_expense = 0
    tax_paid = 0
    collections = 0
    cash_refunds = 0
    qualifying_need_total = 0
    accepted_last_month = 0
    active_months = 0
    paid_unique: set[str] = set()
    cumulative_cash_flow = -(startup + config["equipment_cents"]) if operational else 0
    payback_month: int | None = None
    cash_flow_after_month12 = 0
    maximum_review_hours = 0.0
    first_accepted_month: dict[str, int] = {}
    last_accepted_month: dict[str, int] = {}
    customer_contribution: defaultdict[str, int] = defaultdict(int)
    monthly_profit_history: list[int] = []
    for month in range(1, config["months"] + config["runoff_months"] + 1):
        books.month = month
        cash_start = books.balances["cash"]
        debt_start = books.balances["debt"]
        profit_start = books.profit
        accepted_this_month = 0
        need_this_month = 0
        operated_this_month = False
        if operational and (books.insolvent_month is not None or month > config["months"]):
            operational = False
            closed_month = month
        for invoice in invoices:
            if invoice["refunded"]:
                continue
            if month == invoice["accepted_month"] + 1 and invoice["complaint"]:
                previously_collected = invoice["price"] - invoice["outstanding"]
                books.refund(invoice)
                cash_refunds += previously_collected
                counters["post_acceptance_refunds"] += 1
                customer_contribution[invoice["buyer"]] -= invoice["price"]
                continue
            if invoice["outstanding"] and month >= invoice["due"]:
                amount = invoice["outstanding"]
                if invoice["default"]:
                    books.book("bad_debt", expense=amount, ar=-amount)
                    counters["defaults"] += 1
                    direct_expense += amount
                    customer_contribution[invoice["buyer"]] -= amount
                else:
                    books.collect(amount, config["processor_fraction"], config["processor_fixed_cents"])
                    collections += amount
                    fee = money(amount * config["processor_fraction"]) + config["processor_fixed_cents"]
                    direct_expense += fee
                    customer_contribution[invoice["buyer"]] -= fee
                invoice["outstanding"] = 0
        books.settle_payable()
        if operational and books.available < fixed + policy["marketing_cents_month"] + policy["cash_reserve_cents"]:
            operational = False
            closed_month = month
            counters["cash_preserving_shutdowns"] += 1
        if operational:
            operated_this_month = True
            active_months += 1
            books.charge("recurring_engineering_admin_sales_hosting", fixed)
            books.charge("customer_acquisition", policy["marketing_cents_month"])
            if month in (12, 24):
                books.charge("annual_capability_requalification", money(8 * engineering_rate))
            if prior_share > config["competitor_response_share"]:
                competitor_price = max(config["competitor_floor_price_cents"],
                                       money(competitor_price * config["competitor_response_price_fraction"]))
                competitor_coverage = min(0.99, competitor_coverage + config["competitor_imitation_increment"])
                competitor_quality = min(0.98, competitor_quality + 0.006)
                counters["competitor_responses"] += 1
            competitor_coverage = min(0.99, competitor_coverage + config["competitor_learning_month"]
                                      * scenario.get("competitor_learning_multiplier", 1.0))
            competitor_distribution = min(0.98, competitor_distribution + config["competitor_distribution_growth"])
            unknown = [b for b in identities if not b["aware"]]
            new_awareness = (policy["marketing_cents_month"] / 100 * config["awareness_per_marketing_dollar"]
                             + config["organic_awareness_per_month"]
                             + accepted_last_month * config["word_of_mouth_per_acceptance"])
            new_awareness *= scenario.get("awareness_multiplier", 1.0)
            unknown.sort(key=lambda b: uniform(seed, month, b["id"], "marketing"))
            for buyer in unknown[:money(new_awareness)]:
                buyer["aware"] = True
                counters["acquired_awareness"] += 1
            supplier_outage = uniform(seed, month, "outage") < scenario.get(
                "outage_probability", config["supplier_outage_probability"])
            capacity = config["supplier_review_hours_month"] * scenario.get("capacity_multiplier", 1.0)
            if supplier_outage:
                capacity *= config["supplier_outage_capacity_fraction"]
                counters["supplier_outage_months"] += 1
            used_hours = 0.0
            supplier_price = ((1 + config["supplier_annual_inflation"]) ** ((month - 1) / 12)
                              * scenario.get("supplier_cost_multiplier", 1.0))
            monthly_demand_factor = (0.75 + 0.50 * uniform(seed, month, "demand_shock"))
            order = sorted(identities, key=lambda b: uniform(seed, month, b["id"], "request_order"))
            for buyer in order:
                identity = buyer["id"]
                segment = config["segments"][buyer["segment"]]
                if buyer["aware"] and uniform(seed, month, identity, "forget") < config["awareness_decay_month"]:
                    buyer["aware"] = False
                probability = segment["monthly_need"] * monthly_demand_factor * scenario.get("demand_multiplier", 1.0)
                if uniform(seed, month, identity, "need") >= probability:
                    continue
                need_this_month += 1
                counters["market_needs"] += 1
                if not buyer["aware"] or (policy["industrial_only"] and buyer["segment"] != 1):
                    counters["unreached_or_untargeted_needs"] += 1
                    continue
                counters["reached_needs"] += 1
                if uniform(seed, month, identity, "scope") > segment["in_scope_probability"]:
                    counters["out_of_scope_refusals"] += 1
                    if trace:
                        decisions.append({"month": month, "buyer": identity, "decision": "refuse_scope",
                                          "reason": "Oversized or semantically unsuitable requests are not sold"})
                    continue
                qualifying_need_total += 1
                units = 1 + int(uniform(seed, month, identity, "bundle") < segment["second_outcome_probability"])
                if policy["mode"] != "subscription":
                    units = 1
                value = buyer["value"] * units
                budget = buyer["budget"] * (1.0 if units == 1 else 1.45)
                diy_utility = segment["diy_reliability"] * value - buyer["diy_cost"] * units
                competitor_available = (uniform(seed, month, identity, "comp_distribution") < competitor_distribution
                                        and uniform(seed, month, identity, "comp_coverage") < competitor_coverage)
                comp_utility = (competitor_quality * value - competitor_price * units
                                - config["buyer_competitor_integration_cents"]) if competitor_available else -float("inf")
                outside = max(0.0, diy_utility, comp_utility)
                integration = config["buyer_repeat_vendor_integration_cents"] if buyer["accepted"] else config[
                    "buyer_new_vendor_integration_cents"]
                perceived_quality = max(0.70, config["accepted_quality_probability"] - 0.04 * buyer["failed"])
                willingness = max(0, min(budget, perceived_quality * value - integration - outside))
                price = policy["price_cents"]
                if willingness < price and uniform(seed, month, identity, "negotiate") < config["negotiation_fraction"]:
                    reduced = money(price * (1 - policy["discount_fraction"]))
                    if willingness >= reduced:
                        price = reduced
                        counters["negotiated_orders"] += 1
                churn = (buyer["last_choice"] == "ours" and uniform(seed, month, identity, "churn")
                         < config["buyer_churn_probability"])
                record = {"month": month, "buyer": identity, "segment": segment["name"], "units": units,
                          "value_cents": value, "budget_cents": money(budget), "price_cents": price,
                          "maximum_willing_cents": money(willingness), "outside_utility_cents": money(outside)}
                if willingness < price or churn:
                    buyer["last_choice"] = "competitor" if comp_utility >= max(0, diy_utility) else "DIY_or_abstain"
                    counters["buyer_refusals"] += 1
                    if churn:
                        counters["churn_events"] += 1
                    if trace:
                        decisions.append({**record, "decision": buyer["last_choice"]})
                    continue
                review_hours = policy["review_hours"] * units
                retries = uniform(seed, month, identity, "retry") < config["retry_probability"]
                review_hours *= 1 + int(retries) * config["retry_cost_fraction"]
                variable = money(review_hours * engineering_rate * supplier_price
                                 + policy["support_hours"] * ops_rate * units)
                compute = money(config["compute_seconds_per_attempt"] * config["compute_gb"]
                                * config["compute_usd_per_gb_second"] * 100 * (1 + int(retries)) * units * supplier_price)
                variable += compute + config["delivery_storage_cents"] * units
                deposit = money(price * policy["advance_fraction"])
                initial_fee = money(deposit * config["processor_fraction"]) + config["processor_fixed_cents"]
                if used_hours + review_hours > capacity or books.available < variable + initial_fee + policy["cash_reserve_cents"]:
                    counters["capacity_or_cash_refusals"] += 1
                    if trace:
                        decisions.append({**record, "decision": "capacity_or_cash_refusal"})
                    continue
                books.book("refundable_customer_advance", cash=deposit, custody=deposit)
                books.charge("payment_processing", initial_fee)
                books.charge("execution_verification_support_retries", variable)
                direct_expense += variable + initial_fee
                customer_contribution[identity] -= variable + initial_fee
                used_hours += review_hours
                counters["orders"] += 1
                counters["retries"] += int(retries)
                success = uniform(seed, month, identity, "acceptance") < config["accepted_quality_probability"]
                if not success and retries:
                    success = uniform(seed, month, identity, "retry_recovery") < 0.70
                if not success:
                    books.book("rejected_delivery_deposit_return", cash=-deposit, custody=-deposit)
                    counters["delivery_rejections"] += 1
                    buyer["failed"] += 1
                    buyer["last_choice"] = "rejected"
                    if trace:
                        decisions.append({**record, "decision": "delivery_rejected_refunded"})
                    continue
                books.book("accepted_delivery_earned", revenue=price, custody=-deposit, ar=price - deposit)
                collections += deposit
                buyer["accepted"] += 1
                buyer["last_choice"] = "ours"
                customer_contribution[identity] += price
                first_accepted_month.setdefault(identity, month)
                last_accepted_month[identity] = month
                paid_unique.add(identity)
                accepted_this_month += 1
                counters["accepted_orders"] += 1
                counters["accepted_outcomes"] += units
                if buyer["accepted"] > 1:
                    counters["repeat_accepted_orders"] += 1
                default = uniform(seed, month, identity, "default") < scenario.get(
                    "default_probability", config["invoice_default_probability"])
                delay = config["default_delay_months"] + scenario.get("payment_delay_months", 0)
                delay += int(uniform(seed, month, identity, "extra_delay") < config["extra_delay_probability"])
                invoices.append({"buyer": identity, "price": price, "outstanding": price - deposit,
                                 "accepted_month": month, "due": month + delay, "default": default,
                                 "complaint": uniform(seed, month, identity, "complaint")
                                 < config["post_acceptance_refund_probability"], "refunded": False})
                if trace:
                    decisions.append({**record, "decision": "accepted", "variable_cost_cents": variable,
                                      "deposit_cents": deposit, "invoice_due_month": month + delay})
            prior_share = accepted_this_month / max(1, need_this_month)
            maximum_review_hours = max(maximum_review_hours, used_hours)
        elif policy["mode"] != "stop" and (books.balances["ar"] or books.balances["payable"]
                                           or (closed_month is not None and month <= closed_month + 1)):
            books.charge("runoff_administration", config["settlement_admin_cents_month"])
        if books.balances["asset"]:
            depreciation = min(books.balances["asset"], config["equipment_cents"] // config["equipment_life_months"])
            books.book("equipment_depreciation", expense=depreciation, asset=-depreciation)
        if books.balances["debt"]:
            books.charge("financing_interest", money(books.balances["debt"] * config["credit_apr"] / 12))
        if month in (12, 24, config["months"] + config["runoff_months"]):
            cumulative_pretax = books.profit + tax_paid
            tax = max(0, money(max(0, cumulative_pretax) * config["tax_rate_assumption"]) - tax_paid)
            books.charge("assumed_income_tax", tax)
            tax_paid += tax
        if month > config["months"] and books.available and books.balances["debt"]:
            repayment = min(books.available, books.balances["debt"])
            books.book("credit_principal_repayment", cash=-repayment, debt=-repayment)
        flow = books.balances["cash"] - cash_start - (books.balances["debt"] - debt_start)
        cumulative_cash_flow += flow
        if month > 12:
            cash_flow_after_month12 += flow
        if policy["mode"] != "stop" and payback_month is None and cumulative_cash_flow >= 0:
            payback_month = month
        monthly_profit_history.append(books.profit - profit_start)
        books.close_month(active=int(operated_this_month), competitor_price_cents=competitor_price,
                          competitor_coverage=round(competitor_coverage, 6), accepted=accepted_this_month,
                          market_needs=need_this_month, available_cash=books.available,
                          share=round(prior_share, 6), **{key: val for key, val in counters.items()
                                                       if key not in {"market_needs"}})
        accepted_last_month = accepted_this_month
    if books.balances["custody"] or books.balances["ar"]:
        raise ArithmeticError("Runoff did not settle every deposit and receivable")
    accepted = counters["accepted_orders"]
    retained = accepted - counters["post_acceptance_refunds"]
    startup_expense = books.categories["startup_development_and_administration"]
    contribution = books.revenue - direct_expense
    acquisitions = books.categories["customer_acquisition"] + active_months * money(config["sales_hours_month"] * ops_rate)
    fixed_recurring = (books.categories["recurring_engineering_admin_sales_hosting"]
                       + books.categories["annual_capability_requalification"]
                       + books.categories["equipment_depreciation"] + books.categories["runoff_administration"])
    gross_contribution_per_order = contribution / max(1, retained)
    break_even = math.ceil((fixed_recurring + books.categories["customer_acquisition"]) / max(1, active_months)
                          / max(1, gross_contribution_per_order)) if contribution > 0 and active_months else None
    summary: Json = {
        "seed": seed, "scenario": scenario_name, "policy": policy["name"], "simulated": True,
        "active_months": active_months, "closed_month": closed_month, "insolvent_month": books.insolvent_month,
        "full_horizon_operated": active_months == config["months"],
        "opening_equity_cents": config["equity_cents"], "startup_expense_cents": startup_expense,
        "revenue_cents": books.revenue, "direct_expense_cents": direct_expense, "contribution_cents": contribution,
        "recurring_operating_profit_cents": books.profit + tax_paid + books.categories["financing_interest"] + startup_expense,
        "pretax_project_profit_cents": books.profit + tax_paid, "aftertax_project_profit_cents": books.profit,
        "tax_cents": tax_paid, "financing_cents": books.categories["financing_interest"],
        "free_cash_flow_cents": cumulative_cash_flow, "second_year_and_runoff_cash_flow_cents": cash_flow_after_month12,
        "cash_end_cents": books.balances["cash"], "cash_min_available_cents": books.minimum_available,
        "unpaid_obligations_cents": books.balances["payable"], "debt_end_cents": books.balances["debt"],
        "peak_unfunded_due_obligation_cents": books.peak_unfunded,
        "collections_before_refunds_cents": collections, "cash_refunds_cents": cash_refunds,
        "payback_month": payback_month, "roic_on_opening_equity": books.profit / config["equity_cents"],
        "unique_paying_buyers": len(paid_unique), "qualifying_reached_needs": qualifying_need_total,
        "conversion": accepted / max(1, qualifying_need_total), "net_accepted_orders": retained,
        "contribution_per_net_accepted_order_cents": money(gross_contribution_per_order) if retained else None,
        "observed_customer_acquisition_cost_cents": money(acquisitions / len(paid_unique)) if paid_unique else None,
        "observed_lifetime_contribution_per_buyer_cents": money(sum(customer_contribution.values()) / len(paid_unique))
        if paid_unique else None,
        "break_even_orders_per_active_month": break_even,
        "break_even_conversion_given_reached_need_rate": break_even / (qualifying_need_total / active_months)
        if break_even is not None and qualifying_need_total and active_months else None,
        "maximum_monthly_review_hours": round(maximum_review_hours, 5),
        "maintenance_and_transfer_costs_included": True,
        "capability_transfer_cents": 0,
        "transfer_scope": "No successor transfer is monetized in this enterprise; only maintenance/requalification included",
        "positive_profit_months": sum(x > 0 for x in monthly_profit_history[:config["months"]]),
        **dict(counters), "cost_categories_cents": dict(books.categories),
    }
    if policy["mode"] == "stop":
        summary["full_horizon_operated"] = False
        summary["break_even_orders_per_active_month"] = None
    return {"summary": summary, "monthly": books.monthly, "events": books.events,
            "decisions": decisions, "buyers": identities}


def percentile(values: list[int | float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    return float(ordered[round((len(ordered) - 1) * quantile)])


def aggregate(rows: list[Json]) -> Json:
    profits = [r["aftertax_project_profit_cents"] for r in rows]
    fields = ("revenue_cents", "contribution_cents", "recurring_operating_profit_cents", "pretax_project_profit_cents",
              "aftertax_project_profit_cents", "free_cash_flow_cents", "cash_end_cents", "cash_min_available_cents",
              "unique_paying_buyers", "accepted_orders", "net_accepted_orders", "conversion", "active_months",
              "second_year_and_runoff_cash_flow_cents", "roic_on_opening_equity", "peak_unfunded_due_obligation_cents")
    result: Json = {"worlds": len(rows), "policy": rows[0]["policy"], "scenario": rows[0]["scenario"]}
    for field in fields:
        result["mean_" + field] = statistics.mean(r.get(field, 0) for r in rows)
    result.update({"profit_p10_cents": percentile(profits, 0.1), "profit_p50_cents": percentile(profits, 0.5),
                   "profit_p90_cents": percentile(profits, 0.9), "loss_frequency": sum(p < 0 for p in profits) / len(rows),
                   "insolvency_frequency": sum(r["insolvent_month"] is not None for r in rows) / len(rows),
                   "full_horizon_operation_frequency": sum(r["full_horizon_operated"] for r in rows) / len(rows),
                   "payback_frequency": sum(r["payback_month"] is not None for r in rows) / len(rows),
                   "positive_contribution_frequency": sum(r["contribution_cents"] > 0 for r in rows) / len(rows),
                   "positive_recurring_profit_frequency": sum(r["recurring_operating_profit_cents"] > 0 for r in rows)
                   / len(rows),
                   "mean_profit_standard_error_cents": statistics.stdev(profits) / math.sqrt(len(rows))
                   if len(rows) > 1 else 0})
    for field in ("contribution_per_net_accepted_order_cents", "observed_customer_acquisition_cost_cents",
                  "observed_lifetime_contribution_per_buyer_cents", "break_even_orders_per_active_month",
                  "break_even_conversion_given_reached_need_rate"):
        values = [r[field] for r in rows if r[field] is not None]
        result["mean_" + field] = statistics.mean(values) if values else None
    return result


def write_csv(path: Path, rows: list[Json]) -> None:
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def csv_audit(path: Path) -> Json:
    """Reconstruct every monthly balance and equity identity using Decimal."""
    from decimal import Decimal

    checks = 0
    previous: dict[tuple[str, str, str], Json] = {}
    cumulative_equity: defaultdict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    cumulative_profit: defaultdict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            key = (row["seed"], row["scenario"], row["policy"])
            balance = {a: Decimal(row[a + "_close"]) for a in ACCOUNTS}
            for account in ACCOUNTS:
                assert Decimal(row[account + "_open"]) + Decimal(row[account + "_change"]) == balance[account]
                if key in previous:
                    assert previous[key][account + "_close"] == row[account + "_open"]
                checks += 2
            cumulative_equity[key] += Decimal(row["equity"])
            cumulative_profit[key] += Decimal(row["revenue"]) - Decimal(row["expense"])
            assert sum(balance[a] for a in ("cash", "ar", "asset")) - sum(
                balance[a] for a in ("custody", "payable", "debt")) == cumulative_equity[key] + cumulative_profit[key]
            assert balance["cash"] >= balance["custody"] >= 0
            assert all(value >= 0 for value in balance.values())
            assert cumulative_profit[key] == Decimal(row["cumulative_profit"])
            checks += 4
            previous[key] = row
    return {"worlds": len(previous), "arithmetic_assertions": checks, "passed": True,
            "scope": "Monthly accounting and custody identities; not validation of demand or willingness to pay"}


def campaign(config_path: Path, output: Path, worlds_override: int | None = None) -> Json:
    """Freeze source/config before training and evaluate disjoint fresh worlds."""
    config = read_config(config_path)
    output.mkdir(parents=True, exist_ok=False)
    selection = config["selection"]
    worlds = worlds_override if worlds_override is not None else selection["confirmation_worlds"]
    freeze = {"source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
              "created_unix": int(time.time()), "selection_rule": selection["rule"],
              "training_seed_interval": [selection["training_seeds_start"],
                                         selection["training_seeds_start"] + selection["training_worlds"] - 1],
              "confirmation_seed_interval": [selection["confirmation_seeds_start"],
                                             selection["confirmation_seeds_start"] + worlds - 1],
              "worlds_override": worlds_override, "scenarios": list(config["scenarios"]),
              "note": "Source/config frozen before training; holdout seeds were not used to select policy"}
    (output / "FREEZE.json").write_text(json.dumps(freeze, indent=2) + "\n")
    (output / "config.json").write_bytes(config_path.read_bytes())
    development = []
    training_raw = []
    for policy in config["policies"]:
        rows = [run_world(config, policy, "base", seed)["summary"] for seed in range(
            selection["training_seeds_start"], selection["training_seeds_start"] + selection["training_worlds"])]
        training_raw.extend(rows)
        development.append(aggregate(rows))
    eligible = [x for x in development if x["mean_aftertax_project_profit_cents"] > 0
                and x["loss_frequency"] <= 0.25 and x["insolvency_frequency"] <= 0.05]
    selected_name = max(eligible, key=lambda x: (x["profit_p10_cents"], x["mean_aftertax_project_profit_cents"],
                                               x["policy"]))["policy"] if eligible else "stop"
    best_active = max((x for x in development if x["policy"] != "stop"),
                      key=lambda x: (x["mean_aftertax_project_profit_cents"], x["policy"]))["policy"]
    selection_record = {"selected_policy": selected_name, "diagnostic_active_policy": best_active,
                        "selection_before_holdout": True, "development": development}
    (output / "SELECTION.json").write_text(json.dumps(selection_record, indent=2) + "\n")
    write_csv(output / "training_worlds.csv", [{k: v for k, v in x.items() if k != "cost_categories_cents"}
                                               for x in training_raw])
    confirmation = []
    raw = []
    monthly = []
    policies = [p for p in config["policies"] if p["name"] in {selected_name, best_active}]
    for scenario_name in config["scenarios"]:
        for policy in policies:
            rows = []
            for seed in range(selection["confirmation_seeds_start"], selection["confirmation_seeds_start"] + worlds):
                trace = seed == selection["confirmation_seeds_start"] and policy["mode"] != "stop"
                result = run_world(config, policy, scenario_name, seed, trace=trace)
                rows.append(result["summary"])
                raw.append(result["summary"])
                monthly.extend({"seed": seed, "scenario": scenario_name, "policy": policy["name"], **r}
                               for r in result["monthly"])
                if trace:
                    reference = output / f"reference_{scenario_name}_{policy['name']}.json.gz"
                    with reference.open("wb") as stream:
                        with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as zipped:
                            zipped.write(json.dumps(result, separators=(",", ":")).encode())
            confirmation.append(aggregate(rows))
    write_csv(output / "confirmation_worlds.csv", [{k: v for k, v in x.items() if k != "cost_categories_cents"} for x in raw])
    write_csv(output / "monthly_ledger.csv", monthly)
    write_csv(output / "scenario_summary.csv", confirmation)
    summary = {"schema": "agi-alpha-economic-results/v1", "simulated": True,
               "actual_customers": 0, "actual_revenue_cents": 0, "actual_complete_cost": None,
               "actual_profit": None, "selected_policy": selected_name, "diagnostic_active_policy": best_active,
               "proof_II": "NOT ESTABLISHED" if selected_name == "stop" else "CONDITIONAL SIMULATION ONLY",
               "technical_novelty": "NOT EVALUATED BY ECONOMIC MODEL", "development": development,
               "confirmation": confirmation, "audit": csv_audit(output / "monthly_ledger.csv"),
               "population_warning": "240 authored synthetic organizations, not actual leads or a market-size estimate",
               "demand_warning": "All valuation, budgets, conversion, scope fit, retention and demand are assumptions",
               "historical_campaign_costs": "Actual current and prior research costs unmeasured; simulated launch includes its own stated construction budget only"}
    (output / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.is_file()}
    (output / "SHA256.json").write_text(json.dumps(files, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("economics_config.json"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--worlds", type=int)
    parser.add_argument("--audit", type=Path)
    args = parser.parse_args()
    if args.audit is not None:
        print(json.dumps(csv_audit(args.audit), indent=2))
    elif args.output is not None:
        result = campaign(args.config, args.output, args.worlds)
        print(json.dumps({"selected_policy": result["selected_policy"],
                          "diagnostic_active_policy": result["diagnostic_active_policy"],
                          "confirmation": result["confirmation"], "audit": result["audit"]}, indent=2))
    else:
        parser.error("Provide --output for a new frozen campaign or --audit for a recorded monthly ledger")


if __name__ == "__main__":
    main()
