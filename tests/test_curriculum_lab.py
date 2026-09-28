# SPDX-License-Identifier: Apache-2.0
"""Independent task solving, frozen evaluation and evidence trust boundaries."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import random

import pytest

from alpha_factory_v1.demos.meta_agentic_agi_v3 import curriculum_lab as lab

CASES = lab.read_json(Path(lab.__file__).with_name("scenarios.json"))


def test_interpreter_and_independent_solver() -> None:
    assert lab.execute(["mod3"], -2) == 1
    assert lab.execute(["double", "inc"], 3) == 7
    answer = lab.solve([[-3, -5], [-1, -1], [1, 3], [3, 7]], [-5, 0, 5], lab.config(2, 3, True))
    assert answer["predictions"] == [-9, 1, 11]
    assert answer["program"] == ["double", "inc"]
    # Same observations fit identity and abs. A solver cannot consult the oracle.
    ambiguous = lab.solve([[1, 1], [2, 2]], [-3], lab.config(3, 3, True))
    assert ambiguous["program"] == [] and ambiguous["predictions"] == [-3]
    assert lab.solve([[1, 999]], [2], lab.config())["predictions"] is None
    with pytest.raises(ValueError):
        lab.execute(["import os"], 1)
    with pytest.raises(ValueError):
        lab.execute(["square"] * 4, 1)


@pytest.mark.parametrize("index,status", [(0, "REVIEW_ELIGIBLE"), (1, "HOLD"), (2, "HOLD"), (3, "REVIEW_ELIGIBLE")])
def test_real_outcomes_and_replay(index: int, status: str) -> None:
    state = random.getstate()
    report = lab.evaluate(CASES[index])
    assert random.getstate() == state
    assert lab.verify(report) == report == lab.evaluate(CASES[index])
    result = report["result"]
    assert result["status"] == status
    assert result["proposal"]["status"] == "UNAPPROVED"
    assert result["proposal"]["active"] == lab.config()
    assert report["inputSha256"] in result["jobs"][0]["goal"]
    training_inputs = {x for h in result["history"] for t in h["tasks"] for x in t["inputs"]}
    assert all(not training_inputs.intersection(t["inputs"]) for t in result["heldoutTasks"])
    assert result["candidate"]["correct"] == sum(d["solved"] for d in result["candidate"]["details"])
    for round_ in result["history"]:
        assert round_["replaySize"] <= 48
        assert round_["winner"] in round_["pareto"]
        tasks = round_["tasks"]
        signatures = {tuple(lab.execute(t["oracle"], x) for x in range(-5, 6)) for t in tasks}
        assert len(signatures) == len(tasks)
        for task, detail in zip(tasks, round_["recent"]["details"], strict=True):
            answer = lab.solve(task["examples"], task["inputs"], round_["recent"]["agent"])
            assert answer["predictions"] == detail["predictions"]
    parents = {n["agent"]["id"]: n for n in result["lineage"]}
    for item in result["lineage"]:
        if item["parent"]:
            assert parents[item["parent"]]["round"] < item["round"]


def test_review_policy_cannot_select_the_candidate() -> None:
    source = deepcopy(CASES[0])
    original = lab.evaluate(source)
    source["policy"].update(minAccuracyBps=10000, minGainBps=10000, maxMeanOperations=1)
    changed = lab.evaluate(source)
    for key in ("history", "lineage", "candidate", "baseline", "heldoutTasks"):
        assert changed["result"][key] == original["result"][key]
    assert changed["result"]["status"] == "HOLD"


def test_coverage_and_cost_are_independent_gates() -> None:
    coverage = lab.evaluate(CASES[1])["result"]
    assert not next(g for g in coverage["gates"] if g["id"] == "coverage")["passed"]
    costs = lab.evaluate(CASES[2])["result"]
    assert next(g for g in costs["gates"] if g["id"] == "accuracy")["passed"]
    assert not next(g for g in costs["gates"] if g["id"] == "operations")["passed"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", True),
        ("seed", -1),
        ("rounds", 13),
        ("rounds", 1.2),
        ("maxDepth", 4),
        ("positiveExamples", 1),
        ("families", []),
        ("families", ["arithmetic", "arithmetic"]),
        ("families", ["unknown"]),
        ("temperature", float("nan")),
        ("title", "\ud800"),
        ("id", "../x"),
    ],
)
def test_invalid_scenarios_rejected(field: str, value: object) -> None:
    case = deepcopy(CASES[0])
    case[field] = value
    with pytest.raises(ValueError):
        lab.evaluate(case)


@pytest.mark.parametrize(
    "data", [b'{"a":1,"a":2}', b'{"x":1e999}', b'"\\ud800"', b"\xff", b"[" * 30 + b"0" + b"]" * 30]
)
def test_ambiguous_json_rejected(data: bytes) -> None:
    with pytest.raises(ValueError):
        lab.parse(data)


def test_rehashed_forgery_is_rejected() -> None:
    forged = lab.evaluate(CASES[0])
    forged["result"]["candidate"]["accuracyBps"] = 10000
    forged["sha256"] = lab.digest({k: v for k, v in forged.items() if k != "sha256"})
    with pytest.raises(ValueError, match="recomputation"):
        lab.verify(forged)


def test_bundle_idempotence_and_tamper_rejection(tmp_path: Path) -> None:
    report = lab.evaluate(CASES[0])
    target = lab.write_bundle(report, tmp_path)
    assert lab.write_bundle(report, tmp_path) == target
    assert len(list(target.iterdir())) == 6
    assert lab.read_json(target / "run.json") == report
    (target / "review.md").write_text("altered")
    with pytest.raises(ValueError, match="differs"):
        lab.write_bundle(report, tmp_path)


def test_saturated_grammar_is_bounded() -> None:
    rng = lab.Random(1)
    tasks, rejected = lab.propose(rng, 12, 1, ["remainder"], {"remainder": 100}, False, "test")
    assert len(tasks) == 1 and rejected == 511


def test_unknown_fields_do_not_pass_silently() -> None:
    source = {**CASES[0], "provider": "openai"}
    with pytest.raises(ValueError):
        lab.evaluate(source)
    assert json.loads(lab.canonical(CASES[0])) == CASES[0]
