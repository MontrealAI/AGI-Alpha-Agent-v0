# SPDX-License-Identifier: Apache-2.0
"""Independent evidence accounting. No imports from production financial or market code."""

from __future__ import annotations
import gzip
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_CEILING
from pathlib import Path


def run(root):
    summary = json.loads((root / "summary.json").read_text())
    technical = [json.loads(s) for s in gzip.open(root / "technical.jsonl.gz", "rt")]
    worlds = [json.loads(s) for s in gzip.open(root / "market.jsonl.gz", "rt")]
    expected_tech, expected_worlds = (36, 18) if summary["phase"] == "training" else (48, 192)
    assert len(technical) == expected_tech and len(worlds) == expected_worlds
    failures = [w for w in worlds if w.get("error")]
    assert not failures, failures
    grouped = defaultdict(list)
    for world in worlds:
        groups = defaultdict(int)
        for entry in world["journal"]:
            groups[entry["kind"]] += int(entry["amount"])
        revenue = groups["earned_revenue"] - groups["contra_revenue"]
        collected = groups["collections"] - groups["refund_payment"]
        restricted = groups["restricted_funding"] - groups["restricted_release"] - groups["restricted_refund"]
        assert restricted == 0 and revenue == collected
        assert world["exchange"]["revenue"] == revenue and world["exchange"]["cash"] == collected
        assert len(world["attempts"]) == 24
        assert world["declined"] == sum(not x["participates"] for x in world["attempts"])
        assert revenue == (world["accepted"] - world["reversals"]) * world["priceMicroUSD"]
        eventids = set()
        event_times = defaultdict(lambda: -1)
        for event in world["events"]:
            assert event["id"] not in eventids
            eventids.add(event["id"])
            when = json.loads(event["payload"])["now"]
            assert when >= event_times[event["order_id"]]
            event_times[event["order_id"]] = when
        expense = sum(
            int(
                (Decimal(str(row["quantity"])) * Decimal(str(row["rateUSD"])) * 1000000).quantize(
                    Decimal(1), rounding=ROUND_CEILING
                )
            )
            for row in world["costLedger"]
        )
        # Float serialization near an exact micro-unit boundary can differ by at most one.
        assert abs(world["financial"]["profit"] - (revenue - expense)) <= 1
        assert world["financial"]["cash"] == 100000000 + world["financial"]["profit"]
        assert world["financial"]["unrestrictedEarned"] == max(0, world["financial"]["profit"])
        assert not world["fundedConstruction"] and world["investment"]["decision"] == "HOLD INVESTMENT"
        grouped[(world["scenario"], world["arm"], world["priceMicroUSD"])].append(world)
    comparisons = []
    if summary["phase"] == "confirmation":
        for scenario in summary["policy"]["marketConfirmation"]["scenarios"]:
            left = {w["seed"]: w for w in worlds if w["scenario"] == scenario and w["arm"] == "instrument"}
            right = {w["seed"]: w for w in worlds if w["scenario"] == scenario and w["arm"] == "conventional"}
            assert set(left) == set(right) and len(left) == 16
            diff = [left[s]["financial"]["profit"] - right[s]["financial"]["profit"] for s in left]
            assert all(left[s]["accepted"] == right[s]["accepted"] for s in left)
            comparisons.append(
                {
                    "scenario": scenario,
                    "pairedWorlds": 16,
                    "profitDifferenceMeanMicroUSD": statistics.mean(diff),
                    "differenceRangeMicroUSD": [min(diff), max(diff)],
                    "acceptedCountDifference": 0,
                }
            )
    result = {
        "passed": True,
        "technicalAttempts": len(technical),
        "worldAttempts": len(worlds),
        "buyerOffers": 24 * len(worlds),
        "scenarios": [
            {
                "scenario": k[0],
                "arm": k[1],
                "priceMicroUSD": k[2],
                "worlds": len(v),
                "profitMeanUSD": statistics.mean(w["financial"]["profit"] for w in v) / 1e6,
                "profitRangeUSD": [
                    min(w["financial"]["profit"] for w in v) / 1e6,
                    max(w["financial"]["profit"] for w in v) / 1e6,
                ],
                "profitableWorlds": sum(w["financial"]["profit"] > 0 for w in v),
                "accepted": sum(w["accepted"] for w in v),
                "reversals": sum(w["reversals"] for w in v),
            }
            for k, v in sorted(grouped.items())
        ],
        "pairedComparisons": comparisons,
        "caseOutcomes": dict(Counter(t["investigation"]["status"] for t in technical)),
        "baselineOutcomes": dict(
            Counter(t["cheapestSingleMeasurementAblation"]["result"]["status"] for t in technical)
        ),
        "frozenInputs": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()},
        "scope": "Independent code and arithmetic in the same process environment and author session; not an independent scientist, organization or physical replication.",
    }
    target = root / "audit.json"
    with target.open("x") as f:
        json.dump(result, f, indent=2)
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "passed",
                    "technicalAttempts",
                    "worldAttempts",
                    "buyerOffers",
                    "caseOutcomes",
                    "baselineOutcomes",
                ]
            }
        )
    )


if __name__ == "__main__":
    run(Path(sys.argv[1]))
