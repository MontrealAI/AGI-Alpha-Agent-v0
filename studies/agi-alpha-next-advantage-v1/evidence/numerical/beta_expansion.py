# SPDX-License-Identifier: Apache-2.0
"""Threefold generic-search sensitivity, retaining identical mission thresholds."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

OUTPUT = Path(__file__).resolve().parent
BASE = OUTPUT.parents[1]
sys.path.insert(0, str(BASE / "src"))
from scheduling import risk_score, scenario_factors, solve, verify


def main() -> None:
    path = BASE / "config/numerical_beta_expansion.json"
    config = json.loads(path.read_text())
    rows = []
    for case_file in sorted((OUTPUT / "confirmation").glob("*.json")):
        detail = json.loads(case_file.read_text())
        case = detail["instance"]
        if case["seed"] not in config["case_seeds"]:
            continue
        for offering in config["offerings"]:
            result = solve(case, None, "beta", offering, config["beta_candidates"])
            verification = verify(case, result["schedule"])
            fresh = scenario_factors(case, case["seed"] + 900_000, 64, truth=True)
            risk = risk_score(case, result["schedule"], fresh)
            objective = verification["objective"] if offering == "nominal" else risk["objective"]
            reference = detail["incumbent_verification"]["objective"] if offering == "nominal" else detail["incumbent_robust"]["objective"]
            baseline = detail["results"][f"{offering}/beta"]
            learned = detail["results"][f"{offering}/composed"]
            key = "independent_verification" if offering == "nominal" else "fresh_scenario_score"
            rows.append({"case_id": case["case_id"], "offering": offering, "stratum": case["stratum"],
                         "objective": objective, "accepted": verification["valid"] and objective <= config["same_acceptance"][offering] * reference,
                         "quality": 1 - objective / reference, "beta48_objective": baseline[key]["objective"],
                         "learned48_objective": learned[key]["objective"],
                         "beta144_gain_over_beta48": 1 - objective / baseline[key]["objective"],
                         "learned48_gain_over_beta144": 1 - learned[key]["objective"] / objective,
                         "verification": verification, "fresh_scenario_score": risk, **result})
            print(case["case_id"], offering, objective, flush=True)
    summary = {}
    for offering in config["offerings"]:
        sample = [r for r in rows if r["offering"] == offering]
        summary[offering] = {"n": len(sample), "beta144_accepted": sum(r["accepted"] for r in sample),
                             "mean_beta144_gain_over_beta48": float(np.mean([r["beta144_gain_over_beta48"] for r in sample])),
                             "mean_learned48_gain_over_beta144": float(np.mean([r["learned48_gain_over_beta144"] for r in sample])),
                             "mean_beta144_seconds": float(np.mean([r["solve_seconds"] for r in sample])),
                             "beta144_beats_learned48": sum(r["objective"] < r["learned48_objective"] for r in sample)}
    data = {"config": config, "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "records": rows, "summary": summary}
    (OUTPUT / "beta_expansion_results.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
