# SPDX-License-Identifier: Apache-2.0
"""Finite, prospective offering search. Every market parameter is assumed.

No API calls, customer transactions, proprietary data, or population calibration.
See PROTOCOL.md before interpreting numerical results.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import random
import statistics
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PRICES = (500, 1000, 1500, 2500, 4000, 6000)
TERMS = ((0.0, 1.0),) + tuple(itertools.product((0.25, 0.5, 0.75), (0.5, 1.0)))
ARMS = ("expert_standard", "retained_standard", "expert_arranged", "retained_arranged")


@dataclass(frozen=True)
class Scenario:
    name: str = "central_assumptions"
    seed_cash: float = 6000
    common_build: float = 2400
    retention: float = 400
    retained_cost_ratio: float = 0.55
    common_quality: float = 0.94
    local_quality: float = 0.97
    default_probability: float = 0.05
    withdrawal_probability: float = 0.08
    configuration_probability: float = 0.3
    compatibility_probability: float = 0.7
    max_leads: int = 7
    full_refunds_only: bool = False
    capacity_hours: float = 80
    cash_hour_rate: float = 80
    research_assessment: float = 100
    support_per_job: float = 50
    minimum_quality: float = 0.85


@dataclass(frozen=True)
class Buyer:
    id: str
    human_hours: float
    assumed_human_rate: float
    outside_price: float
    value: float
    customer_effort: float
    configured: bool
    rights: bool
    compatible: bool
    expert_hours: float
    adaptation_hours: float
    technical_uniform: float
    local_uniform: float
    default_uniform: float
    withdrawal_uniform: float


def needs(seed: int, s: Scenario) -> list[Buyer]:
    """Draw needs first; never select compatible buyers by construction."""
    rng = random.Random(seed)
    rows = []
    n = rng.randint(1, s.max_leads)
    for i in range(n):
        configured = rng.random() < s.configuration_probability
        human_hours = rng.uniform(2, 8) if configured else rng.uniform(12, 31)
        rate = rng.uniform(125, 225)
        outside = human_hours * rate
        rows.append(
            Buyer(
                id=f"need-{seed}-{i}",
                human_hours=human_hours,
                assumed_human_rate=rate,
                outside_price=outside,
                value=outside * rng.uniform(0.7, 2.2),
                customer_effort=rng.uniform(40, 240),
                configured=configured,
                rights=rng.random() >= 0.12,
                compatible=rng.random() < s.compatibility_probability,
                expert_hours=rng.uniform(2, 8) if configured else rng.uniform(8, 20),
                adaptation_hours=rng.uniform(0, 4),
                technical_uniform=rng.random(),
                local_uniform=rng.random(),
                default_uniform=rng.random(),
                withdrawal_uniform=rng.random(),
            )
        )
    return rows


def job_terms(b: Buyer, s: Scenario, retained: bool) -> dict[str, float]:
    use = retained and b.compatible
    hours = (b.expert_hours * s.retained_cost_ratio + b.adaptation_hours) if use else b.expert_hours
    qc = s.common_quality if use else 0.97
    q = qc * s.local_quality
    preparation = 0.2 * hours * s.cash_hour_rate + 20
    delivery = 0.8 * hours * s.cash_hour_rate + 15
    return {
        "hours": hours,
        "qc": qc,
        "q": q,
        "preparation": preparation,
        "delivery": delivery,
        "support": s.support_per_job,
    }


def evaluate_plan(
    buyers: list[Buyer], s: Scenario, arm: str, price: float, advance: float, refund: float
) -> dict[str, Any] | None:
    retained = arm.startswith("retained")
    if not buyers:
        return None
    ts = [job_terms(b, s, retained) for b in buyers]
    if not all(b.rights and t["q"] >= s.minimum_quality for b, t in zip(buyers, ts)):
        return None
    # The additional admission hurdle is checked before detailed assessment.
    compatible = sum(b.compatible for b in buyers)
    reachable_margin_bound = sum(max(0, b.outside_price) for b in buyers if b.compatible)
    if retained and (compatible == 0 or reachable_margin_bound < s.retention):
        return None
    utilities = []
    for b, t in zip(buyers, ts):
        q = t["q"]
        expected_payment = q * price + (1 - q) * (1 - refund) * advance * price
        u = q * b.value - expected_payment - b.customer_effort
        outside = max(b.value - b.outside_price, 0)
        if u + 1e-9 < outside:
            return None
        utilities.append(
            {"buyer": b.id, "offer": u, "outside": outside, "gain": u - outside, "expected_payment": expected_payment}
        )
    fixed_a = s.common_build if retained else 0
    fixed_b = s.retention if retained else 0
    hours = sum(t["hours"] for t in ts) + (fixed_a + fixed_b) / s.cash_hour_rate
    if hours > s.capacity_hours:
        return None
    # Parallel staffing is a declared capacity assumption, not observed service time.
    days = hours / 8
    if days > 10:
        return None
    deposit = len(buyers) * advance * price
    refund_reserve = refund * deposit
    # Full precollection funding; no sale on credit finances its own delivery.
    full_cost = (
        fixed_a + fixed_b + s.research_assessment + sum(t["preparation"] + t["delivery"] + t["support"] for t in ts)
    )
    opening_cash = max(0, full_cost - deposit + refund_reserve)
    expected_bad_debt = sum(t["q"] * (1 - advance) * price * s.default_probability for t in ts)
    expected_a = (
        fixed_a + sum(t["preparation"] + t["qc"] * t["delivery"] + t["support"] for t in ts) + expected_bad_debt
    )
    expected_revenue = sum(t["q"] * price + (1 - t["q"]) * (1 - refund) * advance * price for t in ts)
    expected_profit = expected_revenue - expected_a - fixed_b - s.research_assessment
    if expected_profit < 0:
        return None
    return {
        "arm": arm,
        "buyers": [b.id for b in buyers],
        "price": price,
        "advance_fraction": advance,
        "failure_refund_fraction": refund,
        "quality": min(t["q"] for t in ts),
        "hours": hours,
        "days": days,
        "required_opening_cash": opening_cash,
        "opening_cash_available": s.seed_cash,
        "financeable": opening_cash <= s.seed_cash + 1e-9,
        "expected_profit": expected_profit,
        "expected_revenue": expected_revenue,
        "expected_bad_debt": expected_bad_debt,
        "expected_net_receipts": expected_revenue - expected_bad_debt,
        "expected_A": expected_a,
        "B": fixed_b,
        "C": s.research_assessment,
        "advance_collections": deposit,
        "unearned_at_contract": deposit,
        "refund_reserve_at_contract": refund_reserve,
        "participation": utilities,
        "admission_margin_upper_bound": reachable_margin_bound,
        "admission_additional_cost": fixed_b,
    }


def choose(buyers: list[Buyer], s: Scenario, arm: str) -> dict[str, Any]:
    terms = TERMS if arm.endswith("arranged") else ((0.0, 1.0),)
    candidates = []
    profitable_unfunded = 0
    for price, (advance, refund) in itertools.product(PRICES, terms):
        if s.full_refunds_only and refund != 1:
            continue
        for mask in range(1, 1 << len(buyers)):
            subset = [b for i, b in enumerate(buyers) if mask & (1 << i)]
            p = evaluate_plan(subset, s, arm, price, advance, refund)
            if p is None:
                continue
            if p["financeable"]:
                candidates.append(p)
            else:
                profitable_unfunded += 1
    if not candidates:
        return {
            "arm": arm,
            "action": "stop",
            "buyers": [],
            "expected_profit": -s.research_assessment,
            "required_opening_cash": 0,
            "profitable_unfunded_packages": profitable_unfunded,
        }
    # Tie breaking preserves cash rather than compelling a larger investment.
    best = max(candidates, key=lambda p: (p["expected_profit"], -p["required_opening_cash"], -len(p["buyers"])))
    return {**best, "action": "produce", "profitable_unfunded_packages": profitable_unfunded}


def realize(plan: dict[str, Any], buyers: list[Buyer], s: Scenario, seed: int) -> dict[str, Any]:
    """Real cash and accrual rules applied to simulated events, with exact-once costs."""
    if plan["action"] == "stop":
        cost = s.research_assessment
        return {
            "action": "stop",
            "collections": 0,
            "earned_revenue": 0,
            "refunds": 0,
            "expenses": cost,
            "profit": -cost,
            "cash": s.seed_cash - cost,
            "accepted": 0,
            "obligations": 0,
            "reserves": 0,
            "available_funds": s.seed_cash - cost,
            "receivables": 0,
            "ledger": [
                {
                    "day": 0,
                    "kind": "expense",
                    "bucket": "C",
                    "activity": "additional-prospect-assessment",
                    "amount": cost,
                    "cash": s.seed_cash - cost,
                    "unearned": 0,
                    "receivables": 0,
                }
            ],
            "withdrawn": 0,
        }
    retained = plan["arm"].startswith("retained")
    selected = [b for b in buyers if b.id in plan["buyers"]]
    p, a, r = plan["price"], plan["advance_fraction"], plan["failure_refund_fraction"]
    ledger: list[dict[str, Any]] = []
    cash, collections, refunds, earned, expenses, unearned = s.seed_cash, 0.0, 0.0, 0.0, 0.0, 0.0
    receivables, written_off, accepted = 0.0, 0.0, 0
    seen: set[str] = set()

    def event(day: int, kind: str, amount: float, activity: str, bucket: str | None = None) -> None:
        nonlocal cash, collections, refunds, earned, expenses, unearned, receivables, written_off
        if activity in seen:
            raise ValueError("duplicate activity")
        seen.add(activity)
        if kind == "collect_advance":
            cash += amount
            collections += amount
            unearned += amount
        elif kind == "refund":
            cash -= amount
            refunds += amount
            unearned -= amount
        elif kind == "earn_advance":
            earned += amount
            unearned -= amount
        elif kind == "expense":
            cash -= amount
            expenses += amount
        elif kind == "invoice":
            earned += amount
            receivables += amount
        elif kind == "collect_invoice":
            cash += amount
            collections += amount
            receivables -= amount
        elif kind == "writeoff":
            expenses += amount
            receivables -= amount
            written_off += amount
        else:
            raise ValueError(kind)
        ledger.append(
            {
                "day": day,
                "activity": activity,
                "kind": kind,
                "bucket": bucket,
                "amount": round(amount, 6),
                "cash": round(cash, 6),
                "unearned": round(unearned, 6),
                "receivables": round(receivables, 6),
            }
        )

    event(0, "expense", s.research_assessment, "additional-prospect-assessment", "C")
    active = []
    for b in selected:
        event(1, "collect_advance", a * p, b.id + "-advance")
        if b.withdrawal_uniform < s.withdrawal_probability:
            event(1, "refund", a * p, b.id + "-withdrawal-refund")
        else:
            active.append(b)
    # Replan only on observed withdrawal, before construction; terms stay frozen.
    revised = evaluate_plan(active, s, plan["arm"], p, a, r) if active else None
    if revised is None or not revised["financeable"]:
        for b in active:
            event(1, "refund", a * p, b.id + "-cancelled-before-build")
        return {
            "action": "cancel_after_withdrawal",
            "collections": collections,
            "refunds": refunds,
            "earned_revenue": earned,
            "expenses": expenses,
            "profit": earned - expenses,
            "cash": cash,
            "accepted": 0,
            "obligations": 0,
            "reserves": 0,
            "available_funds": cash,
            "receivables": 0,
            "ledger": ledger,
            "withdrawn": len(selected) - len(active),
        }
    if retained:
        event(2, "expense", s.common_build, "commissioned-common-construction", "A")
        event(2, "expense", s.retention, "additional-retention-and-upkeep", "B")
    common_draw = random.Random(seed + 900000).random()
    for b in active:
        t = job_terms(b, s, retained)
        event(2, "expense", t["preparation"], b.id + "-preparation", "A")
        common_pass = (common_draw < t["qc"]) if retained and b.compatible else b.technical_uniform < t["qc"]
        ok = common_pass and b.local_uniform < s.local_quality
        if common_pass:
            event(3, "expense", t["delivery"], b.id + "-conditional-delivery", "A")
        event(4, "expense", t["support"], b.id + "-support", "A")
        if ok:
            accepted += 1
            event(5, "earn_advance", a * p, b.id + "-accepted-development")
            event(5, "invoice", (1 - a) * p, b.id + "-accepted-audit")
            if b.default_uniform < s.default_probability:
                event(30, "writeoff", (1 - a) * p, b.id + "-default", "A")
            else:
                event(30, "collect_invoice", (1 - a) * p, b.id + "-balance")
        else:
            event(5, "refund", r * a * p, b.id + "-failure-refund")
            event(5, "earn_advance", (1 - r) * a * p, b.id + "-accepted-development-failure-record")
    assert abs(unearned) < 1e-7 and abs(receivables) < 1e-7
    assert min(x["cash"] for x in ledger) >= -1e-7
    profit = earned - expenses
    assert abs(cash - s.seed_cash - profit) < 1e-6
    return {
        "action": "produced",
        "collections": collections,
        "refunds": refunds,
        "earned_revenue": earned,
        "expenses": expenses,
        "profit": profit,
        "cash": cash,
        "accepted": accepted,
        "obligations": unearned,
        "reserves": 0,
        "available_funds": cash,
        "receivables": receivables,
        "bad_debt_expense": written_off,
        "ledger": ledger,
        "withdrawn": len(selected) - len(active),
    }


def scenarios() -> list[Scenario]:
    s = Scenario()
    return [
        s,
        replace(s, name="low_opening_cash", seed_cash=1500),
        replace(s, name="high_opening_cash", seed_cash=12000),
        replace(s, name="high_common_cost", common_build=9600),
        replace(s, name="negative_transfer", retained_cost_ratio=1.25),
        replace(s, name="efficient_incumbent", configuration_probability=0.9),
        replace(s, name="low_demand", max_leads=2),
        replace(s, name="full_refund_contract", full_refunds_only=True),
        replace(s, name="payment_and_withdrawal_stress", default_probability=0.25, withdrawal_probability=0.3),
        replace(s, name="ordinary_defaults_progress", retained_cost_ratio=1.0, common_build=2400),
        replace(s, name="quality_obsolescence", common_quality=0.82),
    ]


def execute(seeds: range, out: Path, confirm: bool) -> None:
    out.mkdir(parents=True, exist_ok=True)
    frozen = ROOT / "freeze.json"
    identities = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "model.py", ROOT / "PROTOCOL.md")}
    if confirm:
        manifest = json.loads(frozen.read_text())
        if manifest["files"] != identities:
            raise ValueError("prospective freeze mismatch")
    rows = []
    examples = []
    for s in scenarios() if confirm else [Scenario()]:
        for seed in seeds:
            bs = needs(seed, s)
            for arm in ARMS:
                p = choose(bs, s, arm)
                result = realize(p, bs, s, seed)
                row = {
                    "scenario": s.name,
                    "seed": seed,
                    "arm": arm,
                    "needs": len(bs),
                    "selected": len(p["buyers"]),
                    "plan": p,
                    "result": {k: v for k, v in result.items() if k != "ledger"},
                }
                rows.append(row)
                if len(examples) < 8 and result["action"] == "produced":
                    examples.append(
                        {
                            "scenario": asdict(s),
                            "seed": seed,
                            "buyers": [asdict(b) for b in bs],
                            "plan": p,
                            "realization": result,
                        }
                    )
    summary = []
    for s in scenarios() if confirm else [Scenario()]:
        for arm in ARMS:
            r = [x for x in rows if x["scenario"] == s.name and x["arm"] == arm]
            profits = [x["result"]["profit"] for x in r]
            summary.append(
                {
                    "scenario": s.name,
                    "arm": arm,
                    "horizons": len(r),
                    "financeable_horizons": sum(x["plan"]["action"] == "produce" for x in r),
                    "profitable_but_unfunded_horizons": sum(x["plan"]["profitable_unfunded_packages"] > 0 for x in r),
                    "accepted_audits": sum(x["result"]["accepted"] for x in r),
                    "mean_profit": statistics.mean(profits),
                    "min_profit": min(profits),
                    "max_profit": max(profits),
                    "loss_horizons": sum(x < 0 for x in profits),
                }
            )
    crossings = []
    for s in scenarios() if confirm else [Scenario()]:
        selected = [x for x in rows if x["scenario"] == s.name]
        by_seed: dict[int, dict[str, Any]] = {}
        for x in selected:
            by_seed.setdefault(x["seed"], {})[x["arm"]] = x
        crossings.append(
            {
                "scenario": s.name,
                "combined_feasible_neither_alone": sum(
                    r["retained_arranged"]["plan"]["action"] == "produce"
                    and r["retained_standard"]["plan"]["action"] == "stop"
                    and r["expert_arranged"]["plan"]["action"] == "stop"
                    for r in by_seed.values()
                ),
                "combined_vs_expert_standard_crossing": sum(
                    r["retained_arranged"]["plan"]["action"] == "produce"
                    and r["expert_standard"]["plan"]["action"] == "stop"
                    for r in by_seed.values()
                ),
                "both_feasible_not_a_crossing": sum(
                    r["retained_arranged"]["plan"]["action"] == "produce"
                    and r["expert_standard"]["plan"]["action"] == "produce"
                    for r in by_seed.values()
                ),
            }
        )
    outputs = {
        "rows.json": rows,
        "summary.json": summary,
        "crossings.json": crossings,
        "cash_examples.json": examples,
        "assumptions.json": [asdict(s) for s in scenarios()],
    }
    for name, obj in outputs.items():
        (out / name).write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "rows": len(rows),
                "output": str(out),
                "actual_revenue": 0,
                "actual_complete_cost": None,
                "market_status": "wholly_assumed_simulation",
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("development", "freeze", "confirmation"))
    args = parser.parse_args()
    if args.mode == "freeze":
        manifest = {
            "policy": "finite-menu-v1",
            "seeds": [21000, 21079],
            "files": {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / "model.py", ROOT / "PROTOCOL.md")
            },
            "claim": "no observed demand or economic calibration",
        }
        (ROOT / "freeze.json").write_text(json.dumps(manifest, indent=2) + "\n")
        print(json.dumps(manifest))
    else:
        execute(
            range(21000, 21080) if args.mode == "confirmation" else range(110, 122),
            ROOT / args.mode,
            args.mode == "confirmation",
        )
