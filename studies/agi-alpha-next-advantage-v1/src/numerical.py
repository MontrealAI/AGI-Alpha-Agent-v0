# SPDX-License-Identifier: Apache-2.0
"""Reproduce the prespecified numerical-learning and fresh-transfer experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import time
from pathlib import Path
from typing import Any

import numpy as np

from scheduling import RULES, STRATA, cp_sat, digest, dispatch, incumbent, make_instance, risk_score, scenario_factors, solve, verify

BASE = Path(__file__).resolve().parents[1]
MODES = ("beta", "v1", "v2", "composed", "beta_plus", "shuffled")


def write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


def protocol() -> dict[str, Any]:
    return {
        "version": "numerical-protocol-1.0", "source_base": "80b345828f34fd8a6e592977dd17ef37141305f4",
        "provenance": "Researcher-authored problem generator, solver family and CEM update; actual numerical learning; no autonomous discovery or frontier call.",
        "paid_development_seeds": list(range(11000, 11008)),
        "gym_seeds": list(range(21000, 21024)), "development_seeds": list(range(31000, 31024)),
        "confirmation_seeds": list(range(51000, 51080)),
        "stratum_order": list(STRATA), "candidate_budget_per_solve": 48,
        "v1": {"generations": 4, "population": 16, "elite": 4, "seed": 701},
        "v2": {"generations": 6, "population": 20, "elite": 5, "seed": 702},
        "nominal_objective": "(sum_j weight_j max(completion_j-due_j,0) + 0.1 sum_j weight_j makespan) / (sum_j weight_j mean_processing_time)",
        "robust_objective": "0.5 mean scenario objective + 0.5 CVaR90 scenario objective",
        "acceptance": {"nominal": "All hard constraints and objective <= 0.97 times independently evaluated EDD incumbent.",
                       "robust": "All hard constraints and fresh 64-scenario objective <= 0.95 times incumbent on identical scenarios."},
        "selection_scenarios": 24, "acceptance_scenarios": 64,
        "v2_selection": "Lowest training loss; development describes value, never confirmation. Rejected candidates are retained.",
        "freshness": "Confirmation starts only after policy_freeze.json exists. Learning sees paid/Gym cases only; code does not pass confirmation to learning.",
        "cp_sat": {"cases": "first 3 confirmation cases in each stratum (12 total)", "warm_starts": ["beta", "composed"],
                   "deterministic_time_per_call": 0.08, "workers": 1},
        "strong_beta": "48-candidate portfolio with expanded ATCS parameter grid; no retained learned parameters.",
        "limits": "Finite synthetic machine-scheduling proxy; no globally optimal frontier, buyer demand, human comparison or ASI claim. Main computational baseline is not a current frontier-model ceiling.",
        "technical_acceptance_not_customer": True,
        "interrupted_source": "Initial source stopped after24 development/six uninspected confirmation cases for origin-deliverable and latent-parameter isolation repair; evidence preserved in numerical_interrupted_source. No outcomes used for policy tuning. Fresh seeds51000-51079.",
        "mode_meanings": {"v1": "v1 dispatch; robust uses generic risk evaluator also available to Beta",
                          "v2": "v2 dispatch; robust is explicit removal of scenario-ranking component",
                          "composed": "v2 dispatch plus same generic scenario-ranking component available to Beta",
                          "beta": "No retained dispatch policy; both offerings have competent algorithmic portfolio and robust evaluator",
                          "beta_plus": "No retained policy; expanded classical parameter grid at same candidate budget",
                          "shuffled": "Reverse learned weight coordinates; component-removal falsification, not a competent enterprise"},
    }


def learn(cases: list[dict[str, Any]], initial: np.ndarray, config: dict[str, Any], name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    start = time.perf_counter()
    rng = np.random.default_rng(config["seed"])
    reference = np.asarray([verify(case, incumbent(case))["objective"] for case in cases])
    mean = initial.copy()
    std = np.ones(7) * 0.8
    best_loss = math.inf
    best_theta = initial.copy()
    log = []
    for generation in range(config["generations"]):
        population = np.clip(rng.normal(mean, std, (config["population"], 7)), -3, 5)
        population[0] = best_theta
        if generation == 0:
            population[1: min(9, len(population))] = RULES[: min(8, len(population) - 1)]
        losses = []
        for idx, theta in enumerate(population):
            scores = np.asarray([verify(case, dispatch(case, theta))["objective"] for case in cases])
            ratios = scores / reference
            loss = float(ratios.mean() + 0.05 * ratios.std())
            losses.append(loss)
            log.append({"version": name, "generation": generation, "candidate": idx, "theta": theta.tolist(),
                        "loss": loss, "case_ratios": ratios.tolist(), "schedule_evaluations": len(cases)})
            if loss < best_loss:
                best_loss, best_theta = loss, theta.copy()
        elites = population[np.argsort(losses)[:config["elite"]]]
        mean = 0.3 * mean + 0.7 * elites.mean(axis=0)
        std = np.maximum(0.12, 0.3 * std + 0.7 * elites.std(axis=0))
    artifact = {"kind": "executable-dispatch-parameter-policy", "version": name, "theta": best_theta.tolist(),
                "training_loss": best_loss, "training_cases": [case["case_id"] for case in cases],
                "schedule_evaluations": len(log) * len(cases), "seconds": time.perf_counter() - start,
                "update": "cross-entropy search over seven dispatch weights; no proprietary model weights changed",
                "provenance": "researcher-designed parameterized scheduler; parameters learned by executed CEM",
                "permissions": "Apache-2.0 synthetic artifacts only", "scope": "finite unrelated parallel-machine scheduling",
                "requirements": {"python": ">=3.11,<3.14", "numpy": ">=2.0"},
                "failure_limits": "No optimality guarantee; unfamiliar constraints require a fresh verifier and evaluation."}
    artifact["content_sha256"] = digest({k: v for k, v in artifact.items() if k not in ("seconds", "content_sha256")})
    return artifact, log


def evaluate_split(cases: list[dict[str, Any]], policies: dict[str, dict[str, Any]], output: Path, split: str, budget: int) -> list[dict[str, Any]]:
    records = []
    case_output = output / split
    case_output.mkdir(exist_ok=True)
    for i, case in enumerate(cases):
        baseline = incumbent(case)
        baseline_nominal = verify(case, baseline)
        fresh = scenario_factors(case, case["seed"] + 900_000, 64, truth=True)
        baseline_robust = risk_score(case, baseline, fresh)
        detail = {"instance": case, "incumbent": baseline, "incumbent_verification": baseline_nominal,
                  "incumbent_robust": baseline_robust, "results": {}}
        for offering in ("nominal", "robust"):
            for mode in MODES:
                policy = None
                if mode == "v1":
                    policy = policies["v1"]
                elif mode in ("v2", "composed"):
                    policy = policies["v2"]
                elif mode == "shuffled":
                    policy = dict(policies["v2"], theta=list(reversed(policies["v2"]["theta"])))
                public_case = {key: value for key, value in case.items() if key != "duration_sigma_true"}
                result = solve(public_case, policy, mode, offering, budget)
                checked = verify(case, result["schedule"])
                risk = risk_score(case, result["schedule"], fresh)
                score = checked["objective"] if offering == "nominal" else risk["objective"]
                reference = baseline_nominal["objective"] if offering == "nominal" else baseline_robust["objective"]
                threshold = 0.97 if offering == "nominal" else 0.95
                accepted = checked["valid"] and score <= threshold * reference
                row = {"split": split, "case_id": case["case_id"], "stratum": case["stratum"], "offering": offering,
                       "mode": mode, "accepted": accepted, "quality": float(1 - score / reference), "objective": score,
                       "reference_objective": reference, "valid": checked["valid"], "solve_seconds": result["solve_seconds"],
                       "evals": result["evals"], "scenario_evals": result["scenario_evals"], "jobs": case["n"]}
                records.append(row)
                detail["results"][f"{offering}/{mode}"] = {**result, "independent_verification": checked, "fresh_scenario_score": risk, "accepted": accepted}
        write(case_output / f"{case['case_id']}.json", detail)
        print(f"{split} {i + 1}/{len(cases)} {case['case_id']}", flush=True)
    write(output / f"{split}_records.json", records)
    return records


def summarize(records: list[dict[str, Any]], split: str) -> dict[str, Any]:
    answer = {}
    for offering in ("nominal", "robust"):
        answer[offering] = {}
        for mode in MODES:
            subset = [r for r in records if r["offering"] == offering and r["mode"] == mode]
            b = {r["case_id"]: r for r in records if r["offering"] == offering and r["mode"] == "beta"}
            gains = np.asarray([(b[r["case_id"]]["objective"] - r["objective"]) / b[r["case_id"]]["objective"] for r in subset])
            rng = np.random.default_rng(1002)
            boot = gains[rng.integers(len(gains), size=(2000, len(gains)))].mean(axis=1)
            answer[offering][mode] = {"n": len(subset), "accepted": sum(r["accepted"] for r in subset),
                                     "acceptance_rate": sum(r["accepted"] for r in subset) / len(subset),
                                     "mean_quality": float(np.mean([r["quality"] for r in subset])),
                                     "mean_paired_gain_vs_beta": float(gains.mean()),
                                     "paired_gain_95_percentile_bootstrap": np.quantile(boot, [0.025, 0.975]).tolist(),
                                     "mean_solve_seconds": float(np.mean([r["solve_seconds"] for r in subset])),
                                     "mean_evals": float(np.mean([r["evals"] for r in subset])),
                                     "strata": {s: {"n": sum(r["stratum"] == s for r in subset),
                                                    "accepted": sum(r["accepted"] for r in subset if r["stratum"] == s),
                                                    "mean_gain_vs_beta": float(np.mean([g for g, r in zip(gains, subset) if r["stratum"] == s]))}
                                                for s in STRATA}, "split": split}
    return answer


def run(output: Path, use_cp_sat: bool = True) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    p = protocol()
    write(BASE / "config/numerical_protocol.json", p)
    write(output / "design_protocol.json", p)
    paid = [make_instance(seed, "producer") for seed in p["paid_development_seeds"]]
    gym = [make_instance(seed, STRATA[i % 3]) for i, seed in enumerate(p["gym_seeds"])]
    write(output / "productive_experience_cases.json", paid)
    write(output / "gym_cases.json", gym)
    v1, log1 = learn(paid, RULES[0], p["v1"], "v1")
    v2, log2 = learn(gym, np.asarray(v1["theta"]), p["v2"], "v2")
    write(output / "policy_v1.json", v1)
    write(output / "policy_v2.json", v2)
    write(output / "all_learning_candidates.json", log1 + log2)
    policies = {"v1": json.loads((output / "policy_v1.json").read_text()), "v2": json.loads((output / "policy_v2.json").read_text())}
    productive_deliveries = []
    for case in paid:
        reference = verify(case, incumbent(case))["objective"]
        deliveries = {}
        public_case = {key: value for key, value in case.items() if key != "duration_sigma_true"}
        for mode, policy in (("beta", None), ("v1", policies["v1"])):
            result = solve(public_case, policy, mode, "nominal", p["candidate_budget_per_solve"])
            checked = verify(case, result["schedule"])
            deliveries[mode] = {**result, "independent_verification": checked,
                                "accepted": checked["valid"] and checked["objective"] <= 0.97 * reference}
        productive_deliveries.append({"case_id": case["case_id"], "deliveries": deliveries,
                                     "cash_status": "simulated productive job; no earned revenue"})
    write(output / "productive_deliveries.json", productive_deliveries)
    development = [make_instance(seed, STRATA[i % 4]) for i, seed in enumerate(p["development_seeds"])]
    dev = evaluate_split(development, policies, output, "development", p["candidate_budget_per_solve"])
    dev_summary = summarize(dev, "development")
    freeze = {"protocol_sha256": digest(p), "policies": {k: v["content_sha256"] for k, v in policies.items()},
              "source_files": {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in (Path(__file__), Path(__file__).with_name("scheduling.py"))},
              "development_summary": dev_summary, "confirmation_used_for_selection": False}
    write(output / "policy_freeze.json", freeze)
    confirmation = [make_instance(seed, STRATA[i % 4]) for i, seed in enumerate(p["confirmation_seeds"])]
    conf = evaluate_split(confirmation, policies, output, "confirmation", p["candidate_budget_per_solve"])
    conf_summary = summarize(conf, "confirmation")
    cp_results = []
    if use_cp_sat:
        for case in confirmation[:12]:
            detail = json.loads((output / "confirmation" / f"{case['case_id']}.json").read_text())
            for mode in ("beta", "composed"):
                result = cp_sat(case, detail["results"][f"nominal/{mode}"]["schedule"], p["cp_sat"]["deterministic_time_per_call"])
                cp_results.append({"case_id": case["case_id"], "stratum": case["stratum"], "mode": mode, **result})
                print(f"CP-SAT {case['case_id']} {mode} {result['status']}", flush=True)
    write(output / "cp_sat_comparator.json", cp_results)
    calibration: dict[str, Any] = {"schema_version": "1.0", "technical_acceptance_not_customer": True, "offerings": {},
                                   "learning": {"v1": {"evals": v1["schedule_evaluations"], "seconds": v1["seconds"]},
                                                "v2": {"evals": v2["schedule_evaluations"], "seconds": v2["seconds"]},
                                                "uncertainty": {"observations_per_machine": 60, "fit": "sample standard deviation of log durations", "provenance": "researcher-authored fit/replay; no paid observations"}},
                                   "source_scope": "Executed synthetic scheduling; no frontier-model observation, live identity or market demand."}
    for offering in ("nominal", "robust"):
        calibration["offerings"][offering] = {}
        for mode in MODES:
            d = [r for r in dev if r["offering"] == offering and r["mode"] == mode]
            c = [r for r in conf if r["offering"] == offering and r["mode"] == mode]
            calibration["offerings"][offering][mode] = {
                "development_successes": sum(r["accepted"] for r in d), "development_n": len(d),
                "confirmation_successes": sum(r["accepted"] for r in c), "confirmation_n": len(c),
                "development_mean_cost_units": float(np.mean([r["evals"] + r["scenario_evals"] / 24 for r in d])),
                "development_mean_solve_seconds": float(np.mean([r["solve_seconds"] for r in d])),
                "confirmation_records": c,
            }
    write(output / "economic_calibration.json", calibration)
    lineage = {
        "identities": {"producer": "producer.agent.agi.eth (synthetic label; no live ENS)", "recipient": "recipient.agent.agi.eth (synthetic label; no live ENS)"},
        "productive_work": {"case_id": paid[0]["case_id"], "all_origin_cases": [case["case_id"] for case in paid],
                            "path": "productive_experience_cases.json", "deliverables": "productive_deliveries.json",
                            "cash_status": "eight simulated jobs; no actual revenue", "training_in_paid_delivery": True,
                            "cost_category": "A once; v1 development embedded in productive delivery, not a second R&D bill"},
        "v1": {"path": "policy_v1.json", "sha256": v1["content_sha256"]},
        "gym": {"path": "all_learning_candidates.json", "v2_evals": v2["schedule_evaluations"], "all_candidates_retained": True},
        "v2": {"path": "policy_v2.json", "sha256": v2["content_sha256"]},
        "fresh_recipient": {"case_id": confirmation[1]["case_id"], "path": f"confirmation/{confirmation[1]['case_id']}.json", "loaded_from_serialized_policy": True},
        "composition": {"case_id": confirmation[1]["case_id"], "components": ["v2 dispatch parameters", "estimated-duration scenario replay/risk ranking"], "same_mission_constraints": True},
        "admission_status": "Research artifact only; native protected capsule scope does not authorize arbitrary scheduling execution.",
    }
    write(output / "lineage.json", lineage)
    summary = {"protocol_sha256": digest(p), "freeze_sha256": digest(freeze), "python": platform.python_version(), "numpy": np.__version__,
               "development": dev_summary, "confirmation": conf_summary, "learning": calibration["learning"],
               "cp_sat_cases": len(cp_results) // 2, "claims": {"live_frontier_calls": 0, "live_ens_authentications": 0, "actual_customer_sales": 0,
                   "numerical_learning_executed": True, "autonomous_capability_discovery": False, "proprietary_weight_updates": False}}
    write(output / "summary.json", summary)
    all_records = dev + conf
    with (output / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_records[0]))
        writer.writeheader()
        writer.writerows(all_records)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=BASE / "evidence/numerical")
    parser.add_argument("--skip-cp-sat", action="store_true")
    args = parser.parse_args()
    result = run(args.output, not args.skip_cp_sat)
    print(json.dumps(result["confirmation"], indent=2))
