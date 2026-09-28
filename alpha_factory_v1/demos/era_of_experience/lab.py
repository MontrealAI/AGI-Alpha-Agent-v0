# SPDX-License-Identifier: Apache-2.0
"""Bounded contextual-bandit learning with deterministic, independent shadow evaluation.

Only selected-action observations enter learning memory. Environment probabilities
are simulation parameters, never scores supplied to the learner. Evaluation freezes
the learned policy and uses separate random streams with paired baseline outcomes.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import (
    canonical,
    digest,
    identifier,
    integer,
    keys,
    literal,
    parse,
    text,
)
from alpha_factory_v1.demos.alpha_agi_insight_v0.discovery import read_json as read_json

SCHEMA = "agialpha.experience.scenario.v1"
REPORT_SCHEMA = "agialpha.experience.run.v1"
SCOPE = (
    "Synthetic contextual-bandit experiment, not a general intelligence or a live service. "
    "Evaluation is a finite, reproducible shadow test, not proof of generalization. "
    "The baseline remains active. A passing candidate requires independent validation; "
    "review jobs are unsubmitted and no tokens are transferred."
)


def validate(source: Any) -> dict[str, Any]:
    keys(
        source,
        {"schema", "id", "title", "note", "seed", "training", "reward", "gates", "actions", "contexts"},
        "Scenario",
    )
    if source["schema"] != SCHEMA:
        raise ValueError("Unsupported experience scenario schema")
    identifier(source["id"])
    text(source["title"], "Title", 160)
    text(source["note"], "Note", 600)
    integer(source["seed"], 1, 4294967295, "Seed")
    training = source["training"]
    keys(training, {"steps", "evaluationSteps", "explorationBps", "memoryWindow", "shiftAt"}, "Training")
    for name, low, high in (
        ("steps", 12, 600),
        ("evaluationSteps", 30, 600),
        ("explorationBps", 0, 10000),
        ("memoryWindow", 1, 200),
        ("shiftAt", 0, training["steps"]),
    ):
        integer(training[name], low, high, name)
    keys(source["reward"], {"costWeight", "incidentPenalty", "proxyWeight"}, "Reward")
    for name, high in (("costWeight", 100), ("incidentPenalty", 10000), ("proxyWeight", 100)):
        integer(source["reward"][name], 0, high, name)
    gates = source["gates"]
    limits = {
        "minGain": (0, 10000),
        "maxIncidentBps": (0, 10000),
        "minSuccessBps": (0, 10000),
        "maxMeanCost": (0, 1000),
        "minSamples": (1, 200),
        "maxRetentionLoss": (0, 10000),
        "bountyTokens": (1, 1000000),
    }
    keys(gates, set(limits), "Gates")
    for name, (low, high) in limits.items():
        integer(gates[name], low, high, name)
    actions = source["actions"]
    if not isinstance(actions, list) or not 2 <= len(actions) <= 5:
        raise ValueError("Provide 2–5 actions")
    ids = set()
    for action in actions:
        keys(action, {"id", "label"}, "Action")
        identifier(action["id"])
        text(action["label"], "Action label", 80)
        if action["id"] in ids:
            raise ValueError("Duplicate action ID")
        ids.add(action["id"])
    contexts = source["contexts"]
    if not isinstance(contexts, list) or not 1 <= len(contexts) <= 6:
        raise ValueError("Provide 1–6 contexts")
    ids = set()
    for context in contexts:
        keys(context, {"id", "label", "baseline", "initial", "shifted"}, "Context")
        identifier(context["id"])
        text(context["label"], "Context label", 80)
        if context["id"] in ids:
            raise ValueError("Duplicate context ID")
        ids.add(context["id"])
        integer(context["baseline"], 0, len(actions) - 1, "Baseline action")
        for phase in ("initial", "shifted"):
            outcomes = context[phase]
            if not isinstance(outcomes, list) or len(outcomes) != len(actions):
                raise ValueError("Every context requires one outcome model per action in both phases")
            for outcome in outcomes:
                keys(outcome, {"successBps", "incidentBps", "cost", "proxy"}, "Outcome")
                for name, high in (("successBps", 10000), ("incidentBps", 10000), ("cost", 1000), ("proxy", 1000)):
                    integer(outcome[name], 0, high, name)
    # Round-trip detaches mutable inputs and normalizes integral floats identically to JavaScript.
    result: dict[str, Any] = parse(canonical(source))
    return result


class Random:
    """Specified xorshift32 stream; same unsigned operations in Python and JS."""

    def __init__(self, seed: int) -> None:
        self.state = seed or 1

    def next(self) -> int:
        value = self.state
        value ^= (value << 13) & 0xFFFFFFFF
        value ^= value >> 17
        value ^= (value << 5) & 0xFFFFFFFF
        self.state = value & 0xFFFFFFFF
        return self.state


def observe(model: dict[str, int], rolls: tuple[int, int], reward: dict[str, int]) -> dict[str, int]:
    success = int(rolls[0] < model["successBps"])
    incident = int(rolls[1] < model["incidentBps"])
    return {
        "success": success,
        "incident": incident,
        "cost": model["cost"],
        "proxy": model["proxy"],
        "reward": success * 1000
        - model["cost"] * reward["costWeight"]
        - incident * reward["incidentPenalty"]
        + model["proxy"] * reward["proxyWeight"],
    }


def choose(memory: list[list[int]]) -> int:
    """Maximize the exact sample mean; ties use the earlier action, without floats."""
    best = 0
    for index in range(1, len(memory)):
        left, right = memory[index], memory[best]
        if sum(left) * max(1, len(right)) > sum(right) * max(1, len(left)):
            best = index
    return best


def evaluate(raw: Any) -> dict[str, Any]:
    source = validate(raw)
    spec, contexts, actions = source["training"], source["contexts"], source["actions"]
    reward, gates = source["reward"], source["gates"]
    memory: list[list[list[int]]] = [[[] for _ in actions] for _ in contexts]
    counts = [[0 for _ in actions] for _ in contexts]
    rng = Random(source["seed"])
    trace = []
    for step in range(spec["steps"]):
        ci = step % len(contexts)
        context = contexts[ci]
        exploration, random_action = rng.next() % 10000, rng.next() % len(actions)
        unseen = next((i for i, count in enumerate(counts[ci]) if not count), None)
        action = (
            unseen
            if unseen is not None
            else random_action
            if exploration < spec["explorationBps"]
            else choose(memory[ci])
        )
        phase = "shifted" if spec["shiftAt"] and step >= spec["shiftAt"] else "initial"
        outcome = observe(context[phase][action], (rng.next() % 10000, rng.next() % 10000), reward)
        samples = memory[ci][action]
        samples.append(outcome["reward"])
        del samples[: -spec["memoryWindow"]]
        counts[ci][action] += 1
        trace.append({"step": step + 1, "context": ci, "action": action, "phase": phase, **outcome})
    candidate = [choose(row) for row in memory]
    baseline = [context["baseline"] for context in contexts]

    def shadow(phase: str, seed: int) -> dict[str, Any]:
        stream = Random(seed)
        totals = {
            name: {"reward": 0, "success": 0, "incident": 0, "cost": 0, "proxy": 0}
            for name in ("baseline", "candidate")
        }
        episodes = []
        for step in range(spec["evaluationSteps"]):
            ci = step % len(contexts)
            rolls = (stream.next() % 10000, stream.next() % 10000)
            row: dict[str, Any] = {"step": step + 1, "context": ci}
            for name, policy in (("baseline", baseline), ("candidate", candidate)):
                outcome = observe(contexts[ci][phase][policy[ci]], rolls, reward)
                row[name] = {"action": policy[ci], **outcome}
                for metric, value in outcome.items():
                    totals[name][metric] += value
            episodes.append(row)
        return {"phase": phase, "episodes": episodes, "totals": totals}

    phase = "shifted" if spec["shiftAt"] else "initial"
    evaluation = shadow(phase, source["seed"] ^ 0x9E3779B9)
    retention = shadow("initial", source["seed"] ^ 0xA341316C)
    base, proposed = evaluation["totals"]["baseline"], evaluation["totals"]["candidate"]
    n = spec["evaluationSteps"]
    gain = proposed["reward"] - base["reward"]
    retained_gain = retention["totals"]["candidate"]["reward"] - retention["totals"]["baseline"]["reward"]
    checks = [
        {"id": "gain", "label": "Held-out reward gain", "passed": gain >= gates["minGain"] * n},
        {
            "id": "safety",
            "label": "Incident ceiling",
            "passed": proposed["incident"] * 10000 <= gates["maxIncidentBps"] * n,
        },
        {
            "id": "success",
            "label": "Success floor",
            "passed": proposed["success"] * 10000 >= gates["minSuccessBps"] * n,
        },
        {"id": "cost", "label": "Mean cost ceiling", "passed": proposed["cost"] <= gates["maxMeanCost"] * n},
        {
            "id": "coverage",
            "label": "Selected-action memory",
            "passed": all(len(memory[c][a]) >= gates["minSamples"] for c, a in enumerate(candidate)),
        },
        {
            "id": "retention",
            "label": "Original-environment retention",
            "passed": retained_gain >= -gates["maxRetentionLoss"] * n,
        },
    ]
    input_hash = digest(source)
    proposal = {
        "schema": "agialpha.experience.policy-proposal.v1",
        "inputSha256": input_hash,
        "activePolicy": baseline,
        "candidatePolicy": candidate,
        "state": "UNAPPROVED",
        "actionIds": [action["id"] for action in actions],
        "contextIds": [context["id"] for context in contexts],
    }
    result = {
        "status": "REVIEW_REQUIRED" if all(check["passed"] for check in checks) else "HOLD_BASELINE",
        "inputSha256": input_hash,
        "training": trace,
        "memory": memory,
        "visitCounts": counts,
        "evaluation": evaluation,
        "retention": retention,
        "gainTotal": gain,
        "retentionGainTotal": retained_gain,
        "gates": checks,
        "proposal": proposal,
        "scope": SCOPE,
        "jobs": [
            {
                "goal": f"Independently reproduce Experience {source['id']}; input SHA-256: {input_hash}. Review the reward design, held-out and retention results before any promotion.",
                "successMetric": "Recompute all traces and six gates; test a fresh, separately chosen seed and representative real environment; approve or reject with evidence. A hash is not validator approval.",
                "bounty": str(gates["bountyTokens"] * 10**18),
                "duration": 604800,
                "priceWeight": 5000,
            }
        ],
    }
    report = {"schema": REPORT_SCHEMA, "input": source, "result": result}
    return {**report, "sha256": digest(report)}


def verify(report: Any) -> dict[str, Any]:
    keys(report, {"schema", "input", "result", "sha256"}, "Run")
    expected = evaluate(report["input"])
    if canonical(report) != canonical(expected):
        raise ValueError("Run differs from recomputation; imported policies, outcomes and gates are not trusted")
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
        f"Training: {source['training']['steps']} interactions. Evaluation: {source['training']['evaluationSteps']} paired episodes per suite.",
        f"Held-out total reward gain: {result['gainTotal']}. Retention total gain: {result['retentionGainTotal']}.",
        "",
        "| Review gate | Result |",
        "|---|---|",
    ]
    lines += [f"| {item['label']} | {'PASS' if item['passed'] else 'HOLD'} |" for item in result["gates"]]
    lines += [
        "",
        "Policies use zero-based action indices in scenario order. Active policy remains the baseline.",
        "Evaluation never updates learning memory. Selecting a seed after inspecting results invalidates an independent test.",
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
