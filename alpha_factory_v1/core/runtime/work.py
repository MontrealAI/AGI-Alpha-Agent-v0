# SPDX-License-Identifier: Apache-2.0
"""Bounded, reproducible work and independent output checks."""

from __future__ import annotations

import itertools
import math
import re
from typing import Any, Callable

from alpha_factory_v1.core.simulation import mats

from .models import Allocation, Forecast, Mission, Research, Schedule, Coding
from .store import digest


def research(mission: Mission) -> dict[str, Any]:
    """Rank supplied passages and return exact, attributable quotations."""
    work = mission.work
    assert isinstance(work, Research)
    terms = set(re.findall(r"\w{3,}", mission.goal.lower()))
    passages = []
    for source in work.sources:
        for text in re.split(r"(?<=[.!?])\s+|\n+", source.text):
            quote = text.strip()
            if quote:
                words = set(re.findall(r"\w{3,}", quote.lower()))
                score = len(terms & words) / math.sqrt(max(1, len(words)))
                passages.append((score, source.id, quote[:1200]))
    passages.sort(key=lambda row: (-row[0], row[1], row[2]))
    return {
        "method": "extractive evidence ranking",
        "findings": [{"claim": quote, "source_id": sid, "quote": quote} for _, sid, quote in passages[:8]],
        "sources": [{"id": s.id, "title": s.title, "url": s.url, "sha256": digest(s.text)} for s in work.sources],
        "limits": "Supplied-source analysis; source authenticity and claim interpretation require operator review.",
    }


def _search(
    mission: Mission,
    length: int,
    evaluator: Callable[[list[float]], tuple[float, ...]],
    checkpoint: Callable[[], None],
    max_evaluations: int,
) -> tuple[mats.Population, int]:
    count = 0

    def measured(genome: list[float]) -> tuple[float, ...]:
        nonlocal count
        checkpoint()
        count += 1
        if count > max_evaluations:
            raise ValueError("evaluation budget exhausted")
        values = evaluator(genome)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("non-finite fitness")
        return values

    population = mats.run_evolution(
        measured,
        length,
        population_size=mission.population,
        generations=mission.generations,
        seed=mission.seed,
        populations={},
        scenario_hash=digest(mission.model_dump()),
        exchange_interval=0,
    )
    return population, count


def allocation(
    mission: Mission,
    checkpoint: Callable[[], None],
    max_evaluations: int,
    remembered: list[str] | None = None,
) -> dict[str, Any]:
    """Search feasible allocations; enumerate small cases as an independent oracle."""
    work = mission.work
    assert isinstance(work, Allocation)
    items = work.items

    def select(order: list[int]) -> list[int]:
        chosen: list[int] = []
        cost = risk = 0
        for i in order:
            item = items[i]
            if cost + item.cost <= work.budget and risk + item.risk <= work.max_risk:
                chosen.append(i)
                cost += item.cost
                risk += item.risk
        return sorted(chosen)

    def totals(chosen: list[int]) -> tuple[int, int, int]:
        return (
            sum(items[i].value for i in chosen),
            sum(items[i].cost for i in chosen),
            sum(items[i].risk for i in chosen),
        )

    def decode(genome: list[float]) -> list[int]:
        return select(sorted(range(len(items)), key=lambda i: (-genome[i], items[i].id)))

    def fitness(genome: list[float]) -> tuple[float, ...]:
        value, cost, risk = totals(decode(genome))
        return -float(value), float(cost), float(risk)

    baseline = select(sorted(range(len(items)), key=lambda i: (-items[i].value / items[i].cost, items[i].id)))
    pop, calls = _search(mission, len(items), fitness, checkpoint, max_evaluations)
    candidates = [baseline, *[decode(ind.genome) for ind in pop]]
    if remembered:
        prior = [i for i, item in enumerate(items) if item.id in remembered]
        candidates.append(select(prior + [i for i in range(len(items)) if i not in prior]))
    oracle = None
    if len(items) <= 12 and calls + 2 ** len(items) <= max_evaluations:
        oracle = 0
        for bits in itertools.product((False, True), repeat=len(items)):
            checkpoint()
            selected = [i for i, bit in enumerate(bits) if bit]
            value, cost, risk = totals(selected)
            calls += 1
            if cost <= work.budget and risk <= work.max_risk:
                oracle = max(oracle, value)
                candidates.append(selected)
    best = min(candidates, key=lambda ids: (-totals(ids)[0], totals(ids)[1], totals(ids)[2], ids))
    value, cost, risk = totals(best)
    base_value, _, _ = totals(baseline)
    return {
        "method": "MATS NSGA-II with feasible decoding"
        + (" and exhaustive verification" if oracle is not None else ""),
        "selected": [items[i].id for i in best],
        "value": value,
        "cost": cost,
        "risk": risk,
        "baseline_value": base_value,
        "improvement": value - base_value,
        "optimal_value": oracle,
        "optimality_proven": oracle is not None and value == oracle,
        "evaluations": calls,
        "unit": work.unit,
        "pareto": [
            {"selected": [items[i].id for i in decode(ind.genome)], "objectives": list(ind.fitness or ())}
            for ind in mats.pareto_front(pop)
        ],
        "limits": "Values and risks are supplied planning assumptions; objective improvement is not realized income.",
    }


def build_schedule(work: Schedule, order: list[int]) -> dict[str, Any]:
    """Construct a non-preemptive list schedule for the proposed job order."""
    machines: dict[str, int] = {}
    operations = []
    lateness = 0
    for i in order:
        job = work.jobs[i]
        ready = 0
        for index, operation in enumerate(job.operations):
            start = max(ready, machines.get(operation.machine, 0))
            end = start + operation.duration
            operations.append(
                {"job": job.id, "operation": index, "machine": operation.machine, "start": start, "end": end}
            )
            machines[operation.machine] = ready = end
        lateness += max(0, ready - job.due)
    return {"operations": operations, "makespan": max(machines.values()), "tardiness": lateness}


def schedule(
    mission: Mission,
    checkpoint: Callable[[], None],
    max_evaluations: int,
    remembered: list[str] | None = None,
) -> dict[str, Any]:
    """Optimize job order against measured makespan and tardiness."""
    work = mission.work
    assert isinstance(work, Schedule)

    def order(genome: list[float]) -> list[int]:
        return sorted(range(len(work.jobs)), key=lambda i: (-genome[i], work.jobs[i].id))

    def evaluate(genome: list[float]) -> tuple[float, ...]:
        result = build_schedule(work, order(genome))
        return float(result["makespan"]), float(result["tardiness"])

    baseline = build_schedule(work, list(range(len(work.jobs))))
    pop, calls = _search(mission, len(work.jobs), evaluate, checkpoint, max_evaluations)
    candidates = [(list(range(len(work.jobs))), baseline)]
    candidates += [(order(ind.genome), build_schedule(work, order(ind.genome))) for ind in pop]
    if remembered:
        priority = {ident: i for i, ident in enumerate(remembered)}
        remembered_order = sorted(range(len(work.jobs)), key=lambda i: priority.get(work.jobs[i].id, len(priority) + i))
        candidates.append((remembered_order, build_schedule(work, remembered_order)))
    selected, best = min(candidates, key=lambda item: (item[1]["makespan"], item[1]["tardiness"], item[0]))
    return {
        **best,
        "method": "MATS NSGA-II over feasible job permutations",
        "order": [work.jobs[i].id for i in selected],
        "baseline_makespan": baseline["makespan"],
        "improvement": baseline["makespan"] - best["makespan"],
        "evaluations": calls,
        "unit": work.unit,
        "limits": "Scenario optimization; machines are not actuated and global optimality is not claimed.",
    }


def _predict(history: list[float], policy: str, season: int, horizon: int = 1) -> list[float]:
    if policy == "last":
        return [history[-1]] * horizon
    if policy == "mean":
        return [sum(history) / len(history)] * horizon
    if policy == "drift":
        slope = (history[-1] - history[0]) / max(1, len(history) - 1)
        return [history[-1] + slope * step for step in range(1, horizon + 1)]
    if policy == "seasonal":
        return [history[-season + i % season] for i in range(horizon)]
    raise ValueError("unknown forecasting policy")


def _walk_forward(series: list[float], start: int, policy: str, season: int) -> list[float]:
    return [_predict(series[:i], policy, season)[0] for i in range(start, len(series))]


def forecast(mission: Mission) -> dict[str, Any]:
    """Select on training data, then measure a separate temporal holdout."""
    work = mission.work
    assert isinstance(work, Forecast)
    split = len(work.observations) - work.holdout
    train = work.observations[:split]
    validation_start = max(2 * work.season, len(train) // 2)
    if validation_start >= len(train):
        validation_start = len(train) - 1

    def mae(expected: list[float], predicted: list[float]) -> float:
        return sum(abs(a - b) for a, b in zip(expected, predicted)) / len(expected)

    scores = {
        policy: mae(train[validation_start:], _walk_forward(train, validation_start, policy, work.season))
        for policy in ("last", "mean", "drift", "seasonal")
    }
    chosen = min(scores, key=lambda policy: (scores[policy], policy))
    predictions = _walk_forward(work.observations, split, chosen, work.season)
    baseline = _walk_forward(work.observations, split, "last", work.season)
    actual = work.observations[split:]
    error, base_error = mae(actual, predictions), mae(actual, baseline)
    return {
        "method": "training-only model selection and rolling one-step holdout evaluation",
        "policy": chosen,
        "training_scores": scores,
        "train_count": split,
        "holdout_actual": actual,
        "holdout_predictions": predictions,
        "holdout_mae": error,
        "baseline_mae": base_error,
        "improvement": base_error - error,
        "forecast": _predict(work.observations, chosen, work.season, work.horizon),
        "unit": work.unit,
        "limits": "Historical holdout error does not guarantee future accuracy; no confidence interval is inferred.",
    }


def coding(mission: Mission, code: str) -> dict[str, Any]:
    """Measure a code candidate using immutable, host-scored held-out cases."""
    import ast
    from alpha_factory_v1.core.eval.fitness import evaluate_agent

    assert isinstance(mission.work, Coding)
    ast.parse(code)
    cases = [case.model_dump() for case in mission.work.heldout]
    measured = evaluate_agent(code, cases)
    return {
        "method": "isolated Python execution with host-side held-out scoring",
        "code": code,
        "code_hash": digest(code),
        "benchmark_hash": digest(cases),
        "case_count": len(cases),
        "accuracy": measured["accuracy"],
        "execution_ms": measured["latency_ms"],
        "limits": "Performance on the supplied cases only; generated code is never automatically deployed or merged.",
    }


def verify_result(mission: Mission, result: dict[str, Any]) -> dict[str, Any]:
    """Recompute constraints and arithmetic from immutable input and output."""
    work = mission.work
    checks: list[str] = []
    if isinstance(work, Research):
        sources = {source.id: source.text for source in work.sources}
        findings = result.get("findings", [])
        if not findings or len(findings) > 20:
            raise ValueError("research requires 1–20 findings")
        for item in findings:
            quote = item.get("quote")
            if not isinstance(quote, str) or not quote or quote not in sources.get(item.get("source_id"), ""):
                raise ValueError("finding quote is not present in its cited source")
            if not isinstance(item.get("claim"), str) or not 1 <= len(item["claim"]) <= 3000:
                raise ValueError("invalid finding claim")
        checks += ["every quotation occurs in its cited input", "source identifiers are valid"]
    elif isinstance(work, Allocation):
        selected = result["selected"]
        items = {item.id: item for item in work.items}
        if len(selected) != len(set(selected)) or any(ident not in items for ident in selected):
            raise ValueError("allocation has duplicate or unknown items")
        totals = {key: sum(getattr(items[ident], key) for ident in selected) for key in ("cost", "value", "risk")}
        if totals["cost"] > work.budget or totals["risk"] > work.max_risk:
            raise ValueError("allocation exceeds a constraint")
        if any(result[key] != val for key, val in totals.items()):
            raise ValueError("allocation totals are incorrect")
        checks += ["budget and risk limits", "unique input items", "independent integer totals"]
    elif isinstance(work, Schedule):
        ops = {(op["job"], op["operation"]): op for op in result["operations"]}
        expected_count = sum(len(job.operations) for job in work.jobs)
        if len(ops) != expected_count or len(result["operations"]) != expected_count:
            raise ValueError("missing or duplicate operations")
        timelines: dict[str, list[tuple[int, int]]] = {}
        tardiness = 0
        for job in work.jobs:
            end = 0
            for i, source in enumerate(job.operations):
                op = ops[(job.id, i)]
                if any(not isinstance(op[k], int) or isinstance(op[k], bool) for k in ("start", "end")):
                    raise ValueError("schedule times must be integers")
                if op["machine"] != source.machine or op["start"] < end or op["end"] - op["start"] != source.duration:
                    raise ValueError("schedule violates precedence, duration or machine assignment")
                end = op["end"]
                timelines.setdefault(source.machine, []).append((op["start"], end))
            tardiness += max(0, end - job.due)
        for intervals in timelines.values():
            ordered = sorted(intervals)
            if any(a[1] > b[0] for a, b in zip(ordered, ordered[1:])):
                raise ValueError("machine operations overlap")
        if max(op["end"] for op in ops.values()) != result["makespan"] or tardiness != result["tardiness"]:
            raise ValueError("schedule metrics are incorrect")
        checks += ["all operations exactly once", "machine exclusivity", "job precedence", "duration and makespan"]
    elif isinstance(work, Coding):
        if digest(result["code"]) != result["code_hash"]:
            raise ValueError("code artifact hash mismatch")
        if work.candidate and work.candidate != result["code"]:
            raise ValueError("evaluated code differs from supplied candidate")
        replay = coding(mission, result["code"])
        if any(replay[key] != result[key] for key in ("code_hash", "benchmark_hash", "case_count", "accuracy")):
            raise ValueError("code benchmark did not reproduce")
        if result["accuracy"] != 1.0:
            raise ValueError("candidate did not pass every supplied held-out case")
        checks += [
            "held-out answers never mounted into sandbox",
            "host-scored output equality",
            "independent execution replay",
        ]
    else:
        # Replay the entire temporal split; selection cannot inspect the holdout.
        expected = forecast(mission)
        if digest(expected) != digest(result):
            raise ValueError("forecast cannot be reproduced from its temporal split")
        checks += ["training/holdout separation", "walk-forward predictions and error reproduced"]
    return {
        "passed": True,
        "checks": checks,
        "result_hash": digest(result),
        "semantic_review_required": isinstance(work, Research),
    }
