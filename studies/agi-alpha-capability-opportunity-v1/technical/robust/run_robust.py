# SPDX-License-Identifier: Apache-2.0
"""Prespecified stronger compound-outcome supplement, separate from the original study."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import qmc

HERE = Path(__file__).resolve().parent
TECHNICAL = HERE.parent
sys.path.insert(0, str(TECHNICAL))
from benchmark import make_task, points
from learning import WIDTH, d_optimal_order, features, fit_guarded, fit_portfolio
from run_study import BUDGETS, METHODS, write_json


OUT = HERE / "results"


def hashes() -> dict[str, str]:
    paths = [HERE / "run_robust.py", HERE / "PROTOCOL.json"]
    paths += list(TECHNICAL.glob("*.py"))
    paths += [TECHNICAL / "artifacts" / name for name in ["v1.json", "v2.json", "wrong-prior.json"]]
    return {str(p.relative_to(TECHNICAL)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@lru_cache(maxsize=2)
def menu(seed: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    controls = 2 * qmc.LatinHypercube(d=5, seed=seed + 101).random(512) - 1
    contexts = 2 * qmc.LatinHypercube(d=5, seed=730_003).random(16) - 1
    full = np.concatenate([np.repeat(controls[:, None, :], 16, axis=1), np.repeat(contexts[None, :, :], 512, axis=0)], axis=2)
    matrix = features(full.reshape(-1, 10)).reshape(512, 16, WIDTH)
    costs = 0.2 + np.mean((controls + 1) ** 2, axis=1)
    return controls, full, matrix, costs


def qualifies(responses: np.ndarray) -> bool:
    return bool(len(responses) == 16 and np.mean(responses) >= 0.4 and np.sum(responses >= 0) >= 12)


@lru_cache(maxsize=2)
def audit(seed: int, regime: str) -> dict[str, Any]:
    oracle, _ = make_task(seed, regime)
    _, _, matrix, costs = menu(seed)
    responses = matrix @ oracle.coefficients
    allowed = (np.mean(responses, axis=1) >= 0.4) & (np.sum(responses >= 0, axis=1) >= 12) & (costs <= 1.2)
    prediction_features = features(points(seed + 601_003, 384))
    prediction_truth = prediction_features @ oracle.coefficients
    return {"menu_has_feasible_plan": bool(np.any(allowed)), "qualifying_plan_count": int(np.sum(allowed)),
            "prediction_features": prediction_features, "prediction_truth": prediction_truth,
            "best_cost": float(np.min(costs[allowed])) if np.any(allowed) else None}


def run(seed: int, regime: str, budget: int, method: str, artifacts: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    oracle, hidden = make_task(seed, regime)
    controls, full, model_features, costs = menu(seed)
    validation_count = {24:4, 40:8, 64:12, 96:16}[budget]
    support = None
    if method in ["v1", "v2", "library_v2", "wrong_prior"]:
        support = artifacts["v2" if method=="library_v2" else method]["support"]
    elif method == "oracle_support":
        support = [0] + hidden["active_support"]
    chosen = -1
    verification = np.asarray([], dtype=float)
    model = np.zeros(WIDTH)
    traces = []
    if method == "beta_direct":
        for index in np.argsort(costs):
            if costs[index]>1.2 or budget-oracle.calls<16:
                break
            observed = []
            for context in full[index]:
                observed.append(float(oracle.query(context[None, :])[0]))
                if sum(value<0 for value in observed)>4:
                    break
            traces.append({"plan":int(index),"queries":len(observed),"accepted":qualifies(np.asarray(observed))})
            if qualifies(np.asarray(observed)):
                chosen = int(index)
                verification = np.asarray(observed)
                break
        metadata = {"selected_method":"direct_measured_compound_search","prior_rejected":False,
                    "visible_validation_nrmse":None}
    else:
        count = budget - validation_count - 16
        v = points(seed+110_003,validation_count)
        vy = oracle.query(v)
        vf = features(v)
        if method == "beta_space":
            x = points(seed+220_003,count)
            y = oracle.query(x)
        elif method == "beta_adaptive":
            pilot_count = max(3,count//2)
            pilot_x = points(seed+330_007,pilot_count)
            pilot_y = oracle.query(pilot_x)
            pilot_model,_ = fit_portfolio(features(pilot_x),pilot_y,vf,vy)
            inferred = np.flatnonzero(np.abs(pilot_model)>1e-3).tolist() or None
            pool = points(seed+440_009,192)
            augment = pool[d_optimal_order(pool,inferred)[:count-pilot_count]]
            x = np.concatenate([pilot_x,augment])
            y = np.concatenate([pilot_y,oracle.query(augment)])
        else:
            pool = points(seed+440_009,192)
            x = pool[d_optimal_order(pool,support)[:count]]
            y = oracle.query(x)
        model,metadata = fit_guarded(features(x),y,vf,vy,support)
        predictions = model_features @ model
        allowed = np.flatnonzero((np.mean(predictions,axis=1)>=0.4) & (np.sum(predictions>=0,axis=1)>=12) & (costs<=1.2))
        if len(allowed):
            chosen = int(allowed[np.argmin(costs[allowed])])
            verification = oracle.query(full[chosen])
    elapsed = time.perf_counter()-started
    accepted = bool(chosen>=0 and costs[chosen]<=1.2 and qualifies(verification))
    independent = audit(seed,regime)
    prediction = independent["prediction_features"] @ model
    truth = independent["prediction_truth"]
    error = float(np.sqrt(np.mean((prediction-truth)**2))/max(np.std(truth),0.2))
    row = {"task_id":f"robust-{seed}","seed":seed,"regime":regime,"method":method,"budget":budget,
           "mission":"robust_operation","oracle_calls":oracle.calls,"observed_seconds":elapsed,
           "accepted":accepted,"design_accepted":accepted,"prediction_nrmse":error,"prediction_accepted":error<=0.01,
           "actual_verified_contexts":len(verification),"verified_mean":float(np.mean(verification)) if len(verification) else None,
           "verified_nonnegative_count":int(np.sum(verification>=0)),"chosen_plan":chosen,
           "chosen_plan_cost":float(costs[chosen]) if chosen>=0 else None,
           "menu_has_feasible_plan":independent["menu_has_feasible_plan"],"qualifying_plan_count":independent["qualifying_plan_count"],
           "audit_best_cost":independent["best_cost"],"research_audit_queries":8576,**metadata}
    example = {"task_id":row["task_id"],"method":method,"budget":budget,"coefficients":model.tolist(),
               "chosen_controls":controls[chosen].tolist() if chosen>=0 else None,
               "actual_context_inputs":full[chosen].tolist() if chosen>=0 else [],
               "actual_verified_responses":verification.tolist(),"direct_search_trace":traces,"acceptance":row}
    return row,example


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    groups=[]
    for regime in ["all","compatible","partial_shift","novel_family"]:
        for method in METHODS:
            for budget in BUDGETS:
                chosen=[r for r in rows if r["method"]==method and r["budget"]==budget and (regime=="all" or r["regime"]==regime)]
                if chosen:
                    groups.append({"regime":regime,"method":method,"budget":budget,"n":len(chosen),
                        "accepted":sum(r["accepted"] for r in chosen),"prediction_accepted":sum(r["prediction_accepted"] for r in chosen),
                        "mean_oracle_calls":float(np.mean([r["oracle_calls"] for r in chosen])),
                        "mean_observed_seconds":float(np.mean([r["observed_seconds"] for r in chosen]))})
    paired=[]
    for budget in BUDGETS:
        for regime in ["all","compatible","partial_shift","novel_family"]:
            ids=sorted({r["task_id"] for r in rows if r["budget"]==budget and (regime=="all" or r["regime"]==regime)})
            wins=losses=0
            for task in ids:
                group=[r for r in rows if r["task_id"]==task and r["budget"]==budget]
                skill=next(r for r in group if r["method"]=="v2")["accepted"]
                best=any(r["accepted"] for r in group if r["method"].startswith("beta_"))
                wins+=int(skill and not best)
                losses+=int(best and not skill)
            paired.append({"budget":budget,"regime":regime,"n":len(ids),"v2_wins":wins,"v2_losses":losses,
                           "comparison":"hindsight best of all four Beta policies, deliberately favorable to Beta"})
    return {"groups":groups,"paired_best_beta":paired,"rows":len(rows),
            "unique_research_audit_queries":len({r["task_id"] for r in rows})*8576,
            "cash_revenue_observed":0,"full_original_study_preserved":True}


def execute(split: str) -> None:
    if split=="confirmation":
        frozen=json.loads((OUT/"FREEZE.json").read_text())
        if frozen["hashes"]!=hashes():
            raise RuntimeError("Supplement changed after confirmation freeze")
    regimes=["compatible"]*(6 if split=="development" else 24)+["partial_shift"]*(3 if split=="development" else 12)+["novel_family"]*(3 if split=="development" else 12)
    base=1310000 if split=="development" else 1910000
    artifacts={name:json.loads((TECHNICAL/"artifacts"/file).read_text()) for name,file in [("v1","v1.json"),("v2","v2.json"),("wrong_prior","wrong-prior.json")]}
    rows=[]
    examples=[]
    for index,regime in enumerate(regimes):
        seed=base+107*index
        for budget in BUDGETS:
            for method in METHODS:
                row,example=run(seed,regime,budget,method,artifacts)
                row["split"]=split
                rows.append(row)
                if index in [0,1] and method in ["v2","beta_adaptive","beta_direct"]:
                    examples.append(example)
        write_json(OUT/f"{split}_rows.json",rows)
        print(json.dumps({"robust_split":split,"completed_tasks":index+1,"total_tasks":len(regimes)}),flush=True)
    write_json(OUT/f"{split}_summary.json",summary(rows))
    write_json(OUT/f"{split}_example_deliverables.json",examples)
    with (OUT/f"{split}_rows.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    if split=="confirmation":
        write_json(OUT/"CONFIRMATION_COMPLETE.json",{"completed_utc":datetime.now(timezone.utc).isoformat(),"hashes":hashes(),"rows_sha256":hashlib.sha256((OUT/"confirmation_rows.json").read_bytes()).hexdigest(),"row_count":len(rows)})


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["predeclare","development","freeze","confirmation"])
    args=parser.parse_args()
    if args.action in ["predeclare","freeze"]:
        payload={"frozen_utc":datetime.now(timezone.utc).isoformat(),"hashes":hashes(),"no_supplement_confirmation_access":True,
                 "original_policy_unchanged":True}
        if args.action=="freeze":
            payload["development_sha256"]=hashlib.sha256((OUT/"development_rows.json").read_bytes()).hexdigest()
        write_json(OUT/("PREDECLARED.json" if args.action=="predeclare" else"FREEZE.json"),payload)
    else:
        execute(args.action)


if __name__=="__main__":
    main()
