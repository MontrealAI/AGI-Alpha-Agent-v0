# SPDX-License-Identifier: Apache-2.0
"""Construct joint-access experiments in a precisely bounded diffusion family."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np
from scipy.linalg import expm
from scipy.optimize import Bounds, LinearConstraint, milp

VERSION = "possibility-engine-v1.0"
DEFAULT_BOX = {"rate": [0.8, 1.2], "leak": [0.05, 0.15], "gain": [0.95, 1.05], "noise": 0.005}


def validate_box(box: dict[str, Any]) -> None:
    """Reject non-finite, inverted, negative or unsupported uncertainty."""
    if set(box) != {"rate", "leak", "gain", "noise"}:
        raise ValueError("Uncertainty requires exactly rate, leak, gain and noise")
    for key in ("rate", "leak", "gain"):
        values = box[key]
        if not isinstance(values, list) or len(values) != 2:
            raise ValueError("Each parameter interval needs two bounds")
        lo, hi = values
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
            raise ValueError("Bounds must be finite numbers")
        if lo < 0 or hi < lo or (key in ("rate", "gain") and lo == 0):
            raise ValueError("Invalid parameter interval")
    noise = box["noise"]
    if isinstance(noise, bool) or not isinstance(noise, (int, float)) or not math.isfinite(noise) or noise < 0:
        raise ValueError("Noise must be finite and nonnegative")


def validate_graph(graph: Any) -> np.ndarray:
    """Recognize the exact 16-node regular-graph family before using its formulas."""
    if not isinstance(graph, list) or len(graph) != 16:
        raise ValueError("Supported graph order is exactly sixteen")
    if any(not isinstance(row, list) or len(row) != 16 for row in graph):
        raise ValueError("Graph must be a square matrix")
    if any(type(v) is not int or v not in (0, 1) for row in graph for v in row):
        raise ValueError("Adjacency entries must be integer zero or one")
    a = np.array(graph, dtype=np.int64)
    if np.any(a != a.T) or np.any(np.diag(a)) or np.any(a.sum(axis=1) != 6):
        raise ValueError("Expected simple undirected six-regular graph")
    if not np.array_equal(a @ a, 4 * np.eye(16, dtype=np.int64) + 2 * np.ones((16, 16), dtype=np.int64)):
        raise ValueError("Graph does not satisfy the supported algebraic identity")
    return a


def interval(kind: int, time: float, box: dict[str, Any]) -> tuple[float, float]:
    """Compute a continuous-parameter response envelope, including bounded noise."""
    if kind not in (0, 1, 2) or not math.isfinite(time) or time <= 0:
        raise ValueError("Invalid response class or observation time")
    low_z, high_z = math.exp(-4 * box["rate"][1] * time), math.exp(-4 * box["rate"][0] * time)
    points = [low_z, high_z]
    if kind == 1 and low_z <= 1 / 3 <= high_z:
        points.append(1 / 3)
    if kind == 0:
        values = [(1 - z) ** 2 / 16 for z in points]
    elif kind == 1:
        values = [(1 + 2 * z - 3 * z * z) / 16 for z in points]
    else:
        values = [(1 + 3 * z) ** 2 / 16 for z in points]
    lo = box["gain"][0] * math.exp(-box["leak"][1] * time) * min(values)
    hi = box["gain"][1] * math.exp(-box["leak"][0] * time) * max(values)
    pad = 1e-12
    return lo - box["noise"] - pad, hi + box["noise"] + pad


def nominal(
    a: np.ndarray, actuator: int, sensor: int, time: float, rate: float = 1.0, leak: float = 0.1, gain: float = 1.0
) -> float:
    """Evaluate a direct matrix exponential independently of the envelope formula."""
    return float(gain * expm(-(rate * (6 * np.eye(16) - a) + leak * np.eye(16)) * time)[sensor, actuator])


def validate_input(data: dict[str, Any]) -> tuple[list[np.ndarray], list[dict[str, int]]]:
    """Validate a bounded model, experiment and cost specification."""
    if data.get("schema") != "possibility-engine-input-v1":
        raise ValueError("Unsupported input schema")
    validate_box(data["uncertainty"])
    if not 2 <= len(data["models"]) <= 8 or len({x["id"] for x in data["models"]}) != len(data["models"]):
        raise ValueError("Need two through eight uniquely named hypotheses")
    if any(
        not isinstance(x["id"], str) or re.fullmatch(r"[A-Za-z0-9_-]{1,48}", x["id"]) is None for x in data["models"]
    ):
        raise ValueError("Model identifiers must be short inert names")
    models = [validate_graph(x["adjacency"]) for x in data["models"]]
    times = data["times"]
    if not 1 <= len(times) <= 1000 or any(type(t) not in (int, float) or not math.isfinite(t) or t <= 0 for t in times):
        raise ValueError("Need a bounded positive finite time grid")
    ports = data["experiments"]
    if not 1 <= len(ports) <= 256:
        raise ValueError("Need one through 256 permitted experiments")
    seen = set()
    for e in ports:
        if set(e) != {"actuator", "sensor", "cost_units"}:
            raise ValueError("Experiment requires exactly actuator, sensor and cost_units")
        if any(type(e[k]) is not int for k in e) or not 0 <= e["actuator"] < 16 or not 0 <= e["sensor"] < 16:
            raise ValueError("Invalid integer port")
        if e["cost_units"] <= 0 or e["cost_units"] > 1000000:
            raise ValueError("Cost must be a positive bounded integer")
        pair = e["actuator"], e["sensor"]
        if pair in seen:
            raise ValueError("Duplicate experiment")
        seen.add(pair)
    if data.get("failure_mode", "none") not in ("none", "one_experiment", "one_terminal"):
        raise ValueError("Unsupported failure model")
    return models, ports


def construct(data: dict[str, Any]) -> dict[str, Any]:
    """Build a cheapest robust distinguishing portfolio for all supplied hypotheses."""
    models, ports = validate_input(data)
    box = data["uncertainty"]
    times = sorted(set(float(t) for t in data["times"]))
    timed = []
    for t in times:
        nonedge, edge = interval(0, t, box), interval(1, t, box)
        timed.append((edge[0] - nonedge[1], t, nonedge, edge))
    best = sorted(timed, key=lambda p: (-p[0], p[1]))[0]
    margin, time, nonedge, edge = best
    pairs = list(itertools.combinations(range(len(models)), 2))
    candidates: list[dict[str, Any]] = []
    for number, e in enumerate(ports):
        a, s = e["actuator"], e["sensor"]
        kinds = [2 if a == s else int(m[s, a]) for m in models]
        covered = [i for i, (u, v) in enumerate(pairs) if kinds[u] != kinds[v] and margin > 1e-10]
        candidates.append({"id": number, **e, "kinds": kinds, "covers": covered})
    requirements: list[dict[str, int | None]] = []
    rows = []
    failures = data.get("failure_mode", "none")
    for p in range(len(pairs)):
        if failures == "one_terminal":
            for terminal in [None] + list(range(16)):
                rows.append(
                    [int(p in c["covers"] and terminal not in (c["actuator"], c["sensor"])) for c in candidates]
                )
                requirements.append({"pair": p, "outage_terminal": terminal})
        else:
            rows.append([int(p in c["covers"]) for c in candidates])
            requirements.append({"pair": p, "outage_terminal": None})
    demand = 2 if failures == "one_experiment" else 1
    parameters = {name: box[name][0] / 2 + box[name][1] / 2 for name in ("rate", "leak", "gain")}
    base: dict[str, Any] = {
        "schema": "possibility-engine-result-v1",
        "version": VERSION,
        "input_sha256": hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "scope": "computational experiment construction; no physical validation",
        "time": time,
        "robust_margin": margin,
        "nominal_parameters": parameters,
        "noise_inclusive_intervals": {"nonedge": nonedge, "edge": edge},
        "model_pairs": [[data["models"][u]["id"], data["models"][v]["id"]] for u, v in pairs],
        "failure_mode": failures,
        "candidate_count": len(candidates),
        "candidate_portfolios": candidates,
        "requirements": requirements,
        "time_evaluations": len(times),
        "all_root_rows_identical": all(np.array_equal(models[0][0], m[0]) for m in models[1:]),
        "interval_arithmetic_scope": (
            "analytic extrema, IEEE-754 evaluation with 1e-12 padding; not a formal floating-point proof"
        ),
    }
    if margin <= 1e-10 or any(sum(row) < demand for row in rows):
        return {
            **base,
            "status": "infeasible",
            "reason": "No certified portfolio above the 1e-10 margin guard within supplied limits",
            "selected": [],
            "cost_units": None,
        }
    constraints = LinearConstraint(np.array(rows, dtype=float), np.full(len(rows), demand), np.full(len(rows), np.inf))
    result = milp(
        np.array([e["cost_units"] for e in ports], dtype=float),
        integrality=np.ones(len(ports)),
        bounds=Bounds(np.zeros(len(ports)), np.ones(len(ports))),
        constraints=constraints,
        options={"time_limit": 15.0, "mip_rel_gap": 0.0},
    )
    if not result.success or result.x is None:
        return {**base, "status": "unresolved", "reason": str(result.message), "selected": [], "cost_units": None}
    chosen = [i for i, x in enumerate(result.x) if x > 0.5]
    if any(sum(row[i] for i in chosen) < demand for row in rows):
        raise RuntimeError("Solver witness failed exact integer recheck")
    selected = []
    for i in chosen:
        selected_entry: dict[str, Any] = dict(candidates[i])
        selected_entry["nominal_outputs"] = [
            nominal(m, selected_entry["actuator"], selected_entry["sensor"], time, **parameters) for m in models
        ]
        selected.append(selected_entry)
    return {
        **base,
        "status": "constructed",
        "selected": selected,
        "cost_units": sum(ports[i]["cost_units"] for i in chosen),
        "solver": "SciPy milp / HiGHS, integer witness rechecked",
        "optimality": "solver-reported zero relative gap; independent enumerator required for study acceptance",
    }


def netlist(model: dict[str, Any], actuator: int, sensor: int, time: float, parameters: dict[str, float]) -> str:
    """Export an executable RC analogue; initial capacitor charge is the impulse."""
    a = validate_graph(model["adjacency"])
    lines = [
        f"* Possibility Engine RC analogue: {model['id']}",
        "* Normalized units; no fabricated hardware claim",
        f".param rate={parameters['rate']:.16g} leak={parameters['leak']:.16g} gain={parameters['gain']:.16g}",
        ".option reltol=1e-9 abstol=1e-12",
    ]
    for i in range(16):
        lines.append(f"C{i} n{i} 0 1 IC={int(i == actuator)}")
        if parameters["leak"] > 0:
            lines.append(f"RL{i} n{i} 0 {{1/leak}}")
    for i, j in itertools.combinations(range(16), 2):
        if a[i, j]:
            lines.append(f"R{i}_{j} n{i} n{j} {{1/rate}}")
    lines.append(f"EREAD readout 0 n{sensor} 0 {{gain}}")
    lines.extend(
        [
            f".tran {time / 500:.12g} {time * 1.2:.12g} 0 {time / 1000:.12g} uic",
            f".measure tran observation FIND v(readout) AT={time:.12g}",
            ".end",
            "",
        ]
    )
    return "\n".join(lines)


def deliver(data: dict[str, Any], output: Path) -> dict[str, Any]:
    """Save the complete protocol, numerical predictions and usable circuit inputs."""
    result = construct(data)
    output.mkdir(parents=True, exist_ok=True)
    (output / "input.json").write_text(json.dumps(data, indent=2) + "\n")
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    for e in result["selected"]:
        for i, model in enumerate(data["models"]):
            (output / f"model_{i}_experiment_{e['id']}.cir").write_text(
                netlist(model, e["actuator"], e["sensor"], result["time"], result["nominal_parameters"])
            )
    return result


def main() -> None:
    """Expose a local-only JSON commissioning command."""
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    result = deliver(data, args.output)
    print(json.dumps({k: result[k] for k in ("status", "cost_units", "robust_margin", "time")}))


if __name__ == "__main__":
    main()
