# SPDX-License-Identifier: Apache-2.0
"""Project one explicitly simulated settled scenario through existing native accounting."""

from __future__ import annotations

import argparse
import json
import tempfile
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any

from binding import digest, file_sha, inherited, load_json, native_trust, save

CATEGORIES = ["model", "tools", "compute", "storage", "network", "human", "acceptance", "correction", "overhead"]
MICRO = Decimal("0.000001")


def number(value: Any) -> Decimal:
    """Require a finite model number without interpreting it as an observed receipt."""
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("finite modeled amount required")
    return result


def micro(value: Decimal) -> int:
    """Convert assumed USD into native integer micro-USD using explicit half-even rounding."""
    return int((value * 1_000_000).quantize(Decimal(1), rounding=ROUND_HALF_EVEN))


def close(actual: Decimal, supplied: Any, field: str) -> None:
    """Check source rounding to its declared six-decimal cash precision."""
    if abs(actual - number(supplied)) > MICRO:
        raise ValueError("authoritative simulated ledger does not reconcile: " + field)


def audit_scenario(example: dict[str, Any]) -> dict[str, Any]:
    """Independently replay chronological cash, unearned receipts and invoices."""
    model = example["realization"]
    seed = number(example["scenario"]["seed_cash"])
    cash = seed
    collections = refunds = earned = expenses = unearned = receivables = bad_debt = Decimal(0)
    buckets = {name: Decimal(0) for name in "ABC"}
    paid_buckets = {name: Decimal(0) for name in "ABC"}
    seen: set[str] = set()
    previous_day = -1
    rows = []
    failure_refund = number(example["plan"]["failure_refund_fraction"])
    if not 0 <= failure_refund <= 1:
        raise ValueError("invalid modeled refund term")
    for event in model["ledger"]:
        identity, day, kind, amount = event["activity"], event["day"], event["kind"], number(event["amount"])
        if identity in seen or type(day) is not int or day < previous_day or amount < 0:
            raise ValueError("duplicate, unordered or negative modeled event")
        seen.add(identity)
        previous_day = day
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
            if event["bucket"] not in buckets:
                raise ValueError("expense outside disjoint A/B/C buckets")
            cash -= amount
            expenses += amount
            buckets[event["bucket"]] += amount
            paid_buckets[event["bucket"]] += amount
        elif kind == "invoice":
            earned += amount
            receivables += amount
        elif kind == "collect_invoice":
            cash += amount
            collections += amount
            receivables -= amount
        elif kind == "writeoff":
            if event["bucket"] != "A":
                raise ValueError("unexpected writeoff scope")
            expenses += amount
            buckets["A"] += amount
            bad_debt += amount
            receivables -= amount
        else:
            raise ValueError("unsupported research cash event: " + kind)
        reserve = (Decimal(1) if day <= 1 else failure_refund) * max(Decimal(0), unearned)
        balances = {
            "cash": cash,
            "unearned": unearned,
            "receivables": receivables,
            "refund_reserve": reserve,
            "cash_after_refund_reserve": cash - reserve,
        }
        if min(cash, unearned, receivables) < -MICRO:
            raise ValueError("negative research ledger balance")
        for field, expected in balances.items():
            close(expected, event[field], identity + ":" + field)
        rows.append(
            {
                "activity": identity,
                "kind": kind,
                "event_sha256": digest(event),
                "balances_usd": {key: str(value) for key, value in balances.items()},
            }
        )
    values = {
        "collections": collections,
        "refunds": refunds,
        "earned_revenue": earned,
        "expenses": expenses,
        "cash": cash,
        "profit": earned - expenses,
        "receivables": receivables,
        "obligations": unearned,
        "bad_debt_expense": bad_debt,
    }
    for field, expected in values.items():
        close(expected, model.get(field, 0), field)
    if abs(unearned) > MICRO or abs(receivables) > MICRO:
        raise ValueError("native terminal projection requires settled advances and receivables")
    close(cash, seed + earned - expenses, "seed + accrued profit = final cash after full settlement")
    close(cash - number(model["reserves"]), model["available_funds"], "available_funds")
    return {
        "schema": "independent-simulated-cash-audit/v1",
        "events": rows,
        "seed_usd": str(seed),
        "balances_usd": {key: str(value) for key, value in values.items()},
        "accrual_buckets_usd": {key: str(value) for key, value in buckets.items()},
        "paid_buckets_usd": {key: str(value) for key, value in paid_buckets.items()},
        "source_ledger_sha256": digest(model["ledger"]),
        "scope": "arithmetic and identity check of research assumptions, not market or bank verification",
    }


def commands_for(example: dict[str, Any], audit: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Project settled net receipts and actual modeled cash expenses exactly once.

    A noncash writeoff remains in the authoritative accrual ledger. Because the
    native revenue basis is collected cash, also charging that writeoff here
    would deduct the same default twice. No deposit liability is projected.
    """
    model = example["realization"]
    context = {
        "seed": example["seed"],
        "arm": example["plan"]["arm"],
        "source_ledger_sha256": audit["source_ledger_sha256"],
        "basis": "SIMULATED_ASSUMED_USD",
    }
    net_receipts = number(audit["balances_usd"]["collections"]) - number(audit["balances_usd"]["refunds"])
    commands = []
    for action, record, amount in (
        ("capital", "scenario-seed", number(audit["seed_usd"])),
        ("collection", "settled-net-customer-cash", net_receipts),
    ):
        commands.append(
            {
                "action": action,
                "record": {
                    "record_id": record,
                    "mission_id": "simulated-enterprise",
                    "amount_micro_usd": micro(amount),
                    "evidence_digest": digest({**context, "action": action}),
                },
            }
        )
    totals = {name: 0 for name in "ABC"}
    cash_expenses = sorted(
        (event for event in model["ledger"] if event["kind"] == "expense"), key=lambda event: event["bucket"]
    )
    for event in cash_expenses:
        amount = micro(number(event["amount"]))
        bucket = event["bucket"]
        totals[bucket] += amount
        commands.append(
            {
                "action": "charge",
                "record": {
                    "activity_id": event["activity"],
                    "mission_id": "simulated-enterprise",
                    "bucket": bucket,
                    "category": "overhead",
                    "accrued_micro_usd": amount,
                    "paid_micro_usd": amount,
                    "basis": "attested",
                    "evidence_digest": digest({**context, "event": event}),
                    "note": "SIMULATED all-in research expense, projected once from its original activity. "
                    "Overhead holds inclusive modeled costs; no actual provider bill or zero-cost claim.",
                },
            }
        )
    for bucket in "ABC":
        for category in CATEGORIES:
            if category == "overhead" and any(
                event["kind"] == "expense" and event["bucket"] == bucket for event in model["ledger"]
            ):
                continue
            commands.append(
                {
                    "action": "charge",
                    "record": {
                        "activity_id": "no-additional-" + bucket + "-" + category,
                        "mission_id": "simulated-enterprise",
                        "bucket": bucket,
                        "category": category,
                        "accrued_micro_usd": 0,
                        "paid_micro_usd": 0,
                        "basis": "attested",
                        "evidence_digest": digest({**context, "included": [bucket, category]}),
                        "note": "SIMULATED inclusive costs already allocated; no additional modeled charge in this category. "
                        "This does not measure an actual zero resource cost.",
                    },
                }
            )
        commands.append(
            {
                "action": {"A": "seal", "B": "seal-retention", "C": "seal-investment"}[bucket],
                "record": {
                    "mission_id": "simulated-enterprise",
                    "categories": CATEGORIES,
                    "evidence_digest": digest({**context, "seal": bucket}),
                },
            }
        )
    commands.append({"action": "reserve", "record": micro(number(model["reserves"]))})
    return commands, totals


def journal_events(example: dict[str, Any], source_sha: str) -> dict[str, Any]:
    """Put original chronological simulated events in the existing signed native Journal."""
    native = native_trust()
    from alpha_factory_v1.core.runtime.store import Journal

    def signed_values(value: Any) -> Any:
        if isinstance(value, float):
            return str(value)
        if isinstance(value, dict):
            return {name: signed_values(item) for name, item in value.items()}
        if isinstance(value, list):
            return [signed_values(item) for item in value]
        return value

    with tempfile.TemporaryDirectory(prefix="v4-simulated-cash-journal-") as temporary:
        journal = Journal.initialize(Path(temporary) / "native")
        registry, keys = native.local_principals()
        for event in example["realization"]["ledger"]:
            payload = {
                "journal_identity": journal.identity,
                "source_sha256": source_sha,
                "basis": "SIMULATED_ASSUMED_USD_NOT_BANK_RECEIPT",
                "event": signed_values(event),
                "original_event_sha256": digest(event),
                "encoding": "source JSON floating-point numbers encoded as exact decimal text for native commitments",
            }
            signed = native.sign_record(keys["local-controller"], "local-controller", "v4-simulated-cash", payload)
            checked = registry.verify(signed, "v4-simulated-cash", "controller")
            with journal.transaction() as connection:
                journal.append(
                    connection,
                    "@v4-simulated-cash:" + event["activity"],
                    {
                        "original_event_sha256": digest(event),
                        "encoded_event_sha256": digest(checked["event"]),
                        "signed": signed.model_dump(),
                    },
                )
        verification = journal.verify()
        with journal.transaction() as connection:
            rows = [
                {
                    "sequence": sequence,
                    "mission": mission,
                    "body": json.loads(body),
                    "hash": hashed,
                    "signature": signature,
                }
                for sequence, mission, body, hashed, signature in connection.execute(
                    "SELECT * FROM events ORDER BY seq"
                )
            ]
        return {
            "verification": verification,
            "events": rows,
            "public_controller_key": registry.anchor("local-controller", "controller").public_key,
            "authority": "native local ephemeral Ed25519 fixture; not bank, customer or ENS attestation",
            "private_keys_exported": False,
        }


def run(source: Path, arm: str, seed: int, output: Path) -> dict[str, Any]:
    """Replay one explicitly selected scenario without selecting for a favorable profit."""
    examples = load_json(source)
    selected = [item for item in examples if item["plan"]["arm"] == arm and item["seed"] == seed]
    if len(selected) != 1:
        raise ValueError("select exactly one explicit stored scenario")
    example = selected[0]
    output.mkdir(parents=True, exist_ok=False)
    audited = audit_scenario(example)
    commands, totals = commands_for(example, audited)
    native = inherited().upstream().replay_native(commands, controls=True)
    full_journal = journal_events(example, file_sha(source))
    report = native["report"]
    expected_net = micro(number(audited["balances_usd"]["collections"]) - number(audited["balances_usd"]["refunds"]))
    expected_profit = expected_net - sum(totals.values())
    checks = list(native["controls"])
    checks += [
        {"name": "native-settled-net-receipts", "passed": report["collected_revenue"] == expected_net},
        {"name": "each-original-paid-activity-charged-once", "passed": report["costs"] == totals},
        {"name": "native-settled-profit", "passed": report["complete_cost_profit"] == expected_profit},
        {
            "name": "source-profit-within-quantization-bound",
            "passed": abs(Decimal(expected_profit) / 1_000_000 - number(example["realization"]["profit"]))
            <= MICRO * (1 + len(example["realization"]["ledger"])),
        },
        {
            "name": "native-cash-reconciles",
            "passed": report["cash"] == micro(number(audited["seed_usd"])) + expected_profit,
        },
        {"name": "capital-not-revenue", "passed": native["reports_after_each_command"][0]["collected_revenue"] == 0},
        {"name": "native-original-event-journal-valid", "passed": full_journal["verification"]["valid"] is True},
        {"name": "actual-customer-collections-remain-zero", "passed": native["actual_collections_micro_usd"] == 0},
    ]
    summary = {
        "schema": "v4-simulated-settled-native-accounting/v1",
        "arm": arm,
        "seed": seed,
        "source_file_sha256": file_sha(source),
        "source_example_sha256": digest(example),
        "checks": checks,
        "passed": sum(row["passed"] for row in checks),
        "total": len(checks),
        "authoritative_model": {
            "ledger_sha256": audited["source_ledger_sha256"],
            "realization": {key: value for key, value in example["realization"].items() if key != "ledger"},
        },
        "native_report": report,
        "actual_customer_collections_usd": 0,
        "actual_complete_research_cost_usd": None,
        "scope": "settled terminal net-cash projection only; authoritative chronology, deposits, refunds, "
        "receivables and noncash writeoffs remain in original research ledger and signed event journal",
        "money_basis": "all scenario USD amounts assumed/simulated; no market demand or real earned revenue",
        "rounding": "each projected cash activity rounded half-even to integer micro-USD; residual disclosed",
        "rounding_profit_residual_usd": str(
            Decimal(expected_profit) / 1_000_000 - number(example["realization"]["profit"])
        ),
        "bad_debt_double_counted": False,
        "seed_or_unearned_deposit_counted_as_revenue": False,
    }
    for name, record in (
        ("source-audit", audited),
        ("native-settled-replay", native),
        ("native-original-event-journal", full_journal),
        ("summary", summary),
    ):
        save(output / (name + ".json"), record)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    arguments = parser.parse_args()
    result = run(arguments.source.resolve(), arguments.arm, arguments.seed, arguments.out.resolve())
    print(json.dumps({key: result[key] for key in ("passed", "total", "arm", "seed", "rounding_profit_residual_usd")}))
    raise SystemExit(0 if result["passed"] == result["total"] else 1)
