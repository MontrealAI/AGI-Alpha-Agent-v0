# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


def load(path: Path) -> Any:
    return json.loads(path.read_text())


def sha(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def verify(root: Path, run: Path) -> dict[str, Any]:
    freeze = load(run / "source-freeze.json")
    for relative, wanted in freeze.items():
        path = (root / relative).resolve(strict=True)
        assert path.is_relative_to(root.resolve()) and not (root / relative).is_symlink()
        assert hashlib.sha256(path.read_bytes()).hexdigest() == wanted, relative
    checked = []
    for name in load(run / "index.json"):
        request = load(run / (name + ".request.json"))
        result = load(run / (name + ".result.json"))
        assert result["program_hash"] == sha(request["program"])
        assert result["cohort_hash"] == sha(request["cases"])
        assert {x["case"] for x in result["outcomes"]} == {x["id"] for x in request["cases"]}
        assert len(result["outcomes"]) == len(request["cases"])
        ticks = [x["tick"] for x in result["trace"]]
        assert ticks == sorted(ticks)
        with sqlite3.connect((run / (name + ".sqlite")).resolve().as_uri() + "?mode=ro", uri=True) as db:
            db.execute("PRAGMA query_only=ON")
            journal = list(db.execute("SELECT kind,amount FROM journal"))

            def total(kind: str, entries: list[tuple[str, str]] = journal) -> int:
                return sum(int(v) for k, v in entries if k == kind)

            trades = list(db.execute("SELECT id,price,state,custody,refund_due FROM trades"))
            by_id = {c["id"]: c for c in request["cases"]}
            source = list(db.execute("SELECT tx FROM source_receipts"))
            assert len(source) == len(set(source))
            expense = 0
            for event in result["trace"]:
                kind = {"screen": "screening", "measure": "measurement", "produce": "production"}.get(event["action"])
                if kind:
                    expense += by_id[event["case"]][kind]
            assert expense == total("expense")
            revenue = 0
            for ident, price, state, custody, refund in trades:
                case = by_id[ident]
                if state == "released":
                    assert case["measurement_valid"] is True
                    assert case["observed_value"] >= case["required_value"]
                    assert case["settlement"] == "clear"
                    revenue += int(price)
                wallet = int(db.execute("SELECT balance FROM wallets WHERE buyer=?", (ident,)).fetchone()[0])
                assert wallet == case["buyer_cash"] - (int(price) if custody or state == "released" else 0)
                assert int(refund) == 0
            summary = result["summary"]
            assert total("revenue") == total("collections") == revenue == summary["revenue"]
            assert total("expense") == summary["expenses"]
            assert summary["profit"] == revenue - expense
            assert summary["cash"] == request["opening"] + revenue - total("expense_paid")
            assert summary["payables"] == expense - total("expense_paid")
            assert summary["custodyRestricted"] == sum(int(p) for _, p, _, c, _ in trades if c)
            assert summary["tailReserve"] == sum(int(p) + 200_000 for _, p, s, _, _ in trades if s == "released")
            assert summary["available"] == max(
                0,
                summary["cash"]
                - summary["payables"]
                - summary["custodyReserve"]
                - summary["tailReserve"]
                - summary["workingCapital"],
            )
            assert 0 <= summary["unrestrictedEarned"] <= min(max(0, summary["profit"]), summary["available"])
        checked.append(name)
    comparisons = load(run / "paired-comparison.json")
    assert len(comparisons) == 14 and all(x["same_outcomes"] and x["same_economics"] for x in comparisons)
    protocol = load(run / "protocol.json")
    assert protocol["confirmatory_looks"] == 0 and protocol["alpha_spent"] == "0"
    write_denied = False
    try:
        with (root / next(iter(freeze))).open("ab"):
            pass
    except PermissionError:
        write_denied = True
    return {
        "verified_runs": checked,
        "count": len(checked),
        "paired_component_ties": 14,
        "candidate_write_denied_by_os": write_denied,
        "role": "separate read-only process",
        "independence": "same author, same host; procedural separation only",
        "business_validation": False,
        "confirmation": False,
    }


if __name__ == "__main__":
    from contrib.invention_automation.readonly import enforce

    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    args = parser.parse_args()
    restriction = enforce()
    print(json.dumps({**verify(args.root, args.run), "restriction": restriction}, indent=2))
