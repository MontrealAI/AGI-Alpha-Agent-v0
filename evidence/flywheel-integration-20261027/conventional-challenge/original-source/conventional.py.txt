# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from typing import Any

def solve(problem: dict[str, Any]) -> dict[str, Any]:
    actions = problem["steps"]
    goals = frozenset(problem["required_outputs"])
    obligations = frozenset(problem["obligations"])
    best = None
    answer = []
    examined = 0
    complete = True
    for mask in range(1 << len(actions)):
        if examined >= problem["search_node_cap"]:
            complete = False
            break
        examined += 1
        chosen = [actions[i] for i in range(len(actions)) if mask & (1 << i)]
        if any(s["permission"] == "denied" or not obligations.issubset(s["preserves"]) for s in chosen):
            continue
        cost = sum(s["estimated_cost_micro_usd"] for s in chosen)
        seconds = sum(s["duration_seconds"] for s in chosen)
        if cost > problem["cost_cap_micro_usd"] or seconds > problem["seconds_cap"]:
            continue
        facts = set(problem["starting_facts"])
        remaining = {s["step_id"]: s for s in chosen}
        sequence = []
        while remaining:
            ready = sorted(k for k, s in remaining.items() if set(s["requires"]).issubset(facts))
            if not ready:
                break
            identity = ready[0]
            action = remaining.pop(identity)
            sequence.append(identity)
            facts.update(action["produces"])
        if remaining or not goals.issubset(facts):
            continue
        rank = (sum(s["permission"] == "required" for s in chosen), cost, seconds, tuple(sequence))
        if best is None or rank < best:
            best, answer = rank, sequence
    status = "incomplete" if not complete else "no-plan" if best is None else "conditional-plan" if best[0] else "declared-plan"
    return dict(status=status, rank=best, steps=answer, subsets_examined=examined, search_complete=complete)

def witness(problem: dict[str, Any], report: dict[str, Any]) -> bool:
    actions = {a["step_id"]: a for a in problem["steps"]}
    facts = set(problem["starting_facts"])
    seen = set()
    cost, seconds, pending = 0, 0, []
    try:
        for raw in report["steps"]:
            identity = raw["step_id"]
            a = actions[identity]
            if a != raw or identity in seen or a["permission"] == "denied": return False
            if not set(a["requires"]).issubset(facts): return False
            if not set(problem["obligations"]).issubset(a["preserves"]): return False
            facts.update(a["produces"])
            seen.add(identity)
            cost += a["estimated_cost_micro_usd"]
            seconds += a["duration_seconds"]
            if a["permission"] == "required": pending.append(identity)
        return (report["status"] == ("conditional-plan" if pending else "declared-plan")
                and set(problem["required_outputs"]).issubset(facts)
                and cost <= problem["cost_cap_micro_usd"] and seconds <= problem["seconds_cap"]
                and report["estimated_cost_micro_usd"] == cost and report["duration_seconds"] == seconds
                and report["pending_permissions"] == pending and report["preserved_obligations"] == problem["obligations"]
                and report["authority_granted"] is False and report["customer_acceptance"] is False
                and report["actual_experiment_performed"] is False)
    except (KeyError, TypeError): return False
