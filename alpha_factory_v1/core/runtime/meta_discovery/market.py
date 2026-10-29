# SPDX-License-Identifier: Apache-2.0
"""Conditional competitive exchange simulation; no observed demand or external money."""

from __future__ import annotations
import random
import time
import math
from .comparators import direct_plan
from pathlib import Path
from typing import Any
from .instrument import compile_plan, digest
from .checker import check, reference
from .models import make_task
from .exchange import Exchange
from .economics import Financials

SCENARIOS = ["reference", "free_completed_alternative", "low_trust", "copying", "supplier_failure", "cost_stress"]
PRICES = [1_000_000, 2_000_000, 4_000_000]
SEED_COST = 3_000_000


def operate(root: Path, seed: int, scenario: str, price: int, arm: str) -> dict[str, Any]:
    if scenario not in SCENARIOS or arm not in {"instrument", "conventional"}:
        raise ValueError("scope")
    root.mkdir(exist_ok=False, parents=True)
    db = Exchange(root / "exchange.sqlite")
    rng = random.Random(seed)
    cost = SEED_COST * (20 if scenario == "cost_stress" else 1)
    attempts = []
    accepted = 0
    departures = 0
    reversals = 0
    cpu_start = time.process_time()
    fee_cost = 0
    for i in range(24):
        value = rng.randint(3, 12) * 1_000_000
        trust_cost = int(rng.random() * (8 if scenario == "low_trust" else 1) * 1_000_000)
        delay_cost = rng.randint(0, 500_000)
        competitor = (
            0
            if scenario == "free_completed_alternative"
            else max(100_000, 4_000_000 - i * 180_000)
            if scenario == "copying"
            else rng.randint(2, 6) * 1_000_000
        )
        buyer_cash = rng.randint(0, 9) * 1_000_000
        outage = rng.random() < (0.35 if scenario == "supplier_failure" else 0.02)
        reverse = rng.random() < 0.06
        release_delay = rng.randint(1, 14)
        inconclusive = rng.random() < 0.02
        disputed = rng.random() < 0.15
        clock = 20 * i
        buyer = f"b{i}"
        ident = f"order-{i}"
        participate = (
            buyer_cash >= price
            and value > price + trust_cost + delay_cost
            and price + trust_cost + delay_cost <= competitor
        )
        row: dict[str, Any] = {
            "id": ident,
            "offered": price,
            "outsideCompletedCost": competitor,
            "trustCost": trust_cost,
            "delayCost": delay_cost,
            "buyerCash": buyer_cash,
            "participates": participate,
            "cost": 0,
            "outcome": "declined",
        }
        if not participate:
            departures += 1
            attempts.append(row)
            continue
        task, _ = make_task(["catalyst", "membrane", "photovoltaic"][i % 3], seed * 100 + i, i % 4)
        db.provision_simulated_buyer(buyer, "manager-usdc", buyer_cash)
        db.offer(ident, "meta-discovery-20261028", buyer, "manager-usdc", "USDC", 6, price, task, clock + 10)
        db.event(ident, f"{ident}-consent", "consent", {"buyer": buyer, "termsHash": db.terms_hash(ident)}, clock)
        db.event(ident, f"{ident}-fund", "fund", {"buyer": buyer}, clock)
        row["productionAttempted"] = True
        if outage:
            db.event(ident, f"{ident}-timeout", "timeout", {}, clock + 11)
            row["outcome"] = "outage-refund"
            attempts.append(row)
            continue
        plan = compile_plan(task) if arm == "instrument" else direct_plan(task)
        verification = check(task, plan)
        if not verification["accepted"]:
            raise ValueError("failed production acceptance")
        db.event(ident, f"{ident}-deliver", "deliver", {"artifact": plan}, clock + 1)
        if inconclusive:
            db.event(ident, f"{ident}-validator-timeout", "timeout", {}, clock + 11)
            row["outcome"] = "inconclusive-validator-refund"
            attempts.append(row)
            continue
        db.event(ident, f"{ident}-verify", "verify", {}, clock + 1)
        if release_delay > 10:
            db.event(ident, f"{ident}-settlement-timeout", "timeout", {}, clock + 11)
            row["outcome"] = "delayed-settlement-refund"
            attempts.append(row)
            continue
        db.event(ident, f"{ident}-settle", "dispute" if disputed else "settle", {}, clock + release_delay)
        raw = db.download(ident, buyer)
        accepted += 1
        row.update(outcome="accepted", artifactHash=digest(plan), bytes=len(raw), scientificVerdict=plan["status"])
        fee = int(price * 0.025)
        cost += fee
        fee_cost += fee
        row["cost"] += fee
        if reverse:
            db.event(ident, f"{ident}-chargeback", "chargeback", {}, clock + 15)
            reversals += 1
            row["outcome"] = "accepted-later-reversed"
        attempts.append(row)
    cpu_seconds = time.process_time() - cpu_start
    cpu_cost = math.ceil(cpu_seconds * 100_000 / 3600)
    storage_bytes = (root / "exchange.sqlite").stat().st_size
    storage_cost = math.ceil(storage_bytes / 1e9 * 0.03 * 1_000_000)
    cost += cpu_cost + storage_cost
    accounts = db.accounting("manager-usdc")
    financials = Financials(
        opening=100_000_000,
        revenue=accounts["revenue"],
        expenses=cost,
        collections=accounts["cash"],
        payments=min(cost, 100_000_000 + accounts["cash"]),
    )
    result = {
        "seed": seed,
        "scenario": scenario,
        "arm": arm,
        "priceMicroUSD": price,
        "accepted": accepted,
        "declined": departures,
        "reversals": reversals,
        "financial": financials.report(),
        "exchange": accounts,
        "attempts": attempts,
        "investment": financials.invest(2_000_000, 0),
        "fundedConstruction": False,
        "investmentReason": "Incremental successor benefit has not been identified or measured. Expected net value is conservatively set to zero, not inferred from profitability. No funded construction is claimed.",
        "economicBasis": "conditional analyst model; no calibrated demand probability; seed costs include B/C",
        "costUnits": "microUSD; all deterministic acquisition/production/checking/support CPU measured together; no inference during orders",
        "costLedger": [
            {
                "layer": "C",
                "activity": "seed research development and validation",
                "quantity": 300000 * (20 if scenario == "cost_stress" else 1),
                "unit": "estimated input tokens",
                "rateUSD": 0.000005,
                "allocation": "entire hypothetical seed cost once per alternative world",
            },
            {
                "layer": "C",
                "activity": "seed implementation and correction",
                "quantity": 50000 * (20 if scenario == "cost_stress" else 1),
                "unit": "estimated output tokens",
                "rateUSD": 0.00003,
            },
            {
                "layer": "A",
                "activity": "all world CPU including failures",
                "quantity": cpu_seconds,
                "unit": "CPU second",
                "rateUSD": 0.1 / 3600,
            },
            {
                "layer": "B",
                "activity": "one-month artifact retention",
                "quantity": storage_bytes / 1e9,
                "unit": "GB-month",
                "rateUSD": 0.03,
            },
            {
                "layer": "A",
                "activity": "settlement fees",
                "quantity": fee_cost / 25000,
                "unit": "gross settled USD",
                "rateUSD": 0.025,
            },
        ],
        "ratesBasis": "Explicit sensitivity assumptions, not observed provider invoices; C multiplied by 20 in cost_stress",
        "journal": [dict(x) for x in db.db.execute("SELECT * FROM journal")],
        "events": [dict(x) for x in db.db.execute("SELECT * FROM events")],
        "physicalQualified": False,
    }
    db.close()
    (root / "exchange.sqlite").unlink()
    root.rmdir()
    return result
