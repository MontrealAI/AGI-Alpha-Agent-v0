# SPDX-License-Identifier: Apache-2.0
"""Apply the prospectively frozen secondary grid to every saved comparison."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def write(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    output = Path(__file__).resolve().parent
    base = output.parents[1]
    config_path = base / "config/numerical_quality_frontier.json"
    config = json.loads(config_path.read_text())
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    splits = {s: json.loads((output / f"{s}_records.json").read_text()) for s in config["splits"]}
    rows = []
    for split, records in splits.items():
        for offering in config["offerings"]:
            for mode in config["modes"]:
                for target in config["grid_improvement_over_edd"]:
                    for stratum in ("all", "producer", "recipient", "scale", "shift"):
                        sample = [r for r in records if r["offering"] == offering and r["mode"] == mode
                                  and (stratum == "all" or r["stratum"] == stratum)]
                        hits = sum(r["valid"] and r["quality"] >= target for r in sample)
                        rows.append({"split": split, "offering": offering, "mode": mode, "stratum": stratum,
                                     "improvement_target": target, "n": len(sample), "successes": hits,
                                     "acceptance_rate": hits / len(sample)})
    write(output / "quality_frontier.json", {"status": "secondary sensitivity; primary acceptance unchanged",
                                             "grid_sha256": config_sha, "configuration": config, "rows": rows})
    with (output / "quality_frontier.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    calibration_path = output / "economic_calibration.json"
    original = output / "economic_calibration_primary.json"
    if not original.exists():
        original.write_bytes(calibration_path.read_bytes())
    calibration = json.loads(original.read_text())
    for offering, modes in calibration["offerings"].items():
        for mode, entry in modes.items():
            entry["development_records"] = [dict(r, objective_ratio=r["objective"] / r["reference_objective"])
                                            for r in splits["development"] if r["offering"] == offering and r["mode"] == mode]
            entry["confirmation_records"] = [dict(r, objective_ratio=r["objective"] / r["reference_objective"])
                                             for r in splits["confirmation"] if r["offering"] == offering and r["mode"] == mode]
    calibration["postprocessing"] = {"script": "quality_frontier_analysis.py", "grid_sha256": config_sha,
                                      "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                      "primary_source_output": "economic_calibration_primary.json",
                                      "primary_acceptance_unchanged": True}
    write(calibration_path, calibration)
    interrupted = output.parent / "numerical_interrupted_source"
    attempts = []
    for directory, status in ((interrupted, "interrupted; not qualified confirmation"), (output, "completed final source")):
        schedule_evals = 0
        scenario_evals = 0
        seconds = 0.0
        cases = {}
        for split in ("development", "confirmation"):
            paths = sorted((directory / split).glob("*.json"))
            cases[split] = len(paths)
            for path in paths:
                data = json.loads(path.read_text())
                for item in data["results"].values():
                    schedule_evals += item["evals"]
                    scenario_evals += item["scenario_evals"]
                    seconds += item["solve_seconds"]
        for version in ("v1", "v2"):
            policy = json.loads((directory / f"policy_{version}.json").read_text())
            schedule_evals += policy["schedule_evaluations"]
            seconds += policy["seconds"]
        productive = directory / "productive_deliveries.json"
        if productive.exists():
            for case in json.loads(productive.read_text()):
                for item in case["deliveries"].values():
                    schedule_evals += item["evals"]
                    scenario_evals += item["scenario_evals"]
                    seconds += item["solve_seconds"]
        attempts.append({"directory": directory.name, "status": status, "complete_saved_cases": cases,
                         "persisted_schedule_evaluations": schedule_evals,
                         "persisted_scenario_objective_evaluations": scenario_evals,
                         "summed_measured_solver_and_training_seconds": seconds,
                         "excluded": "I/O, process startup, acceptance verification, CP-SAT challenge, and any interrupted unsaved partial case; not total wall time."})
    write(output / "research_execution_overhead.json", {
        "classification": "Executed research counterfactual workload, distinct from any one simulated enterprise's disjoint A/B/C ledger.",
        "attempts": attempts, "interrupted_work_preserved": True, "model_calls": 0,
        "note": "Counts are lower bounds on actual whole-study computation; no unobserved costs set to zero. Researcher labor and opportunity cost are not measured."})
    contrasts = []
    comparisons = [
        ("nominal", "beta", "v1", "productive-learning"),
        ("nominal", "v1", "v2", "additional-Gym"),
        ("nominal", "shuffled", "v2", "learned-coordinate-control"),
        ("robust", "beta", "composed", "shared-composed-specialist"),
        ("robust", "v1", "composed", "additional-Gym-with-common-risk-evaluator"),
        ("robust", "v2", "composed", "scenario-composition-additional-compute"),
    ]
    for offering, baseline, candidate, label in comparisons:
        a = {r["case_id"]: r for r in splits["confirmation"] if r["offering"] == offering and r["mode"] == baseline}
        b = {r["case_id"]: r for r in splits["confirmation"] if r["offering"] == offering and r["mode"] == candidate}
        gains = np.asarray([1 - b[key]["objective"] / value["objective"] for key, value in a.items()])
        samples = np.random.default_rng(831).integers(len(gains), size=(4000, len(gains)))
        contrasts.append({"offering": offering, "comparison": label, "baseline": baseline, "candidate": candidate,
                          "mean_paired_gain": float(gains.mean()), "ci95_paired_percentile": np.quantile(gains[samples].mean(1), [0.025, 0.975]).tolist(),
                          "n": len(gains), "matched_selection_budget": label != "scenario-composition-additional-compute"})
    write(output / "causal_contrasts.json", {"status": "Analysis of predefined modes on frozen confirmation; confidence intervals are not multiplicity-adjusted and exclude uncertainty about task-generator assumptions.", "rows": contrasts})


if __name__ == "__main__":
    main()
