# SPDX-License-Identifier: Apache-2.0
"""Bounded, reproducible Monte Carlo search over supplied workflow designs."""
from __future__ import annotations

import hashlib
from itertools import product
import json
import math
from pathlib import Path
from typing import Any, cast

from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import (
    canonical,
    digest,
    identifier,
    integer,
    keys,
    parse,
    read_json as read_json,
    text,
)
from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import literal

SCHEMA = "agialpha.mats.scenario.v1"
REPORT_SCHEMA = "agialpha.mats.run.v1"
Q = 1_000_000
LOG_Q = json.loads(Path(__file__).with_name("uct_log.json").read_text(encoding="utf-8"))
SCOPE = (
    "Search optimizes a supplied, synthetic workflow model, not real agents or financial returns. "
    "The exhaustive oracle audits the training model separately and never selects the candidate. "
    "Held-out evaluation does not change the search. Policies remain unapproved and review jobs unsubmitted."
)


class Random:
    """Private xorshift32 stream; never mutate process-global randomness."""

    def __init__(self, seed: int) -> None:
        self.state = seed or 1

    def next(self) -> int:
        value = self.state
        value ^= (value << 13) & 0xFFFFFFFF
        value ^= value >> 17
        value ^= (value << 5) & 0xFFFFFFFF
        self.state = value & 0xFFFFFFFF
        return self.state


def validate(raw: Any) -> dict[str, Any]:
    keys(
        raw,
        {"schema", "id", "title", "note", "seed", "search", "objective", "gates", "resources", "stages"},
        "Scenario",
    )
    if raw["schema"] != SCHEMA:
        raise ValueError("Unsupported MATS scenario schema")
    identifier(raw["id"])
    text(raw["title"], "Title", 160)
    text(raw["note"], "Assumptions", 600)
    integer(raw["seed"], 1, 4294967295, "Seed")
    limits = {
        "iterations": (1, 240),
        "depth": (1, 6),
        "explorationBps": (0, 40000),
        "trainingSamples": (4, 64),
        "evaluationSamples": (20, 128),
    }
    keys(raw["search"], {*limits, "auditOracle"}, "Search")
    for field, (low, high) in limits.items():
        integer(raw["search"][field], low, high, field)
    if type(raw["search"]["auditOracle"]) is not bool:
        raise ValueError("auditOracle must be true or false")
    for section, bounds in (
        (
            "objective",
            {"value": (0, 10000), "costWeight": (0, 100), "timeWeight": (0, 100), "escapePenalty": (0, 100000)},
        ),
        (
            "gates",
            {
                "minGain": (0, 10000),
                "maxEscapeBps": (0, 10000),
                "deadline": (1, 10000),
                "maxMeanCost": (0, 10000),
                "maxReviewMinutes": (0, 1440),
                "bountyTokens": (1, 1000000),
            },
        ),
    ):
        keys(raw[section], set(bounds), section)
        for field, (low, high) in bounds.items():
            integer(raw[section][field], low, high, field)
    resources = raw["resources"]
    if not isinstance(resources, list) or not 1 <= len(resources) <= 4:
        raise ValueError("Provide 1–4 resource pools")
    ids: set[str] = set()
    for resource in resources:
        keys(resource, {"id", "label", "capacity"}, "Resource")
        identifier(resource["id"])
        text(resource["label"], "Resource label", 80)
        integer(resource["capacity"], 1, 4, "Resource capacity")
        if resource["id"] in ids:
            raise ValueError("Duplicate resource ID")
        ids.add(resource["id"])
    stages = raw["stages"]
    if not isinstance(stages, list) or not 2 <= len(stages) <= 6:
        raise ValueError("Provide 2–6 stages in topological order")
    seen: set[str] = set()
    space = 1
    for index, stage in enumerate(stages):
        keys(stage, {"id", "label", "metaAgent", "resource", "depends", "baseline", "choices"}, "Stage")
        identifier(stage["id"])
        if stage["id"] in seen:
            raise ValueError("Duplicate stage ID")
        seen.add(stage["id"])
        text(stage["label"], "Stage label", 80)
        text(stage["metaAgent"], "Meta-agent label", 80)
        identifier(stage["resource"])
        if stage["resource"] not in ids:
            raise ValueError("Unknown stage resource")
        depends = stage["depends"]
        if not isinstance(depends, list) or len(depends) > 6:
            raise ValueError("Dependencies must be a bounded list of earlier stage indices")
        for dependency in depends:
            integer(dependency, 0, index - 1, "Dependency index")
        if len(set(depends)) != len(depends):
            raise ValueError("Duplicate dependency")
        choices = stage["choices"]
        if not isinstance(choices, list) or not 2 <= len(choices) <= 4:
            raise ValueError("Each stage needs 2–4 executable model choices")
        integer(stage["baseline"], 0, len(choices) - 1, "Baseline choice")
        option_ids: set[str] = set()
        for choice in choices:
            keys(choice, {"id", "label", "minutes", "cost", "defectBps", "detectBps", "reviewMinutes"}, "Choice")
            identifier(choice["id"])
            if choice["id"] in option_ids:
                raise ValueError("Duplicate choice ID")
            option_ids.add(choice["id"])
            text(choice["label"], "Choice label", 80)
            for field, low, high in (
                ("minutes", 1, 240),
                ("cost", 0, 1000),
                ("defectBps", 0, 10000),
                ("detectBps", 0, 10000),
                ("reviewMinutes", 0, 240),
            ):
                integer(choice[field], low, high, field)
        space *= len(choices)
    if space > 1024:
        raise ValueError("The bounded laboratory supports at most 1,024 complete designs")
    return cast(dict[str, Any], parse(canonical(raw)))


def workloads(source: dict[str, Any], count: int, seed: int) -> list[list[list[int]]]:
    stream = Random(seed)
    return [
        [[80 + stream.next() % 41, stream.next() % 10000, stream.next() % 10000] for _ in source["stages"]]
        for _ in range(count)
    ]


def simulate(source: dict[str, Any], policy: list[int], rolls: list[list[int]]) -> dict[str, Any]:
    """Schedule the DAG with resource contention, fault propagation and detected rework."""
    slots = {pool["id"]: [0] * pool["capacity"] for pool in source["resources"]}
    rows: list[dict[str, Any]] = []
    for index, stage in enumerate(source["stages"]):
        choice = stage["choices"][policy[index]]
        demand, defect, detection = rolls[index]
        fault = any(rows[parent]["fault"] for parent in stage["depends"]) or defect < choice["defectBps"]
        rework = int(fault and detection < choice["detectBps"])
        duration = (choice["minutes"] * demand + 99) // 100 * (1 + rework)
        lanes = slots[stage["resource"]]
        lane = min(range(len(lanes)), key=lambda item: lanes[item])
        start = max([lanes[lane], *[rows[parent]["end"] for parent in stage["depends"]]])
        end = start + duration
        lanes[lane] = end
        rows.append(
            {
                "stage": index,
                "choice": policy[index],
                "lane": lane,
                "start": start,
                "end": end,
                "cost": choice["cost"] * (1 + rework),
                "rework": rework,
                "fault": bool(fault and not rework),
                "reviewMinutes": choice["reviewMinutes"] * (1 + rework),
            }
        )
    predecessors = {parent for stage in source["stages"] for parent in stage["depends"]}
    escaped = int(any(row["fault"] for index, row in enumerate(rows) if index not in predecessors))
    cost = sum(row["cost"] for row in rows)
    makespan = max(row["end"] for row in rows)
    objective = source["objective"]
    return {
        "utility": objective["value"]
        - cost * objective["costWeight"]
        - makespan * objective["timeWeight"]
        - escaped * objective["escapePenalty"],
        "cost": cost,
        "makespan": makespan,
        "escaped": escaped,
        "rework": sum(row["rework"] for row in rows),
        "reviewMinutes": sum(row["reviewMinutes"] for row in rows),
        "stages": rows,
    }


def measure(
    source: dict[str, Any], policy: list[int], samples: list[list[list[int]]], details: bool = False
) -> dict[str, Any]:
    episodes = [simulate(source, policy, row) for row in samples]
    totals = {
        key: sum(row[key] for row in episodes)
        for key in ("utility", "cost", "makespan", "escaped", "rework", "reviewMinutes")
    }
    result = {
        "totals": totals,
        "p95Minutes": sorted(row["makespan"] for row in episodes)[(95 * len(episodes) + 99) // 100 - 1],
    }
    if details:
        result["episodes"] = episodes
    return result


def moves(source: dict[str, Any], policy: list[int], forbidden: set[tuple[int, ...]]) -> list[dict[str, int]]:
    result = []
    for index, stage in enumerate(source["stages"]):
        for option in range(len(stage["choices"])):
            changed = list(policy)
            changed[index] = option
            if option != policy[index] and tuple(changed) not in forbidden:
                result.append({"stage": index, "from": policy[index], "to": option})
    return result


def rewritten(policy: list[int], move: dict[str, int]) -> list[int]:
    result = list(policy)
    result[move["stage"]] = move["to"]
    return result


def uct(total: int, visits: int, parent_visits: int, exploration: int) -> int:
    """Fixed-point UCT: a shared log table and integer square root fix tie behavior."""
    if visits <= 0:
        return 10**15
    return total // visits + exploration * math.isqrt(LOG_Q[max(1, parent_visits)] * Q // visits) // 10000


def search(source: dict[str, Any]) -> dict[str, Any]:
    spec = source["search"]
    baseline = [stage["baseline"] for stage in source["stages"]]
    samples = workloads(source, spec["trainingSamples"], source["seed"] ^ 0x9E3779B9)
    stream = Random(source["seed"])
    cache: dict[tuple[int, ...], dict[str, Any]] = {}

    def score(policy: list[int]) -> dict[str, Any]:
        key = tuple(policy)
        if key not in cache:
            cache[key] = measure(source, policy, samples)
        return cache[key]

    upper_cost = sum(max(choice["cost"] for choice in stage["choices"]) * 2 for stage in source["stages"])
    upper_time = sum(
        (max(choice["minutes"] for choice in stage["choices"]) * 120 + 99) // 100 * 2 for stage in source["stages"]
    )
    objective = source["objective"]
    span = upper_cost * objective["costWeight"] + upper_time * objective["timeWeight"] + objective["escapePenalty"] + 1
    floor = objective["value"] - span
    nodes: list[dict[str, Any]] = []

    def add(policy: list[int], parent: int | None, move: dict[str, int] | None, path: list[int]) -> int:
        depth = len(path)
        forbidden = {tuple(nodes[index]["policy"]) for index in path} | {tuple(policy)}
        node: dict[str, Any] = {
            "id": len(nodes),
            "parent": parent,
            "depth": depth,
            "policy": list(policy),
            "rewrite": move,
            "children": [],
            "visits": 0,
            "totalQ": 0,
            "untried": moves(source, policy, forbidden) if depth < spec["depth"] else [],
        }
        nodes.append(node)
        if parent is not None:
            nodes[parent]["children"].append(node["id"])
        return int(node["id"])

    add(baseline, None, None, [])
    best = list(baseline)
    best_score = score(best)["totals"]["utility"]
    best_iteration = 0
    best_path: list[dict[str, int]] = []
    trace = []
    for iteration in range(spec["iterations"]):
        path = [0]
        expanded: int | None = None
        while nodes[path[-1]]["depth"] < spec["depth"]:
            node = nodes[path[-1]]
            if node["untried"]:
                move = node["untried"].pop(stream.next() % len(node["untried"]))
                expanded = add(rewritten(node["policy"], move), node["id"], move, path)
                path.append(expanded)
                break
            if not node["children"]:
                break
            selected = max(
                node["children"],
                key=lambda index: uct(
                    nodes[index]["totalQ"], nodes[index]["visits"], node["visits"], spec["explorationBps"]
                ),
            )
            path.append(selected)
        policy = list(nodes[path[-1]]["policy"])
        forbidden = {tuple(nodes[index]["policy"]) for index in path}
        rollout = []
        for _ in range(nodes[path[-1]]["depth"], spec["depth"]):
            options = moves(source, policy, forbidden)
            if not options:
                break
            move = options[stream.next() % len(options)]
            rollout.append(move)
            policy = rewritten(policy, move)
            forbidden.add(tuple(policy))
        measured = score(policy)
        utility = measured["totals"]["utility"]
        value_q = (utility - floor * spec["trainingSamples"]) * Q // (span * spec["trainingSamples"])
        for index in path:
            nodes[index]["visits"] += 1
            nodes[index]["totalQ"] += value_q
        if utility > best_score or (utility == best_score and tuple(policy) < tuple(best)):
            best, best_score, best_iteration = list(policy), utility, iteration + 1
            best_path = [nodes[index]["rewrite"] for index in path[1:]] + rollout
        trace.append(
            {
                "iteration": iteration + 1,
                "path": path,
                "expanded": expanded,
                "rollout": rollout,
                "policy": policy,
                "utilityTotal": utility,
                "valueQ": value_q,
                "bestUtilityTotal": best_score,
                "bestPolicy": list(best),
            }
        )
    exported_nodes = [
        {**{key: value for key, value in node.items() if key != "untried"}, "untriedCount": len(node["untried"])}
        for node in nodes
    ]
    return {
        "nodes": exported_nodes,
        "trace": trace,
        "candidate": best,
        "candidateTraining": score(best),
        "baselineTraining": score(baseline),
        "candidateIteration": best_iteration,
        "candidateRewrites": best_path,
        "uniqueEvaluations": len(cache),
        "simulationEpisodes": len(cache) * spec["trainingSamples"],
        "normalization": {"floor": floor, "span": span, "scale": Q},
    }


def evaluate(raw: Any) -> dict[str, Any]:
    source = validate(raw)
    spec, gates = source["search"], source["gates"]
    result = search(source)
    baseline = [stage["baseline"] for stage in source["stages"]]
    samples = workloads(source, spec["evaluationSamples"], source["seed"] ^ 0xA341316C)
    evaluation = {
        name: measure(source, policy, samples, True)
        for name, policy in (("baseline", baseline), ("candidate", result["candidate"]))
    }
    totals = evaluation["candidate"]["totals"]
    gain = totals["utility"] - evaluation["baseline"]["totals"]["utility"]
    count = spec["evaluationSamples"]
    checks = [
        {
            "id": "gain",
            "label": "Held-out utility gain",
            "observed": gain,
            "limit": gates["minGain"] * count,
            "comparison": ">=",
            "passed": gain >= gates["minGain"] * count,
        },
        {
            "id": "quality",
            "label": "Escaped-defect ceiling",
            "observed": totals["escaped"] * 10000,
            "limit": gates["maxEscapeBps"] * count,
            "comparison": "<=",
            "passed": totals["escaped"] * 10000 <= gates["maxEscapeBps"] * count,
        },
        {
            "id": "deadline",
            "label": "95th-percentile delivery time",
            "observed": evaluation["candidate"]["p95Minutes"],
            "limit": gates["deadline"],
            "comparison": "<=",
            "passed": evaluation["candidate"]["p95Minutes"] <= gates["deadline"],
        },
        {
            "id": "cost",
            "label": "Mean resource-cost ceiling",
            "observed": totals["cost"],
            "limit": gates["maxMeanCost"] * count,
            "comparison": "<=",
            "passed": totals["cost"] <= gates["maxMeanCost"] * count,
        },
        {
            "id": "review",
            "label": "Mean reviewer-effort ceiling",
            "observed": totals["reviewMinutes"],
            "limit": gates["maxReviewMinutes"] * count,
            "comparison": "<=",
            "passed": totals["reviewMinutes"] <= gates["maxReviewMinutes"] * count,
        },
    ]
    oracle: dict[str, Any] = {"enabled": spec["auditOracle"], "evaluations": 0}
    space = math.prod(len(stage["choices"]) for stage in source["stages"])
    if spec["auditOracle"]:
        training = workloads(source, spec["trainingSamples"], source["seed"] ^ 0x9E3779B9)
        best_score: int | None = None
        best_policy = []
        for choices in product(*(range(len(stage["choices"])) for stage in source["stages"])):
            total = measure(source, list(choices), training)["totals"]["utility"]
            if best_score is None or total > best_score:
                best_score, best_policy = total, list(choices)
        oracle.update(
            evaluations=space,
            simulationEpisodes=space * spec["trainingSamples"],
            policy=best_policy,
            utilityTotal=best_score,
            gapTotal=best_score - result["candidateTraining"]["totals"]["utility"],
        )
    input_hash = digest(source)
    proposal = {
        "schema": "agialpha.mats.policy-proposal.v1",
        "inputSha256": input_hash,
        "activePolicy": baseline,
        "candidatePolicy": result["candidate"],
        "stageIds": [stage["id"] for stage in source["stages"]],
        "state": "UNAPPROVED",
    }
    result.update(
        evaluation=evaluation,
        gainTotal=gain,
        gates=checks,
        oracle=oracle,
        designSpace=space,
        proposal=proposal,
        status="REVIEW_REQUIRED" if all(check["passed"] for check in checks) else "HOLD_BASELINE",
        scope=SCOPE,
        inputSha256=input_hash,
        jobs=[
            {
                "goal": f"Independently reproduce MATS {source['id']}; input SHA-256: {input_hash}. Review the search, resource model, defect assumptions and candidate workflow.",
                "successMetric": "Recompute every selection, rewrite, rollout and review gate; validate with fresh workloads and representative real measurements. Approve or reject with evidence; a checksum is not validator approval.",
                "bounty": str(gates["bountyTokens"] * 10**18),
                "duration": 604800,
                "priceWeight": 5000,
            }
        ],
    )
    report = {"schema": REPORT_SCHEMA, "input": source, "result": result}
    return {**report, "sha256": digest(report)}


def verify(report: Any) -> dict[str, Any]:
    keys(report, {"schema", "input", "result", "sha256"}, "Run")
    expected = evaluate(report["input"])
    if canonical(report) != canonical(expected):
        raise ValueError("Run differs from recomputation; imported trees, policies and gates are not trusted")
    return expected


def brief(report: dict[str, Any]) -> str:
    source, result = report["input"], report["result"]
    lines = [
        f"# {literal(source['title'])}",
        "",
        result["status"],
        "",
        literal(source["note"]),
        "",
        f"Search: {source['search']['iterations']} iterations, {result['uniqueEvaluations']} unique designs, {result['simulationEpisodes']} simulated training workloads.",
        f"Held-out utility gain: {result['gainTotal']} across {source['search']['evaluationSamples']} paired workloads.",
        f"Oracle: {result['oracle']['evaluations']} additional design evaluations; never used to select the candidate.",
        "",
        "| Review gate | Result | Exact comparison |",
        "|---|---|---|",
    ]
    lines += [
        f"| {gate['label']} | {'PASS' if gate['passed'] else 'HOLD'} | {gate['observed']} {gate['comparison']} {gate['limit']} |"
        for gate in result["gates"]
    ]
    lines += [
        "",
        "The active workflow remains the baseline. Candidate indices refer to choices in scenario order.",
        "Selecting a seed after inspecting evaluation results invalidates an independent test.",
        "",
        SCOPE,
        "",
        f"Run SHA-256: {report['sha256']}",
        "",
    ]
    return "\n".join(lines)


def artifacts(report: dict[str, Any]) -> dict[str, bytes]:
    report = verify(report)
    values = {
        "scenario.json": canonical(report["input"]) + b"\n",
        "run.json": canonical(report) + b"\n",
        "policy-proposal.json": canonical(report["result"]["proposal"]) + b"\n",
        "jobs.json": canonical(report["result"]["jobs"]) + b"\n",
        "review.md": brief(report).encode("utf-8"),
    }
    values["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(values.items())
    ).encode()
    return values


def write_bundle(report: dict[str, Any], root: Path) -> Path:
    values = artifacts(report)
    root.mkdir(parents=True, exist_ok=True)
    target = root / str(report["sha256"])
    try:
        target.mkdir()
    except FileExistsError:
        if target.is_symlink() or not target.is_dir() or {path.name for path in target.iterdir()} != set(values):
            raise ValueError("Existing run is incomplete or altered; use a new output directory") from None
        for name, data in values.items():
            path = target / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != data:
                raise ValueError("Existing run differs; use a new output directory")
        return target
    for name, data in values.items():
        with (target / name).open("xb") as stream:
            stream.write(data)
    return target
