# SPDX-License-Identifier: Apache-2.0
"""Additive post-run audit of manifest completeness and aggregate economic statistics."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any


def statistics_from_worlds(worlds: list[dict[str, Any]]) -> dict[str, float | int]:
    """Recompute published statistics without importing simulation functions."""
    count = len(worlds)
    profits = [world["profit_cents"] for world in worlds]
    ordered = sorted(profits)
    mean_profit = Fraction(sum(profits), count)
    result: dict[str, float | int] = {
        "worlds": count,
        "mean_profit_cents": float(mean_profit),
        "profit_sampling_se_cents": math.sqrt(sum((Fraction(p) - mean_profit) ** 2 for p in profits)
                                              / (count * (count - 1))) if count > 1 else 0,
        "probability_loss": sum(value < 0 for value in profits) / count,
        "worst_loss_cents": min(profits),
        "profit_p05_cents": ordered[int((count - 1) * 0.05)],
        "profit_p95_cents": ordered[int((count - 1) * 0.95)],
        "max_cash_requirement_cents": max(world["cash_requirement_cents"] for world in worlds),
        "stop_fraction": sum(world["stop_month"] is not None for world in worlds) / count,
        "successor_fraction": sum(world["successor_funded"] for world in worlds) / count,
        "mean_total_human_hours": sum(sum(world["hours"].values()) for world in worlds) / count,
    }
    for label, source in {"mean_operating_contribution_cents": "operating_contribution_cents",
                          "mean_revenue_cents": "recognized_revenue_cents", "mean_collections_cents": "collections_cents",
                          "mean_total_project_cost_cents": "total_project_cost_cents",
                          "mean_cash_requirement_cents": "cash_requirement_cents"}.items():
        result[label] = sum(world[source] for world in worlds) / count
    for name in ("signed", "accepted", "renewals"):
        result[f"mean_{name}"] = sum(world["counts"][name] for world in worlds) / count
    return result


def main() -> None:
    """Audit every declared seed/scenario pair and all reported scenario statistics."""
    parser = argparse.ArgumentParser()
    parser.add_argument("study", type=Path)
    args = parser.parse_args()
    root = args.study
    directory = root / "economics/confirmation"
    config = json.loads((root / "economics/assumptions.json").read_text())
    policy = json.loads((root / "economics/selected_policy.json").read_text())
    seeds = json.loads((root / "evidence/confirmation/seeds.json").read_text())["economic_seeds"]
    manifest = json.loads((directory / "world_manifest.json").read_text())
    published = json.loads((directory / "summary.json").read_text())
    expected = {f"worlds/{scenario}-{seed}.json" for scenario in config["scenarios"] for seed in seeds}
    assert {item["path"] for item in manifest} == expected and len(manifest) == len(expected)
    assert {str(path.relative_to(directory)) for path in (directory / "worlds").glob("*.json")} == expected
    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in config["scenarios"]}
    for item in manifest:
        path = directory / item["path"]
        raw = path.read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item["sha256"]
        world = json.loads(raw)
        assert world["policy"] == policy and world["seed"] in seeds and world["conventional"] is False
        grouped[world["scenario"]].append(world)
    comparisons = []
    for scenario, worlds in grouped.items():
        assert len(worlds) == len(seeds) == len({world["seed"] for world in worlds})
        recomputed = statistics_from_worlds(worlds)
        assert set(recomputed) == set(published[scenario]), "Unexpected or omitted aggregate field"
        for key, value in recomputed.items():
            assert math.isclose(value, published[scenario][key], rel_tol=1e-12, abs_tol=1e-7), (scenario, key)
        comparisons.append({"scenario": scenario, "worlds": len(worlds), "aggregate_fields_checked": len(recomputed),
                            "status": "pass"})
    receipt = {"status": "pass", "scope": "Additive audit; no frozen decision or simulation source changed",
               "manifest_worlds": len(manifest), "seed_count_per_scenario": len(seeds), "scenarios": comparisons,
               "audit_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               "world_manifest_sha256": hashlib.sha256((directory / "world_manifest.json").read_bytes()).hexdigest(),
               "summary_sha256": hashlib.sha256((directory / "summary.json").read_bytes()).hexdigest()}
    output = root / "verification/economic_aggregate_audit.json"
    output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": "pass", "manifest_worlds": len(manifest), "aggregate_fields_checked":
                      sum(entry["aggregate_fields_checked"] for entry in comparisons)}))


if __name__ == "__main__":
    main()
