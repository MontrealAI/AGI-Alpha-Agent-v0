# SPDX-License-Identifier: Apache-2.0
"""Bounded hypothetical enterprise game with an integer-cents double-entry journal."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "assumptions.json").read_text())
ASSETS = {"cash", "restricted_cash", "receivables"}
LIABILITIES = {"customer_deposits", "refund_payable", "support_payable", "debt"}
STARTUP = {
    "research",
    "failed_discovery",
    "development",
    "independent_validation",
    "documentation",
    "startup_inference",
    "startup_compute",
    "startup_tools",
}
FINANCE = {"financing_fee", "financing_interest"}


def cents(value: float) -> int:
    return int(round(value))


def sample(seed: int, key: str) -> random.Random:
    """Return a named common-random-number stream, independent of branch execution."""
    return random.Random(
        int.from_bytes(hashlib.sha256(f"{seed}:{key}".encode()).digest()[:8], "big")
    )


def uniform(seed: int, key: str) -> float:
    return sample(seed, key).random()


def poisson(seed: int, key: str, mean: float) -> int:
    rng, n, product = sample(seed, key), 0, 1.0
    while product > math.exp(-mean):
        n, product = n + 1, product * rng.random()
    return n - 1


def sim_date(month: int) -> str:
    year, zero_month = divmod(2026 * 12 + 10 + month, 12)
    return f"{year:04d}-{zero_month + 1:02d}-01"


@dataclass
class Book:
    world: str
    entries: list[dict[str, Any]] = field(default_factory=list)
    balances: dict[str, int] = field(default_factory=dict)
    peak_funding: int = 0
    min_usable: int = 10**18
    gross_collections: int = 0
    refunds: int = 0

    def post(
        self,
        tick: int,
        event: str,
        amount: int = 0,
        debit: str = "",
        credit: str = "",
        contract: str | None = None,
        **details: Any,
    ) -> None:
        """Record one balanced journal leg; zero entries describe lifecycle events."""
        if amount < 0 or (amount and (not debit or not credit or debit == credit)):
            raise ValueError("Invalid journal posting")
        self.entries.append(
            {
                "world_id": self.world,
                "tick": tick,
                "date": sim_date(tick),
                "event_type": event,
                "amount_cents": amount,
                "debit_account": debit,
                "credit_account": credit,
                "contract_id": contract,
                **details,
            }
        )
        if amount:
            self.balances[debit] = self.balances.get(debit, 0) + amount
            self.balances[credit] = self.balances.get(credit, 0) - amount
        self.peak_funding = max(
            self.peak_funding,
            -self.balances.get("equity", 0)
            - self.balances.get("debt", 0)
            - self.balances.get("cash", 0),
        )
        self.min_usable = min(self.min_usable, self.usable())

    def usable(self) -> int:
        return self.balances.get("cash", 0) + sum(
            self.balances.get(x, 0) for x in ("refund_payable", "support_payable")
        )

    def ensure_cash(self, tick: int, amount: int) -> None:
        """Draw only the modeled finite facility before every unrestricted cash payment."""
        missing = max(0, amount - self.balances.get("cash", 0))
        if missing:
            if missing - self.balances.get("debt", 0) > CONFIG["credit_limit_cents"]:
                raise RuntimeError(
                    "Modeled financing exhausted; terminal insolvency must not be hidden"
                )
            self.post(tick, "credit_draw", missing, "cash", "debt")

    def pay(
        self,
        tick: int,
        event: str,
        amount: int,
        contract: str | None = None,
        **details: Any,
    ) -> None:
        """Pay an expense after checking modeled cash funding."""
        self.ensure_cash(tick, amount)
        self.post(tick, event, amount, f"expense:{event}", "cash", contract, **details)

    def profit(self, operating: bool = False) -> int:
        expenses = sum(
            v
            for k, v in self.balances.items()
            if k.startswith("expense:")
            and (
                not operating
                or k[8:] not in STARTUP | FINANCE | {"successor_experiment"}
            )
        )
        return -self.balances.get("revenue", 0) - expenses


def policy_grid() -> list[dict[str, Any]]:
    p = CONFIG["policies"]
    return [
        {
            "id": f"{epoch}-p{price // 100}-d{int(deposit * 100)}-c{cap}",
            "price_cents": price,
            "deposit_fraction": deposit,
            "capacity": cap,
            "stop_month": p["stop_month"],
            "stop_trailing_contribution_cents": p["stop_trailing_contribution_cents"],
        }
        for epoch, prices in (
            ("initial", p["prices_cents"]),
            ("redesign", p["redesign_prices_cents"]),
        )
        for price in prices
        for deposit in p["deposit_fractions"]
        for cap in p["monthly_capacities"]
    ]


def buyer(
    seed: int, key: str, scenario: dict[str, Any], renewal: bool = False
) -> dict[str, Any]:
    """Create private buyer circumstances; dollar values are explicit assumptions."""
    rng = sample(seed, key)
    v = CONFIG["mean_buyer_value_cents"] * scenario["value_factor"]
    value = cents(
        rng.lognormvariate(
            math.log(v) - CONFIG["value_log_sigma"] ** 2 / 2, CONFIG["value_log_sigma"]
        )
        * (0.7 if renewal else 1)
    )
    return {
        "key": key,
        "value": value,
        "budget": cents(rng.uniform(0.18, 0.65) * value),
        "internal_capacity": rng.random() < 0.45,
        "urgency": rng.uniform(0.05, 0.3),
        "future_relationship_value": cents(rng.uniform(0, 500000)),
        "bundle_customer": rng.random() < 0.25,
        "renewal": renewal,
        "free_quality": scenario.get("free_quality", 0.82),
        "free_hours": scenario.get("free_hours", 16),
        "free_delay": scenario.get("free_delay", 2),
    }


def utilities(
    b: dict[str, Any], price: int, rival_price: int, deposit: float
) -> dict[str, float]:
    """Payoffs use the same technical success for enterprise and competent current-AI rival."""
    v, urgency = b["value"], b["urgency"]
    self_hours = 24 if b["internal_capacity"] else 60
    self_delay = 1 if b["internal_capacity"] else 3
    rival = rival_price * (0.75 if b["bundle_customer"] else 1)
    q = {
        "enterprise": 0.90 * v / (1 + urgency) - price - 25000 - deposit * price * 0.03,
        "competitor": 0.90 * v / (1 + urgency) - rival - 30000,
        "self": 0.90 * v / (1 + urgency * self_delay)
        - self_hours * CONFIG["internal_hourly_cents"],
        "free": b["free_quality"] * v / (1 + urgency * b["free_delay"])
        - b["free_hours"] * CONFIG["internal_hourly_cents"],
        "wait": 0.65 * v / (1 + urgency * 6),
        "decline": 0.0,
    }
    if price > b["budget"]:
        q["enterprise"] = -1e18
    if rival > b["budget"]:
        q["competitor"] = -1e18
    return q


def choice(seed: int, key: str, values: dict[str, float], rationality: str) -> str:
    if rationality == "best_response":
        return max(values, key=lambda x: (values[x], x))
    scale = CONFIG["choice_temperature_cents"]
    scored = {
        k: v - scale * math.log(-math.log(max(1e-12, uniform(seed, key + ":" + k))))
        for k, v in values.items()
    }
    return max(scored, key=lambda x: (scored[x], x))


def rival_strategy(
    seed: int, tick: int, policy: dict[str, Any], scenario: dict[str, Any]
) -> tuple[int, str, dict[str, float]]:
    """Myopic rival best response over public archetypes, not private actual buyer data."""
    price = policy["price_cents"]
    if scenario["compete"] == "imitate" and tick >= 4:
        return max(300000, cents(price * 0.70)), "same_ai_imitate_and_cut", {}
    prices = {
        "match": price,
        "cut": max(350000, cents(price * 0.85)),
        "premium_bundle": price + 100000,
    }
    expected = {}
    for name, quote in prices.items():
        wins = 0.0
        for j in range(24):
            b = buyer(seed, f"rival_information:{tick}:{j}", scenario)
            u = utilities(b, price, quote, policy["deposit_fraction"])
            mx = max(u.values())
            weights = {
                k: math.exp(max(-700, (v - mx) / CONFIG["choice_temperature_cents"]))
                for k, v in u.items()
            }
            wins += weights["competitor"] / sum(weights.values())
        expected[name] = wins * (quote - 230000) - (40000 if name == "cut" else 0)
    action = max(expected, key=lambda name: expected[name])
    return prices[action], action, expected


def run_world(
    seed: int, scenario_name: str, policy: dict[str, Any], conventional: bool = False
) -> dict[str, Any]:
    """Run acquisition through final runoff; no money or external service is accessed."""
    cfg, scenario = CONFIG, CONFIG["scenarios"][scenario_name]
    world_id = f"{scenario_name}:{seed}:{policy['id']}:{'conventional' if conventional else 'candidate'}"
    book = Book(world_id)
    contracts: list[dict[str, Any]] = []
    events: dict[int, list[tuple[str, dict[str, Any]]]] = {}
    counts = {
        k: 0
        for k in (
            "leads",
            "qualified",
            "negotiations",
            "signed",
            "accepted",
            "corrected",
            "failed",
            "renewals",
            "refunds",
            "withheld",
            "recovered",
            "capacity_declines",
        )
    }
    choices = {
        k: 0 for k in ("enterprise", "competitor", "self", "free", "wait", "decline")
    }
    hours: dict[str, float] = {}
    active, stop_month, successor = True, None, False
    monthly_contribution: list[int] = []
    cumulative_before = 0
    quality_shock = 1.7 if uniform(seed, "shared_quality_shock") < 0.10 else 1.0

    def schedule(tick: int, kind: str, c: dict[str, Any]) -> None:
        events.setdefault(tick, []).append((kind, c))

    def labor(
        tick: int, category: str, effort: float, c: dict[str, Any] | None = None
    ) -> None:
        hours[category] = hours.get(category, 0.0) + effort
        book.pay(
            tick,
            category,
            cents(
                effort * cfg["hourly"][category] * 100 * scenario.get("labor_factor", 1)
            ),
            c["id"] if c else None,
            hours=effort,
            hourly_rate_usd=cfg["hourly"][category],
        )

    def settle_expense_liability(
        tick: int,
        account: str,
        expense: str,
        provision: int,
        actual: int,
        c: dict[str, Any],
    ) -> None:
        if actual > provision:
            book.post(
                tick,
                expense + "_adjustment",
                actual - provision,
                f"expense:{expense}",
                account,
                c["id"],
            )
        elif provision > actual:
            book.post(
                tick,
                expense + "_release",
                provision - actual,
                account,
                f"expense:{expense}",
                c["id"],
            )
        if actual:
            book.ensure_cash(tick, actual)
            book.post(tick, expense + "_payment", actual, account, "cash", c["id"])

    def acceptance(tick: int, c: dict[str, Any]) -> None:
        c["accepted"], c["state"] = True, "accepted"
        counts["accepted"] += 1
        book.post(
            tick, "acceptance", contract=c["id"], scope="software_only", simulated=True
        )
        book.post(
            tick,
            "recognize_deposit",
            c["deposit"],
            "customer_deposits",
            "revenue",
            c["id"],
        )
        book.post(
            tick,
            "release_restricted_deposit",
            c["deposit"],
            "cash",
            "restricted_cash",
            c["id"],
        )
        book.post(
            tick,
            "invoice_balance",
            c["price"] - c["deposit"],
            "receivables",
            "revenue",
            c["id"],
        )
        c["support_provision"] = cents(
            cfg["hours"]["support"] * cfg["hourly"]["support"] * 100
        )
        c["refund_provision"] = cents(
            c["price"] * cfg["warranty_probability"] * cfg["warranty_refund_fraction"]
        )
        book.post(
            tick,
            "accrue_support",
            c["support_provision"],
            "expense:support",
            "support_payable",
            c["id"],
        )
        book.post(
            tick,
            "accrue_warranty",
            c["refund_provision"],
            "expense:warranty_refund",
            "refund_payable",
            c["id"],
        )
        schedule(tick + 1, "collect", c)
        schedule(tick + 3, "support", c)
        if c["signed_tick"] + 6 <= cfg["horizon_months"]:
            schedule(c["signed_tick"] + 6, "renewal_opportunity", c)

    def sign(tick: int, b: dict[str, Any], price: int) -> None:
        c: dict[str, Any] = {
            "id": f"c{len(contracts) + 1:04d}",
            "signed_tick": tick,
            "price": price,
            "deposit": cents(price * policy["deposit_fraction"]),
            "buyer": b,
            "accepted": False,
            "collected": 0,
            "refunded": 0,
            "closed": False,
            "state": "contracted",
        }
        contracts.append(c)
        counts["signed"] += 1
        counts["renewals"] += int(b["renewal"])
        book.post(
            tick,
            "contract",
            contract=c["id"],
            price_cents=price,
            deposit_cents=c["deposit"],
            acceptance="executable protocol and reproducible model-scope checks",
            renewal=b["renewal"],
        )
        book.post(
            tick,
            "restricted_deposit_collection",
            c["deposit"],
            "restricted_cash",
            "customer_deposits",
            c["id"],
        )
        book.gross_collections += c["deposit"]
        c["collected"] += c["deposit"]
        schedule(tick + 1, "deliver", c)

    book.post(0, "opening_equity", cfg["opening_equity_cents"], "cash", "equity")
    for category, effort, rate in cfg["startup"]:
        book.pay(
            0, category, cents(effort * rate * 100), hours=effort, hourly_rate_usd=rate
        )
        hours[category] = effort
    for category in ("startup_inference", "startup_compute", "startup_tools"):
        book.pay(0, category, cfg[category + "_cents"])
    book.pay(0, "financing_fee", cfg["facility_fee_cents"])

    for tick in range(1, cfg["horizon_months"] + cfg["runoff_months"] + 1):
        signed_this_month = 0
        supplier_factor = scenario["supplier_factor"] if tick >= 7 else 1
        capacity_factor = scenario["capacity_factor"] if tick >= 7 else 1
        cap = max(1, int(policy["capacity"] * capacity_factor))
        rival_price, rival_action, rival_values = rival_strategy(
            seed, tick, policy, scenario
        )
        book.post(
            tick,
            "competitor_choice",
            quote_cents=rival_price,
            action=rival_action,
            modeled_payoff_cents=rival_values,
        )
        if tick == 7:
            book.post(
                tick,
                "supplier_terms",
                inference_multiplier=supplier_factor,
                capacity_factor=capacity_factor,
            )

        for kind, c in events.pop(tick, []):
            key = c["buyer"]["key"]
            if kind == "deliver":
                labor(tick, "delivery", cfg["hours"]["delivery"], c)
                labor(tick, "verification", cfg["hours"]["verification"], c)
                book.pay(
                    tick,
                    "inference",
                    cents(cfg["delivery_inference_cents"] * supplier_factor),
                    c["id"],
                )
                book.pay(tick, "compute", cfg["delivery_compute_cents"], c["id"])
                book.pay(tick, "tools", cfg["delivery_tools_cents"], c["id"])
                fail = min(
                    0.85,
                    (1 - cfg["first_pass_probability"])
                    * scenario["failure_factor"]
                    * quality_shock,
                )
                book.post(
                    tick,
                    "delivery",
                    contract=c["id"],
                    simulated=True,
                    kind="software_design_pack",
                )
                if uniform(seed, key + ":delivery") < fail:
                    counts["corrected"] += 1
                    c["state"] = "correction"
                    book.post(tick, "correction_required", contract=c["id"])
                    schedule(tick + 1, "correct", c)
                else:
                    acceptance(tick, c)
            elif kind == "correct":
                labor(tick, "correction", cfg["hours"]["correction"], c)
                labor(tick, "verification", 2, c)
                if uniform(seed, key + ":repair") < cfg[
                    "repair_success_probability"
                ] / max(1, quality_shock * 0.8):
                    acceptance(tick, c)
                else:
                    counts["failed"] += 1
                    c["state"], c["closed"] = "refunded_failed_delivery", True
                    book.post(
                        tick,
                        "failed_delivery_refund",
                        c["deposit"],
                        "customer_deposits",
                        "restricted_cash",
                        c["id"],
                    )
                    c["refunded"] += c["deposit"]
                    book.refunds += c["deposit"]
                    book.post(
                        tick,
                        "contract_closed",
                        contract=c["id"],
                        resolution="failed_delivery_refunded",
                    )
            elif kind == "collect":
                invoice = c["price"] - c["deposit"]
                p = scenario["enforcement"]
                deviation = (
                    invoice - p * invoice - c["buyer"]["future_relationship_value"]
                )
                liquidity = (
                    uniform(seed, key + ":liquidity")
                    < cfg["liquidity_failure_probability"]
                )
                withhold = deviation > 0 or liquidity
                book.post(
                    tick,
                    "payment_choice",
                    contract=c["id"],
                    withhold=withhold,
                    deviation_gain_cents=cents(deviation),
                    liquidity_failure=liquidity,
                )
                if withhold:
                    counts["withheld"] += 1
                    pursue = p * invoice > cfg["collection_cost_cents"]
                    book.post(
                        tick, "collection_policy", contract=c["id"], pursue=pursue
                    )
                    if pursue:
                        book.pay(
                            tick, "collection", cfg["collection_cost_cents"], c["id"]
                        )
                    recovered = pursue and uniform(seed, key + ":recovery") < p
                    if recovered:
                        counts["recovered"] += 1
                        book.post(
                            tick,
                            "late_collection",
                            invoice,
                            "cash",
                            "receivables",
                            c["id"],
                        )
                        c["collected"] += invoice
                        book.gross_collections += invoice
                    else:
                        book.post(
                            tick,
                            "bad_debt",
                            invoice,
                            "expense:bad_debt",
                            "receivables",
                            c["id"],
                        )
                else:
                    book.post(
                        tick,
                        "final_collection",
                        invoice,
                        "cash",
                        "receivables",
                        c["id"],
                    )
                    c["collected"] += invoice
                    book.gross_collections += invoice
                c["collection_closed"] = True
            elif kind == "support":
                support = cents(
                    c["support_provision"]
                    * (0.7 + uniform(seed, key + ":support") * 0.8)
                )
                settle_expense_liability(
                    tick,
                    "support_payable",
                    "support",
                    c["support_provision"],
                    support,
                    c,
                )
                hours["support"] = hours.get("support", 0) + support / (
                    cfg["hourly"]["support"] * 100
                )
                warranty = uniform(seed, key + ":warranty") < min(
                    0.8, cfg["warranty_probability"] * quality_shock
                )
                refund = (
                    min(
                        c["collected"],
                        cents(c["price"] * cfg["warranty_refund_fraction"]),
                    )
                    if warranty
                    else 0
                )
                settle_expense_liability(
                    tick,
                    "refund_payable",
                    "warranty_refund",
                    c["refund_provision"],
                    refund,
                    c,
                )
                if refund:
                    counts["refunds"] += 1
                    book.refunds += refund
                    c["refunded"] += refund
                c["closed"], c["state"] = True, "closed"
                book.post(tick, "support_closed", contract=c["id"], refund_cents=refund)
                book.post(
                    tick,
                    "contract_closed",
                    contract=c["id"],
                    resolution="accepted_collection_and_warranty_closed",
                )
            elif (
                kind == "renewal_opportunity"
                and active
                and tick <= cfg["horizon_months"]
            ):
                if uniform(seed, key + ":new_need") < 0.45:
                    b = buyer(seed, key + ":renewal", scenario, True)
                    labor(tick, "qualification", cfg["hours"]["qualification"])
                    u = utilities(
                        b,
                        policy["price_cents"],
                        rival_price,
                        policy["deposit_fraction"],
                    )
                    selected = choice(seed, b["key"], u, scenario["rationality"])
                    choices[selected] += 1
                    book.post(
                        tick, "renewal_choice", contract=c["id"], selected=selected
                    )
                    if selected == "enterprise" and signed_this_month < cap:
                        labor(tick, "negotiation", cfg["hours"]["negotiation"])
                        sign(tick, b, policy["price_cents"])
                        signed_this_month += 1

        outstanding = sum(not c["closed"] for c in contracts)
        if tick <= cfg["horizon_months"] and active:
            labor(tick, "maintenance", cfg["hours"]["maintenance_monthly"])
            labor(tick, "acquisition", cfg["hours"]["operations_monthly"])
            leads = poisson(
                seed, f"leads:{tick}", cfg["lead_mean"] * scenario["lead_factor"]
            )
            for j in range(leads):
                key = f"buyer:{tick}:{j}"
                counts["leads"] += 1
                labor(tick, "acquisition", cfg["hours"]["acquisition"])
                if uniform(seed, key + ":qualify") > cfg["qualification_probability"]:
                    book.post(tick, "qualification_decline", buyer_key=key)
                    continue
                counts["qualified"] += 1
                labor(tick, "qualification", cfg["hours"]["qualification"])
                b = buyer(seed, key, scenario)
                selected = choice(
                    seed,
                    key,
                    utilities(
                        b,
                        policy["price_cents"],
                        rival_price,
                        policy["deposit_fraction"],
                    ),
                    scenario["rationality"],
                )
                choices[selected] += 1
                book.post(
                    tick,
                    "buyer_choice",
                    buyer_key=key,
                    selected=selected,
                    budget_cents=b["budget"],
                    value_cents=b["value"],
                    internal_capacity=b["internal_capacity"],
                )
                if selected != "enterprise":
                    continue
                counts["negotiations"] += 1
                labor(tick, "negotiation", cfg["hours"]["negotiation"])
                if signed_this_month >= cap:
                    counts["capacity_declines"] += 1
                    book.post(tick, "capacity_decline", buyer_key=key)
                    continue
                u = utilities(
                    b, policy["price_cents"], rival_price, policy["deposit_fraction"]
                )
                outside = max(v for k, v in u.items() if k != "enterprise")
                discount = min(
                    cents(policy["price_cents"] * 0.1),
                    max(0, cents(outside - u["enterprise"])),
                )
                price = policy["price_cents"] - discount
                if price < 350000 or uniform(seed, key + ":contract") < 0.08:
                    book.post(tick, "negotiation_decline", buyer_key=key)
                    continue
                book.post(
                    tick,
                    "negotiated_price",
                    buyer_key=key,
                    price_cents=price,
                    discount_cents=discount,
                )
                sign(tick, b, price)
                signed_this_month += 1
        elif outstanding:
            labor(tick, "maintenance", 2)

        if tick <= cfg["horizon_months"] or outstanding:
            book.pay(tick, "financing_fee", cfg["monthly_facility_cents"])
        debt = -book.balances.get("debt", 0)
        if debt:
            book.pay(tick, "financing_interest", cents(debt * cfg["credit_apr"] / 12))

        contribution = book.profit(True)
        monthly_contribution.append(contribution - cumulative_before)
        cumulative_before = contribution
        stage = cfg["successor"]
        if (
            not successor
            and tick >= stage["earliest_month"]
            and tick <= cfg["horizon_months"]
            and stage["lower_bound_success_probability"]
            * stage["lower_bound_incremental_value_cents"]
            >= stage["experiment_cost_cents"]
            and counts["accepted"] >= stage["min_accepted"]
            and counts["renewals"] >= stage["min_renewals"]
            and contribution >= stage["min_operating_contribution_cents"]
            and book.usable() - stage["experiment_cost_cents"]
            >= stage["min_cash_after_cents"]
        ):
            book.pay(tick, "successor_experiment", stage["experiment_cost_cents"])
            successor = True
            book.post(
                tick,
                "successor_stage_decision",
                stage=1,
                funded=True,
                future_value_booked_cents=0,
                stage2="hold_pending_external_evidence",
            )
        if active and tick >= policy["stop_month"] and tick <= cfg["horizon_months"]:
            if (
                sum(monthly_contribution[-3:])
                < policy["stop_trailing_contribution_cents"]
                or book.usable() < 1500000
            ):
                active, stop_month = False, tick
                book.post(
                    tick,
                    "stop_new_sales",
                    reason="frozen_trailing_contribution_or_cash_rule",
                )
        if tick == cfg["horizon_months"]:
            active = False
            book.post(tick, "sales_horizon_closed")
        book.min_usable = min(book.min_usable, book.usable())

    if events:
        raise AssertionError(f"Unfinished events: {sorted(events)}")
    debt = -book.balances.get("debt", 0)
    if debt:
        if book.balances.get("cash", 0) < debt:
            raise RuntimeError("Insolvent exit: debt cannot be marked paid")
        book.post(18, "repay_credit", debt, "debt", "cash")
    book.pay(
        18, "exit", 75000, scope="archive, handoff and closure; no terminal asset value"
    )
    book.post(
        18, "enterprise_exit", all_contracts_closed=all(c["closed"] for c in contracts)
    )
    if any(
        book.balances.get(k, 0)
        for k in LIABILITIES | {"restricted_cash", "receivables"}
    ):
        raise AssertionError("Unclosed terminal balance")
    if not all(c["closed"] for c in contracts):
        raise AssertionError("Unclosed contract")
    cost = sum(v for k, v in book.balances.items() if k.startswith("expense:"))
    out = {
        "world_id": world_id,
        "seed": seed,
        "scenario": scenario_name,
        "policy": policy,
        "simulation": True,
        "conventional": conventional,
        "counts": counts,
        "choices": choices,
        "profit_cents": book.profit(),
        "operating_contribution_cents": book.profit(True),
        "recognized_revenue_cents": -book.balances.get("revenue", 0),
        "collections_cents": book.gross_collections,
        "refunds_cents": book.refunds,
        "net_collections_cents": book.gross_collections - book.refunds,
        "restricted_cash_cents": book.balances.get("restricted_cash", 0),
        "usable_cash_cents": book.usable(),
        "total_project_cost_cents": cost,
        "cash_requirement_cents": book.peak_funding,
        "minimum_usable_cash_cents": book.min_usable,
        "stop_month": stop_month,
        "successor_funded": successor,
        "hours": hours,
        "monthly_operating_contribution_cents": monthly_contribution,
        "final_account_balances": book.balances,
        "contracts": contracts,
        "journal": book.entries,
    }
    if out["usable_cash_cents"] - cfg["opening_equity_cents"] != out["profit_cents"]:
        raise AssertionError("Cash to profit reconciliation failed")
    return out


def summarize(worlds: list[dict[str, Any]]) -> dict[str, Any]:
    """Sampling uncertainty is conditional on fixed model assumptions."""
    p = [w["profit_cents"] for w in worlds]
    ordered = sorted(p)
    n = len(worlds)

    def mean(key: str) -> float:
        return float(statistics.mean(w[key] for w in worlds))

    return {
        "worlds": n,
        "mean_profit_cents": statistics.mean(p),
        "profit_sampling_se_cents": statistics.stdev(p) / math.sqrt(n) if n > 1 else 0,
        "probability_loss": sum(v < 0 for v in p) / n,
        "worst_loss_cents": min(p),
        "profit_p05_cents": ordered[int((n - 1) * 0.05)],
        "profit_p95_cents": ordered[int((n - 1) * 0.95)],
        "mean_operating_contribution_cents": mean("operating_contribution_cents"),
        "mean_revenue_cents": mean("recognized_revenue_cents"),
        "mean_collections_cents": mean("collections_cents"),
        "mean_total_project_cost_cents": mean("total_project_cost_cents"),
        "mean_cash_requirement_cents": mean("cash_requirement_cents"),
        "max_cash_requirement_cents": max(w["cash_requirement_cents"] for w in worlds),
        "mean_signed": statistics.mean(w["counts"]["signed"] for w in worlds),
        "mean_accepted": statistics.mean(w["counts"]["accepted"] for w in worlds),
        "mean_renewals": statistics.mean(w["counts"]["renewals"] for w in worlds),
        "mean_total_human_hours": statistics.mean(
            sum(w["hours"].values()) for w in worlds
        ),
        "stop_fraction": sum(w["stop_month"] is not None for w in worlds) / n,
        "successor_fraction": sum(w["successor_funded"] for w in worlds) / n,
    }


def run_no_launch(seed: int) -> dict[str, Any]:
    """Stop after the already-costed research campaign; retain its full sunk costs."""
    book = Book(f"no_launch:{seed}")
    book.post(0, "opening_equity", CONFIG["opening_equity_cents"], "cash", "equity")
    hours = {}
    for category, effort, rate in CONFIG["startup"]:
        book.pay(
            0, category, cents(effort * rate * 100), hours=effort, hourly_rate_usd=rate
        )
        hours[category] = effort
    for category in ("startup_inference", "startup_compute", "startup_tools"):
        book.pay(0, category, CONFIG[category + "_cents"])
    book.pay(
        0,
        "exit",
        75000,
        scope="archive the completed study; decline new commercial work",
    )
    book.post(0, "enterprise_exit", all_contracts_closed=True)
    return {
        "world_id": book.world,
        "seed": seed,
        "scenario": "no_launch",
        "policy": {"id": "no_launch"},
        "simulation": True,
        "counts": {"signed": 0, "accepted": 0, "renewals": 0},
        "choices": {},
        "profit_cents": book.profit(),
        "operating_contribution_cents": book.profit(True),
        "recognized_revenue_cents": 0,
        "collections_cents": 0,
        "refunds_cents": 0,
        "net_collections_cents": 0,
        "restricted_cash_cents": 0,
        "usable_cash_cents": book.usable(),
        "total_project_cost_cents": -book.profit(),
        "cash_requirement_cents": book.peak_funding,
        "minimum_usable_cash_cents": book.min_usable,
        "stop_month": 0,
        "successor_funded": False,
        "hours": hours,
        "monthly_operating_contribution_cents": [book.profit(True)],
        "final_account_balances": book.balances,
        "contracts": [],
        "journal": book.entries,
    }


def develop(output: Path) -> None:
    """Execute two bounded grids totaling twenty-four policies on twelve shared development seeds."""
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for policy in policy_grid():
        summaries = {}
        for name in CONFIG["selection_weights"]:
            worlds = [run_world(s, name, policy) for s in CONFIG["development_seeds"]]
            summaries[name] = summarize(worlds)
        score = sum(
            CONFIG["selection_weights"][name] * v["mean_profit_cents"]
            for name, v in summaries.items()
        )
        rows.append(
            {"policy": policy, "selection_score_cents": score, "scenarios": summaries}
        )
    best = max(
        rows, key=lambda x: (x["selection_score_cents"], -x["policy"]["capacity"])
    )
    (output / "policy_comparison.json").write_text(json.dumps(rows, indent=2) + "\n")
    (ROOT / "selected_policy.json").write_text(
        json.dumps(best["policy"], indent=2) + "\n"
    )
    (output / "selection.json").write_text(
        json.dumps(
            {
                "selected": best["policy"],
                "score_cents": best["selection_score_cents"],
                "weights_are_design_weights_not_market_probabilities": True,
                "launch_against_zero_cost_stop": best["selection_score_cents"] > 0,
                "development_seed_count": 12,
                "policies": 24,
                "unique_parameter_combinations": 20,
                "no_live_demand_validation": True,
            },
            indent=2,
        )
        + "\n"
    )
    witness = run_world(CONFIG["development_seeds"][0], "reference", best["policy"])
    (output / "witness.json").write_text(json.dumps(witness, indent=2) + "\n")
    print(
        json.dumps(
            {
                "selected": best["policy"],
                "score_usd": best["selection_score_cents"] / 100,
            }
        )
    )


def confirm(seed_file: Path, output: Path) -> None:
    """Require a matching frozen source/policy manifest and independently issued fresh seeds."""
    freeze = json.loads((ROOT / "FREEZE.json").read_text())
    for name, expected in freeze["sha256"].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Frozen file changed: {name}")
    bank = json.loads(seed_file.read_text())
    seeds = bank.get("seeds", bank.get("economic_seeds", []))
    if "freeze_sha256" in bank:
        if (
            hashlib.sha256((ROOT.parent / "FREEZE.json").read_bytes()).hexdigest()
            != bank["freeze_sha256"]
        ):
            raise ValueError("Study freeze does not match verifier seed bank")
    elif (
        bank.get("economic_freeze_sha256")
        != hashlib.sha256((ROOT / "FREEZE.json").read_bytes()).hexdigest()
    ):
        raise ValueError("Verifier seed bank must bind the study or economic freeze")
    if (
        len(seeds) < 128
        or len(set(seeds)) != len(seeds)
        or set(seeds) & set(CONFIG["development_seeds"])
    ):
        raise ValueError("At least 128 unique fresh verifier-issued seeds are required")
    policy = json.loads((ROOT / "selected_policy.json").read_text())
    output.mkdir(parents=True, exist_ok=True)
    summaries, worlds_out = {}, []
    for name in CONFIG["scenarios"]:
        worlds = [run_world(s, name, policy) for s in seeds]
        summaries[name] = summarize(worlds)
        for world in worlds:
            world_path = output / "worlds" / f"{name}-{world['seed']}.json"
            world_path.parent.mkdir(exist_ok=True)
            world_path.write_text(json.dumps(world, separators=(",", ":")) + "\n")
            worlds_out.append(
                {
                    "path": str(world_path.relative_to(output)),
                    "sha256": hashlib.sha256(world_path.read_bytes()).hexdigest(),
                }
            )
    reference = [run_world(s, "reference", policy, True) for s in seeds]
    summaries["conventional_same_arrangement"] = summarize(reference)
    stopped = [run_no_launch(s) for s in seeds]
    summaries["no_launch_after_research"] = summarize(stopped)
    (output / "no_launch_witness.json").write_text(
        json.dumps(stopped[0], indent=2) + "\n"
    )
    (output / "summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
    (output / "world_manifest.json").write_text(json.dumps(worlds_out, indent=2) + "\n")
    print(json.dumps(summaries, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["develop", "confirm", "world"])
    parser.add_argument("--seed-file", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "development")
    args = parser.parse_args()
    if args.mode == "develop":
        develop(args.output)
    elif args.mode == "confirm":
        if args.seed_file is None:
            parser.error("--seed-file is required")
        confirm(args.seed_file, args.output)
    else:
        print(json.dumps(run_world(12001, "reference", policy_grid()[0]), indent=2))


if __name__ == "__main__":
    main()
