# SPDX-License-Identifier: Apache-2.0
"""Read-only reconstruction of simulated receipts and money, separate from the producer."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from .delta_acceptance import verify_delta


def encode(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def hashed(value: Any) -> str:
    return hashlib.sha256(encode(value)).hexdigest()


def audit(directory: Path) -> dict[str, Any]:
    """Check scoped chronology, actual artifacts, receipt binding and independent arithmetic."""
    failures: list[str] = []
    try:
        summary = json.loads((directory / "summary.json").read_bytes())
        events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
        conditional = summary["contract"] == "conditional"
        total = {key: 0 for key in ("cash", "revenue", "expense", "receivable", "liability", "reserves")}
        history: dict[str, dict[str, Any]] = {}
        previous = "0" * 64
        previous_day = -1
        scope = {"opening_capital", "reserve", "release_reserve", "accrue_cost", "pay_cost", "quote", "decline",
                 "buyer_decline", "lock_refused", "external_escrow_locked", "external_escrow_refunded",
                 "delivery_failed", "artifact", "acceptance_refused", "settlement_commit", "earned", "collect",
                 "delivery", "revenue_reversal", "refund", "writeoff"}
        artifacts = accepted = 0
        opening_count = 0
        for n, event in enumerate(events, 1):
            if event["seq"] != n or event["previous"] != previous:
                raise ValueError("Journal continuity")
            raw = {key: value for key, value in event.items() if key != "hash"}
            if hashed(raw) != event["hash"] or event["day"] < previous_day:
                raise ValueError("Journal digest or chronology")
            previous, previous_day = event["hash"], event["day"]
            kind, amount, details = event["type"], event["amount_micro_usd"], event["details"]
            if kind not in scope or type(amount) is not int or amount < 0:
                raise ValueError("Unsupported event or negative/unknown money")
            order = str(event["order_id"])
            state = history.setdefault(order, {})
            if kind == "quote":
                state["price"] = details["price"]
            if kind == "external_escrow_locked":
                if state.get("locked") or amount or details["external_amount"] != state["price"]:
                    raise ValueError("Duplicate or unbound custody lock")
                state.update(locked=True, request_hash=details["request_hash"])
            if kind == "external_escrow_refunded":
                if not state.get("locked") or state.get("commit") or state.get("external_refund"):
                    raise ValueError("Invalid external refund")
                if amount or details["external_amount"] != state["price"]:
                    raise ValueError("Custody funds enter enterprise accounting")
                state["external_refund"] = True
            if kind == "artifact":
                relative = Path(details["path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("Artifact path escapes directory")
                path = directory / relative
                if path.is_symlink():
                    raise ValueError("Symlink artifact")
                data = path.read_bytes()
                if hashlib.sha256(data).hexdigest() != details["artifact_hash"]:
                    raise ValueError("Artifact bytes differ")
                artifact = json.loads(data)
                packet = artifact["packet"]
                if packet is not None:
                    verdict = verify_delta(artifact["before"], artifact["delta"], packet, artifact["request"])
                    if verdict != artifact["acceptance"]:
                        raise ValueError("Actual independent acceptance differs")
                elif artifact["acceptance"]["verdict"] == "PASS_IN_SCOPE":
                    raise ValueError("Empty artifact accepted")
                state["artifact"] = artifact
                artifacts += 1
                if details["accepted"] != (artifact["acceptance"]["verdict"] == "PASS_IN_SCOPE"):
                    raise ValueError("Artifact acceptance label differs")
            if kind == "settlement_commit":
                if not state.get("locked") or state.get("external_refund") or state.get("commit"):
                    raise ValueError("Unfunded, refunded or repeated commit")
                artifact = state["artifact"]
                if artifact["acceptance"]["verdict"] != "PASS_IN_SCOPE":
                    raise ValueError("Unaccepted settlement")
                receipt = details["receipt"]
                request_hash = hashed({key: artifact[key] for key in ("before", "delta", "request")})
                if receipt["request_hash"] != request_hash or request_hash != state["request_hash"]:
                    raise ValueError("Wrong settlement input")
                if receipt["packet_hash"] != hashed(artifact["packet"]):
                    raise ValueError("Wrong settlement packet")
                if receipt["output_hash"] != hashlib.sha256(artifact["packet"]["native_package"]["output_csv"].encode()).hexdigest():
                    raise ValueError("Wrong output binding")
                if receipt["amount"] != state["price"] or receipt["id"] != hashed({k: v for k, v in receipt.items() if k != "id"}):
                    raise ValueError("Wrong receipt amount or digest")
                if receipt.get("actual_money") is not False or receipt["basis"] != "simulated_custodian_atomic_transition":
                    raise ValueError("Simulation scope changed")
                state["commit"] = receipt["id"]
            if kind in {"earned", "collect", "delivery"}:
                if state.get(kind):
                    raise ValueError("Duplicate income/collection/delivery")
                if conditional:
                    if not state.get("commit") or details.get("receipt_id") != state["commit"]:
                        raise ValueError("Missing commit binding")
                    if kind == "collect" and not state.get("earned"):
                        raise ValueError("Collection before acceptance")
                    if kind == "delivery" and not state.get("collect"):
                        raise ValueError("Unpaid artifact release")
                if kind == "earned":
                    if state["artifact"]["acceptance"]["verdict"] != "PASS_IN_SCOPE" or amount != state["price"]:
                        raise ValueError("Wrong accepted income")
                    accepted += 1
                if kind == "collect" and (not state.get("earned") or amount != state["price"]):
                    raise ValueError("Invalid collection")
                if kind == "delivery":
                    if details["output_hash"] != hashlib.sha256(state["artifact"]["packet"]["native_package"]["output_csv"].encode()).hexdigest():
                        raise ValueError("Wrong delivered bytes")
                state[kind] = True
            if kind == "opening_capital":
                opening_count += 1
                total["cash"] += amount
            elif kind == "earned":
                total["revenue"] += amount
                total["receivable"] += amount
            elif kind == "collect":
                total["cash"] += amount
                total["receivable"] -= amount
            elif kind == "accrue_cost":
                if amount != event["quantity"] * event["unit_rate_micro_usd"]:
                    raise ValueError("Cost quantity-rate mismatch")
                total["expense"] += amount
                total["liability"] += amount
            elif kind == "pay_cost":
                total["cash"] -= amount
                total["liability"] -= amount
            elif kind == "reserve":
                total["reserves"] += amount
            elif kind == "release_reserve":
                total["reserves"] -= amount
            elif kind == "writeoff":
                total["expense"] += amount
                total["receivable"] -= amount
            elif kind == "revenue_reversal":
                reduction = details["receivable_reduction_micro_usd"]
                if type(reduction) is not int or not 0 <= reduction <= amount:
                    raise ValueError("Invalid reversal")
                total["revenue"] -= amount
                total["receivable"] -= reduction
                total["liability"] += amount - reduction
            elif kind == "refund":
                total["cash"] -= amount
                total["liability"] -= amount
            if any(total[key] < 0 for key in ("cash", "receivable", "liability", "reserves")):
                raise ValueError("Negative financial position")
        if opening_count != 1:
            raise ValueError("Opening funding reset")
        if conditional:
            for state in history.values():
                if state.get("locked") and not (state.get("external_refund") or (state.get("commit") and state.get("delivery"))):
                    raise ValueError("Unclosed custody transition")
        expected = {key + "_micro_usd": value for key, value in total.items()}
        expected.update(profit_micro_usd=total["revenue"] - total["expense"], unknown_cost_count=0)
        if expected != summary["modeled_balances"] or summary["journal_head"] != previous:
            raise ValueError("Summary does not reconstruct")
        if accepted != summary["accepted"] or artifacts != summary["artifact_attempts"]:
            raise ValueError("Wrong experiment counts")
    except (ValueError, TypeError, KeyError, OSError) as error:
        failures.append(str(error))
    return {"path": str(directory), "verdict": "PASS_IN_SCOPE" if not failures else "REJECTED", "failures": failures,
            "scope": "Finite journal, artifact and arithmetic checks; not economic assumption calibration"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    args = parser.parse_args()
    root = Path(args.directory)
    paths = [root] if (root / "summary.json").exists() else sorted(path.parent for path in root.glob("*/summary.json"))
    if not paths:
        parser.error("No recorded worlds")
    results = [audit(path) for path in paths]
    print(json.dumps({"worlds": len(results), "passed": sum(row["verdict"] == "PASS_IN_SCOPE" for row in results),
                      "results": results}, indent=2))
    return int(any(row["verdict"] != "PASS_IN_SCOPE" for row in results))


if __name__ == "__main__":
    raise SystemExit(main())
