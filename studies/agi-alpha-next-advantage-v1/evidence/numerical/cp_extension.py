# SPDX-License-Identifier: Apache-2.0
"""Reproduce the separately declared equal-budget CP-SAT sensitivity."""

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

OUTPUT = Path(__file__).resolve().parent
BASE = OUTPUT.parents[1]
sys.path.insert(0, str(BASE / "src"))
from scheduling import cp_sat


def main() -> None:
    path = BASE / "config/numerical_cp_extension.json"
    config = json.loads(path.read_text())
    records = []
    for case_file in sorted((OUTPUT / "confirmation").glob("*.json")):
        detail = json.loads(case_file.read_text())
        case = detail["instance"]
        if case["seed"] not in config["case_seeds"]:
            continue
        for mode in config["warm_start_modes"]:
            warm = detail["results"][f"nominal/{mode}"]
            result = cp_sat(case, warm["schedule"], config["deterministic_time_budget"])
            records.append({"case_id": case["case_id"], "mode": mode, "warm_objective": warm["independent_verification"]["objective"], **result})
            print(case["case_id"], mode, result["status"], result["verification"]["objective"], flush=True)
    pairs = {}
    for row in records:
        pairs.setdefault(row["case_id"], {})[row["mode"]] = row
    paired = []
    for case_id, modes in pairs.items():
        a, b = modes["beta"], modes["composed"]
        a_score, b_score = a["verification"]["objective"], b["verification"]["objective"]
        paired.append({"case_id": case_id, "v2_vs_beta_cp_gain": 1 - b_score / a_score,
                       "beta_cp_improvement": 1 - a_score / a["warm_objective"],
                       "v2_cp_improvement": 1 - b_score / b["warm_objective"]})
    result = {"config": config, "config_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "records": records, "paired": paired,
              "mean_v2_vs_beta_cp_gain": float(np.mean([r["v2_vs_beta_cp_gain"] for r in paired])),
              "mean_beta_cp_improvement": float(np.mean([r["beta_cp_improvement"] for r in paired])),
              "mean_v2_cp_improvement": float(np.mean([r["v2_cp_improvement"] for r in paired])),
              "scope": "Higher-resource solver sensitivity on twelve existing cases; neither an optimum nor a live-frontier comparison."}
    (OUTPUT / "cp_extension_results.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")


if __name__ == "__main__":
    main()
