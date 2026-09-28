# SPDX-License-Identifier: Apache-2.0
"""Independent arithmetic, search invariants and adversarial evidence boundaries."""
from __future__ import annotations

from copy import deepcopy
import csv
import io
import json
from pathlib import Path
import random

import pytest

from alpha_factory_v1.demos.meta_agentic_tree_search_v0.search_lab import (
    artifacts,
    canonical,
    digest,
    evaluate,
    parse,
    read_json,
    simulate,
    validate,
    verify,
    write_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = read_json(ROOT / "alpha_factory_v1/demos/meta_agentic_tree_search_v0/scenarios.json")


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["id"])
def test_reproducible_search_and_exact_backpropagation(case):
    state = random.getstate()
    original = deepcopy(case)
    report = evaluate(case)
    r = report["result"]
    assert case == original and random.getstate() == state
    assert report == evaluate(case) == verify(report)
    assert r["status"] == ("HOLD_BASELINE" if case["id"] == "proxy-trap" else "REVIEW_REQUIRED")
    assert r["proposal"]["activePolicy"] == [stage["baseline"] for stage in case["stages"]]
    assert r["proposal"]["state"] == "UNAPPROVED"
    assert r["nodes"][0]["visits"] == case["search"]["iterations"]
    assert len(r["nodes"][0]["children"]) > 1
    for node in r["nodes"]:
        events = [event for event in r["trace"] if node["id"] in event["path"]]
        assert node["visits"] == len(events)
        assert node["totalQ"] == sum(event["valueQ"] for event in events)
        assert node["depth"] <= case["search"]["depth"]
        if node["parent"] is not None:
            parent = r["nodes"][node["parent"]]
            assert node["id"] in parent["children"]
            assert sum(a != b for a, b in zip(parent["policy"], node["policy"])) == 1
    for event in r["trace"]:
        route = [r["nodes"][index]["policy"] for index in event["path"]]
        assert len(set(map(tuple, route))) == len(route)
        policy = list(route[-1])
        for move in event["rollout"]:
            assert policy[move["stage"]] == move["from"]
            policy[move["stage"]] = move["to"]
            assert policy not in route
            route.append(list(policy))
        assert policy == event["policy"]
    ranked = [(r["baselineTraining"]["totals"]["utility"], r["proposal"]["activePolicy"])]
    ranked += [(event["utilityTotal"], event["policy"]) for event in r["trace"]]
    assert r["candidate"] == min(ranked, key=lambda item: (-item[0], item[1]))[1]
    assert r["oracle"]["gapTotal"] >= 0
    for name in ("baseline", "candidate"):
        measured = r["evaluation"][name]
        for metric, value in measured["totals"].items():
            assert value == sum(episode[metric] for episode in measured["episodes"])


def test_hand_calculated_fault_repair_and_resource_contention():
    case = deepcopy(CASES[0])
    case["stages"] = case["stages"][:2]
    case["objective"].update(value=100, costWeight=2, timeWeight=3, escapePenalty=1000)
    first, second = case["stages"]
    first["choices"][0].update(minutes=10, cost=2, defectBps=0, detectBps=0, reviewMinutes=1)
    second["choices"][0].update(minutes=5, cost=3, defectBps=10000, detectBps=10000, reviewMinutes=2)
    observed = simulate(case, [0, 0], [[100, 0, 0], [100, 0, 0]])
    assert {
        key: observed[key] for key in ("utility", "cost", "makespan", "escaped", "rework", "reviewMinutes")
    } == dict(utility=24, cost=8, makespan=20, escaped=0, rework=1, reviewMinutes=5)
    assert [(row["start"], row["end"]) for row in observed["stages"]] == [(0, 10), (10, 20)]
    second["depends"] = []
    assert simulate(case, [0, 0], [[100, 0, 0], [100, 0, 0]])["makespan"] == 10
    case["resources"][0]["capacity"] = 1
    assert simulate(case, [0, 0], [[100, 0, 0], [100, 0, 0]])["makespan"] == 20
    second["choices"][0]["detectBps"] = 0
    assert simulate(case, [0, 0], [[100, 0, 0], [100, 0, 0]])["escaped"] == 1


def test_oracle_and_held_out_evaluation_cannot_choose_or_train_the_candidate():
    case = deepcopy(CASES[1])
    original = evaluate(case)["result"]
    assert original["oracle"]["gapTotal"] > 0  # The chosen design is not replaced with the oracle's answer.
    case["search"].update(auditOracle=False, evaluationSamples=128)
    case["gates"].update(maxEscapeBps=0, deadline=1, maxMeanCost=0)
    changed = evaluate(case)["result"]
    for field in (
        "nodes",
        "trace",
        "candidate",
        "candidateRewrites",
        "candidateTraining",
        "baselineTraining",
        "uniqueEvaluations",
        "simulationEpisodes",
    ):
        assert original[field] == changed[field]
    assert changed["oracle"] == {"enabled": False, "evaluations": 0}
    assert changed["status"] == "HOLD_BASELINE"


def test_exact_oracle_for_a_deterministic_design_space():
    case = deepcopy(CASES[0])
    case["stages"] = case["stages"][:2]
    case["search"].update(iterations=40, depth=2, trainingSamples=4)
    case["objective"].update(value=10000, costWeight=1, timeWeight=0, escapePenalty=0)
    for stage in case["stages"]:
        for index, choice in enumerate(stage["choices"]):
            choice.update(cost=[9, 2, 6][index], defectBps=0, detectBps=0)
    result = evaluate(case)["result"]
    assert result["oracle"]["policy"] == [1, 1]
    assert result["oracle"]["utilityTotal"] == (10000 - 4) * 4
    assert result["oracle"]["evaluations"] == 9
    assert result["candidate"] == [1, 1] and result["oracle"]["gapTotal"] == 0


@pytest.mark.parametrize(
    "mutation",
    [
        lambda c: c.update(extra=True),
        lambda c: c.update(seed=True),
        lambda c: c.update(seed=float("nan")),
        lambda c: c["search"].update(iterations=0),
        lambda c: c["search"].update(iterations=241),
        lambda c: c["search"].update(depth=7),
        lambda c: c["search"].update(auditOracle=1),
        lambda c: c["search"].update(explorationBps=40001),
        lambda c: c["search"].update(trainingSamples=65),
        lambda c: c["resources"][0].update(capacity=0),
        lambda c: c["resources"].append(c["resources"][0]),
        lambda c: c["stages"][0].update(depends=[0]),
        lambda c: c["stages"][1].update(depends=[0, 0]),
        lambda c: c["stages"][0].update(resource=[]),
        lambda c: c["stages"][0].update(baseline=4),
        lambda c: c["stages"][0]["choices"][0].update(defectBps=-1),
        lambda c: c["stages"][0]["choices"][0].update(minutes=0),
        lambda c: c.update(title="\ud800"),
    ],
)
def test_invalid_scenarios_rejected(mutation):
    case = deepcopy(CASES[0])
    mutation(case)
    with pytest.raises(ValueError):
        validate(case)


@pytest.mark.parametrize(
    "raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b"\xff", b"[" * 30 + b"0" + b"]" * 30, b" " * 1_000_001]
)
def test_untrusted_json_is_bounded(raw):
    with pytest.raises((ValueError, RecursionError)):
        parse(raw)


def test_rehashed_forgery_is_not_accepted():
    report = evaluate(CASES[0])
    report["result"]["nodes"][0]["visits"] += 1
    report["sha256"] = digest({key: value for key, value in report.items() if key != "sha256"})
    with pytest.raises(ValueError, match="recomputation"):
        verify(report)


def test_evidence_is_complete_immutable_and_native_jobs_compile(tmp_path):
    from alpha_factory_v1.core.runtime.ascension import compile_plan

    report = evaluate(CASES[0])
    files = artifacts(report)
    target = write_bundle(report, tmp_path)
    assert len(files) == 6 and write_bundle(report, tmp_path) == target
    assert {p.name: p.read_bytes() for p in target.iterdir()} == files
    for job in report["result"]["jobs"]:
        assert report["result"]["inputSha256"] in job["goal"]
    plan = compile_plan(report["result"]["jobs"])
    assert plan
    (target / "run.json").write_text("{}")
    with pytest.raises(ValueError, match="differs"):
        write_bundle(report, tmp_path)


def test_legacy_tree_counts_negative_rewards_once_and_branches():
    from alpha_factory_v1.demos.meta_agentic_tree_search_v0.mats.tree import Node, Tree

    root = Node([0])
    tree = Tree(root, exploration=0)
    first = Node([1], reward=-3)
    tree.add_child(tree.select(), first)
    tree.backprop(first)
    assert first.reward == -3 and first.visits == 1 and root.reward == -3
    second = Node([2], reward=-2)
    assert tree.select() is root
    tree.add_child(root, second)
    tree.backprop(second)
    assert root.reward == -5 and root.visits == 2 and tree.best_leaf() is second
    third = Node([3], reward=-10)
    tree.add_child(second, third)
    tree.backprop(third)
    assert tree.best_leaf() is first  # Internal nodes are never returned as leaves.
    with pytest.raises(ValueError):
        tree.add_child(first, root)


def test_legacy_csv_and_rng_are_isolated(tmp_path):
    from alpha_factory_v1.demos.meta_agentic_tree_search_v0.run_demo import run

    state = random.getstate()
    run(episodes=4, rewriter="random", seed=12, log_dir=tmp_path)
    assert random.getstate() == state
    rows = list(csv.reader(io.StringIO((tmp_path / "scores.csv").read_text())))
    assert len(rows) == 6 and all(len(row) == 3 for row in rows)
    with pytest.raises(ValueError):
        run(episodes=0)
    with pytest.raises(ValueError):
        run(exploration=float("nan"))
