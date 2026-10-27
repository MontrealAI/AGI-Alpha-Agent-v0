# SPDX-License-Identifier: Apache-2.0
"""Frozen, offline research runs. All enterprise events are simulated."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import statistics
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

from .simulator import Policy, Scenario, SCENARIOS, simulate

ROOT = Path(__file__).resolve().parents[1]
TRAIN_SEEDS = list(range(730001, 730025))
CONFIRM_SEEDS = list(range(740001, 740065))
SENSITIVITY_SEEDS = list(range(750001, 750017))
ARMS = ("beta", "isolated", "network", "network_no_invest")
ABLATION_ARMS = ("remove_representation", "remove_falsifier", "remove_composition", "duplicate", "no_retention")


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def policies() -> list[Policy]:
    prices = [("fixed", x, 0.0) for x in (.35, .55, .75, 1.0, 1.15)]
    prices += [("adaptive", .75, x) for x in (-.10, 0.0, .10)]
    answer = []
    for mode, ratio, offset in prices:
        for hurdle in (None, 1.0, 1.35, 2.0):
            suffix = "retain" if hurdle is None else f"invest-{hurdle:g}"
            name = f"{mode}-{ratio if mode == 'fixed' else offset:g}-{suffix}"
            answer.append(Policy(name=name, pricing=mode, price_ratio=ratio, price_offset=offset,
                                 invest=hurdle is not None, hurdle=hurdle or 1.35))
    return answer


def sensitivity_cases() -> list[tuple[str, dict]]:
    # All declared before confirmation; one-factor tests except explicitly named joint stresses.
    return [
        ("human-price-10pct", {"human_price_factor": .1}),
        ("human-price-25pct", {"human_price_factor": .25}),
        ("human-price-50pct", {"human_price_factor": .5}),
        ("leads-0.05", {"leads_per_week": .05}),
        ("leads-0.25", {"leads_per_week": .25}),
        ("leads-0.5", {"leads_per_week": .5}),
        ("leads-1", {"leads_per_week": 1.0}),
        ("leads-2", {"leads_per_week": 2.0}),
        ("leads-8", {"leads_per_week": 8.0}),
        ("leads-16", {"leads_per_week": 16.0}),
        ("token-price-3x", {"token_cost_factor": 3.0}),
        ("token-price-10x", {"token_cost_factor": 10.0}),
        ("cache-disabled", {"cache_enabled": False}),
        ("trust-0.45", {"initial_trust": .45}),
        ("integration-0.35", {"integration_fraction": .35}),
        ("correlated-fault-0.25", {"common_fault_probability": .25}),
        ("validator-detection-0.40", {"semantic_detection": .4, "executable_detection": .85}),
        ("construct-0.30", {"construction_success": .3}),
        ("construct-0.95", {"construction_success": .95}),
        ("build-effort-0.10", {"construction_cost_factor": .1}),
        ("build-effort-0.50", {"construction_cost_factor": .5}),
        ("build-effort-2", {"construction_cost_factor": 2.0}),
        ("transfer-0.40", {"transfer_success": .4}),
        ("transfer-0.98", {"transfer_success": .98}),
        ("integration-check-4x", {"transfer_validation_factor": 4.0}),
        ("overlap-0", {"initial_overlap": 0.0}),
        ("overlap-0.90", {"initial_overlap": .9}),
        ("reuse-savings-0", {"reuse_savings_factor": 0.0}),
        ("lifetime-12", {"useful_lifetime": 12}),
        ("lifetime-104", {"useful_lifetime": 104}),
        ("beta-static", {"external_improvement": 0.0}),
        ("beta-fast", {"external_improvement": .6}),
        ("copying-fast", {"copying_hazard": .05}),
        ("obsolescence-0.05", {"obsolete_hazard": .05}),
        ("diversity-1", {"diversity": 1}),
        ("specialization-0", {"specialization": 0.0}),
        ("specialization-0.8", {"specialization": .8}),
        ("depth-1-only", {"depth_weights": (1.0, 0.0, 0.0)}),
        ("depth-3-heavy", {"depth_weights": (.15, .25, .6)}),
        ("validators-1", {"validator_slots": 1}),
        ("validators-4", {"validator_slots": 4}),
        ("quota-quarter", {"quota_input_m": 50, "quota_output_m": 10}),
        ("compute-double", {"quota_input_m": 400, "quota_output_m": 80}),
        ("agents-double", {"agents": 12}),
        ("scale-complete-double", {"agents": 12, "validator_slots": 4, "quota_input_m": 400, "quota_output_m": 80}),
        ("seed-10000", {"seed_capital": 10000}),
        ("seed-25000", {"seed_capital": 25000}),
        ("collections-12weeks", {"collection_delay": 12}),
        ("joint-commercial-downside", {"human_price_factor": .1, "leads_per_week": .5, "token_cost_factor": 3,
                                       "initial_trust": .5, "collection_delay": 12}),
        ("cheap-extraction-focused", {"construction_cost_factor": .1, "diversity": 1}),
    ]


def freeze(out: Path) -> dict:
    files = sorted([p for p in (ROOT / "src").glob("*.py")]
                   + [p for p in (ROOT / "tests").glob("test_*.py")]
                   + [ROOT / "sources/calibration.json", ROOT / "sources/workload_catalog.json",
                      ROOT / "evidence/RESEARCH_PROTOCOL.md", ROOT / "evidence/FINAL_RUN_DESIGN.md",
                      ROOT / "evidence/recipient_ablation_design.md"])
    missing = [str(p) for p in files if not p.exists()]
    if missing:
        raise RuntimeError(f"Cannot freeze missing material: {missing}")
    manifest = {
        "schema": "beyond-beta-protocol/1", "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "title": "Beyond Beta: The Network That Invents Its Economy",
        "status": "frozen-before-training-and-confirmation", "source_kind": "simulation-design",
        "training_seeds": TRAIN_SEEDS, "confirmation_seeds": CONFIRM_SEEDS,
        "sensitivity_seeds": SENSITIVITY_SEEDS, "arms": ARMS, "ablation_arms": ABLATION_ARMS,
        "ablation_seeds": CONFIRM_SEEDS[:16], "scenarios": {k: asdict(v) for k, v in SCENARIOS.items()},
        "policy_candidates": [asdict(x) for x in policies()], "sensitivity_cases": sensitivity_cases(),
        "objective": "Maximize mean 104-week collected operating surplus net of accrued costs and closing obligations; no terminal skill valuation.",
        "training_constraint": "Observed training cash-shortfall frequency <=0.05; this is an empirical screen, not a risk guarantee.",
        "tie_break": "Within 1 USD prefer no investment, then lexicographic policy name.",
        "policy_scope": "32-policy finite family, selected on network arm; same frozen policy applied to every primary arm.",
        "sensitivity_policy": "Frozen central policy, with and without discretionary investment; response rules see each declared scenario prior.",
        "statistics": "Independent-world means; 95% normal Monte Carlo intervals for means and paired differences; Wilson intervals for binary frequencies. Not empirical market confidence.",
        "ledger_scope": "Every confirmation world has a complete transaction ledger; first predeclared seed also retains complete traces for every scenario/arm.",
        "resource_control": "Equal initial agents, quotas, seed, ordinary experience and external draws across arms; real sharing/invention overhead charged where incurred.",
        "source_hashes": {str(p.relative_to(ROOT)): digest(p) for p in files},
        "antecedent_evidence": {"mechanism": digest(ROOT / "evidence/mechanism_witness.json"),
                                "graph": digest(ROOT / "evidence/graph_demo.json")},
        "not_established": ["matched frontier task acceptance", "customer demand", "human-only matched effort", "operational Alpha", "live ENS", "sales", "self-acceleration"],
    }
    path = out / "protocol_freeze.json"
    if path.exists():
        raise RuntimeError("A freeze already exists; use a distinct output directory, never overwrite a protocol.")
    write_json(path, manifest)
    return manifest


def verify_freeze(out: Path) -> dict:
    manifest = json.loads((out / "protocol_freeze.json").read_text())
    for name, expected in manifest["source_hashes"].items():
        if digest(ROOT / name) != expected:
            raise RuntimeError(f"Frozen source changed: {name}")
    return manifest


def worker(task):
    case, scenario, policy, seed, arm, retain = task
    result = simulate(scenario, policy, seed, arm, retain)
    result["case"] = case
    return result


def execute(tasks, workers: int):
    with ProcessPoolExecutor(max_workers=workers) as pool:
        yield from pool.map(worker, tasks, chunksize=4)


def mean_ci(values: list[float]) -> dict:
    n = len(values)
    mean = statistics.fmean(values) if n else 0.0
    se = statistics.stdev(values) / math.sqrt(n) if n > 1 else 0.0
    return {"n": n, "mean": mean, "lower": mean - 1.96 * se, "upper": mean + 1.96 * se,
            "min": min(values) if n else None, "max": max(values) if n else None,
            "median": statistics.median(values) if n else None}


def frequency(values: list[bool]) -> dict:
    n, count = len(values), sum(values)
    p, z = count / n, 1.96
    center = (p + z*z / (2*n)) / (1 + z*z/n)
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / (1 + z*z/n)
    return {"count": count, "n": n, "rate": p, "lower": center-half, "upper": center+half}


def aggregate(rows: list[dict]) -> dict:
    answer = {k: mean_ci([float(r.get(k, 0)) for r in rows]) for k in
              ("profit", "cash", "collections", "expenses", "investment_count", "investment_cost", "min_cash",
               "closing_obligations", "available_cash", "max_input_m", "max_output_m", "unfinished_jobs", "receivables")}
    for k in ("accepted_useful", "orders", "late", "false_passes", "admitted_skills", "recipient_useful",
              "retired_into_beta", "successful_transfer", "failed_transfer", "quota_wait_weeks", "validator_wait_weeks",
              "buyer_human", "buyer_postpone", "buyer_none", "capacity_refused", "cash_refused"):
        answer[k] = mean_ci([float(r["stats"].get(k, 0)) for r in rows])
    ratios = [r["mean_price_ratio"] for r in rows if r["mean_price_ratio"] is not None]
    answer["mean_price_ratio"] = mean_ci(ratios)
    answer["cash_shortfall"] = frequency([bool(r["stats"].get("cash_shortfall")) for r in rows])
    answer["positive_profit"] = frequency([r["profit"] > 0 for r in rows])
    answer["any_investment"] = frequency([r["investment_count"] > 0 for r in rows])
    answer["cost_categories"] = {k: statistics.fmean([r["costs"].get(k, 0) for r in rows])
                                  for k in sorted({k for r in rows for k in r["costs"]})}
    return answer


def train(out: Path, workers: int) -> dict:
    verify_freeze(out)
    if (out / "selected_policies.json").exists():
        raise RuntimeError("Training output exists; use a separate replay directory.")
    grid = policies()
    tasks = [(name, s, p, seed, "network", False) for name, s in SCENARIOS.items() for p in grid for seed in TRAIN_SEEDS]
    grouped = {}
    with (out / "training_runs.jsonl").open("w") as stream:
        for i, r in enumerate(execute(tasks, workers), 1):
            stream.write(json.dumps(r, separators=(",", ":")) + "\n")
            grouped.setdefault((r["scenario"], r["policy"]["name"]), []).append(r)
            if i % 192 == 0:
                print(f"training {i}/{len(tasks)}", flush=True)
    evaluations, selected = [], {}
    for scenario in SCENARIOS:
        candidates = []
        for p in grid:
            rows = grouped[scenario, p.name]
            a = aggregate(rows)
            feasible = a["cash_shortfall"]["rate"] <= .05
            row = {"scenario": scenario, "policy": asdict(p), "mean_profit": a["profit"]["mean"],
                   "cash_shortfall": a["cash_shortfall"], "feasible": feasible}
            evaluations.append(row)
            if feasible:
                candidates.append(row)
        if not candidates:
            raise RuntimeError(f"No policy passes risk screen in {scenario}; report no supported policy, do not improvise.")
        best = max(x["mean_profit"] for x in candidates)
        tied = [x for x in candidates if best - x["mean_profit"] <= 1.0]
        selected[scenario] = min(tied, key=lambda x: (x["policy"]["invest"], x["policy"]["name"]))["policy"]
    write_json(out / "policy_search.json", evaluations)
    result = {"selected_at_utc": datetime.now(timezone.utc).isoformat(), "policies": selected,
              "training_results_sha256": digest(out / "training_runs.jsonl"),
              "protocol_sha256": digest(out / "protocol_freeze.json"), "confirmation_seen": False}
    write_json(out / "selected_policies.json", result)
    return result


def confirmation(out: Path, workers: int) -> dict:
    verify_freeze(out)
    selected = json.loads((out / "selected_policies.json").read_text())
    if (out / "confirmation_runs.jsonl").exists():
        raise RuntimeError("Confirmation output exists; never overwrite a confirmation set.")
    tasks = [(name, s, Policy(**selected["policies"][name]), seed, arm, True)
             for name, s in SCENARIOS.items() for arm in ARMS for seed in CONFIRM_SEEDS]
    rows, samples = [], []
    with (out / "confirmation_runs.jsonl").open("w") as stream, gzip.open(out / "confirmation_ledgers.jsonl.gz", "wt", compresslevel=6) as ledgers:
        for i, r in enumerate(execute(tasks, workers), 1):
            ledgers.write(json.dumps({"scenario": r["scenario"], "arm": r["arm"], "seed": r["seed"],
                                     "ledger": r["ledger"], "weekly": r["weekly"], "outcomes": r["outcomes"]},
                                    separators=(",", ":")) + "\n")
            if r["seed"] == CONFIRM_SEEDS[0]:
                samples.append(r)
                write_json(out / "samples" / f"{r['scenario']}-{r['arm']}.json", r)
            slim = {k: v for k, v in r.items() if k not in {"ledger", "weekly", "events", "outcomes", "skills"}}
            rows.append(slim)
            stream.write(json.dumps(slim, separators=(",", ":")) + "\n")
            if i % 64 == 0:
                print(f"confirmation {i}/{len(tasks)}", flush=True)
    summary = {"source_kind": "simulation", "n_worlds_per_scenario_arm": len(CONFIRM_SEEDS), "scenarios": {}, "paired": {}}
    for name in SCENARIOS:
        summary["scenarios"][name] = {a: aggregate([r for r in rows if r["scenario"] == name and r["arm"] == a]) for a in ARMS}
        indexed = {(r["arm"], r["seed"]): r for r in rows if r["scenario"] == name}
        summary["paired"][name] = {}
        for treatment, control in (("network", "beta"), ("network", "isolated"), ("network", "network_no_invest"), ("isolated", "beta")):
            key = f"{treatment}-minus-{control}"
            summary["paired"][name][key] = {
                "profit": mean_ci([indexed[treatment, s]["profit"] - indexed[control, s]["profit"] for s in CONFIRM_SEEDS]),
                "accepted_useful": mean_ci([indexed[treatment, s]["stats"].get("accepted_useful", 0) - indexed[control, s]["stats"].get("accepted_useful", 0) for s in CONFIRM_SEEDS])}
    write_json(out / "summary.json", summary)
    write_json(out / "demo_data.json", {"summary": summary, "samples": samples, "sensitivity": [],
                                       "mechanism": json.loads((ROOT / "evidence/mechanism_witness.json").read_text()),
                                       "graph": json.loads((ROOT / "evidence/graph_demo.json").read_text())})
    return summary


def sensitivities(out: Path, workers: int) -> None:
    verify_freeze(out)
    selected = json.loads((out / "selected_policies.json").read_text())["policies"]
    policy = Policy(**selected["central"])
    tasks = []
    for label, changes in sensitivity_cases():
        scenario = replace(SCENARIOS["central"], name=label, **changes)
        for arm in ("beta", "network"):
            for investment in (False, True):
                if arm == "beta" and investment:
                    continue
                p = replace(policy, name=f"{policy.name}-{'optional-invest' if investment else 'retain'}", invest=investment)
                for seed in SENSITIVITY_SEEDS:
                    tasks.append((label + ("-optional-invest" if investment else "-retain"), scenario, p, seed, arm, False))
    grouped, rows = {}, []
    with (out / "sensitivity_runs.jsonl").open("w") as stream:
        for i, r in enumerate(execute(tasks, workers), 1):
            rows.append(r)
            grouped.setdefault((r["case"], r["arm"]), []).append(r)
            stream.write(json.dumps(r, separators=(",", ":")) + "\n")
            if i % 192 == 0:
                print(f"sensitivity {i}/{len(tasks)}", flush=True)
    summary = [{"case": case, "arm": arm, **aggregate(rs)} for (case, arm), rs in grouped.items()]
    write_json(out / "sensitivity.json", summary)
    tasks = [(name, scenario, Policy(**selected[name]), seed, arm, False)
             for name, scenario in SCENARIOS.items() for arm in ABLATION_ARMS for seed in CONFIRM_SEEDS[:16]]
    ablations = list(execute(tasks, workers))
    write_json(out / "ablation_runs.json", ablations)
    write_json(out / "ablation_summary.json", [{"scenario": name, "arm": arm,
               **aggregate([r for r in ablations if r["scenario"] == name and r["arm"] == arm])}
              for name in SCENARIOS for arm in ABLATION_ARMS])
    demo = json.loads((out / "demo_data.json").read_text())
    demo["sensitivity"] = summary
    write_json(out / "demo_data.json", demo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("freeze", "train", "confirm", "sensitivity", "all"))
    parser.add_argument("--out", type=Path, default=ROOT / "results")
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.phase in {"freeze", "all"}:
        freeze(args.out)
        print("Protocol frozen", flush=True)
    if args.phase in {"train", "all"}:
        result = train(args.out, args.workers)
        print(json.dumps(result["policies"], indent=2), flush=True)
    if args.phase in {"confirm", "all"}:
        confirmation(args.out, args.workers)
    if args.phase in {"sensitivity", "all"}:
        sensitivities(args.out, args.workers)


if __name__ == "__main__":
    main()
