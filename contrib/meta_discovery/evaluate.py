# SPDX-License-Identifier: Apache-2.0
"""Training or frozen confirmation. No network, model calls or monetary actions."""

from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import random
import secrets
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from alpha_factory_v1.core.runtime.meta_discovery import instrument, checker, comparators, governance, market, models

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PROTOCOL = {
    "schema": "agialpha/meta-evaluation/v1",
    "campaign": "meta-discovery-20261028",
    "technicalTraining": {"families": ["catalyst", "membrane", "photovoltaic"], "seedsPerFamily": 12, "seedStart": 101},
    "technicalConfirmation": {"families": ["catalyst", "membrane", "photovoltaic"], "seedsPerFamily": 16},
    "marketTraining": {
        "seeds": [6101, 6102],
        "pricesMicroUSD": market.PRICES,
        "scenarios": ["reference", "copying", "low_trust"],
        "arm": "instrument",
    },
    "marketConfirmation": {
        "seedsPerScenario": 16,
        "scenarios": market.SCENARIOS,
        "arms": ["instrument", "conventional"],
        "buyersPerWorld": 24,
    },
    "selectionRule": "Maximum mean training profit over all three scenarios and two seeds; tie favors lower price. No confirmation-based selection.",
    "arms": ["instrument", "direct_exact", "conventional_milp", "greedy_ablation"],
    "fairness": "Identical task, action set, declared intervals, costs, budgets and ordinary libraries. Private truth is not supplied to plan constructors. Arm order shuffled from task seed.",
    "primaryEndpoint": "Paired accepted status and minimum experiment cost versus independent exact enumeration and conventional SciPy HiGHS MILP. All attempts retained.",
    "secondaryEndpoints": [
        "independent numerical decision",
        "baseline-one-cheapest-measurement ablation",
        "wall/CPU time",
        "net simulated profit",
        "cash and funding origin",
    ],
    "uncertainty": "Descriptive paired means and seed ranges; no population, physical, market-probability or frontier-model inference. Timings environment-specific.",
    "freshness": "Fresh random seed generated only after source and policy freeze. Within predeclared reduced-model families; not a newly found consequential real-world problem.",
    "repairRule": "At most two training repair rounds. Confirmation is immutable. No final-case editing or replacement; infrastructure failure retained, rerun only same bytes with a versioned log.",
    "boundaries": "No real spend, external contact, chain transaction, hosted service or repository writes. Live generalist/prompt-only model arms are NOT RUN; deterministic controls are not substitutes for that evidence.",
    "resourceBudget": {
        "wallMinutesTotal": 100,
        "startUTC": "2026-10-28T22:45:00+00:00",
        "deadlineUTC": "2026-10-29T00:25:00+00:00",
        "protectedFinalReproductionMinutes": 15,
        "repairRounds": 2,
        "externalSpendUSD": 0,
        "freshSeedRedraws": 0,
    },
    "financialPolicy": {
        "unit": "microUSD",
        "openingSimulationCash": 100000000,
        "seedCostReference": 3000000,
        "seedCostStress": 60000000,
        "developmentAllocation": "One hypothetical C seed expense per alternative world; actual inference metering unavailable. No actual paid job is claimed.",
        "cashBasis": "Segregated restricted escrow is not seller cash. Receipts recognized only with verified release. Refunds reverse revenue and cash.",
        "investment": "No invented successor benefit. Conditional cash availability alone does not authorize a construction. No profit-funded closed loop is claimed.",
    },
    "scope": "Exact finite interval separation only. Assumed noise and candidate completeness. Not physical validation or novel experimental-design theory.",
}


def sources():
    package = ROOT / "alpha_factory_v1/core/runtime/meta_discovery"
    return sorted(package.glob("*.py")) + [
        ROOT / "alpha_factory_v1/core/runtime/cli.py",
        Path(__file__).resolve(),
        HERE / "audit.py",
        HERE / "test_regressions.py",
        ROOT / "pyproject.toml",
        HERE / "CAMPAIGN_DESIGN.md",
    ]


def measure(task, private, seed):
    arms = {
        "instrument": instrument.compile_plan,
        "direct_exact": comparators.direct_plan,
        "conventional_milp": comparators.conventional_milp,
        "greedy_ablation": comparators.greedy_ablation,
    }
    order = list(arms)
    random.Random(seed).shuffle(order)
    outputs = {}
    for name in order:
        start, cpu = time.perf_counter(), time.process_time()
        try:
            result = arms[name](task)
            entry = {"result": result, "error": None}
        except Exception as exc:
            entry = {"result": None, "error": {"type": type(exc).__name__, "message": str(exc)}}
        entry.update(seconds=time.perf_counter() - start, cpuSeconds=time.process_time() - cpu)
        if name in {"instrument", "direct_exact"} and entry["result"]:
            entry["check"] = checker.check(task, entry["result"])
        outputs[name] = entry
    observations = {}
    plan = outputs["instrument"]["result"]
    if plan and plan["status"] == "GO" and plan["selected"]:
        observations = models.investigate(task, private, plan["selected"])
    baseline = [min(task["experiments"], key=lambda e: (e["cost"], e["id"]))["id"]]
    baseline_obs = models.investigate(task, private, baseline)
    return {
        "task": task,
        "privateTruthForPosthocAuditOnly": private,
        "armOrder": order,
        "arms": outputs,
        "observations": observations,
        "investigation": instrument.update_belief(task, observations)
        if observations
        else {"status": "NOT_EXECUTED", "reason": "no certified plan"},
        "cheapestSingleMeasurementAblation": {
            "observations": baseline_obs,
            "result": instrument.update_belief(task, baseline_obs),
        },
    }


def dump(path, data):
    instrument.write_new(path, data)


def run(phase, out):
    out.mkdir(parents=True, exist_ok=False)
    policy = dict(PROTOCOL)
    if phase == "confirmation":
        training = json.loads((out.parent / "training" / "summary.json").read_text())
        policy["selectedPriceMicroUSD"] = training["selectedPriceMicroUSD"]
        policy["trainingSummarySha256"] = hashlib.sha256(
            (out.parent / "training" / "summary.json").read_bytes()
        ).hexdigest()
        record = governance.freeze(sources(), policy, out / "freeze.json")
        # Unpredictable numeric seed after frozen content is recorded; no seed screening.
        seed = secrets.randbits(48)
        dump(
            out / "freshness.json",
            {"seed": seed, "generatedUTC": datetime.now(timezone.utc).isoformat(), "afterFreezeHash": record["hash"]},
        )
    else:
        record = None
        seed = 101
    started = time.monotonic()
    technical = []
    count = 12 if phase == "training" else 16
    with gzip.open(out / "technical.jsonl.gz", "xt", encoding="utf8") as stream:
        for fi, family in enumerate(PROTOCOL["technicalTraining"]["families"]):
            for i in range(count):
                case_seed = seed + fi * 1000 + i
                task, private = models.make_task(family, case_seed, i % 4)
                item = measure(task, private, case_seed)
                stream.write(json.dumps(item, sort_keys=True) + "\n")
                arm = item["arms"]["instrument"]
                exact, milp = item["arms"]["direct_exact"], item["arms"]["conventional_milp"]
                technical.append(
                    {
                        "id": task["id"],
                        "family": family,
                        "status": arm["result"]["status"] if arm["result"] else "ERROR",
                        "accepted": arm.get("check", {}).get("accepted", False),
                        "exactTie": bool(
                            arm["result"]
                            and exact["result"]
                            and all(arm["result"][k] == exact["result"][k] for k in ("status", "cost", "selected"))
                        ),
                        "milpTie": bool(
                            arm["result"]
                            and milp["result"]
                            and all(arm["result"][k] == milp["result"][k] for k in ("status", "cost"))
                        ),
                        "seconds": {k: v["seconds"] for k, v in item["arms"].items()},
                        "investigation": item["investigation"]["status"],
                        "baseline": item["cheapestSingleMeasurementAblation"]["result"]["status"],
                    }
                )
    rows = []
    if phase == "training":
        jobs = [
            (s, sc, p, "instrument")
            for p in market.PRICES
            for sc in PROTOCOL["marketTraining"]["scenarios"]
            for s in [6101, 6102]
        ]
    else:
        jobs = [
            (seed + 10000 + i, sc, policy["selectedPriceMicroUSD"], arm)
            for sc in market.SCENARIOS
            for i in range(16)
            for arm in ["instrument", "conventional"]
        ]
        random.Random(seed).shuffle(jobs)
    with gzip.open(out / "market.jsonl.gz", "xt", encoding="utf8") as stream:
        for i, (s, sc, p, arm) in enumerate(jobs):
            try:
                world = market.operate(out / ("temporary-world-" + str(i)), s, sc, p, arm)
                stream.write(json.dumps(world, sort_keys=True) + "\n")
                rows.append(
                    {
                        "seed": s,
                        "scenario": sc,
                        "price": p,
                        "arm": arm,
                        "profit": world["financial"]["profit"],
                        "cash": world["financial"]["cash"],
                        "earned": world["financial"]["unrestrictedEarned"],
                        "accepted": world["accepted"],
                        "declined": world["declined"],
                        "reversals": world["reversals"],
                        "error": None,
                    }
                )
            except Exception as exc:
                failure = {
                    "seed": s,
                    "scenario": sc,
                    "price": p,
                    "arm": arm,
                    "error": {"type": type(exc).__name__, "message": str(exc)},
                }
                stream.write(json.dumps(failure) + "\n")
                rows.append(failure)
    price_means = {
        str(p): statistics.mean([r["profit"] for r in rows if r["price"] == p and r["error"] is None])
        for p in sorted({r["price"] for r in rows})
    }
    selected = (
        int(max(price_means, key=lambda p: (price_means[p], -int(p))))
        if phase == "training"
        else policy["selectedPriceMicroUSD"]
    )
    summary = {
        "phase": phase,
        "createdUTC": datetime.now(timezone.utc).isoformat(),
        "seconds": time.monotonic() - started,
        "policy": policy,
        "technical": technical,
        "market": rows,
        "selectedPriceMicroUSD": selected,
        "trainingPriceMeansMicroUSD": price_means if phase == "training" else None,
        "technicalCounts": dict(Counter(t["status"] for t in technical)),
        "exactTies": sum(t["exactTie"] for t in technical),
        "milpTies": sum(t["milpTie"] for t in technical),
        "technicalAccepted": sum(t["accepted"] for t in technical),
        "marketErrors": sum(r["error"] is not None for r in rows),
        "physicalQualified": False,
        "fullLifecycleQualified": False,
    }
    if record:
        governance.check_freeze(record, policy)
        summary["freezeRecheck"] = True
    dump(out / "summary.json", summary)
    print(
        json.dumps(
            {
                k: summary[k]
                for k in [
                    "phase",
                    "seconds",
                    "technicalCounts",
                    "exactTies",
                    "milpTies",
                    "technicalAccepted",
                    "marketErrors",
                    "selectedPriceMicroUSD",
                ]
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["training", "confirmation"])
    p.add_argument("output", type=Path)
    args = p.parse_args()
    run(args.phase, args.output.resolve())
