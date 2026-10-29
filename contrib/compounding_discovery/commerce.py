# SPDX-License-Identifier: Apache-2.0
"""Competitive simulated exchange using actual independent route certificates.

Scenario utilities are authored assumptions, not observed demand. The primary
outside option is an already completed identical free certificate. The secondary
integration-cost scenario is a sensitivity, never a customer or market finding.
"""

from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Any, Callable

from alpha_factory_v1.core.runtime.claim_probe.protected_exchange import ProtectedExchange
from alpha_factory_v1.core.runtime.compounding_discovery import engine
from alpha_factory_v1.core.runtime.structural_transfer import eadarp_check

KEY = b"compounding-commerce-scenario-v1"
CONTRACT = "agialpha/compounding-discovery-simulated-exchange/v1"
SCENARIOS = (
    "free_completed",
    "assumed_integration_cost",
    "low_trust",
    "slow_settlement",
    "scarce_buyer_cash",
    "scarce_seller_liquidity",
    "failed_delivery",
    "late_reversal",
    "nonpayment",
    "assurance_failure",
    "custody_loss",
)
PRICES = (200000, 500000, 1000000, 2000000)
CPU_RATE = Fraction(1, 36000)
DEVELOPMENT = [
    {
        "id": "commerce-development-input",
        "stage": "seed-development",
        "quantity": "40000",
        "rate": "1/200000",
        "amount": "1/5",
        "basis": "estimated-model-token-equivalent",
    },
    {
        "id": "commerce-development-output",
        "stage": "seed-development",
        "quantity": "8000",
        "rate": "3/100000",
        "amount": "6/25",
        "basis": "estimated-model-token-equivalent",
    },
]


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def write(path: Path, value: Any) -> None:
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write("\n")


def cost_micro(value: Fraction) -> int:
    amount = value * 1000000
    return -(-amount.numerator // amount.denominator)


def validate_task(task: dict[str, Any]) -> None:
    eadarp_check.independent_model(task)


def check(task: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    verdict = eadarp_check.check(task, artifact)
    return {**verdict, "decisive": verdict.get("accepted") is True}


def open_exchange(path: Path, opening: int = 50000000) -> ProtectedExchange:
    return ProtectedExchange(
        path, key=KEY, contract=CONTRACT, validate=validate_task, check=check, opening=opening, working=100000
    )


def consent(ex: ProtectedExchange, ident: str) -> None:
    order = ex.order(ident)
    terms = {k: order[k] for k in ["id", "buyer", "price", "rail", "task_hash", "contract", "deadline"]}
    ex.event(ident, "consent-" + ident, "consent", {"buyer": order["buyer"], "termsHash": digest(terms)}, 0)


def must_refuse(fn: Callable[[], Any]) -> str:
    try:
        fn()
    except (ValueError, PermissionError, InterruptedError, sqlite3.IntegrityError) as error:
        return type(error).__name__
    raise AssertionError("required protection accepted an invalid action")


def audit(path: Path) -> dict[str, Any]:
    """Independently reconstruct money from SQL journal and trade state."""
    with sqlite3.connect("file:" + str(path.resolve()) + "?mode=ro", uri=True) as db:
        config = json.loads(db.execute("SELECT value FROM config WHERE id=1").fetchone()[0])
        entries = list(db.execute("SELECT kind,amount FROM journal"))

        def total(kind: str) -> int:
            return sum(int(amount) for k, amount in entries if k == kind)

        trades = list(db.execute("SELECT price,state,custody,refund_due FROM trades"))
        revenue = total("revenue") - total("contra_revenue")
        expense = total("expense")
        collections = total("collections") - total("reversal_paid")
        cash = (
            config["opening"]
            + collections
            + total("recovery_income")
            - total("expense_paid")
            - total("investment_paid")
        )
        refunds = sum(int(row[3]) for row in trades)
        custody = sum(int(row[0]) for row in trades if row[2] and row[1] in {"funded", "verified"})
        tail = sum(int(row[0]) + 200000 for row in trades if row[1] == "released")
        liability = max(0, expense - total("expense_paid")) + refunds
        source_transactions = list(db.execute("SELECT tx FROM source_receipts"))
        event_ids = list(db.execute("SELECT id FROM events"))
        assert len(source_transactions) == len(set(source_transactions))
        assert len(event_ids) == len(set(event_ids))
        assert cash >= 0
    return {
        "revenue": revenue,
        "expenses": expense,
        "profit": revenue + total("recovery_income") - expense,
        "collections": collections,
        "cash": cash,
        "payables": liability,
        "custodyReserve": custody,
        "tailReserve": tail,
        "source_receipts": len(source_transactions),
        "events": len(event_ids),
        "audit_passed": True,
    }


def buyer_choice(scenario: str, price: int, index: int) -> dict[str, Any]:
    outside = 0 if scenario == "free_completed" else 300000
    completion = Fraction(4, 5) if scenario == "low_trust" else Fraction(1)
    delay = 30 if scenario == "slow_settlement" else 2
    trust = 20000
    cash = 100000 if scenario == "scarce_buyer_cash" else 10000000
    value = 5000000
    carry = Fraction(price * 15 * delay, 100 * 365)
    delay_loss = 100000 * delay if scenario == "slow_settlement" else 0
    own = completion * (value - price) - trust - carry - delay_loss
    alternative = value - outside
    accepts = cash >= price and own > alternative
    return {
        "id": f"buyer-{index}",
        "value_assumed_microUSD": value,
        "outside_complete_cost_assumed_microUSD": outside,
        "outside_description": "already completed identical free certificate"
        if outside == 0
        else "free direct solver plus assumed autonomous integration equivalent; sensitivity only",
        "completion_belief": str(completion),
        "cash_microUSD": cash,
        "delay_days": delay,
        "trust_cost_microUSD": trust,
        "lockup_cost_microUSD": str(carry),
        "expected_utility_microUSD": str(own),
        "outside_utility_microUSD": str(alternative),
        "accepts": accepts,
        "basis": "authored simulated preferences; no observed buyer, purchase intent or empirical probabilities",
    }


def run_world(
    root: Path, task: dict[str, Any], captures: list[Any], mapping: dict[str, Any], scenario: str, price: int, arm: str
) -> dict[str, Any]:
    world_started = time.process_time_ns()
    root.mkdir(parents=True, exist_ok=False)
    target = copy.deepcopy(task)
    target["id"] = f"commerce-{scenario}-{price}-{arm}"
    request = {
        "schema": engine.SCHEMA,
        "id": target["id"],
        "target": target,
        "capabilities": dict.fromkeys("ASC", arm == "ASC"),
        "budget": {"operations": 100, "solver_calls": 16, "cpu_seconds": 30},
        "seed": 913,
        "captures": captures,
        "mapping": mapping,
    }
    choices = [buyer_choice(scenario, price, i) for i in range(4)]
    opening = 100000 if scenario == "scarce_seller_liquidity" else 50000000
    ex = open_exchange(root / "exchange.sqlite", opening)
    cost_events = []
    charged_cpu = Fraction(0)

    def charge(ident: str, quantity: str, rate: str, stage: str, basis: str) -> None:
        nonlocal charged_cpu
        amount = Fraction(quantity) * Fraction(rate)
        if basis == "measured-cpu-equivalent":
            charged_cpu += amount / CPU_RATE
        row = {"id": ident, "stage": stage, "quantity": quantity, "rate": rate, "amount": str(amount), "basis": basis}
        ex.cost(ident, cost_micro(amount))
        cost_events.append(row)

    for row in DEVELOPMENT:
        charge(row["id"], row["quantity"], row["rate"], row["stage"], row["basis"])
    outcomes = []
    produced = None
    for choice in choices:
        ident = choice["id"]
        charge(
            "qualification-" + ident,
            "1000",
            "1/200000",
            "autonomous-offer-qualification",
            "estimated-input-token-equivalent",
        )
        if not choice["accepts"]:
            outcomes.append({"buyer": ident, "state": "declined", "reason": "outside-option-or-liquidity"})
            continue
        ex.wallet(ident, choice["cash_microUSD"])
        ex.offer(ident, ident, price, "nonrecourse-simulated", target, 10)
        consent(ex, ident)
        charge(
            "acquisition-" + ident, "10000", "1/200000", "autonomous-acquisition", "estimated-input-token-equivalent"
        )
        charge(
            "integration-" + ident,
            "10000",
            "1/200000",
            "buyer-specific-contract-integration",
            "estimated-input-token-equivalent",
        )
        charge("payment-fee-" + ident, "1", "3/100", "payment-provider-simulated", "assumed-fee")
        if scenario == "nonpayment":
            refused = must_refuse(lambda: ex.event(ident, "prepare-unfunded-" + ident, "prepare", {}, 1))
            ex.event(ident, "cancel-" + ident, "cancel", {}, 1)
            outcomes.append({"buyer": ident, "state": "cancelled", "prepare_without_payment_refused": refused})
            continue
        try:
            ex.event(ident, "fund-" + ident, "fund", ex.provider.issue(ex.order(ident), "funded"), 1)
        except ValueError as error:
            outcomes.append({"buyer": ident, "state": "funding-refused", "error": type(error).__name__})
            continue
        charge(
            "financing-" + ident,
            str(Fraction(price * 2, 1000000)),
            "3/7300",
            "two-day-equity-collateral-financing",
            "assumed-15percent-annual-capital",
        )
        held = ex.snapshot()
        assert held["custodyRestricted"] >= price
        before = must_refuse(lambda: ex.download(ident, ident))
        if produced is None:
            produced = engine.execute(request)
            engine.verify_result(request, produced)
            charge(
                "actual-certificate-execution",
                "1",
                produced["cost_total"],
                "initial-certificate-production",
                "measured-cpu-equivalent",
            )
            write(root / "production.json", produced)
        artifact = copy.deepcopy(produced["artifact"])
        if scenario == "failed_delivery":
            artifact["vehicles"][0]["arrival_kwh"][0] = "-1"
            refused = must_refuse(lambda: ex.event(ident, "prepare-" + ident, "prepare", artifact, 2))
            ex.event(ident, "refund-" + ident, "refund", {}, 3)
            outcomes.append({"buyer": ident, "state": "refunded", "independent_failed_delivery_refused": refused})
            continue
        if scenario == "custody_loss":
            ex.event(ident, "custody-loss-" + ident, "custody_loss", {}, 2)
            ex.event(ident, "refund-" + ident, "refund", {}, 3)
            outcomes.append({"buyer": ident, "state": "refunded", "custody_loss": True})
            continue
        started = time.process_time_ns()
        ex.event(ident, "prepare-" + ident, "prepare", artifact, 2)
        quantity = str(Fraction(time.process_time_ns() - started, 10**9))
        charge(
            "actual-prepare-" + ident,
            quantity,
            str(CPU_RATE),
            "independent-preparation-and-encryption",
            "measured-cpu-equivalent",
        )
        no_download = must_refuse(lambda: ex.download(ident, ident))
        if scenario == "assurance_failure":
            receipt = ex.provider.issue(ex.order(ident), "cleared")
            receipt["payload"]["price"] = "1"
            refused = must_refuse(lambda: ex.event(ident, "release-forged-" + ident, "release", receipt, 3))
            ex.event(ident, "refund-" + ident, "refund", {}, 11)
            outcomes.append({"buyer": ident, "state": "refunded", "forged_assurance_refused": refused})
            continue
        receipt = ex.provider.issue(ex.order(ident), "cleared")
        started = time.process_time_ns()
        ex.event(ident, "release-" + ident, "release", receipt, 3)
        quantity = str(Fraction(time.process_time_ns() - started, 10**9))
        charge(
            "actual-release-" + ident,
            quantity,
            str(CPU_RATE),
            "independent-checked-settlement",
            "measured-cpu-equivalent",
        )
        charge(
            "tail-financing-" + ident,
            str(Fraction((price + 200000) * 97, 1000000)),
            "3/7300",
            "principal-plus-fee-tail-capital-through-day100",
            "assumed-15percent-annual-capital",
        )
        delivered = ex.download(ident, ident)
        assert json.loads(delivered) == artifact
        outcomes.append(
            {
                "buyer": ident,
                "state": "released",
                "artifact_hash": digest(artifact),
                "download_before_funding_refused": before,
                "download_before_release_refused": no_download,
            }
        )
        if scenario == "late_reversal":
            ex.event(ident, "late-reversal-" + ident, "late_reversal", {}, 100)
            outcomes[-1]["state"] = "late-reversed"
            outcomes[-1]["access_after_reversal_refused"] = must_refuse(lambda: ex.download(ident, ident))
    charge(
        "one-month-retention-allocation", "1000000", "3/100000000000", "one-month1MBretention", "assumed-storage-rate"
    )
    charge("working-capital-horizon", "10", "3/7300", "working-capital100days", "assumed-15percent-annual-capital")
    elapsed_cpu = Fraction(time.process_time_ns() - world_started, 1000000000)
    charge(
        "all-unmetered-world-cpu",
        str(max(Fraction(0), elapsed_cpu - charged_cpu)),
        str(CPU_RATE),
        "offers-failed-attempts-accounting-closing-envelope",
        "measured-cpu-equivalent",
    )
    snapshot = ex.snapshot()
    investment_refusal = must_refuse(lambda: ex.reserve_investment("unearned-successor", 1, 1))
    ex.close()
    reconstructed = audit(root / "exchange.sqlite")
    for key in ["revenue", "expenses", "profit", "collections", "cash", "payables", "custodyReserve", "tailReserve"]:
        assert reconstructed[key] == snapshot[key], (key, reconstructed[key], snapshot[key])
    summary = {
        "scenario": scenario,
        "arm": arm,
        "price_microUSD": price,
        "buyers": choices,
        "outcomes": outcomes,
        "snapshot": snapshot,
        "independent_audit": reconstructed,
        "cost_events": cost_events,
        "cost_event_count": len(cost_events),
        "cost_unrounded_USD": str(sum((Fraction(row["amount"]) for row in cost_events), Fraction())),
        "rounding_policy": "ceil each actual resource event to microUSD once",
        "new_successor_authorization": False,
        "earned_funding_refused": investment_refusal,
        "opening_equity_microUSD": opening,
        "source_hashes": engine.source_hashes(),
        "payment_provider_scope": "local HMAC scenario oracle, no external finality or currency service",
        "cost_scope": "merchant seed development plus perbuyer integration/acquisition/fees and actual certificate execution; counterfactual enterprises are not actual invoices",
    }
    write(root / "summary.json", summary)
    return summary


def mechanism_checks(root: Path, task: dict[str, Any]) -> dict[str, Any]:
    root.mkdir(exist_ok=False)
    artifact = engine.execute(
        {
            "schema": engine.SCHEMA,
            "id": "payment-controls",
            "target": task,
            "capabilities": dict.fromkeys("ASC", False),
            "budget": {"operations": 100, "solver_calls": 16, "cpu_seconds": 30},
            "seed": 21,
        }
    )["artifact"]
    ex = open_exchange(root / "exchange.sqlite")
    ex.wallet("buyer", 2000000)
    ex.offer("order", "buyer", 200000, "nonrecourse-simulated", task, 10)
    consent(ex, "order")
    unfunded = must_refuse(lambda: ex.download("order", "buyer"))
    ex.event("order", "fund", "fund", ex.provider.issue(ex.order("order"), "funded"), 1)
    ex.event("order", "prepare", "prepare", artifact, 2)
    checked_private = must_refuse(lambda: ex.download("order", "buyer"))
    receipt = ex.provider.issue(ex.order("order"), "cleared")
    interrupted = must_refuse(lambda: ex.event("order", "release", "release", receipt, 3, crash=True))
    assert ex.snapshot()["revenue"] == 0
    ex.close()
    ex = open_exchange(root / "exchange.sqlite")
    ex.event("order", "release", "release", receipt, 3)
    ex.event("order", "release", "release", receipt, 3)
    assert ex.snapshot()["revenue"] == 200000
    ex.offer("other", "buyer", 200000, "nonrecourse-simulated", task, 10)
    consent(ex, "other")
    prior = ex.provider.issue(ex.order("other"), "funded", receipt["payload"]["source_tx"])
    duplicate_tx = must_refuse(lambda: ex.event("other", "duplicate-tx", "fund", prior, 1))
    ex.event("order", "reversal", "late_reversal", {}, 100)
    access = must_refuse(lambda: ex.download("order", "buyer"))
    ex.close()
    result = {
        "unfunded_output": unfunded,
        "private_verified_output": checked_private,
        "interruption": interrupted,
        "duplicate_settlement_revenue_once": True,
        "restart_recovered": True,
        "duplicate_external_tx": duplicate_tx,
        "reversal_access": access,
        "independent_audit": audit(root / "exchange.sqlite"),
        "scope": "mechanism integration probes, not market demand or earned investment evidence",
    }
    write(root / "result.json", result)
    return result


def run(output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("fresh output directory required")
    output.mkdir(parents=True)
    here = Path(__file__).resolve().parent
    task = json.loads((here / "base-target.json").read_text())
    capture = json.loads((here / "capture.json").read_text())
    mapping = json.loads((here / "mapping.json").read_text())
    source_paths = [
        Path(__file__),
        Path(__file__).parents[2] / "alpha_factory_v1/core/runtime/claim_probe/protected_exchange.py",
    ]
    freeze = {
        "sources": {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths},
        "task_hash": digest(task),
        "engine_sources": engine.source_hashes(),
        "scenarios": list(SCENARIOS),
        "prices": list(PRICES),
        "buyers_per_world": 4,
        "development": DEVELOPMENT,
        "default_scope": "competitive simulated commerce; no observed demand",
        "all_payments_simulated": True,
        "actual_external_spend_USD": 0,
    }
    write(output / "freeze.json", freeze)
    rows = []
    for scenario in SCENARIOS:
        for price in PRICES:
            for arm in ["none", "ASC"]:
                rows.append(
                    run_world(output / f"{scenario}-{price}-{arm}", task, [capture], mapping, scenario, price, arm)
                )
    checks = mechanism_checks(output / "mechanism-checks", task)
    assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == sha for p, sha in freeze["sources"].items())
    assert engine.source_hashes() == freeze["engine_sources"], "runtime changed during commercial execution"
    summary = {
        "worlds": len(rows),
        "matched_pairs": len(rows) // 2,
        "scenarios": list(SCENARIOS),
        "primary_free_completed": [
            {k: row[k] for k in ["arm", "price_microUSD", "snapshot"]}
            for row in rows
            if row["scenario"] == "free_completed"
        ],
        "positive_complete_cost_worlds": sum(row["snapshot"]["profit"] > 0 for row in rows),
        "earned_funded_successors": 0,
        "buyer_acceptances": sum(buyer["accepts"] for row in rows for buyer in row["buyers"]),
        "released_deliveries": sum(outcome["state"] == "released" for row in rows for outcome in row["outcomes"]),
        "all_world_audits_passed": all(row["independent_audit"]["audit_passed"] for row in rows),
        "profit_range_microUSD": [
            min(row["snapshot"]["profit"] for row in rows),
            max(row["snapshot"]["profit"] for row in rows),
        ],
        "mechanism_checks": checks,
        "development_once_per_counterfactual_enterprise_USD": "11/25",
        "development_actual_campaign_event_id": "commerce-development:shared-once-not88actualinvoices",
        "scope": "authored market sensitivities only; primary outside option is completed free equivalent",
        "commercial_flywheel_established": False,
        "source_freeze_unchanged": True,
        "actual_external_spend_USD": 0,
        "no_new_billed_API": True,
        "no_customers_or_purchase_intent_observed": True,
    }
    write(output / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = run(args.output)
    except Exception as error:
        if args.output.exists() and not (args.output / "failure.json").exists():
            write(
                args.output / "failure.json",
                {
                    "error": type(error).__name__,
                    "accepted": False,
                    "scope": "preserved failed invocation, not a market result",
                },
            )
        raise
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
