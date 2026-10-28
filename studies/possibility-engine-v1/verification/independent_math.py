# SPDX-License-Identifier: Apache-2.0
"""Independent integer-graph witness and closed-form experimental competitor."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from pathlib import Path
from typing import Any


def construct_graphs() -> dict[str, Any]:
    """Construct the two graphs directly, then align only the root neighborhoods."""
    order = 16
    rook: list[list[int]] = [[0] * order for _ in range(order)]
    shrikhande: list[list[int]] = [[0] * order for _ in range(order)]
    steps = {(1, 0), (3, 0), (0, 1), (0, 3), (1, 1), (3, 3)}
    for i, j in itertools.combinations(range(order), 2):
        xi, yi = divmod(i, 4)
        xj, yj = divmod(j, 4)
        rook[i][j] = rook[j][i] = int(xi == xj or yi == yj)
        shrikhande[i][j] = shrikhande[j][i] = int(((xi - xj) % 4, (yi - yj) % 4) in steps)
    old_neighbors = [i for i in range(1, order) if rook[0][i]]
    new_neighbors = [i for i in range(1, order) if shrikhande[0][i]]
    old_other = [i for i in range(1, order) if not rook[0][i]]
    new_other = [i for i in range(1, order) if not shrikhande[0][i]]
    relabel = dict(zip([0] + old_neighbors + old_other, [0] + new_neighbors + new_other))
    aligned = [[0] * order for _ in range(order)]
    for i in range(order):
        for j in range(order):
            aligned[relabel[i]][relabel[j]] = rook[i][j]
    return {
        "schema": "possibility-engine-graph-witness-v1",
        "order": order,
        "root": 0,
        "model_a": "rook",
        "model_b": "shrikhande",
        "rook_original_to_aligned": {str(k): v for k, v in relabel.items()},
        "root_neighbors": new_neighbors,
        "models": [
            {"id": "rook", "adjacency": aligned, "edges": edge_list(aligned)},
            {"id": "shrikhande", "adjacency": shrikhande, "edges": edge_list(shrikhande)},
        ],
    }


def edge_list(adjacency: list[list[int]]) -> list[list[int]]:
    """Return an undirected graph as sorted edge pairs."""
    return [[i, j] for i, j in itertools.combinations(range(len(adjacency)), 2) if adjacency[i][j]]


def product(left: list[list[int]], right: list[list[int]]) -> list[list[int]]:
    """Multiply small integer matrices without numerical or study dependencies."""
    return [[sum(a * b for a, b in zip(row, col)) for col in zip(*right)] for row in left]


def validate_graph(adjacency: list[list[int]]) -> dict[str, Any]:
    """Check exact graph identities sufficient for the transfer-function proof."""
    n = len(adjacency)
    assert n == 16
    assert all(len(row) == n for row in adjacency)
    assert all(value in (0, 1) for row in adjacency for value in row)
    assert all(adjacency[i][i] == 0 for i in range(n))
    assert all(adjacency[i][j] == adjacency[j][i] for i in range(n) for j in range(n))
    assert all(sum(row) == 6 for row in adjacency)
    seen = {0}
    while True:
        expanded = seen | {j for i in seen for j in range(n) if adjacency[i][j]}
        if expanded == seen:
            break
        seen = expanded
    assert len(seen) == n
    squared = product(adjacency, adjacency)
    assert all(squared[i][j] == 4 * int(i == j) + 2 for i in range(n) for j in range(n))
    four_cliques = [
        list(nodes)
        for nodes in itertools.combinations(range(n), 4)
        if all(adjacency[i][j] for i, j in itertools.combinations(nodes, 2))
    ]
    return {
        "vertices": n,
        "edges": len(edge_list(adjacency)),
        "degree": 6,
        "connected": True,
        "exact_identity_A_squared_equals_4I_plus_2J": True,
        "four_clique_count": len(four_cliques),
        "four_cliques": four_cliques,
        "laplacian_eigenvalues_with_multiplicities": [[0, 1], [4, 6], [8, 9]],
    }


def impulse_entry(adjacency: int, diagonal: bool, t: float, k: float, leak: float, gain: float = 1.0) -> float:
    """Evaluate the exact spectral-projector formula for this witness family."""
    if t < 0 or k < 0 or leak < 0 or gain < 0:
        raise ValueError("Time, rate, leakage and gain must be nonnegative")
    p0 = 1 / 16
    p4 = adjacency / 4 + int(diagonal) / 2 - 1 / 8
    p8 = int(diagonal) / 2 - adjacency / 4 + 1 / 16
    return gain * math.exp(-leak * t) * (p0 + p4 * math.exp(-4 * k * t) + p8 * math.exp(-8 * k * t))


def response_interval(
    adjacency: int,
    t: float,
    rate_range: tuple[float, float],
    leak_range: tuple[float, float],
    gain_range: tuple[float, float],
) -> tuple[float, float]:
    """Enclose off-diagonal response exactly apart from elementary floating rounding."""
    k0, k1 = rate_range
    l0, l1 = leak_range
    g0, g1 = gain_range
    if not (t > 0 and 0 <= k0 <= k1 and 0 <= l0 <= l1 and 0 <= g0 <= g1):
        raise ValueError("Invalid positive-time uncertainty box")
    z0, z1 = math.exp(-4 * k1 * t), math.exp(-4 * k0 * t)
    candidates = [z0, z1]
    if adjacency and z0 <= 1 / 3 <= z1:
        candidates.append(1 / 3)
    values = [((1 + 2 * z - 3 * z * z) if adjacency else (1 - z) ** 2) / 16 for z in candidates]
    lower = g0 * math.exp(-l1 * t) * min(values)
    upper = g1 * math.exp(-l0 * t) * max(values)
    padding = 2e-15
    return max(0.0, lower - padding), upper + padding


def independent_competitor(
    witness: dict[str, Any],
    times: list[float],
    rate_range: tuple[float, float],
    leak_range: tuple[float, float],
    gain_range: tuple[float, float],
    error: float,
    actuators: list[int] | None = None,
    sensors: list[int] | None = None,
) -> dict[str, Any]:
    """Enumerate legal ports using closed-form robust response intervals."""
    if error < 0:
        raise ValueError("Error bound must be nonnegative")
    left, right = [model["adjacency"] for model in witness["models"]]
    choices = []
    for actuator in actuators if actuators is not None else range(16):
        for sensor in sensors if sensors is not None else range(16):
            if left[sensor][actuator] == right[sensor][actuator]:
                continue
            for t in times:
                first = response_interval(left[sensor][actuator], t, rate_range, leak_range, gain_range)
                second = response_interval(right[sensor][actuator], t, rate_range, leak_range, gain_range)
                gap = max(first[0] - second[1], second[0] - first[1]) - 2 * error
                choices.append({"actuator": actuator, "sensor": sensor, "time": t, "margin": gap,
                                "model_a_interval": first, "model_b_interval": second})
    if not choices:
        return {"status": "no_feasible_protocol", "evaluations": 0}
    choices.sort(key=lambda entry: (-entry["margin"], entry["actuator"], entry["sensor"], entry["time"]))
    return {"status": "accepted" if choices[0]["margin"] > 0 else "no_feasible_protocol",
            "evaluations": len(choices), "best": choices[0]}


def verify_witness(witness: dict[str, Any]) -> dict[str, Any]:
    """Establish both nonisomorphism and exact limits of the original ports."""
    first, second = [entry["adjacency"] for entry in witness["models"]]
    facts = [validate_graph(graph) for graph in (first, second)]
    assert facts[0]["four_clique_count"] == 8
    assert facts[1]["four_clique_count"] == 0
    assert first[0] == second[0]
    differing = [[i, j] for i in range(16) for j in range(16) if first[i][j] != second[i][j]]
    assert differing and all(i != 0 and j != 0 for i, j in differing)
    return {
        "status": "pass",
        "graphs": facts,
        "nonisomorphic_by_four_clique_count": True,
        "current_port_all_waveforms_identical": True,
        "any_actuator_with_root_sensor_identical": True,
        "any_sensor_with_root_actuator_identical": True,
        "differing_ordered_joint_ports": differing,
        "differing_ordered_joint_port_count": len(differing),
        "proof_basis": "A^2=4I+2J; AJ=JA=6J; functions of L lie in span(I,A,J)",
        "assumptions": ["zero common initial state", "linear time-invariant diffusion", "common uniform edge rate",
                        "common uniform leakage", "node labels identify physical ports", "ideal impulse or specified pulse"],
        "scope": "exact model identities; no physical network measurement",
    }


def main() -> None:
    """Write a canonical witness, independent result and matched-information baseline."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    witness = construct_graphs()
    raw = (json.dumps(witness, indent=2, sort_keys=True) + "\n").encode()
    (args.out / "independent_graphs.json").write_bytes(raw)
    result = verify_witness(witness)
    result["witness_sha256"] = hashlib.sha256(raw).hexdigest()
    result["competitor"] = independent_competitor(
        witness, [j / 1000 for j in range(50, 501)], (0.8, 1.2), (0.05, 0.15), (0.95, 1.05), 0.005
    )
    (args.out / "independent_math_result.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: value for key, value in result.items() if key not in ("graphs", "differing_ordered_joint_ports")},
                     indent=2))


if __name__ == "__main__":
    main()
