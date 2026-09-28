# SPDX-License-Identifier: Apache-2.0
"""Bounded, reproducible program-induction curriculum with independent review.

Programs are lists of seven integer operators interpreted as data. No Python,
provider, tool or external transaction is executed by this laboratory.
"""
from __future__ import annotations

import hashlib
from itertools import product
from pathlib import Path
from typing import Any, cast

from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import (
    canonical,
    digest,
    identifier,
    integer,
    keys,
    literal,
    parse,
    read_json as read_json,
    text,
)

SCHEMA = "agialpha.curriculum.scenario.v1"
REPORT_SCHEMA = "agialpha.curriculum.run.v1"
SCOPE = (
    "Bounded program induction over synthetic integer tasks; no model weights are trained. "
    "Free energy is an operation-cost/entropy proxy, not physical energy or an ELBO. "
    "Review eligibility is not approval. The baseline stays active; jobs are unsubmitted and unfunded."
)
OPS = ("inc", "dec", "double", "negate", "abs", "square", "mod3")
FAMILIES = ("arithmetic", "nonlinear", "remainder")
BUDGETS = (8, 32, 128, 400)
# Rounded natural logarithms in millinats. Shared literally with the browser.
LOG_Q = (
    0,
    0,
    693,
    1099,
    1386,
    1609,
    1792,
    1946,
    2079,
    2197,
    2303,
    2398,
    2485,
    2565,
    2639,
    2708,
    2773,
    2833,
    2890,
    2944,
    2996,
    3045,
    3091,
    3135,
    3178,
    3219,
    3258,
    3296,
    3332,
    3367,
    3401,
    3434,
    3466,
    3497,
    3526,
    3555,
    3584,
    3611,
    3638,
    3664,
    3689,
    3714,
    3738,
    3761,
    3784,
    3807,
    3829,
    3850,
    3871,
)


class Random:
    """Private xorshift32 stream with exact cross-runtime behavior."""

    def __init__(self, seed: int):
        self.state = seed or 0x9E3779B9

    def next(self) -> int:
        x = self.state
        x ^= (x << 13) & 0xFFFFFFFF
        x ^= x >> 17
        x ^= (x << 5) & 0xFFFFFFFF
        self.state = x & 0xFFFFFFFF
        return self.state


def validate(raw: Any) -> dict[str, Any]:
    keys(
        raw,
        {
            "schema",
            "id",
            "title",
            "note",
            "seed",
            "rounds",
            "tasksPerRound",
            "maxDepth",
            "families",
            "positiveExamples",
            "temperature",
            "policy",
        },
        "Scenario",
    )
    if raw["schema"] != SCHEMA:
        raise ValueError("Unsupported curriculum scenario schema")
    identifier(raw["id"])
    text(raw["title"], "Title", 120)
    text(raw["note"], "Note", 600)
    for key, low, high in (
        ("seed", 0, 4294967295),
        ("rounds", 1, 12),
        ("tasksPerRound", 3, 12),
        ("maxDepth", 1, 3),
        ("temperature", 0, 1000),
    ):
        integer(raw[key], low, high, key)
    if type(raw["positiveExamples"]) is not bool:
        raise ValueError("positiveExamples must be a boolean")
    if (
        not isinstance(raw["families"], list)
        or not raw["families"]
        or len(raw["families"]) > 3
        or any(item not in FAMILIES for item in raw["families"])
        or len(set(raw["families"])) != len(raw["families"])
    ):
        raise ValueError("Choose unique arithmetic, nonlinear and/or remainder families")
    keys(raw["policy"], {"minAccuracyBps", "minFamilyBps", "minGainBps", "maxMeanOperations"}, "Policy")
    for key in ("minAccuracyBps", "minFamilyBps", "minGainBps"):
        integer(raw["policy"][key], 0, 10000, key)
    integer(raw["policy"]["maxMeanOperations"], 1, 10000, "maxMeanOperations")
    return cast(dict[str, Any], parse(canonical(raw)))


def execute(program: list[str], x: int) -> int:
    """Interpret a validated, finite arithmetic grammar; never evaluate source."""
    if not isinstance(program, list) or len(program) > 3 or any(op not in OPS for op in program):
        raise ValueError("Programs contain at most three known operators")
    integer(x, -8, 8, "Input")
    for op in program:
        if op == "inc":
            x += 1
        elif op == "dec":
            x -= 1
        elif op == "double":
            x *= 2
        elif op == "negate":
            x = -x
        elif op == "abs":
            x = abs(x)
        elif op == "square":
            x *= x
        else:
            x %= 3
    return x


def family(program: list[str]) -> str:
    if "mod3" in program:
        return "remainder"
    if "square" in program or "abs" in program:
        return "nonlinear"
    return "arithmetic"


def programs(depth: int, wide: bool = True) -> list[list[str]]:
    palette = OPS if wide else OPS[:4]
    return [[]] + [list(p) for length in range(1, depth + 1) for p in product(palette, repeat=length)]


def config(depth: int = 1, budget: int = 0, wide: bool = False) -> dict[str, Any]:
    return {
        "id": f"d{depth}-b{BUDGETS[budget]}-{'wide' if wide else 'core'}",
        "depth": depth,
        "budgetIndex": budget,
        "wide": wide,
    }


def neighbors(parent: dict[str, Any], depth: int) -> list[dict[str, Any]]:
    d, b, w = parent["depth"], parent["budgetIndex"], parent["wide"]
    candidates = [config(d, b, w), config(min(depth, d + 1), b, w), config(d, min(3, b + 1), w), config(d, b, True)]
    return list({c["id"]: c for c in candidates}.values())


def solve(examples: list[list[int]], inputs: list[int], agent: dict[str, Any]) -> dict[str, Any]:
    """Solver sees only examples and test inputs; it never receives an oracle."""
    operations, tried = 0, 0
    for candidate in programs(agent["depth"], agent["wide"])[: BUDGETS[agent["budgetIndex"]]]:
        tried += 1
        matches = True
        for x, y in examples:
            operations += max(1, len(candidate))
            if execute(candidate, x) != y:
                matches = False
                break
        if matches:
            operations += max(1, len(candidate)) * len(inputs)
            return {
                "program": candidate,
                "predictions": [execute(candidate, x) for x in inputs],
                "operations": operations,
                "tried": tried,
            }
    return {"program": None, "predictions": None, "operations": operations, "tried": tried}


def propose(
    rng: Random,
    count: int,
    depth: int,
    families: list[str],
    weights: dict[str, int],
    positive: bool,
    prefix: str,
    review: bool = False,
) -> tuple[list[dict[str, Any]], int]:
    pool = {f: [p for p in programs(depth) if family(p) == f] for f in families}
    seen: set[tuple[int, ...]] = set()
    tasks: list[dict[str, Any]] = []
    attempts = 0
    while len(tasks) < count and attempts < 512:
        attempts += 1
        draw = rng.next() % sum(weights[f] for f in families)
        selected = families[-1]
        for f in families:
            draw -= weights[f]
            if draw < 0:
                selected = f
                break
        p = pool[selected][rng.next() % len(pool[selected])]
        signature = tuple(execute(p, x) for x in range(-5, 6))
        if signature in seen:
            continue
        seen.add(signature)
        train = [1, 2, 3, 4] if positive else [-3, -1, 1, 3]
        tests = [-8, -6, 6, 8] if review else [-5, -2, 0, 5]
        tasks.append(
            {
                "id": f"{prefix}-{len(tasks) + 1}",
                "family": selected,
                "oracle": p,
                "examples": [[x, execute(p, x)] for x in train],
                "inputs": tests,
                "expected": [execute(p, x) for x in tests],
            }
        )
    return tasks, attempts - len(tasks)


def assess(agent: dict[str, Any], tasks: list[dict[str, Any]], temperature: int) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    solved = {f: 0 for f in FAMILIES}
    counts = {f: 0 for f in FAMILIES}
    for task in tasks:
        result = solve(task["examples"], task["inputs"], agent)
        ok = result["predictions"] == task["expected"]
        counts[task["family"]] += 1
        solved[task["family"]] += int(ok)
        details.append({"task": task["id"], "solved": ok, **result})
    total = len(tasks)
    correct = sum(solved.values())
    operations = sum(r["operations"] for r in details)
    entropy = LOG_Q[correct] - sum(n * LOG_Q[n] for n in solved.values()) // correct if correct else 0
    accuracy = correct * 10000 // total
    mean_ops = operations // total
    energy = mean_ops - temperature * entropy // 1000
    return {
        "agent": agent,
        "correct": correct,
        "total": total,
        "accuracyBps": accuracy,
        "operations": operations,
        "meanOperations": mean_ops,
        "entropyMilliNats": entropy,
        "freeEnergyProxy": energy,
        "utility": accuracy - mean_ops + temperature * entropy // 1000,
        "families": {
            f: {
                "correct": solved[f],
                "total": counts[f],
                "accuracyBps": solved[f] * 10000 // counts[f] if counts[f] else 0,
            }
            for f in FAMILIES
        },
        "details": details,
    }


def pareto(rows: list[dict[str, Any]]) -> list[str]:
    return [
        r["agent"]["id"]
        for r in rows
        if not any(
            o["accuracyBps"] >= r["accuracyBps"]
            and o["meanOperations"] <= r["meanOperations"]
            and (o["accuracyBps"] > r["accuracyBps"] or o["meanOperations"] < r["meanOperations"])
            for o in rows
        )
    ]


def evaluate(raw: Any) -> dict[str, Any]:
    source = validate(raw)
    rng = Random(source["seed"])
    active = config()
    champion = active
    archive: dict[str, dict[str, Any]] = {active["id"]: {"agent": active, "parent": None, "round": 0}}
    weights = {f: 100 for f in source["families"]}
    difficulty = 1
    replay: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    for generation in range(1, source["rounds"] + 1):
        tasks, rejected = propose(
            rng,
            source["tasksPerRound"],
            difficulty,
            source["families"],
            weights,
            source["positiveExamples"],
            f"r{generation}",
        )
        replay = (replay + tasks)[-48:]
        candidates = neighbors(champion, source["maxDepth"])
        for candidate in candidates:
            if candidate["id"] not in archive:
                archive[candidate["id"]] = {"agent": candidate, "parent": champion["id"], "round": generation}
        rows = [assess(c, replay, source["temperature"]) for c in candidates]
        front = pareto(rows)
        selected = sorted(
            (r for r in rows if r["agent"]["id"] in front),
            key=lambda r: (-r["utility"], -r["accuracyBps"], r["meanOperations"], r["agent"]["id"]),
        )[0]
        champion = selected["agent"]
        recent = assess(champion, tasks, source["temperature"])
        next_weights = {
            f: 100
            + 4
            * recent["families"][f]["correct"]
            * (recent["families"][f]["total"] - recent["families"][f]["correct"])
            * 100
            // max(1, recent["families"][f]["total"] ** 2)
            + (100 if recent["families"][f]["total"] == 0 else 0)
            for f in source["families"]
        }
        next_difficulty = difficulty
        if recent["accuracyBps"] >= 7500:
            next_difficulty = min(source["maxDepth"], difficulty + 1)
        elif recent["accuracyBps"] < 3500:
            next_difficulty = max(1, difficulty - 1)
        history.append(
            {
                "round": generation,
                "difficulty": difficulty,
                "nextDifficulty": next_difficulty,
                "weights": weights,
                "nextWeights": next_weights,
                "tasks": tasks,
                "rejected": rejected,
                "replaySize": len(replay),
                "candidates": rows,
                "pareto": front,
                "winner": champion["id"],
                "recent": recent,
            }
        )
        weights, difficulty = next_weights, next_difficulty
    # This stream is created only after selection. Each family requests eight distinct behaviors, subject to grammar saturation.
    holdout_rng = Random(source["seed"] ^ 0xA5A5A5A5)
    heldout: list[dict[str, Any]] = []
    for f in FAMILIES:
        batch, _ = propose(holdout_rng, 8, source["maxDepth"], [f], {f: 100}, False, f"heldout-{f}", review=True)
        heldout.extend(batch)
    baseline = assess(active, heldout, source["temperature"])
    candidate = assess(champion, heldout, source["temperature"])
    gain = candidate["accuracyBps"] - baseline["accuracyBps"]
    policy = source["policy"]
    gates = [
        {
            "id": "accuracy",
            "label": "Held-out accuracy",
            "observed": candidate["accuracyBps"],
            "limit": policy["minAccuracyBps"],
            "comparison": ">=",
        },
        {
            "id": "coverage",
            "label": "Weakest task family",
            "observed": min(v["accuracyBps"] for v in candidate["families"].values()),
            "limit": policy["minFamilyBps"],
            "comparison": ">=",
        },
        {
            "id": "gain",
            "label": "Gain over baseline",
            "observed": gain,
            "limit": policy["minGainBps"],
            "comparison": ">=",
        },
        {
            "id": "operations",
            "label": "Mean operation budget",
            "observed": candidate["meanOperations"],
            "limit": policy["maxMeanOperations"],
            "comparison": "<=",
        },
    ]
    for gate in gates:
        gate["passed"] = (
            gate["observed"] >= gate["limit"] if gate["comparison"] == ">=" else gate["observed"] <= gate["limit"]
        )
    input_hash = digest(source)
    proposal = {
        "schema": "agialpha.curriculum.proposal.v1",
        "inputSha256": input_hash,
        "status": "UNAPPROVED",
        "active": active,
        "candidate": champion,
        "reason": "Independent validator approval and task-specific deployment testing are required.",
    }
    jobs = [
        {
            "goal": f"Reproduce curriculum {source['id']}; input SHA-256: {input_hash}. Inspect the solver, lineage and independent evaluation.",
            "successMetric": "Recompute all tasks and gates exactly, then validate the frozen solver on fresh domain tasks. Independent validators approve or reject with evidence.",
            "bounty": "100000000000000000000",
            "duration": 604800,
            "priceWeight": 5000,
        }
    ]
    result = {
        "status": "REVIEW_ELIGIBLE" if all(g["passed"] for g in gates) else "HOLD",
        "history": history,
        "lineage": list(archive.values()),
        "heldoutTasks": heldout,
        "baseline": baseline,
        "candidate": candidate,
        "gainBps": gain,
        "gates": gates,
        "proposal": proposal,
        "jobs": jobs,
    }
    report = {"schema": REPORT_SCHEMA, "scope": SCOPE, "input": source, "inputSha256": input_hash, "result": result}
    return {**report, "sha256": digest(report)}


def verify(raw: Any) -> dict[str, Any]:
    keys(raw, {"schema", "scope", "input", "inputSha256", "result", "sha256"}, "Run")
    expected = evaluate(raw["input"])
    if canonical(expected) != canonical(raw):
        raise ValueError("Run does not match independent recomputation; hashes alone do not prove correctness")
    return expected


def brief(report: dict[str, Any]) -> str:
    result, source = report["result"], report["input"]
    rows = [
        f"# {literal(source['title'])}",
        "",
        result["status"],
        "",
        literal(source["note"]),
        "",
        f"Frozen solver: {result['candidate']['agent']['id']}; accuracy: {result['candidate']['accuracyBps']}/10000.",
        f"Baseline: {result['baseline']['accuracyBps']}/10000; gain: {result['gainBps']} basis points.",
        "",
        "| Gate | Result | Comparison |",
        "|---|---|---|",
    ]
    rows += [
        f"| {g['label']} | {'PASS' if g['passed'] else 'HOLD'} | {g['observed']} {g['comparison']} {g['limit']} |"
        for g in result["gates"]
    ]
    rows += [
        "",
        "The active solver remains the baseline. Do not tune seeds or policies after reading held-out results.",
        "",
        SCOPE,
        "",
        f"Run SHA-256: {report['sha256']}",
        "",
    ]
    return "\n".join(rows)


def artifacts(report: dict[str, Any]) -> dict[str, bytes]:
    report = verify(report)
    values = {
        "scenario.json": canonical(report["input"]) + b"\n",
        "run.json": canonical(report) + b"\n",
        "solver-proposal.json": canonical(report["result"]["proposal"]) + b"\n",
        "jobs.json": canonical(report["result"]["jobs"]) + b"\n",
        "review.md": brief(report).encode("utf-8"),
    }
    values["SHA256SUMS"] = "".join(
        f"{hashlib.sha256(data).hexdigest()}  {name}\n" for name, data in sorted(values.items())
    ).encode()
    return values


def write_bundle(report: dict[str, Any], root: Path) -> Path:
    # Intentionally use this lab's recomputation and artifact schema.
    values = artifacts(report)
    root.mkdir(parents=True, exist_ok=True)
    target = root / str(report["sha256"])
    try:
        target.mkdir()
    except FileExistsError:
        if target.is_symlink() or not target.is_dir() or {p.name for p in target.iterdir()} != set(values):
            raise ValueError("Existing run is incomplete or altered; choose a new output directory") from None
        if any(
            (target / n).is_symlink() or not (target / n).is_file() or (target / n).read_bytes() != data
            for n, data in values.items()
        ):
            raise ValueError("Existing run differs; choose a new output directory")
        return target
    for name, data in values.items():
        with (target / name).open("xb") as stream:
            stream.write(data)
    return target
