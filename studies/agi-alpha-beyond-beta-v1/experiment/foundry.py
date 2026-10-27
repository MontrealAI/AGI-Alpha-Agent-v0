# SPDX-License-Identifier: Apache-2.0
"""A bounded optimization product, not a live frontier-model experiment.

Compile capacities into assignment slots; independently validate the original
integer flow using residual potentials. Public algorithms are deliberately used.
"""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import platform
import time
from pathlib import Path
import numpy as np
import scipy
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]


def check_input(instance):
    if set(instance) != {"costs", "capacities", "allowed"}:
        raise ValueError("Supported scope is integer assignment costs, capacity and eligibility only")
    c, cap, allowed = instance["costs"], instance["capacities"], instance["allowed"]
    n, m = len(c), len(cap)
    if not 1 <= n <= 200 or not 1 <= m <= 40:
        raise ValueError("Instance outside supported bounds")
    if len(allowed) != n or any(len(row) != m for row in c + allowed):
        raise ValueError("Dimension mismatch")
    if any(type(x) is not int or not 0 <= x <= 200 for x in cap):
        raise ValueError("Capacity must be an integer in [0,200]")
    if sum(cap) > 800:
        raise ValueError("At most 800 resource slots")
    if any(type(x) is not int or not -10000 <= x <= 10000 for row in c for x in row):
        raise ValueError("Costs must be bounded integers")
    if any(type(x) is not bool for row in allowed for x in row):
        raise ValueError("Eligibility must be boolean")
    return n, m


def produce(instance):
    n, m = check_input(instance)
    slots = [j for j, cap in enumerate(instance["capacities"]) for _ in range(cap)]
    if len(slots) < n:
        return {"status": "abstain", "reason": "insufficient capacity"}
    matrix = np.array([[instance["costs"][i][j] if instance["allowed"][i][j] else np.inf
                        for j in slots] for i in range(n)], dtype=float)
    try:
        rows, columns = linear_sum_assignment(matrix)
    except ValueError:
        return {"status": "abstain", "reason": "no feasible complete matching"}
    assignment = [slots[int(k)] for k in columns]
    return {"status": "candidate", "assignment": assignment,
            "cost": sum(instance["costs"][i][j] for i, j in enumerate(assignment))}


def validate(instance, candidate):
    """Exact integer residual-network proof; does not call the producer solver.

Given a feasible fixed-value integral flow, absence of a negative-cost residual
cycle is an optimality certificate. Bellman-Ford from a zero-cost super-source
constructs integer potentials; every residual reduced cost must be nonnegative.
This proves correctness ONLY relative to the input model, not real-world intent.
"""
    n, m = check_input(instance)
    a = candidate.get("assignment", [])
    if len(a) != n or any(type(j) is not int or j < 0 or j >= m for j in a):
        return {"accepted": False, "reason": "malformed assignment"}
    if any(not instance["allowed"][i][j] for i, j in enumerate(a)):
        return {"accepted": False, "reason": "forbidden edge"}
    count = [a.count(j) for j in range(m)]
    if any(count[j] > instance["capacities"][j] for j in range(m)):
        return {"accepted": False, "reason": "capacity violation"}
    cost = sum(instance["costs"][i][j] for i, j in enumerate(a))
    if candidate.get("cost") != cost:
        return {"accepted": False, "reason": "objective mismatch"}
    source, sink = n + m, n + m + 1
    nodes = sink + 1
    edges = [(i, source, 0) for i in range(n)]
    for i in range(n):
        for j in range(m):
            if instance["allowed"][i][j]:
                cij = instance["costs"][i][j]
                edges.append((n + j, i, -cij) if a[i] == j else (i, n + j, cij))
    for j in range(m):
        if count[j] < instance["capacities"][j]:
            edges.append((n + j, sink, 0))
        if count[j] > 0:
            edges.append((sink, n + j, 0))
    potentials = [0] * nodes
    for k in range(nodes):
        changed = False
        for u, v, w in edges:
            if potentials[v] > potentials[u] + w:
                potentials[v] = potentials[u] + w
                changed = True
        if not changed:
            break
    if changed:
        return {"accepted": False, "reason": "negative residual cycle: suboptimal"}
    assert all(w + potentials[u] - potentials[v] >= 0 for u, v, w in edges)
    digest = hashlib.sha256(json.dumps(instance, sort_keys=True).encode()).hexdigest()
    return {"accepted": True, "reason": "original constraints and exact integer optimality",
            "instance_sha256": digest, "objective": cost, "potentials": potentials,
            "residual_edges": len(edges), "scope": "supplied finite assignment model only"}


def generate(seed, n, m):
    rng = np.random.default_rng(seed)
    cap = [int(np.ceil(n / m)) + 1 for _ in range(m)]
    costs = rng.integers(-10, 101, size=(n, m)).tolist()
    allowed = (rng.random((n, m)) > .3).tolist()
    # Plant feasibility only; the solver never sees the planted assignment.
    for i in range(n):
        allowed[i][i % m] = True
    return {"costs": costs, "capacities": cap, "allowed": allowed}


def brute(instance):
    n, m = check_input(instance)
    best = None
    for a in itertools.product(range(m), repeat=n):
        if any(a.count(j) > instance["capacities"][j] for j in range(m)):
            continue
        if any(not instance["allowed"][i][j] for i, j in enumerate(a)):
            continue
        cost = sum(instance["costs"][i][j] for i, j in enumerate(a))
        if best is None or cost < best:
            best = cost
    return best


def run(seed=771029, small=120, large=180):
    # Protocol is written before confirmation; this experiment is not economic
    # calibration of LLM correctness, construction probability, or buyer demand.
    rows = []
    for k in range(small + large):
        n, m = (6 + k % 2, 3) if k < small else ((20, 60, 120)[k % 3], (5, 10, 20)[k % 3])
        x = generate(seed + k, n, m)
        start = time.perf_counter_ns()
        out = produce(x)
        producer_ms = (time.perf_counter_ns() - start) / 1e6
        start = time.perf_counter_ns()
        checked = validate(x, out)
        validator_ms = (time.perf_counter_ns() - start) / 1e6
        exact = brute(x) if k < small else None
        assert checked["accepted"] and (exact is None or exact == out["cost"])
        # Unrestricted reconstruction has the identical tool and solution.
        rebuild = produce(json.loads(json.dumps(x)))
        assert rebuild == out
        bad = dict(out, cost=out["cost"] + 1)
        assert not validate(x, bad)["accepted"]
        overloaded = dict(out, assignment=[0] * n)
        overloaded["cost"] = sum(row[0] for row in x["costs"])
        assert not validate(x, overloaded)["accepted"]
        rows.append({"instance": k, "n": n, "m": m, "cost": out["cost"],
                     "producer_ms": producer_ms, "validator_ms": validator_ms,
                     "small_exhaustive_agreement": exact is not None, "valid": True})
    # Meaningfully different negative controls: capacity, eligibility, optimality,
    # unsupported semantics, infeasibility and common specification error.
    trap = {"costs": [[1, 9], [9, 1]], "capacities": [1, 1], "allowed": [[True, True], [True, True]]}
    assert not validate(trap, {"assignment": [1, 0], "cost": 18})["accepted"]
    forbidden = dict(trap, allowed=[[False, True], [True, True]])
    assert not validate(forbidden, {"assignment": [0, 1], "cost": 2})["accepted"]
    impossible = dict(trap, capacities=[0, 1])
    assert produce(impossible)["status"] == "abstain"
    rejected_scope = False
    try:
        produce(dict(trap, precedence=[[0, 1]]))
    except ValueError:
        rejected_scope = True
    assert rejected_scope
    wrong_spec = dict(trap, costs=[[9, 1], [1, 9]])
    shared_wrong = produce(wrong_spec)
    assert validate(wrong_spec, shared_wrong)["accepted"]
    # The same purported solution is wrong relative to the original intent.
    assert not validate(trap, shared_wrong)["accepted"]
    result = {"evidence_type": "observed local deterministic computation on synthetic instances",
              "not_evidence_for": ["frontier model discovery", "customer demand", "real-world correctness", "novel optimization algorithm"],
              "seed": seed, "small_instances": small, "large_instances": large,
              "accepted": len(rows), "unrestricted_rebuild_equal": len(rows),
              "corrupt_objectives_rejected": len(rows), "overloaded_outputs_rejected": len(rows),
              "negative_controls": {"suboptimal_rejected": True, "forbidden_rejected": True,
                  "infeasible_abstained": True, "unsupported_precedence_rejected": True,
                  "shared_wrong_spec_passes_its_own_checker": True},
              "producer_ms_median": float(np.median([x["producer_ms"] for x in rows])),
              "validator_ms_median": float(np.median([x["validator_ms"] for x in rows])),
              "validator_ms_p95": float(np.quantile([x["validator_ms"] for x in rows], .95)),
              "python": platform.python_version(), "scipy": scipy.__version__, "numpy": np.__version__,
              "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "instances": rows}
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path)
    p.add_argument("--output", type=Path, default=ROOT / "results" / "mechanism.json")
    p.add_argument("--seed", type=int, default=771029)
    p.add_argument("--small", type=int, default=120)
    p.add_argument("--large", type=int, default=180)
    args = p.parse_args()
    if args.input:
        x = json.loads(args.input.read_text())
        candidate = produce(x)
        result = {"candidate": candidate, "validation": validate(x, candidate) if candidate["status"] == "candidate" else None}
    else:
        result = run(args.seed, args.small, args.large)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "instances"}, indent=2))
