# SPDX-License-Identifier: Apache-2.0
"""Reproduce development, freeze, then independent fresh confirmation without API calls."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import scipy
import sklearn

from benchmark import COST_CEILING, TARGET_RESPONSE, evaluate, make_task, points
from learning import WIDTH, d_optimal_order, features, fit_guarded, fit_portfolio, learn_artifact


HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
ARTIFACTS = HERE / "artifacts"
PROTOCOL = HERE.parent / "PROTOCOL.json"
METHODS = ["beta_space", "beta_dopt", "beta_adaptive", "beta_direct", "v1", "v2", "library_v2", "wrong_prior", "oracle_support"]
BUDGETS = [24, 40, 64, 96]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def source_hashes() -> dict[str, str]:
    sources = sorted(HERE.glob("*.py")) + [PROTOCOL]
    return {str(path.relative_to(HERE.parent)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}


def train() -> None:
    all_models = []
    ledger = []
    for index in range(11):
        task_seed = 210_000 + index * 101
        oracle, _ = make_task(task_seed, "compatible")
        x = points(task_seed + 13, 128)
        started = time.perf_counter()
        y = oracle.query(x)
        model, metadata = fit_portfolio(features(x[:104]), y[:104], features(x[104:]), y[104:])
        observed_seconds = time.perf_counter() - started
        all_models.append(model)
        score = evaluate(model, oracle, task_seed)
        ledger.append({
            "event_id": f"origin-{index:02d}" if index == 0 else f"gym-{index:02d}",
            "category": "A" if index == 0 else "C",
            "purpose": "paid characterization required learning" if index == 0 else "optional broader motif learning",
            "oracle_calls": oracle.calls,
            "training_calls": 104,
            "visible_validation_calls": 24,
            "research_assessment_calls": score["independent_scorer_calls"] - (384 if index==0 else 0),
            "research_diagnostic_calls":16,
            "observed_seconds": observed_seconds,
            "accepted": score["prediction_accepted"],
            "paid_verification_calls": 384 if index ==0 else 0,
            "complete_delivery_calls": 512 if index ==0 else 128,
            "prediction_nrmse": score["prediction_nrmse"],
            "design_accepted": score["design_accepted"],
            "selected_method": metadata["selected_method"],
            "learned_nonzero_terms": np.flatnonzero(np.abs(model) > 1e-3).tolist(),
        })
        if index == 0:
            write_json(ARTIFACTS / "v1.json", learn_artifact(all_models, "v1"))
            write_json(ARTIFACTS / "origin-deliverable.json", {
                "coefficients": model.tolist(), "acceptance": score, "training_observations": {
                    "inputs": x.tolist(), "outputs": y.tolist()}, "provenance": "researcher-authored learner; automatic sparse fit",
            })
    write_json(ARTIFACTS / "v2.json", learn_artifact(all_models, "v2"))
    wrong = np.random.default_rng(841_007).choice(np.arange(WIDTH), size=len(learn_artifact(all_models, "v2")["support"]), replace=False)
    write_json(ARTIFACTS / "wrong-prior.json", {"version": "wrong_prior", "support": np.sort(wrong).tolist()})
    write_json(OUT / "learning_ledger.json", {"events": ledger, "origin_oracle_calls": ledger[0]["oracle_calls"],
               "gym_oracle_calls": sum(item["oracle_calls"] for item in ledger[1:]),
               "research_assessment_calls": sum(item["research_assessment_calls"] for item in ledger),
               "all_failed_campaigns_retained": True, "live_frontier_calls": 0})


def task_schedule(split: str) -> list[tuple[int, str]]:
    if split == "development":
        regimes = ["compatible"] * 6 + ["partial_shift"] * 3 + ["novel_family"] * 3
        base = 310_000
    else:
        regimes = ["compatible"] * 24 + ["partial_shift"] * 12 + ["novel_family"] * 12
        base = 910_000
    return [(base + index * 107, regime) for index, regime in enumerate(regimes)]


def run_method(seed: int, regime: str, budget: int, method: str, artifacts: dict[str, Any]) -> tuple[dict[str, Any], np.ndarray]:
    started = time.perf_counter()
    oracle, hidden = make_task(seed, regime)
    validation_count = 0 if method=="beta_direct" else (8 if budget <=40 else (12 if budget==64 else 16))
    count = budget - validation_count - 1
    validation_points = points(seed + 110_003, validation_count)
    validation_values = oracle.query(validation_points)
    validation_features = features(validation_points)
    support = None
    if method in ["v1", "v2", "library_v2", "wrong_prior"]:
        support = artifacts["v2" if method == "library_v2" else method]["support"]
    elif method == "oracle_support":
        support = [0] + hidden["active_support"]

    chosen_override = None
    verified_response = None
    if method == "beta_direct":
        plans = points(seed + 720_007, 512)
        costs = 0.2 + np.mean((plans+1)**2, axis=1)
        candidates = [int(i) for i in np.argsort(costs) if costs[i] <= COST_CEILING]
        queried_points, queried_values = [], []
        chosen_override = -1
        for index in candidates[:count+1]:
            value = float(oracle.query(plans[index:index+1])[0])
            queried_points.append(plans[index])
            queried_values.append(value)
            if value >= TARGET_RESPONSE:
                chosen_override = index
                verified_response = value
                break
        x, y = np.asarray(queried_points), np.asarray(queried_values)
    elif method == "beta_space":
        x = points(seed + 220_003, count)
        y = oracle.query(x)
    elif method == "beta_adaptive":
        pilot_count = max(10, count // 2)
        pilot_x = points(seed + 330_007, pilot_count)
        pilot_y = oracle.query(pilot_x)
        pilot_model, _ = fit_portfolio(features(pilot_x), pilot_y, validation_features, validation_values)
        inferred = np.flatnonzero(np.abs(pilot_model) > 1e-3).tolist()
        if not inferred:
            inferred = None
        pool = points(seed + 440_009, 192)
        order = d_optimal_order(pool, inferred)
        augmentation = pool[order[: count - pilot_count]]
        x = np.concatenate([pilot_x, augmentation])
        y = np.concatenate([pilot_y, oracle.query(augmentation)])
    else:
        pool = points(seed + 440_009, 192)
        order = d_optimal_order(pool, support)
        x = pool[order[:count]]
        y = oracle.query(x)

    if method == "beta_direct":
        model = np.zeros(WIDTH)
        metadata = {"selected_method":"direct_actual_evaluation","selected_parameter":0,"visible_validation_nrmse":0.0,"prior_rejected":False}
    else:
        model, metadata = fit_guarded(features(x), y, validation_features, validation_values, support)
        plans = points(seed+720_007,512)
        costs = 0.2 + np.mean((plans+1)**2,axis=1)
        predicted = features(plans) @ model
        candidates = np.flatnonzero((predicted >=TARGET_RESPONSE+0.01)&(costs<=COST_CEILING))
        chosen_override = int(candidates[np.argmin(costs[candidates])]) if len(candidates) else -1
        if chosen_override >=0:
            verified_response = float(oracle.query(plans[chosen_override:chosen_override+1])[0])
    elapsed = time.perf_counter() - started
    scores = evaluate(model, oracle, seed, chosen_override)
    actual_acceptance = verified_response is not None and verified_response>=TARGET_RESPONSE
    if bool(actual_acceptance) != scores["design_accepted"]:
        raise AssertionError("Operational verification disagrees with independent audit")
    row = {
        "task_id": f"task-{seed}", "seed": seed, "regime": regime,
        "recipient": "design.agent.agi.eth" if seed % 2 else "diagnostics.agent.agi.eth",
        "identity_status": "simulated, no ENS authentication", "method": method,
        "budget": budget, "oracle_calls": oracle.calls, "observed_seconds": elapsed,
        "training_calls": len(x), "visible_validation_calls": validation_count,
        "final_verification_calls": int(chosen_override>=0) if method !="beta_direct" else len(x),
        "response_service_calls": oracle.calls +384,
        "operational_verified_response":verified_response,
        "operational_acceptance_from_actual_query":bool(actual_acceptance),
        "artifact_version": "v2" if method == "library_v2" else method,
        **metadata, **scores,
    }
    return row, model


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups = []
    for regime in ["all", "compatible", "partial_shift", "novel_family"]:
        for method in METHODS:
            for budget in BUDGETS:
                group = [r for r in rows if r["method"] == method and r["budget"] == budget and (regime == "all" or r["regime"] == regime)]
                if not group:
                    continue
                groups.append({
                    "regime": regime, "method": method, "budget": budget, "n": len(group),
                    "accepted": sum(r["accepted"] for r in group),
                    "prediction_accepted": sum(r["prediction_accepted"] for r in group),
                    "design_accepted": sum(r["design_accepted"] for r in group),
                    "diagnosis_accepted": sum(r["diagnosis_accepted"] for r in group),
                    "median_nrmse": float(np.median([r["prediction_nrmse"] for r in group])),
                    "mean_observed_seconds": float(np.mean([r["observed_seconds"] for r in group])),
                    "prior_rejections": sum(r["prior_rejected"] for r in group),
                })
    comparisons = []
    for budget in BUDGETS:
        for regime in ["all", "compatible", "partial_shift", "novel_family"]:
            task_ids = sorted({r["task_id"] for r in rows if r["budget"] == budget and (regime == "all" or r["regime"] == regime)})
            wins, losses, ties = 0, 0, 0
            for task_id in task_ids:
                group = [r for r in rows if r["task_id"] == task_id and r["budget"] == budget]
                specialist = next(r for r in group if r["method"] == "v2")["accepted"]
                best_beta = any(r["accepted"] for r in group if r["method"].startswith("beta_"))
                wins += int(specialist and not best_beta)
                losses += int(best_beta and not specialist)
                ties += int(specialist == best_beta)
            comparisons.append({"budget": budget, "regime": regime, "n": len(task_ids), "v2_wins": wins,
                                "v2_losses": losses, "ties": ties,
                                "comparison": "hindsight best of three Beta methods, diagnostic favorable to Beta"})
    return {"groups": groups, "paired_best_beta": comparisons, "row_count": len(rows),
            "regime_labels_hidden_from_policies": True,
            "unique_cached_audit_queries": len({r["task_id"] for r in rows}) *896,
            "diagnosis_original_simulator_available": True,
            "direct_paired_diagnosis_calls":32,
            "all_quantities": "Observed executable synthetic oracle calls and numerical outcomes; no measured physical simulator or live frontier model"}


def execute(split: str, limit: int | None = None) -> None:
    if split == "confirmation":
        freeze_path = OUT / "FREEZE.json"
        frozen = json.loads(freeze_path.read_text())
        if frozen["source_hashes"] != source_hashes():
            raise RuntimeError("Technical source or protocol changed after confirmation freeze")
        current_artifacts = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ARTIFACTS.glob("*.json")}
        if frozen["artifact_hashes"] != current_artifacts:
            raise RuntimeError("Learned artifact bytes changed after confirmation freeze")
    artifacts = {name: json.loads((ARTIFACTS / filename).read_text()) for name, filename in [
        ("v1", "v1.json"), ("v2", "v2.json"), ("wrong_prior", "wrong-prior.json")
    ]}
    rows = []
    selected_models = []
    tasks = task_schedule(split)[:limit]
    for task_number, (seed, regime) in enumerate(tasks):
        for budget in BUDGETS:
            for method in METHODS:
                row, model = run_method(seed, regime, budget, method, artifacts)
                row["split"] = split
                rows.append(row)
                if task_number == 0 and method in ["v1", "v2", "beta_adaptive", "beta_space"]:
                    selected_models.append({"task_id": row["task_id"], "method": method, "budget": budget,
                                            "coefficients": model.tolist(), "acceptance": row})
        write_json(OUT / f"{split}_rows.json", rows)
        print(json.dumps({"split": split, "completed_tasks": task_number + 1, "total_tasks": len(tasks), "rows": len(rows)}), flush=True)
    with (OUT / f"{split}_rows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    write_json(OUT / f"{split}_summary.json", summarize(rows))
    write_json(OUT / f"{split}_example_deliverables.json", selected_models)
    if split == "confirmation":
        write_json(OUT / "raw_rows.json", rows)
        (OUT / "raw_rows.csv").write_bytes((OUT / "confirmation_rows.csv").read_bytes())
        write_json(OUT / "summary.json", summarize(rows))
        write_json(OUT / "CONFIRMATION_COMPLETE.json", {"completed_utc": datetime.now(timezone.utc).isoformat(),
                   "source_hashes": source_hashes(), "rows_sha256": hashlib.sha256((OUT / "raw_rows.json").read_bytes()).hexdigest(),
                   "n_tasks": len(tasks), "n_rows": len(rows), "research_scorer_calls_per_method_task": 896})


def freeze() -> None:
    write_json(OUT / "FREEZE.json", {"frozen_utc": datetime.now(timezone.utc).isoformat(),
               "source_hashes": source_hashes(), "artifact_hashes": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in ARTIFACTS.glob("*.json")},
               "development_rows_sha256": hashlib.sha256((OUT / "development_rows.json").read_bytes()).hexdigest(),
               "python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
               "sklearn": sklearn.__version__,
               "independence": "Procedural fresh-task separation within one research team, not an organizationally independent audit or cryptographic isolation",
               "confirmation_access_before_freeze": False,
               "development_trace_revision":"After development, explicit recording and assertion of the already executed final verification response was added; no policies, thresholds, targets, fitting methods or random seeds changed"})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["train", "development", "freeze", "confirmation"])
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    if args.action == "train":
        train()
    elif args.action == "freeze":
        freeze()
    else:
        execute(args.action, args.limit)


if __name__ == "__main__":
    main()
