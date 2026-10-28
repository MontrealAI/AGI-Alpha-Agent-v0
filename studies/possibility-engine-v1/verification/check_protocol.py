# SPDX-License-Identifier: Apache-2.0
"""Check delivered experiment semantics and cost without importing the constructor."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any

from independent_math import impulse_entry, response_interval, validate_graph


def cover_masks(data: dict[str, Any]) -> tuple[list[int], int, int]:
    """Build requirement masks directly from the model adjacency matrices."""
    graphs = [model["adjacency"] for model in data["models"]]
    pairs = list(itertools.combinations(range(len(graphs)), 2))
    outages: list[int | None] = [None] + list(range(16)) if data.get("failure_mode") == "one_terminal" else [None]
    masks = []
    for experiment in data["experiments"]:
        actuator, sensor = experiment["actuator"], experiment["sensor"]
        mask = 0
        for index, ((first, second), outage) in enumerate(itertools.product(pairs, outages)):
            if (outage not in (actuator, sensor)
                    and graphs[first][sensor][actuator] != graphs[second][sensor][actuator]):
                mask |= 1 << index
        masks.append(mask)
    return masks, (1 << (len(pairs) * len(outages))) - 1, 2 if data.get("failure_mode") == "one_experiment" else 1


def exhaustive_minimum(data: dict[str, Any]) -> tuple[int | None, list[int], int]:
    """Compute the exact optimum for bounded candidate sets by complete enumeration."""
    masks, target, demand = cover_masks(data)
    useful = [index for index, mask in enumerate(masks) if mask]
    if demand == 1 and data.get("failure_mode", "none") == "none" and len(data["models"]) == 2:
        if not useful:
            return None, [], len(masks)
        chosen = min(useful, key=lambda index: (data["experiments"][index]["cost_units"], index))
        return data["experiments"][chosen]["cost_units"], [chosen], len(masks)
    if len(useful) > 20:
        raise ValueError("Independent complete enumeration is limited to twenty useful experiments")
    best_cost: int | None = None
    best_indices: list[int] = []
    examined = 0
    for selection in range(1 << len(useful)):
        indices = [useful[i] for i in range(len(useful)) if selection & (1 << i)]
        cost = sum(data["experiments"][i]["cost_units"] for i in indices)
        if best_cost is not None and cost >= best_cost:
            continue
        examined += 1
        once, twice = 0, 0
        for index in indices:
            twice |= once & masks[index]
            once |= masks[index]
        if (once if demand == 1 else twice) == target:
            best_cost, best_indices = cost, indices
    return best_cost, best_indices, examined


def check(data: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """Validate a complete delivery and compare with independent optimum."""
    for model in data["models"]:
        validate_graph(model["adjacency"])
    input_hash = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    assert result["input_sha256"] == input_hash, "Result is bound to a different input"
    box = data["uncertainty"]
    rate, leak, gain = tuple(box["rate"]), tuple(box["leak"]), tuple(box["gain"])
    parameters = {key: sum(box[key]) / 2 for key in ("rate", "leak", "gain")}
    assert result["nominal_parameters"] == parameters, "Nominal parameters are not the declared box midpoint"
    candidates = []
    for time in sorted(set(data["times"])):
        nonedge = response_interval(0, time, rate, leak, gain)
        edge = response_interval(1, time, rate, leak, gain)
        margin = edge[0] - nonedge[1] - 2 * box["noise"]
        candidates.append((margin, time, nonedge, edge))
    margin, time, nonedge, edge = sorted(candidates, key=lambda entry: (-entry[0], entry[1]))[0]
    assert math.isclose(result["time"], time, rel_tol=0, abs_tol=1e-12), "Different selected time"
    assert math.isclose(result["robust_margin"], margin, rel_tol=0, abs_tol=5e-11), "Incorrect robust margin"
    for label, interval in (("nonedge", nonedge), ("edge", edge)):
        expected = interval[0] - box["noise"], interval[1] + box["noise"]
        assert all(abs(a - b) < 5e-11 for a, b in zip(result["noise_inclusive_intervals"][label], expected))
    optimum, independent_indices, examined = exhaustive_minimum(data)
    if margin <= 1e-10 or optimum is None:
        assert result["status"] == "infeasible", "An impossible instance was accepted"
        assert result["selected"] == []
        assert result["cost_units"] is None
        return {"status": "pass", "outcome": "correct_refusal", "enumerated_portfolios": examined,
                "robust_margin": margin, "minimum_cost": None}
    assert result["status"] == "constructed", "A feasible instance was not constructed"
    selected = [entry["id"] for entry in result["selected"]]
    assert len(selected) == len(set(selected)), "Duplicate selected experiment"
    masks, target, demand = cover_masks(data)
    once, twice = 0, 0
    maximum_nominal_error = 0.0
    for entry in result["selected"]:
        index = entry["id"]
        assert type(index) is int and 0 <= index < len(data["experiments"]), "Invalid selected experiment id"
        original = data["experiments"][index]
        assert all(entry[key] == original[key] for key in ("actuator", "sensor", "cost_units"))
        twice |= once & masks[index]
        once |= masks[index]
        assert len(entry["nominal_outputs"]) == len(data["models"]), "Missing nominal prediction"
        for model, actual in zip(data["models"], entry["nominal_outputs"]):
            adjacency = model["adjacency"][entry["sensor"]][entry["actuator"]]
            expected = impulse_entry(adjacency, entry["sensor"] == entry["actuator"], time,
                                     parameters["rate"], parameters["leak"], parameters["gain"])
            error = abs(expected - actual)
            maximum_nominal_error = max(maximum_nominal_error, error)
            assert error < 1e-12, "Nominal output differs from independent spectral formula"
    assert (once if demand == 1 else twice) == target, "Selected portfolio fails a model/outage requirement"
    cost = sum(data["experiments"][index]["cost_units"] for index in selected)
    assert cost == result["cost_units"] == optimum, "Portfolio is not independently cost-optimal"
    return {"status": "pass", "outcome": "construction_checked", "enumerated_portfolios": examined,
            "robust_margin": margin, "minimum_cost": optimum, "independent_selected": independent_indices,
            "maximum_nominal_error": maximum_nominal_error, "retained_exclusive_advantage": False}


def main() -> None:
    """Check a saved input/result pair and optionally write the independent receipt."""
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check(json.loads((args.directory / "input.json").read_text()),
                   json.loads((args.directory / "result.json").read_text()))
    raw = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(raw)
    print(raw, end="")


if __name__ == "__main__":
    main()
