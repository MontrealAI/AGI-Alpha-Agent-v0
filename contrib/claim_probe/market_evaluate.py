# SPDX-License-Identifier: Apache-2.0
"""Freeze and assess conditional commerce; seed selection never follows outcomes."""

import collections
import hashlib
import json
import secrets
import statistics
import sys
import time
from pathlib import Path

from contrib.claim_probe.market import PRICES, RATES, SCENARIOS, operate


def run(mode, output, training=None):
    if mode not in {"training", "confirmation"}:
        raise ValueError("evaluation mode")
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve().parents[2]
    paths = sorted(Path(__file__).parent.glob("*.py"))
    paths += sorted((source / "alpha_factory_v1/core/runtime/claim_probe").glob("*.py"))
    paths += [
        source / "alpha_factory_v1/core/runtime/meta_discovery/exchange.py",
        source / "alpha_factory_v1/core/runtime/meta_discovery/economics.py",
        source.parent / "PROTOCOL.md",
    ]
    if mode == "confirmation":
        prior = json.loads(Path(training).read_text())
        price = prior["selectedPriceMicroUSD"]
    else:
        price = None
    freeze = {
        "sourceHashes": {str(p.relative_to(source.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        "rates": RATES,
        "mode": mode,
        "policy": "Price fixed from training median profit across non-free stress scenarios; all stress results retained, no probability weighting",
        "priceMicroUSD": price,
        "scenarios": SCENARIOS,
        "pairsPerScenario": 7 if mode == "confirmation" else 3,
        "primaryFundingWorld": {"scenario": "reference", "index": 0, "arm": "instrument"},
        "investmentCapMicroUSD": 10_000_000,
        "valuationAssumption": "Ten future requests at 0.25 participation and 5 USD net price, .25 USD upkeep; conditional expected surplus 2.25 USD",
        "endpoints": [
            "participation",
            "accepted",
            "netCollections",
            "completeCostProfit",
            "unrestrictedEarned",
            "investmentDecision",
        ],
        "scope": "No calibrated market probabilities or actual invoices; full conditional model only",
    }
    (out / "freeze.json").write_text(json.dumps(freeze, sort_keys=True, indent=2) + "\n")
    freeze_hash = hashlib.sha256((out / "freeze.json").read_bytes()).hexdigest()
    seed = secrets.randbits(44) if mode == "confirmation" else 28102026
    (out / "freshness.json").write_text(
        json.dumps(
            {
                "freezeSha256": freeze_hash,
                "seed": seed,
                "generatedAfterFreeze": True,
                "UTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
            indent=2,
        )
        + "\n"
    )
    rows = []
    for scenario in SCENARIOS:
        for i in range(freeze["pairsPerScenario"]):
            for candidate_price in [price] if price is not None else PRICES:
                for arm in ["instrument", "ordinary_library"]:
                    directory = out / f"{scenario}-{i}-{candidate_price}-{arm}"
                    result = operate(directory, seed + i, scenario, candidate_price, arm)
                    result["index"] = i
                    rows.append(result)
    with (out / "worlds.jsonl").open("x") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    if price is None:
        scores = {
            str(p): statistics.median(
                x["financial"]["profit"]
                for x in rows
                if x["priceMicroUSD"] == p
                and x["arm"] == "instrument"
                and x["scenario"] != "free_completed_alternative"
            )
            for p in PRICES
        }
        price = max(PRICES, key=lambda p: (scores[str(p)], -p))
    else:
        scores = None
    summary = {
        "mode": mode,
        "worlds": len(rows),
        "pairedWorlds": len(rows) // 2,
        "freezeSha256": freeze_hash,
        "selectedPriceMicroUSD": price,
        "trainingScores": scores,
        "groups": {},
    }
    for scenario in SCENARIOS:
        for arm in ["instrument", "ordinary_library"]:
            group = [x for x in rows if x["scenario"] == scenario and x["arm"] == arm and x["priceMicroUSD"] == price]
            summary["groups"][scenario + "/" + arm] = {
                "worlds": len(group),
                "profitRangeMicroUSD": [
                    min(x["financial"]["profit"] for x in group),
                    max(x["financial"]["profit"] for x in group),
                ],
                "accepted": sum(
                    sum(y["outcome"] in {"accepted", "accepted-later-reversed"} for y in x["offers"]) for x in group
                ),
                "participated": sum(sum(y["participates"] for y in x["offers"]) for x in group),
                "profitPositive": sum(x["financial"]["profit"] > 0 for x in group),
                "investmentApproved": sum(x["investment"]["decision"] == "CONTINUE" for x in group),
            }
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if mode == "confirmation":
        primary = next(x for x in rows if x["scenario"] == "reference" and x["index"] == 0 and x["arm"] == "instrument")
        decision = {
            "campaign": "AGI-ALPHA-RESEARCH-ENTERPRISE-20261028",
            "world": {"seed": primary["seed"], "scenario": "reference", "index": 0, "arm": "instrument"},
            "worldSha256": hashlib.sha256(json.dumps(primary, sort_keys=True).encode()).hexdigest(),
            "decision": primary["investment"],
            "financial": primary["financial"],
            "constructionBudgetMicroUSD": 10_000_000,
            "asset": "new exact multi-affine claim checker; not yet constructed",
            "actualConstruction": False,
            "valuationBasis": primary["investmentAssumption"],
            "funding": "unrestricted simulated earned cash; opening equity excluded by policy",
            "createdUTC": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        (out / "funding-decision.json").write_text(json.dumps(decision, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
