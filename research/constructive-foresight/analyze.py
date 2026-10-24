# SPDX-License-Identifier: Apache-2.0
"""Descriptive and paired analyses of the retained numerical confirmation."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def interval(values: list[float], seed: int = 20261023) -> list[float]:
    rng = np.random.default_rng(seed)
    a = np.asarray(values, dtype=float)
    means = np.mean(a[rng.integers(0, len(a), size=(2000, len(a)))], axis=1)
    return np.quantile(means, [0.025, 0.975]).tolist()


def main() -> None:
    path = ROOT / "results/confirmation/batches.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    frozen = json.loads((ROOT / "results/forecast_freeze.json").read_text())
    names = json.loads((ROOT / "protocol.json").read_text())["matrices_in_order"]
    statistics, paired = [], []
    for name in names:
        for q in (1, 4, 16):
            for method in ("cold_direct", "native_cached", "certified_ready"):
                group = [r for r in rows if (r["matrix"], r["q"], r["method"]) == (name, q, method)]
                result = {"matrix": name, "q": q, "method": method, "n": len(group),
                          "qualified": sum(r["qualified"] for r in group)}
                for key in ("total_seconds", "response_seconds", "factor_seconds", "preflight_seconds",
                            "metadata_seconds", "solve_seconds", "validation_seconds", "rhs_formation_seconds",
                            "cpu_seconds", "overhead_seconds"):
                    result[key] = float(np.median([r[key] for r in group]))
                for key in ("relative_residual_l2", "backward_error_linf", "manufactured_forward_error_l2"):
                    values = [v for r in group for v in r[key] if v is not None]
                    result["max_" + key] = max(values) if values else None
                statistics.append(result)
            if q == 16:
                for baseline in ("cold_direct", "native_cached"):
                    ratios, inverse_ratios, differences = [], [], []
                    for block in range(12):
                        b = next(r for r in rows if (r["matrix"], r["q"], r["block"], r["method"]) == (name, q, block, baseline))
                        c = next(r for r in rows if (r["matrix"], r["q"], r["block"], r["method"]) == (name, q, block, "certified_ready"))
                        ratios.append(b["total_seconds"] / c["total_seconds"])
                        inverse_ratios.append(c["total_seconds"] / b["total_seconds"])
                        differences.append(b["total_seconds"] - c["total_seconds"])
                    paired.append({"matrix": name, "baseline": baseline, "q": q,
                                   "median_ratio_baseline_over_instrument": float(np.median(ratios)),
                                   "median_ratio_instrument_over_baseline": float(np.median(inverse_ratios)),
                                   "mean_seconds_saved": float(np.mean(differences)),
                                   "paired_block_bootstrap_95_seconds_saved": interval(differences)})
    scored = []
    for f in frozen["forecasts"]:
        for r in rows:
            if (r["matrix"], r["q"], r["method"]) != (f["matrix"], f["q"], f["method"]):
                continue
            seconds = r["total_seconds" if f["state"] == "cold" else "response_seconds"]
            y = int(r["qualified"] and seconds <= f["deadline_seconds"])
            scored.append({**f, "block": r["block"], "batch_id": r["id"], "event": y,
                           "actual_elapsed_seconds": seconds, "brier": (f["probability"] - y) ** 2,
                           "base_brier": (frozen["base_probability"] - y) ** 2})
    forecast = {"n_targets_scored": len(scored), "distinct_targets": len(frozen["forecasts"]),
                "brier": float(np.mean([x["brier"] for x in scored])),
                "base_brier": float(np.mean([x["base_brier"] for x in scored])),
                "base_probability": frozen["base_probability"], "positive_events": sum(x["event"] for x in scored),
                "bins": [], "states": [], "deadline_strata": []}
    for probability in sorted(set(r["probability"] for r in scored)):
        group = [r for r in scored if r["probability"] == probability]
        forecast["bins"].append({"probability": probability, "observed": float(np.mean([r["event"] for r in group])), "n": len(group)})
    for state in ("cold", "ready"):
        group = [r for r in scored if r["state"] == state]
        forecast["states"].append({"state": state, "n": len(group), "brier": float(np.mean([r["brier"] for r in group])),
                                   "base_brier": float(np.mean([r["base_brier"] for r in group])),
                                   "positive": sum(r["event"] for r in group)})
    for multiplier in (0.5, 1.0, 2.0):
        group = [r for r in scored if r["deadline_multiplier"] == multiplier]
        block_gaps = [float(np.mean([r["brier"] - r["base_brier"] for r in group if r["block"] == b]))
                      for b in range(12)]
        forecast["deadline_strata"].append({"multiplier": multiplier, "primary": multiplier == 1.0,
                                            "n": len(group), "brier": float(np.mean([r["brier"] for r in group])),
                                            "base_brier": float(np.mean([r["base_brier"] for r in group])),
                                            "positive": sum(r["event"] for r in group),
                                            "paired_block_95_brier_difference": interval(block_gaps)})
    block_effects = [float(np.mean([r["brier"] - r["base_brier"] for r in scored if r["block"] == b])) for b in range(12)]
    forecast["mean_brier_difference"] = float(np.mean(block_effects))
    forecast["paired_block_bootstrap_95_brier_difference"] = interval(block_effects)
    budgets = {phase: json.loads((ROOT / "results" / phase / "summary.json").read_text())
               for phase in ("development", "calibration", "confirmation")}
    result = {"scope": "Four fixed matrices on one shared host; paired run blocks, not independent sectors",
              "confirmation_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "statistics": statistics,
              "q16_comparisons": paired, "forecasts": forecast, "budgets": budgets,
              "qualified_batches": sum(r["qualified"] for r in rows),
              "qualified_rhs": sum(r["accepted_count"] for r in rows),
              "extra_preflight_rhs": 2 * sum(r["method"] == "certified_ready" for r in rows),
              "unknown_costs": ["authoring inference", "human review", "external acceptance", "maintenance", "opportunity cost"]}
    (ROOT / "results/numerical_analysis.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (ROOT / "results/forecast_outcomes.json").write_text(json.dumps(scored, separators=(",", ":"), allow_nan=False) + "\n")
    print(json.dumps({"qualified_batches": result["qualified_batches"], "qualified_rhs": result["qualified_rhs"],
                      "forecasts": forecast, "q16_comparisons": paired}, indent=2))


if __name__ == "__main__":
    main()
