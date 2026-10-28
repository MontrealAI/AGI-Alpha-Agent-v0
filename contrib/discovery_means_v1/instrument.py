# SPDX-License-Identifier: Apache-2.0
"""Exact finite minimax investigation with set-valued observation contracts.

No tool, physical action, permission or scientific coverage is created here.
Each supplied symbol is a possible observation, not a probability distribution.
"""

from __future__ import annotations

import itertools
import re
import time
from typing import Any

from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest

SCHEMA = "discovery-means-adaptive/v1"


def _int(value: Any, low: int, high: int, name: str) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{name} requires an exact integer in [{low}, {high}]")
    return value


def _names(values: Any, low: int, high: int, name: str) -> list[str]:
    if type(values) is not list or not low <= len(values) <= high:
        raise ValueError(f"{name} requires {low} through {high} entries")
    if any(type(x) is not str or re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", x) is None for x in values):
        raise ValueError(f"{name} requires bounded inert names")
    if len(set(values)) != len(values):
        raise ValueError(f"{name} requires unique entries")
    return sorted(values)


def validate(problem: dict[str, Any]) -> dict[str, Any]:
    """Validate a closed finite problem and return a deterministic copy."""
    if type(problem) is not dict:
        raise ValueError("problem must be an object")
    required = {"hypotheses", "experiments", "max_cost", "max_experiments"}
    if not required <= set(problem) or set(problem) - required - {"max_states"}:
        raise ValueError("unexpected or missing problem fields")
    if len(canonical(problem)) > 250_000:
        raise ValueError("problem exceeds the byte cap")
    hypotheses = _names(problem["hypotheses"], 2, 8, "hypotheses")
    experiments = problem["experiments"]
    if type(experiments) is not list or not 1 <= len(experiments) <= 12:
        raise ValueError("experiments requires one through twelve entries")
    clean = []
    for experiment in experiments:
        if type(experiment) is not dict or set(experiment) != {"id", "cost", "allowed", "outcomes"}:
            raise ValueError("experiment has unexpected or missing fields")
        identity = _names([experiment["id"]], 1, 1, "experiment id")[0]
        cost = _int(experiment["cost"], 1, 1_000_000, "cost")
        if type(experiment["allowed"]) is not bool:
            raise ValueError("allowed requires explicit boolean; it is only a supplied constraint")
        outcomes = experiment["outcomes"]
        if type(outcomes) is not dict or set(outcomes) != set(hypotheses):
            raise ValueError("every experiment must define every hypothesis")
        clean.append(
            {
                "id": identity,
                "cost": cost,
                "allowed": experiment["allowed"],
                "outcomes": {h: _names(outcomes[h], 1, 8, "outcomes") for h in hypotheses},
            }
        )
    _names([x["id"] for x in clean], 1, 12, "experiment ids")
    return {
        "hypotheses": hypotheses,
        "experiments": sorted(clean, key=lambda x: x["id"]),
        "max_cost": _int(problem["max_cost"], 0, 12_000_000, "max_cost"),
        "max_experiments": _int(problem["max_experiments"], 0, 12, "max_experiments"),
        "max_states": _int(problem.get("max_states", 100_000), 1, 100_000, "max_states"),
    }


class _BudgetExceeded(Exception):
    pass


def solve(problem: dict[str, Any]) -> dict[str, Any]:
    """Construct a worst-case-cost-optimal conditional policy within finite limits."""
    p = validate(problem)
    available = tuple(e["id"] for e in p["experiments"] if e["allowed"])
    exps = {e["id"]: e for e in p["experiments"]}
    cache: dict[tuple[Any, ...], tuple[int, int, dict[str, Any], int, int] | None] = {}
    states = 0
    started = time.process_time()

    def visit(
        hypotheses: tuple[str, ...], choices: tuple[str, ...], cash: int, depth: int
    ) -> tuple[int, int, dict[str, Any], int, int] | None:
        nonlocal states
        key = (hypotheses, choices, cash, depth)
        if key in cache:
            return cache[key]
        if states >= p["max_states"]:
            raise _BudgetExceeded("search state cap")
        if time.process_time() - started > 20:
            raise _BudgetExceeded("20 CPU-second cap")
        states += 1
        if len(hypotheses) == 1:
            tree: dict[str, Any] = {"kind": "leaf", "hypothesis": hypotheses[0]}
            result = (0, 0, tree, 1, len(canonical(tree)))
            cache[key] = result
            return result
        best = None
        if depth:
            for identity in choices:
                e = exps[identity]
                if e["cost"] > cash:
                    continue
                symbols = sorted({s for h in hypotheses for s in e["outcomes"][h]})
                branches = {}
                costs, depths, sizes, byte_sizes = [], [], [], []
                for symbol in symbols:
                    remaining = tuple(h for h in hypotheses if symbol in e["outcomes"][h])
                    child = visit(remaining, tuple(x for x in choices if x != identity), cash - e["cost"], depth - 1)
                    if child is None:
                        break
                    costs.append(child[0])
                    depths.append(child[1])
                    sizes.append(child[3])
                    byte_sizes.append(child[4])
                    branches[symbol] = child[2]
                else:
                    tree = {"kind": "probe", "experiment": identity, "branches": branches}
                    size = 1 + sum(sizes)
                    shell = {"kind": "probe", "experiment": identity, "branches": dict.fromkeys(symbols)}
                    byte_size = len(canonical(shell)) - 4 * len(symbols) + sum(byte_sizes)
                    if size > 5000 or byte_size > 250_000:
                        raise _BudgetExceeded("expanded policy output cap")
                    candidate = (e["cost"] + max(costs), 1 + max(depths), tree, size, byte_size)
                    if best is None or (candidate[0], candidate[1], identity) < (
                        best[0],
                        best[1],
                        best[2]["experiment"],
                    ):
                        best = candidate
        cache[key] = best
        return best

    complete = True
    stopping_reason = "exhaustive finite search completed"
    try:
        answer = visit(tuple(p["hypotheses"]), available, p["max_cost"], p["max_experiments"])
    except _BudgetExceeded as exc:
        complete, answer, stopping_reason = False, None, str(exc)
    unresolved = [
        [a, b]
        for a, b in itertools.combinations(p["hypotheses"], 2)
        if not any(set(exps[e]["outcomes"][a]).isdisjoint(exps[e]["outcomes"][b]) for e in available)
    ]
    return {
        "schema": SCHEMA,
        "problem_digest": digest(SCHEMA, p),
        "status": "incomplete" if not complete else "optimal" if answer else "infeasible",
        "policy": answer[2] if answer else None,
        "worst_cost": answer[0] if answer else None,
        "worst_depth": answer[1] if answer else None,
        "search_states": states,
        "complete": complete,
        "stopping_reason": stopping_reason,
        "objective": "minimum worst-case cost under hard depth cap; depth ties are not globally optimized",
        "policy_nodes": answer[3] if answer else None,
        "policy_bytes": answer[4] if answer else None,
        "unresolved_pairs": unresolved,
        "authority_granted": False,
        "coverage_qualified": False,
        "scope": "finite supplied observation sets; no physical or customer acceptance",
    }


def verify(problem: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Check every successful-policy branch without calling the constructor.

    This checks feasibility and claimed cost/depth, not global optimality or an
    infeasibility claim. The study's separately authored oracle checks those claims.
    """
    p = validate(problem)
    if type(report) is not dict or report.get("problem_digest") != digest(SCHEMA, p):
        return {"accepted_policy": False, "reason": "problem commitment mismatch", "optimality_checked": False}
    if report.get("status") != "optimal" or report.get("complete") is not True:
        return {"accepted_policy": False, "reason": "no complete successful policy", "optimality_checked": False}
    experiments = {e["id"]: e for e in p["experiments"]}
    count = 0

    def walk(node: Any, hypotheses: set[str], used: set[str], cost: int, depth: int) -> tuple[int, int]:
        nonlocal count
        count += 1
        if count > 5000 or type(node) is not dict or cost > p["max_cost"] or depth > p["max_experiments"]:
            raise ValueError("policy size or branch budget exceeded")
        if node.get("kind") == "leaf":
            if set(node) != {"kind", "hypothesis"} or hypotheses != {node["hypothesis"]}:
                raise ValueError("leaf does not uniquely identify the remaining hypothesis")
            return cost, depth
        if set(node) != {"kind", "experiment", "branches"} or node.get("kind") != "probe":
            raise ValueError("invalid policy node")
        identity, branches = node["experiment"], node["branches"]
        if type(identity) is not str or identity not in experiments or identity in used:
            raise ValueError("unknown or repeated probe")
        e = experiments[identity]
        if not e["allowed"] or type(branches) is not dict:
            raise ValueError("probe is disallowed or branches are invalid")
        expected = {s for h in hypotheses for s in e["outcomes"][h]}
        if set(branches) != expected:
            raise ValueError("all possible observations require exactly one branch")
        values = [
            walk(
                branches[s],
                {h for h in hypotheses if s in e["outcomes"][h]},
                used | {identity},
                cost + e["cost"],
                depth + 1,
            )
            for s in sorted(expected)
        ]
        return max(x[0] for x in values), max(x[1] for x in values)

    try:
        cost, depth = walk(report["policy"], set(p["hypotheses"]), set(), 0, 0)
        valid = (
            type(report.get("worst_cost")) is int
            and type(report.get("worst_depth")) is int
            and (cost, depth) == (report["worst_cost"], report["worst_depth"])
            and report.get("authority_granted") is False
            and report.get("coverage_qualified") is False
        )
    except (ValueError, KeyError, TypeError, RecursionError):
        valid, cost, depth = False, None, None
    return {
        "accepted_policy": valid,
        "worst_cost": cost,
        "worst_depth": depth,
        "checked_nodes": count,
        "optimality_checked": False,
        "scope": "independent branch feasibility, not adequacy of supplied hypotheses",
    }


def advance(problem: dict[str, Any], report: dict[str, Any], transcript: list[dict[str, str]]) -> dict[str, Any]:
    """Consume inert observations and return the next permitted local data action."""
    p = validate(problem)
    if not verify(p, report)["accepted_policy"]:
        raise ValueError("only a verified successful policy can consume observations")
    if type(transcript) is not list or len(transcript) > p["max_experiments"]:
        raise ValueError("transcript exceeds its declared depth")
    node = report["policy"]
    experiments = {e["id"]: e for e in p["experiments"]}
    cost = 0
    for row in transcript:
        if type(row) is not dict or set(row) != {"experiment", "outcome"}:
            raise ValueError("transcript rows require exactly experiment and outcome")
        if node["kind"] != "probe" or row["experiment"] != node["experiment"]:
            raise ValueError("observation is not the requested next experiment")
        if type(row["outcome"]) is not str or row["outcome"] not in node["branches"]:
            raise ValueError("observation lies outside the declared model; reassess")
        cost += experiments[node["experiment"]]["cost"]
        node = node["branches"][row["outcome"]]
    return {
        "problem_digest": report["problem_digest"],
        "spent_cost_units": cost,
        "transcript_digest": digest("discovery-means-transcript/v1", transcript),
        "next_experiment": node.get("experiment"),
        "identified_hypothesis": node.get("hypothesis"),
        "authority_granted": False,
        "physical_execution": False,
    }
