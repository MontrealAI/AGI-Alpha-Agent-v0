# SPDX-License-Identifier: Apache-2.0
"""Final prospectively frozen stronger-Beta secondary fresh confirmation."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

EVIDENCE = Path(__file__).resolve().parent
BASE = EVIDENCE.parents[1]
OUTPUT = EVIDENCE / "beta144_confirmation"
sys.path.insert(0, str(BASE / "src"))
from scheduling import STRATA, incumbent, make_instance, risk_score, scenario_factors, solve, verify


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n")


def main() -> None:
    config_path = BASE / "config/numerical_beta144_confirmation.json"
    config = json.loads(config_path.read_text())
    policy_path = EVIDENCE / "policy_v2.json"
    policy = json.loads(policy_path.read_text())
    freeze = {"config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
              "policy_file_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest(),
              "policy_content_sha256": policy["content_sha256"],
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scheduler_sha256": hashlib.sha256((BASE / "src/scheduling.py").read_bytes()).hexdigest(),
              "confirmation_used_for_policy_selection": False, "config": config}
    write(OUTPUT / "freeze.json", freeze)
    all_rows = []
    for split in ("development", "confirmation"):
        for index, seed in enumerate(config[f"{split}_seeds"]):
            case = make_instance(seed, STRATA[index % 4])
            public = {key: value for key, value in case.items() if key != "duration_sigma_true"}
            reference_schedule = incumbent(case)
            reference = verify(case, reference_schedule)
            fresh = scenario_factors(case, seed + 900_000, 64, truth=True)
            reference_risk = risk_score(case, reference_schedule, fresh)
            detail = {"instance": case, "reference_schedule": reference_schedule,
                      "reference_verification": reference, "reference_risk": reference_risk, "results": {}}
            for offering in config["offerings"]:
                for mode, budget in config["modes"].items():
                    model = policy if mode == "learned48" else None
                    strategy = "composed" if model is not None else "beta"
                    result = solve(public, model, strategy, offering, budget)
                    check = verify(case, result["schedule"])
                    risk = risk_score(case, result["schedule"], fresh)
                    objective = check["objective"] if offering == "nominal" else risk["objective"]
                    baseline = reference["objective"] if offering == "nominal" else reference_risk["objective"]
                    accepted = check["valid"] and objective <= config[f"{offering}_acceptance_ratio"] * baseline
                    row = {"case_id": case["case_id"], "stratum": case["stratum"], "split": split,
                           "offering": offering, "mode": mode, "objective": objective,
                           "reference_objective": baseline, "objective_ratio": objective / baseline,
                           "quality": 1 - objective / baseline, "valid": check["valid"], "accepted": accepted,
                           "solve_seconds": result["solve_seconds"], "evals": result["evals"],
                           "scenario_evals": result["scenario_evals"], "jobs": case["n"]}
                    all_rows.append(row)
                    detail["results"][f"{offering}/{mode}"] = {**result, "independent_verification": check,
                                                               "fresh_scenario_score": risk, "accepted": accepted}
            write(OUTPUT / split / f"{case['case_id']}.json", detail)
            print(split, index + 1, case["case_id"], flush=True)
        write(OUTPUT / f"{split}_records.json", [row for row in all_rows if row["split"] == split])
    calibration = {"status": "secondary fresh confirmation; primary study unchanged",
                   "freeze_sha256": hashlib.sha256((OUTPUT / "freeze.json").read_bytes()).hexdigest(),
                   "technical_acceptance_not_customer": True, "offerings": {}, "learning": "No additional learning; frozen policy reused.",
                   "mode_mapping": {"beta48": "primary beta48", "learned48": "primary v2 nominal / composed robust", "beta144": "same Beta algorithm with144 candidates"}}
    for offering in config["offerings"]:
        calibration["offerings"][offering] = {}
        for mode in config["modes"]:
            dev = [r for r in all_rows if r["offering"] == offering and r["mode"] == mode and r["split"] == "development"]
            conf = [r for r in all_rows if r["offering"] == offering and r["mode"] == mode and r["split"] == "confirmation"]
            calibration["offerings"][offering][mode] = {
                "development_records": dev, "confirmation_records": conf, "development_n": len(dev),
                "development_successes": sum(r["accepted"] for r in dev), "confirmation_n": len(conf),
                "confirmation_successes": sum(r["accepted"] for r in conf),
                "development_mean_solve_seconds": float(np.mean([r["solve_seconds"] for r in dev])),
                "confirmation_mean_solve_seconds": float(np.mean([r["solve_seconds"] for r in conf])),
                "development_mean_cost_units": float(np.mean([r["evals"] + r["scenario_evals"] / 24 for r in dev])),
            }
    write(OUTPUT / "calibration.json", calibration)
    summaries = []
    for offering in config["offerings"]:
        for mode in config["modes"]:
            group = calibration["offerings"][offering]
            current = group[mode]["confirmation_records"]
            beta = {r["case_id"]: r for r in group["beta48"]["confirmation_records"]}
            strong = {r["case_id"]: r for r in group["beta144"]["confirmation_records"]}
            gain = np.asarray([1 - r["objective"] / beta[r["case_id"]]["objective"] for r in current])
            gain_strong = np.asarray([1 - r["objective"] / strong[r["case_id"]]["objective"] for r in current])
            rng = np.random.default_rng(9381)
            indices = rng.integers(len(gain), size=(4000, len(gain)))
            summaries.append({"offering": offering, "mode": mode, "n": len(current),
                              "accepted": sum(r["accepted"] for r in current), "mean_gain_over_beta48": float(gain.mean()),
                              "mean_gain_over_beta144": float(gain_strong.mean()),
                              "gain_over_beta144_ci95": np.quantile(gain_strong[indices].mean(axis=1), [0.025, 0.975]).tolist(),
                              "mean_solve_seconds": float(np.mean([r["solve_seconds"] for r in current])),
                              "quality_grid_successes": {str(t): sum(r["valid"] and r["quality"] >= t for r in current) for t in config["quality_grid"]}})
    write(OUTPUT / "summary.json", {"rows": summaries,
                                     "scope": "12 balanced synthetic fresh cases; secondary small-sample robustness, not a replacement for80-case primary. Intervals omit generator uncertainty and are not multiplicity-adjusted.",
                                     "total_schedule_evaluations": sum(r["evals"] for r in all_rows),
                                     "total_scenario_evaluations": sum(r["scenario_evals"] for r in all_rows),
                                     "total_measured_solver_seconds": sum(r["solve_seconds"] for r in all_rows)})


if __name__ == "__main__":
    main()
