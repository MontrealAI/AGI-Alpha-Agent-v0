# SPDX-License-Identifier: Apache-2.0
"""All credible-comparator contrasts; explicitly exploratory accounting sensitivity.

This program reads retained outcomes. It does not run, fit, or alter a policy.
The preregistered primary intervals remain those in decision_summary.json.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent


def estimate(values: list[float]) -> dict:
    a = np.asarray(values)
    rng = np.random.default_rng(9001)
    boot = np.mean(a[rng.integers(0, len(a), (2000, len(a)))], axis=1)
    return {"mean": float(np.mean(a)), "paired_seed_block_95": np.quantile(boot, [0.025, 0.975]).tolist()}


def main() -> None:
    path = ROOT / "results/decision-confirmation/decision_observations.csv.gz"
    summary = json.loads((path.parent / "decision_summary.json").read_text())
    with gzip.open(path, "rt") as stream:
        rows = list(csv.DictReader(stream))
    policies = sorted({r["policy"] for r in rows})
    regimes = list(json.loads((ROOT / "decision_protocol.json").read_text())["regimes"])
    seeds = sorted({int(r["seed"]) for r in rows})
    groups = {}
    for row in rows:
        key = (row["regime"], int(row["seed"]), row["policy"])
        groups.setdefault(key, []).append(row)
    means = {(reg, seed, pol, field): np.mean([float(r[field]) for r in group])
             for (reg, seed, pol), group in groups.items()
             for field in ("mission_credits", "accepted", "accounted_cost_seconds", "decision_cpu_seconds")}
    comparisons = []
    for regime in regimes + ["equal_weight_six_regime_average"]:
        rr = regimes if regime == "equal_weight_six_regime_average" else [regime]
        for policy in policies:
            if policy == "constructive_foresight":
                continue
            deltas = [float(np.mean([means[r, s, "constructive_foresight", "mission_credits"]
                                   - means[r, s, policy, "mission_credits"] for r in rr])) for s in seeds]
            comparisons.append({"regime": regime, "comparator": policy,
                                "eligible": policy != "clairvoyant_menu", **estimate(deltas)})
    sensitivity = []
    for regime in regimes:
        for value_per_accepted in (1.0, 0.75, 0.5, 0.25):
            deltas = []
            for s in seeds:
                accepted = means[regime, s, "constructive_foresight", "accepted"] - means[regime, s, "static_expert", "accepted"]
                cost = means[regime, s, "constructive_foresight", "accounted_cost_seconds"] - means[regime, s, "static_expert", "accounted_cost_seconds"]
                deltas.append(float(value_per_accepted * accepted - cost / summary["clock_seconds"]))
            sensitivity.append({"regime": regime, "credit_per_accepted": value_per_accepted, **estimate(deltas)})
    result = {"source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
              "evidence_class": "derived analysis of fixed simulated trajectories",
              "interval_scope": "24 paired seed blocks; model-conditional Monte Carlo uncertainty only",
              "primary": "Use unchanged decision_summary.json for preregistered primary comparisons",
              "comparisons": comparisons,
              "sensitivity_boundary": "Post-confirmation accounting sensitivity: fixed actions/outcomes, changed assumed service-value credit; no policy refitting, new worlds or demand elasticity model. It is not a forecast of market price compression.",
              "sensitivity": sensitivity,
              "late_attempts_all_policy_rows": int(sum(float(r["late_attempts"]) for r in rows))}
    (ROOT / "results/decision_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"contrasts": len(comparisons), "sensitivity_cells": len(sensitivity),
                      "overall": [r for r in comparisons if r["regime"] == "equal_weight_six_regime_average"]}, indent=2))


if __name__ == "__main__":
    main()
