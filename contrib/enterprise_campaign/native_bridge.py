# SPDX-License-Identifier: Apache-2.0
"""Import synthetic campaign evidence into original signed Journal/CostLedger APIs.

This is local fictional accounting conformance, never native catalog delivery,
customer qualification, provider metering, or authority to operate a live service.
Private rehearsal credentials exist only in temporary directories, then disappear.
"""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Journal, canonical, digest
from alpha_factory_v1.core.runtime.successor.flywheel_costs import Charge, CostLedger
from alpha_factory_v1.core.runtime.successor.trust import TrustAnchor, TrustRegistry, sign_record

REPO = Path(__file__).resolve().parents[2]
MISSION = "fictional-campaign-accounting-import"
PRINCIPAL = "fictional-campaign-accountant"
SOURCES = (
    "alpha_factory_v1/core/runtime/store.py",
    "alpha_factory_v1/core/runtime/successor/flywheel_costs.py",
    "alpha_factory_v1/core/runtime/successor/trust.py",
    "tests/runtime/test_flywheel_protected.py",
)


def _write(path: Path, value: Any) -> None:
    path.write_bytes(canonical(value) + b"\n")


def _events(path: Path) -> tuple[bytes, list[dict[str, Any]]]:
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines()]
    previous = "0" * 64
    identities: set[str] = set()
    for sequence, event in enumerate(rows, 1):
        if event["seq"] != sequence or event["previous"] != previous or event["id"] in identities:
            raise ValueError("source sequence, predecessor, or event identity is invalid")
        identities.add(event["id"])
        if digest({k: v for k, v in event.items() if k != "hash"}) != event["hash"]:
            raise ValueError("source event hash mismatch")
        previous = event["hash"]
    if not rows:
        raise ValueError("empty source event journal")
    return raw, rows


def _source_totals(events: list[dict[str, Any]]) -> dict[str, Any]:
    costs: dict[str, int | None] = {}
    payments = 0
    paid_by_activity: dict[str, int] = {}
    for event in events:
        kind, amount, activity = event["type"], event.get("amount_micro_usd"), event.get("activity_id")
        if kind not in {"accrue_cost", "pay_cost"}:
            continue
        if not isinstance(activity, str) or not activity:
            raise ValueError("cost event requires an activity identity")
        if amount is not None and (type(amount) is not int or amount < 0):
            raise ValueError("cost amount must be nonnegative integer or unknown")
        if kind == "accrue_cost":
            if activity in costs:
                raise ValueError("source activity accrued more than once")
            costs[activity] = amount
        else:
            if activity not in costs or costs[activity] is None or amount is None:
                raise ValueError("payment has no existing known accrual")
            paid_by_activity[activity] = paid_by_activity.get(activity, 0) + amount
            accrued = costs[activity]
            if accrued is None:
                raise ValueError("payment has no existing known accrual")
            if paid_by_activity[activity] > accrued:
                raise ValueError("source payments exceed an individual activity accrual")
            payments += amount
    return {
        "activities": len(costs),
        "known_accrual_micro_usd": sum(v or 0 for v in costs.values()),
        "paid_micro_usd": payments,
        "unknown_activities": sum(v is None for v in costs.values()),
    }


def _category(event: dict[str, Any]) -> str:
    unit = event.get("details", {}).get("unit", "")
    if unit in {"input_token", "output_token"}:
        return "model"
    if unit == "millicpu_hour":
        return "compute"
    if unit == "MiB-day-rounded-up":
        return "storage"
    return "overhead"


def _account(ledger: CostLedger, key: Ed25519PrivateKey, action: str, record: Any, operation: str) -> None:
    ledger.apply(
        sign_record(
            key,
            PRINCIPAL,
            "flywheel-cost-command",
            {
                "journal_identity": ledger.journal.identity,
                "operation_id": operation,
                "action": action,
                "record": record,
            },
        )
    )


def _native_run(events: list[dict[str, Any]], export: Path | None) -> dict[str, Any]:
    """Replay through inspected native APIs; only explicitly public data may leave."""
    with tempfile.TemporaryDirectory(prefix="campaign-native-private-", dir="/dev/shm") as temporary:
        journal = Journal.initialize(Path(temporary) / "journal")
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        trust = TrustRegistry({PRINCIPAL: TrustAnchor(public, frozenset({"accounting"}))})
        ledger = CostLedger(journal, trust)
        activities: dict[str, str] = {}
        with journal.transaction() as cx:
            for event in events:
                journal.append(cx, "@fictional-campaign-source:" + str(event["seq"]), {"source_event": event})
        groups: dict[str, dict[str, Any]] = {}
        by_activity: dict[str, dict[str, Any]] = {}
        for event in events:
            if event["type"] == "accrue_cost":
                activity = event["activity_id"]
                bucket = "A" if event.get("allocation") == "delivery" else "C"
                known = event["amount_micro_usd"] is not None
                batch = f"source-batch/{bucket}/{_category(event)}/{'known' if known else 'unknown'}"
                group = groups.setdefault(
                    batch, {"bucket": bucket, "category": _category(event), "known": known, "source_activities": []}
                )
                entry = {
                    "activity_id": activity,
                    "accrual_event_id": event["id"],
                    "accrual_event_hash": event["hash"],
                    "accrued_micro_usd": event["amount_micro_usd"],
                    "payments": [],
                }
                if activity in activities:
                    raise ValueError("batch mapping overlap")
                activities[activity] = batch
                by_activity[activity] = entry
                group["source_activities"].append(entry)
            elif event["type"] == "pay_cost":
                by_activity[event["activity_id"]]["payments"].append(
                    {
                        "event_id": event["id"],
                        "event_hash": event["hash"],
                        "amount_micro_usd": event["amount_micro_usd"],
                    }
                )
        expected_activities = {e["activity_id"] for e in events if e["type"] == "accrue_cost"}
        if set(activities) != expected_activities or sum(len(g["source_activities"]) for g in groups.values()) != len(
            activities
        ):
            raise AssertionError("source activity batch mapping missing or overlapping")
        first_command: tuple[str, Any, str] | None = None
        for activity, group in sorted(groups.items()):
            evidence = digest(group)
            with journal.transaction() as cx:
                journal.append(cx, "@fictional-campaign-batch:" + activity, {"batch": group, "batch_digest": evidence})
            charge = Charge(
                activity_id=activity,
                mission_id=MISSION,
                bucket=group["bucket"],
                category=group["category"],
                accrued_micro_usd=sum(r["accrued_micro_usd"] for r in group["source_activities"])
                if group["known"]
                else None,
                paid_micro_usd=0,
                basis="attested" if group["known"] else "unknown",
                evidence_digest=evidence,
                note="Fictional modeled research cost batch; not actual provider cost. Signed source activity map "
                + evidence,
            )
            command = ("charge", charge.model_dump(), "charge-" + activity)
            _account(ledger, key, *command)
            if first_command is None:
                first_command = command
            paid = sum(p["amount_micro_usd"] for r in group["source_activities"] for p in r["payments"])
            if paid:
                _account(
                    ledger,
                    key,
                    "payment",
                    {
                        "payment_id": "payment-" + activity,
                        "activity_id": activity,
                        "amount_micro_usd": paid,
                        "evidence_digest": digest({"batch": activity, "payments": group}),
                    },
                    "payment-" + activity,
                )
        before_replay = ledger.report()
        if first_command:
            _account(ledger, key, *first_command)
        if ledger.report() != before_replay:
            raise AssertionError("native accounting operation replay double-counted")
        state, report = ledger.snapshot(), ledger.report()
        rows = state["charges"].values()
        totals = {
            "activities": len(activities),
            "known_accrual_micro_usd": sum(r["accrued_micro_usd"] or 0 for r in rows),
            "paid_micro_usd": sum(r["paid_micro_usd"] for r in rows),
            "unknown_activities": sum(len(g["source_activities"]) for g in groups.values() if not g["known"]),
        }
        if sum(report["costs"].values()) != totals["known_accrual_micro_usd"]:
            raise AssertionError("native report accrual differs from native charge rows")
        if report["cash"] != -totals["paid_micro_usd"]:
            raise AssertionError("native cost-only cash differs from native payments")
        if report["unknown_costs"] != bool(totals["unknown_activities"]):
            raise AssertionError("native report lost unknown liabilities")
        with journal.transaction() as cx:
            native_report_record = journal.append(
                cx,
                "@fictional-campaign-cost-report",
                {
                    "native_cost_report": report,
                    "totals": totals,
                    "source_head": events[-1]["hash"],
                    "fictional_local_test_only": True,
                    "catalog_adapter": "HOLD",
                },
            )
        verification = journal.verify()
        if export is not None:
            with sqlite3.connect(journal.path) as cx, gzip.open(export / "native-journal.jsonl.gz", "wt") as stream:
                for sequence, mission, body, hashed, signature in cx.execute("SELECT * FROM events ORDER BY seq"):
                    stream.write(
                        json.dumps(
                            {
                                "seq": sequence,
                                "mission": mission,
                                "body": json.loads(body),
                                "hash": hashed,
                                "signature": signature,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
            _write(
                export / "native-public-keys.json",
                {
                    "journal_public_key": journal.public,
                    "journal_identity": journal.identity,
                    "accounting_public_key": public,
                    "principal": PRINCIPAL,
                    "roles": ["accounting"],
                    "provenance": "ephemeral fictional local test grants; no live authority",
                },
            )
        return {
            "totals": totals,
            "report": report,
            "journal_verification": verification,
            "idempotent_operation_replay": True,
            "source_activity_mapping": activities,
            "signed_native_cost_report_record": native_report_record,
            "native_charge_rows": list(state["charges"].values()),
            "native_payment_rows": list(state.get("payments", {}).values()),
            "batch_mapping_complete_no_overlap": True,
        }


def _fixture_checks() -> dict[str, bool]:
    with tempfile.TemporaryDirectory(prefix="campaign-native-fixture-", dir="/dev/shm") as temporary:
        journal = Journal.initialize(Path(temporary) / "journal")
        key = Ed25519PrivateKey.generate()
        public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()
        ledger = CostLedger(journal, TrustRegistry({PRINCIPAL: TrustAnchor(public, frozenset({"accounting"}))}))
        charge = Charge(
            activity_id="unknown-fixture",
            mission_id=MISSION,
            bucket="C",
            category="model",
            accrued_micro_usd=None,
            paid_micro_usd=0,
            basis="unknown",
            evidence_digest="0" * 64,
            note="Fictional unresolved liability; actual provider cost unknown, never zero.",
        )
        _account(ledger, key, "charge", charge.model_dump(), "fixture-unknown")
        report = ledger.report()
        if not report["unknown_costs"] or report["obligations"] is not None or report["available_funds"] is not None:
            raise AssertionError("native unknown liability was relabeled as known")
        for activity in ("nonexistent-fixture", "unknown-fixture"):
            try:
                _account(
                    ledger,
                    key,
                    "payment",
                    {
                        "payment_id": "payment-" + activity,
                        "activity_id": activity,
                        "amount_micro_usd": 1,
                        "evidence_digest": "1" * 64,
                    },
                    "attempt-" + activity,
                )
            except ValueError:
                pass
            else:
                raise AssertionError("native ledger accepted nonexistent or unknown-accrual payment")
        return {
            "unknown_stays_unknown": True,
            "nonexistent_payment_refused": True,
            "unknown_accrual_payment_refused": True,
            "native_fixture_signatures_verified": journal.verify()["valid"],
        }


def verify_public_export(output: Path) -> dict[str, Any]:
    """Verify exported native journal bytes using the original Journal hash/signature convention."""
    keys = json.loads((output / "native-public-keys.json").read_text())
    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(keys["journal_public_key"]))
    previous, count, source_count = "0" * 64, 0, 0
    with gzip.open(output / "native-journal.jsonl.gz", "rt") as stream:
        for line in stream:
            row = json.loads(line)
            body = row["body"]
            count += 1
            if (
                row["seq"] != count
                or body["sequence"] != count
                or body["previous"] != previous
                or body["identity"] != keys["journal_identity"]
                or body["mission"] != row["mission"]
                or digest(body) != row["hash"]
            ):
                raise ValueError("exported native journal integrity mismatch")
            key.verify(base64.b64decode(row["signature"], validate=True), bytes.fromhex(row["hash"]))
            source_count += "source_event" in body["document"]
            previous = row["hash"]
    return {"valid": True, "events": count, "head": previous, "source_event_records": source_count}


def bridge(source: Path, output: Path, *, replay: bool = True) -> dict[str, Any]:
    """Export public signed evidence and reconcile native totals to source events."""
    source = source.resolve()
    if output.resolve() == source.parent:
        raise ValueError("use a separate output directory")
    raw, events = _events(source)
    expected = _source_totals(events)
    output.mkdir(parents=True, exist_ok=False)
    fixtures = _fixture_checks()
    native = _native_run(events, output)
    public_verification = verify_public_export(output)
    if public_verification["source_event_records"] != len(events):
        raise AssertionError("public signed export lost source event records")
    if public_verification["head"] != native["journal_verification"]["head"]:
        raise AssertionError("export differs from original verified native journal")
    if native["totals"] != expected:
        raise AssertionError("native costs/payments disagree with independently summed event source")
    replay_totals = _native_run(events, None)["totals"] if replay else None
    if replay and replay_totals != expected:
        raise AssertionError("new-key replay numeric results disagree")
    report = {
        "schema": "synthetic-native-accounting-bridge/v1",
        "source_events_sha256": hashlib.sha256(raw).hexdigest(),
        "source_event_count": len(events),
        "source_event_head": events[-1]["hash"],
        "market_period_count": sum(event["type"] == "market_period" for event in events),
        "source_totals": expected,
        "native": native,
        "checks": {**fixtures, "public_native_signature_verification": public_verification},
        "numeric_replay_with_new_ephemeral_keys": replay_totals,
        "all_numeric_comparisons_passed": True,
        "source_identities": {name: hashlib.sha256((REPO / name).read_bytes()).hexdigest() for name in SOURCES},
        "bridge_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limits": {
            "catalog_adapter": "HOLD: unsupported by native public-source research delivery slice",
            "native_delivery_or_customer_qualification": False,
            "complete_cost_seals_issued": False,
            "fictional_accounting_only": True,
            "actual_provider_costs": "unknown; modeled source estimates only",
            "live_service_authority": False,
            "private_keys_or_api_tokens_exported": False,
            "capital_collections_reserves": "source events preserved; excluded from native cost-only ledger",
        },
    }
    _write(output / "native-cost-report.json", report)
    _write(
        output / "native-receipt.json",
        {
            "source_event_count": len(events),
            "source_head": events[-1]["hash"],
            "report_sha256": hashlib.sha256((output / "native-cost-report.json").read_bytes()).hexdigest(),
            "public_journal_sha256": hashlib.sha256((output / "native-journal.jsonl.gz").read_bytes()).hexdigest(),
            "catalog_adapter": "HOLD",
            "fictional_local_test_only": True,
        },
    )
    return report


def main() -> None:
    """Run an explicit local import with optional second-key numeric replay."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="campaign events.jsonl")
    parser.add_argument("output", type=Path, help="new public evidence directory")
    parser.add_argument("--skip-numeric-replay", action="store_true")
    args = parser.parse_args()
    result = bridge(args.source, args.output, replay=not args.skip_numeric_replay)
    print(
        json.dumps(
            {
                "source_events": result["source_event_count"],
                "periods": result["market_period_count"],
                "totals": result["source_totals"],
                "checks": result["checks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
