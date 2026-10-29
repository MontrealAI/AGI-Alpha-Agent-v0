# SPDX-License-Identifier: Apache-2.0
"""A bounded, conditional competitive audit market with actual checked artifacts."""

from __future__ import annotations

import math
import random
import time
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from typing import Any

from alpha_factory_v1.core.runtime.claim_probe import checker, contracts, instrument
from alpha_factory_v1.core.runtime.meta_discovery.economics import Financials
from alpha_factory_v1.core.runtime.meta_discovery.exchange import Exchange
from contrib.claim_probe.comparators import ordinary_library
from contrib.claim_probe.generate import make_task

SCENARIOS = ["reference", "free_completed_alternative", "copying", "low_trust", "supplier_failure", "cost_stress"]
PRICES = [2_000_000, 5_000_000, 10_000_000]
RATES = {
    "inputPerMillionUSD": 5,
    "outputPerMillionUSD": 30,
    "CPUHourUSD": 0.1,
    "GBMonthUSD": 0.03,
    "settlementRate": 0.025,
    "chargebackUSD": 0.2,
    "annualCapitalRate": 0.15,
}


def operate(root: Path, seed: int, scenario: str, price: int, arm: str) -> dict[str, Any]:
    """Execute separate, paired-world orders; all assets and accounts are simulated."""
    if scenario not in SCENARIOS or arm not in {"instrument", "ordinary_library"}:
        raise ValueError("market scope")
    root.mkdir(parents=True, exist_ok=False)
    db = Exchange(
        root / "exchange.sqlite",
        contract_id="claim-probe/v1",
        task_validator=contracts.validate,
        result_checker=checker.check,
    )
    rng = random.Random(seed)
    cpu_start = time.process_time()
    multiplier = 20 if scenario == "cost_stress" else 1
    costs: list[dict[str, Any]] = [
        {
            "id": "seed-input",
            "layer": "C",
            "activity": "autonomous seed research, implementation, failures and validation",
            "quantity": 900000 * multiplier,
            "unit": "estimated input token",
            "rateUSD": RATES["inputPerMillionUSD"] / 1e6,
            "basis": "estimated",
        },
        {
            "id": "seed-output",
            "layer": "C",
            "activity": "autonomous seed implementation and corrections",
            "quantity": 100000 * multiplier,
            "unit": "estimated output token",
            "rateUSD": RATES["outputPerMillionUSD"] / 1e6,
            "basis": "estimated",
        },
        {
            "id": "integration-input",
            "layer": "B",
            "activity": "incremental packaging, integration, source audit and upkeep",
            "quantity": 60000,
            "unit": "estimated input token",
            "rateUSD": RATES["inputPerMillionUSD"] / 1e6,
            "basis": "estimated",
        },
        {
            "id": "integration-output",
            "layer": "B",
            "activity": "incremental interface implementation and handoff",
            "quantity": 10000,
            "unit": "estimated output token",
            "rateUSD": RATES["outputPerMillionUSD"] / 1e6,
            "basis": "estimated",
        },
    ]
    costs.extend(
        [
            {
                "id": "seed-compute",
                "layer": "C",
                "activity": "seed builds, failed attempts, training and reproduction computation",
                "quantity": 600,
                "unit": "estimated CPU second",
                "rateUSD": RATES["CPUHourUSD"] / 3600,
                "basis": "estimated",
            },
            {
                "id": "retained-environment",
                "layer": "B",
                "activity": "one source/dependency environment retained for one month",
                "quantity": 1.5,
                "unit": "estimated GB-month",
                "rateUSD": RATES["GBMonthUSD"],
                "basis": "estimated",
            },
        ]
    )
    fees = 0
    capital_days = 0.0
    rows = []
    occupied = []
    for i in range(24):
        value = rng.randint(4, 50) * 1_000_000
        outside = (
            0
            if scenario == "free_completed_alternative"
            else max(200_000, 14_000_000 - i * 550_000)
            if scenario == "copying"
            else rng.randint(3, 18) * 1_000_000
        )
        buyer_cash = rng.randint(0, 40) * 1_000_000
        trust = rng.randint(0, 12 if scenario == "low_trust" else 2) * 1_000_000
        delay = rng.randint(1, 14)
        outage = rng.random() < (0.3 if scenario == "supplier_failure" else 0.02)
        reverse = rng.random() < 0.06
        disputed = rng.random() < 0.15
        inconclusive = rng.random() < 0.03
        service_days = rng.randint(1, 4)
        occupied = [end for end in occupied if end > i]
        capacity = len(occupied) < 2
        lock_cost = math.ceil(price * 0.15 * delay / 365)
        total_buyer = price + trust + lock_cost
        participates = capacity and buyer_cash >= price and value >= total_buyer and total_buyer <= outside
        row = {
            "id": f"order-{i}",
            "price": price,
            "outsideCompletedCost": outside,
            "buyerValue": value,
            "buyerCash": buyer_cash,
            "trustCost": trust,
            "lockCost": lock_cost,
            "capacityAvailable": capacity,
            "participates": participates,
            "outcome": "declined",
        }
        if not participates:
            rows.append(row)
            continue
        occupied.append(i + service_days)
        buyer = f"buyer-{i}"
        ident = row["id"]
        task = make_task(seed * 100 + i, ["positive", "narrow", "tangency"][i % 3], i)
        db.provision_simulated_buyer(buyer, "manager-usdc", buyer_cash)
        db.offer(ident, "AGI-ALPHA-RESEARCH-ENTERPRISE-20261028", buyer, "manager-usdc", "USDC", 6, price, task, i + 10)
        db.event(ident, ident + "-consent", "consent", {"buyer": buyer, "termsHash": db.terms_hash(ident)}, i)
        db.event(ident, ident + "-fund", "fund", {"buyer": buyer}, i)
        assert db.preview(ident).keys() <= {
            "id",
            "campaign",
            "route",
            "currency",
            "decimals",
            "price",
            "state",
            "artifact_hash",
            "deadline",
        }
        try:
            db.download(ident, buyer)
        except PermissionError:
            pass
        else:
            raise ValueError("premature artifact release")
        capital_days += (price / 1e6) * min(delay, 11)
        if outage:
            db.event(ident, ident + "-timeout", "timeout", {}, i + 11)
            row["outcome"] = "supplier-refund"
        else:
            result = ordinary_library(task)
            verdict = checker.check(task, result)
            if not verdict["accepted"]:
                raise ValueError("production artifact failed independent checking")
            db.event(ident, ident + "-deliver", "deliver", {"artifact": result}, i + 1)
            if not verdict["decisive"] or inconclusive or delay > 10:
                db.event(ident, ident + "-timeout", "timeout", {}, i + 11)
                row["outcome"] = "incomplete-or-delayed-refund"
            else:
                db.event(ident, ident + "-verify", "verify", {}, i + 1)
                db.event(ident, ident + "-settle", "dispute" if disputed else "settle", {}, i + delay)
                raw = db.download(ident, buyer)
                row.update(
                    outcome="accepted",
                    artifactHash=contracts.digest(result),
                    bytes=len(raw),
                    conclusion=result["status"],
                )
                fees += math.ceil(price * 0.025)
                if reverse:
                    db.event(ident, ident + "-chargeback", "chargeback", {}, i + 15)
                    fees += 200000
                    row["outcome"] = "accepted-later-reversed"
        rows.append(row)
    accounts = db.accounting("manager-usdc")
    cpu = time.process_time() - cpu_start
    storage = (root / "exchange.sqlite").stat().st_size
    costs.extend(
        [
            {
                "id": "CPU",
                "layer": "A",
                "activity": "all acquisition, negotiation, production, checking, retry/refund/support and journal computation",
                "quantity": cpu,
                "unit": "measured CPU second",
                "rateUSD": RATES["CPUHourUSD"] / 3600,
                "basis": "measured",
            },
            {
                "id": "storage",
                "layer": "B",
                "activity": "complete private artifact and journal retention for one month",
                "quantity": storage / 1e9,
                "unit": "measured GB-month quantity",
                "rateUSD": RATES["GBMonthUSD"],
                "basis": "measured",
            },
            {
                "id": "payment",
                "layer": "A",
                "activity": "settlement, disputes and irreversible chargeback fees",
                "quantity": fees / 1e6,
                "unit": "USD fees",
                "rateUSD": 1,
                "basis": "modeled",
            },
            {
                "id": "financing",
                "layer": "A",
                "activity": "capital tied up while producing/waiting, conservative price-sized exposure",
                "quantity": capital_days,
                "unit": "USD-day",
                "rateUSD": RATES["annualCapitalRate"] / 365,
                "basis": "estimated",
            },
        ]
    )
    expense = sum(
        int(
            (Decimal(str(x["quantity"])) * Decimal(str(x["rateUSD"])) * 1000000).to_integral_value(
                rounding=ROUND_CEILING
            )
        )
        for x in costs
    )
    reserve = 2_000_000
    financial = Financials(
        opening=25_000_000,
        revenue=accounts["revenue"],
        expenses=expense,
        collections=accounts["cash"],
        payments=min(expense, 25_000_000 + accounts["cash"]),
        reserve=reserve,
        working_capital=1_000_000,
        historical_investment=0,
    )
    state = financial.report()
    # Decision is conditional on declared future need, not booked future revenue.
    investment = financial.invest(10_000_000, 2_250_000)
    result = {
        "seed": seed,
        "scenario": scenario,
        "arm": arm,
        "priceMicroUSD": price,
        "offers": rows,
        "exchange": accounts,
        "financial": state,
        "costLedger": costs,
        "expenseMicroUSD": expense,
        "openingCash": 25_000_000,
        "reserveMicroUSD": reserve,
        "workingCapitalMicroUSD": 1_000_000,
        "investment": investment,
        "investmentAssumption": "10 future joint-parameter audit requests, participation 0.25, net price 5 USD, upkeep 0.25 USD, construction cap 10 USD; analyst assumption, not observed demand or present revenue",
        "actualConstruction": False,
        "deploymentPolicy": "Ordinary exact SymPy solver selected before confirmation after training; both market arms share it. Bernstein mechanism remains independently compared in technical evaluation.",
        "authority": "local simulated exchange only; native Jobs/Manager execution unqualified",
        "ratesBasis": "Declared counterfactual production-rate scenario; quantities estimated except CPU/storage. Actual incremental external spend 0; actual session metering/subscription allocation unknown. No API calls or invoices.",
        "scope": "Conditional repeated competitive simulation, not calibrated demand or an equilibrium claim",
    }
    result["journal"] = [dict(x) for x in db.db.execute("SELECT * FROM journal ORDER BY seq")]
    db.close()
    return result
