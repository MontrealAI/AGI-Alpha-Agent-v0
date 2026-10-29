# SPDX-License-Identifier: Apache-2.0
"""Turn sealed transfer outcomes into conservative constraints for future reuse.

Plans use exposed historical work. They neither execute a candidate nor qualify
projected benefit, future cases, business profit or operating authority.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

from . import verifier

SCHEMA = "agialpha/retention-plan/v1"


def _nonnegative_integer(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative measured integer cost required")
    return value


def eligible_horizons(
    candidate: tuple[Fraction, Fraction],
    controls: dict[str, tuple[Fraction, Fraction]],
    reduction: Fraction,
) -> dict[str, int | None]:
    """Intersect exact linear cost inequalities against EVERY control."""
    if not controls or not 0 < reduction < 1 or any(x < 0 for pair in (candidate, *controls.values()) for x in pair):
        raise ValueError("nonnegative costs, controls and a strict improvement threshold required")
    lower, upper = 1, None
    ratio = 1 - reduction
    for fixed, variable in controls.values():
        if fixed == 0 and variable == 0:
            return {"minimum": None, "maximum": None}
        numerator = candidate[0] - ratio * fixed
        denominator = ratio * variable - candidate[1]
        if denominator > 0:
            required = numerator / denominator
            lower = max(lower, -(-required.numerator // required.denominator))
        elif denominator < 0:
            allowed = numerator / denominator
            limit = allowed.numerator // allowed.denominator
            upper = limit if upper is None else min(upper, limit)
        elif numerator > 0:
            return {"minimum": None, "maximum": None}
    if upper is not None and lower > upper:
        return {"minimum": None, "maximum": None}
    return {"minimum": lower, "maximum": upper}


def _historical_models(directory: Path) -> tuple[dict[str, Any], dict[str, tuple[Fraction, Fraction]]]:
    """Reconstruct cost facts; do not accept a favorable edited summary."""
    protocol = verifier.read(directory / "protocol.json")
    summary = verifier.read(directory / "summary.json")
    receipt = verifier.read(directory / "verification.json")
    freeze = verifier.read(directory / "freeze.json")
    if (
        verifier.hash_value(protocol) != freeze["protocol_hash"]
        or verifier.hash_value(verifier.read(directory / "cost-policy.json")) != freeze["cost_policy_hash"]
        or hashlib.sha256((directory / "freeze.json").read_bytes()).hexdigest() != summary["freeze_sha256"]
    ):
        raise ValueError("historical protocol, cost policy or freeze identity differs")
    if (
        receipt != summary["audit"]
        or receipt.get("freeze_verified") is not True
        or receipt.get("rejected")
        or receipt["accepted"] != receipt["planned"]
        or receipt["observed"] != receipt["planned"]
    ):
        raise ValueError("a complete historically accepted panel is required")
    for name, field in (("observations.jsonl", "observations_sha256"), ("costs.jsonl", "costs_sha256")):
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != receipt[field]:
            raise ValueError("historical verifier receipt does not bind these outputs and costs")
    arms = protocol["arms"]
    if len(set(arms)) != len(arms) or "retained" not in arms or set(arms) != set(summary["arms"]):
        raise ValueError("the complete declared comparator set is required")
    task_ids = {verifier.hash_value(task) for task in verifier.read(directory / "tasks.json")}
    count, repeats = len(task_ids), protocol["repeats"]
    if count != protocol["cases_per_regime"] * len(protocol["regimes"]) or type(repeats) is not int or repeats < 1:
        raise ValueError("historical task denominator differs")
    grouped: dict[str, dict[str, list[int]]] = {arm: {} for arm in arms}
    seen: set[tuple[str, str, int]] = set()
    for line in (directory / "costs.jsonl").read_text().splitlines():
        event = json.loads(line, object_pairs_hook=verifier._pairs)
        identity = (event["task_hash"], event["arm"], event["repeat"])
        if (
            identity in seen
            or identity[0] not in task_ids
            or identity[1] not in grouped
            or type(identity[2]) is not int
            or not 0 <= identity[2] < repeats
        ):
            raise ValueError("missing, duplicate or unplanned historical cost identity")
        seen.add(identity)
        grouped[identity[1]].setdefault(identity[0], []).append(_nonnegative_integer(event["cpu_ns"]))
    if len(seen) != count * repeats * len(arms):
        raise ValueError("historical cost denominator differs")
    common = _nonnegative_integer(receipt["process_cpu_ns"]) - sum(
        _nonnegative_integer(value) for value in receipt["arm_check_cpu_ns"].values()
    )
    if common < 0:
        raise ValueError("historical verification accounting is inconsistent")
    lifecycle = verifier.read(directory / "lifecycle.json")
    if verifier.hash_value(lifecycle) != verifier.read(directory / "candidate-freeze.json")["lifecycle_hash"]:
        raise ValueError("historical lifecycle accounting changed after the candidate freeze")
    models = {}
    for arm, tasks in grouped.items():
        deployment = sum(int(statistics.median(values)) for values in tasks.values())
        audit = _nonnegative_integer(receipt["arm_check_cpu_ns"][arm]) // repeats
        setup = _nonnegative_integer(lifecycle["setup_cpu_ns"][arm])
        fixed = setup + (0 if arm.startswith("highs") else common)
        actual = summary["arms"][arm]
        if (
            deployment != actual["deployment_median_cpu_ns"]
            or setup != actual["setup_cpu_ns"]
            or fixed + deployment + audit != actual["lifecycle_cpu_ns"]
        ):
            raise ValueError("summary understates historical setup, checking or deployment cost")
        models[arm] = (Fraction(fixed), Fraction(deployment + audit, count))
    return {
        "protocol": protocol,
        "summary": summary,
        "receipt": receipt,
        "tasks": count,
        "unallocated_verification_cpu_ns": common,
    }, models


def _projection(
    candidate: tuple[Fraction, Fraction],
    controls: dict[str, tuple[Fraction, Fraction]],
    reduction: Fraction,
    tasks: int,
) -> dict[str, Any]:
    costs = {arm: fixed + tasks * variable for arm, (fixed, variable) in controls.items()}
    incumbent = min(costs, key=lambda arm: (costs[arm], arm))
    candidate_cost = candidate[0] + tasks * candidate[1]
    return {
        "eligible_task_interval": eligible_horizons(candidate, controls, reduction),
        "incumbent": incumbent,
        "projected_retained_cpu_ns": str(candidate_cost),
        "projected_incumbent_cpu_ns": str(costs[incumbent]),
        "meets_frozen_cpu_threshold": costs[incumbent] > 0 and candidate_cost <= (1 - reduction) * costs[incumbent],
    }


def plan(directory: Path, expected_seal: str, future_tasks: int) -> dict[str, Any]:
    """Retain an adverse lesson and a bounded projection, without promoting it."""
    from .operator import check_seal

    if type(future_tasks) is not int or not 1 <= future_tasks <= 1_000_000:
        raise ValueError("future task count must be an integer from 1 to 1000000")
    started, wall = time.process_time_ns(), time.monotonic_ns()
    check_seal(directory, expected_seal)
    data, models = _historical_models(directory)
    candidate = models["retained"]
    controls = {arm: model for arm, model in models.items() if arm != "retained"}
    reduction = Fraction(data["protocol"]["minimum_lifecycle_cpu_reduction"])
    planning_cpu = time.process_time_ns() - started
    candidate = (candidate[0] + planning_cpu, candidate[1])
    fixed_scenario = _projection(candidate, controls, reduction, future_tasks)
    recurring_models = {}
    for arm, (fixed, variable) in models.items():
        overhead = 0 if arm.startswith("highs") else data["unallocated_verification_cpu_ns"]
        recurring_models[arm] = (fixed - overhead, variable + Fraction(overhead, data["tasks"]))
    recurring_candidate = recurring_models["retained"]
    recurring_candidate = (recurring_candidate[0] + planning_cpu, recurring_candidate[1])
    recurring_scenario = _projection(
        recurring_candidate,
        {arm: pair for arm, pair in recurring_models.items() if arm != "retained"},
        reduction,
        future_tasks,
    )
    unresolved = {
        arm: record["unresolved_costs"] for arm, record in data["summary"]["arms"].items() if record["unresolved_costs"]
    }
    if not data["summary"]["measured_cpu_advantage"]:
        lesson = (
            "Observed deployment savings did not repay learning, construction and verification over the tested horizon."
        )
    else:
        lesson = "The observed CPU advantage is scoped to this exposed panel; new work still requires fresh comparison."
    if not fixed_scenario["meets_frozen_cpu_threshold"]:
        decision = "KEEP_INCUMBENT"
    elif not recurring_scenario["meets_frozen_cpu_threshold"]:
        decision = "MEASURE_VERIFICATION_SCALING_FIRST"
    else:
        decision = "FRESH_EVALUATION_REQUIRED"
    return {
        "schema": SCHEMA,
        "source_evidence_seal_sha256": expected_seal,
        "planning_sources": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (Path(__file__), Path(__file__).with_name("operator.py"))
        },
        "source_code_freeze_sha256": hashlib.sha256((directory / "freeze.json").read_bytes()).hexdigest(),
        "historical_tasks": data["tasks"],
        "historical_result": data["summary"]["overall_demonstration"],
        "requested_future_tasks": future_tasks,
        "decision": decision,
        "incumbent": recurring_scenario["incumbent"],
        "retained_lesson": lesson,
        "constraint": "Reuse must repay learning, preparation, unsuccessful transfer, verification and planning costs.",
        "cpu_only_projection_scenarios": {
            "unallocated_verification_fixed": fixed_scenario,
            "unallocated_verification_recurring": recurring_scenario,
        },
        "unallocated_verification_cpu_ns": data["unallocated_verification_cpu_ns"],
        "frozen_minimum_cpu_reduction": str(reduction),
        "unresolved_historical_costs": unresolved,
        "complete_cost_advantage": None,
        "future_benefit_established": False,
        "authority_granted": False,
        "production_default_changed": False,
        "confirmation": False,
        "planning_cpu_ns_charged_in_projection": planning_cpu,
        "analysis_wall_ns": time.monotonic_ns() - wall,
        "limits": [
            "stationary workload/cost projection from one exposed fixed-route family",
            "fixed versus recurring split of common verification cost is unmeasured; scenarios are sensitivity assumptions",
            "historical verifier receipt is bound by the trusted seal, not requalification of changed code",
            "unknown monetary and future operating costs remain unknown; no automatic reuse or profit claim",
            "source cases are exposed development experience and cannot count again as fresh confirmation",
            "projection is a reason to test a new frozen candidate, not evidence that the test will pass",
        ],
    }
