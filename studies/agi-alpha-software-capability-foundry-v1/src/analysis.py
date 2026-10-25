# SPDX-License-Identifier: Apache-2.0
"""Frozen analysis: instance-level paired log ratios, no favorable-case selection."""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import random
import statistics

def percentile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = int(position)
    return ordered[low] + (ordered[min(low + 1,len(ordered)-1)] - ordered[low]) * (position - low)

def paired(rows: list[dict], first: str, second: str, resamples: int = 10000, seed: int = 395022) -> dict:
    arms = {arm: {r["case"]:r for r in rows if r["arm"] == arm} for arm in (first,second)}
    names = sorted(arms[first])
    if set(names) != set(arms[second]) or not names:
        return {"estimable": False, "reason": "missing-instance"}
    ratios = [math.log(arms[first][case]["total_cpu_seconds"] / arms[second][case]["total_cpu_seconds"]) for case in names]
    rng = random.Random(seed)
    distribution = [math.exp(sum(rng.choices(ratios,k=len(ratios)))/len(ratios)) for _ in range(resamples)]
    return {"estimable": True, "instances":len(names), "geometric_cpu_ratio":math.exp(statistics.mean(ratios)),
            "ci95":[percentile(distribution,0.025),percentile(distribution,0.975)],
            "mean_paired_cpu_seconds":statistics.mean(arms[first][c]["total_cpu_seconds"] - arms[second][c]["total_cpu_seconds"] for c in names),
            "unit":"generated repository instance; repeated operations aggregated, conditional source/host inference"}

def analyze(path: Path) -> dict:
    campaign = json.loads(path.read_text())
    rows = campaign["outcomes"]
    expected_arms = {"specialist","no_asset","history","conventional","flywheel","equivalent","reconstruction"}
    pairs = [(r["case"], r["arm"]) for r in rows]
    names = {r["case"] for r in rows}
    if (len(names) != 24 or len(rows) != 24 * len(expected_arms) or len(set(pairs)) != len(pairs)
        or set(pairs) != {(case,arm) for case in names for arm in expected_arms}):
        raise ValueError("Confirmation must contain 24 complete unique instances by seven arms")
    all_correct = all(all(r.get(k) for k in ("read_passed","child_passed","trace_passed","budget_passed")) for r in rows)
    comparisons = {arm:paired(rows,arm,"specialist") for arm in sorted({r["arm"] for r in rows}) if arm != "specialist"}
    summary = {}
    for arm in sorted({r["arm"] for r in rows}):
        own = [r for r in rows if r["arm"]==arm]
        summary[arm]={"instances":len(own), "read_passed":sum(r["read_passed"] for r in own),
            "child_passed":sum(r["child_passed"] for r in own), "trace_passed":sum(r["trace_passed"] for r in own),
            "budget_passed":sum(r["budget_passed"] for r in own),
            "total_cpu_seconds":sum(r["total_cpu_seconds"] for r in own),
            "total_wall_seconds":sum(r["wall_seconds"] for r in own),
            "median_instance_cpu_seconds":statistics.median(r["total_cpu_seconds"] for r in own),
            "service_wall_seconds":sum(r["service_wall_seconds"] for r in own),
            "improvement_wall_seconds":sum(r["improvement_wall_seconds"] for r in own),
            "parent_invocations":sum(t["invocations"] for r in own for t in r["parent_traces"] if t)}
    primary = comparisons["flywheel"]
    admitted = all_correct and primary.get("estimable") and primary["ci95"][1] < 0.95
    conditions = {}
    for arm in expected_arms:
        conditions[arm] = {}
        for phase, stage in (("read","read"),("child","diagnose")):
            collected = {"fresh_process":[], "warm_process":[]}
            for case in sorted(names):
                raw = json.loads((path.parent / case / arm / (phase+".json")).read_text())
                selected = [r for r in raw.get("costs",[]) if r["stage"]==stage]
                for condition in collected:
                    values = [r["total_cpu_seconds"] for r in selected if r["condition"]==condition]
                    if values:
                        collected[condition].append(statistics.mean(values))
            for condition, values in collected.items():
                conditions[arm][phase+"_"+condition] = {"instances":len(values),
                    "mean_cpu_seconds":statistics.mean(values) if values else None,
                    "median_cpu_seconds":statistics.median(values) if values else None}
    return {"schema":"foundry-analysis/v1", "all_correct":all_correct,"primary":primary,
        "conditions":conditions,"timings_qualified":all_correct,
        "decision":"ADMIT_SCOPED_CPU_BENEFIT" if admitted else "HOLD_FLYWHEEL_SUPERIORITY",
        "arms":summary,"comparisons_to_specialist":comparisons,
        "flywheel_vs_history":paired(rows,"flywheel","history"),
        "flywheel_vs_conventional":paired(rows,"flywheel","conventional"),
        "flywheel_vs_reconstruction":paired(rows,"flywheel","reconstruction"),
        "flywheel_vs_equivalent":paired(rows,"flywheel","equivalent"),
        "upfront_research_paid_back":None,"monetary_profit":None,"acceleration_established":False,
        "limitations":["one host and one public source ecosystem","24 generated instances, not 24 natural repositories",
            "bounded deterministic templates, no autonomous language-model construction comparison",
            "shared OS cache not flushed; no physical disk-cold inference",
            "research/model/human/integration/maintenance costs incomplete; full payback unknown"]}

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args.campaign)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"decision":result["decision"],"all_correct":result["all_correct"],"primary":result["primary"]}))
