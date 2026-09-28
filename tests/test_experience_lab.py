# SPDX-License-Identifier: Apache-2.0
"""Independent oracles and adversarial boundaries for experience learning."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys

import pytest

from alpha_factory_v1.demos.era_of_experience.lab import (
    Random,
    artifacts,
    canonical,
    digest,
    evaluate,
    observe,
    parse,
    read_json,
    validate,
    verify,
    write_bundle,
)

ROOT = Path(__file__).resolve().parents[1]
CASES = read_json(ROOT / "alpha_factory_v1/demos/era_of_experience/scenarios.json")


@pytest.mark.parametrize("case", CASES, ids=lambda c: c["id"])
def test_reproducible_and_frozen(case: dict) -> None:
    state = random.getstate()
    report = evaluate(case)
    assert random.getstate() == state
    assert report == evaluate(case) == verify(report)
    result = report["result"]
    assert result["proposal"]["activePolicy"] == [c["baseline"] for c in case["contexts"]]
    assert result["proposal"]["state"] == "UNAPPROVED"
    assert result["status"] == ("HOLD_BASELINE" if case["id"] == "reward-trap" else "REVIEW_REQUIRED")
    for ci, row in enumerate(result["memory"]):
        for ai, memory in enumerate(row):
            observed = [
                event["reward"] for event in result["training"] if event["context"] == ci and event["action"] == ai
            ]
            window = case["training"]["memoryWindow"]
            assert memory == observed[-window:]
            assert result["visitCounts"][ci][ai] == len(observed)
    for name in ("evaluation", "retention"):
        suite = result[name]
        assert len(suite["episodes"]) == case["training"]["evaluationSteps"]
        for policy in ("baseline", "candidate"):
            for metric, total in suite["totals"][policy].items():
                assert total == sum(event[policy][metric] for event in suite["episodes"])


def test_deterministic_environment_has_an_exact_policy_and_reward_oracle() -> None:
    case = deepcopy(CASES[0])
    case["contexts"] = [case["contexts"][0]]
    case["training"].update(steps=12, evaluationSteps=30, explorationBps=0, memoryWindow=3)
    case["contexts"][0]["initial"] = [
        {"successBps": 10000, "incidentBps": 0, "cost": cost, "proxy": 0} for cost in [100, 10, 80]
    ]
    case["contexts"][0]["shifted"] = deepcopy(case["contexts"][0]["initial"])
    report = evaluate(case)["result"]
    assert [e["action"] for e in report["training"]] == [0, 1, 2] + [1] * 9
    assert report["proposal"]["candidatePolicy"] == [1]
    assert report["evaluation"]["totals"]["candidate"]["reward"] == 950 * 30
    assert report["gainTotal"] == 450 * 30
    assert report["visitCounts"] == [[1, 10, 1]]
    assert report["memory"] == [[[500], [950, 950, 950], [600]]]
    assert not next(g for g in report["gates"] if g["id"] == "coverage")["passed"]


def test_evaluation_cannot_change_learning_or_memory() -> None:
    case = deepcopy(CASES[0])
    original = evaluate(case)["result"]
    case["training"]["evaluationSteps"] = 600
    changed = evaluate(case)["result"]
    for name in ("training", "memory", "visitCounts"):
        assert original[name] == changed[name]
    assert original["proposal"]["candidatePolicy"] == changed["proposal"]["candidatePolicy"]
    # Future simulator settings do not enter learning before a shift occurs.
    for context in case["contexts"]:
        context["shifted"][1]["successBps"] = 0
    assert evaluate(case)["result"]["training"] == original["training"]


def test_reward_hacking_does_not_bypass_independent_safety_gate() -> None:
    result = evaluate(CASES[2])["result"]
    assert result["gainTotal"] > 0
    assert result["proposal"]["candidatePolicy"] == [1, 1, 1]
    assert result["status"] == "HOLD_BASELINE"
    assert [g["id"] for g in result["gates"] if not g["passed"]] == ["safety"]


def test_identical_policies_receive_identical_paired_outcomes() -> None:
    case = deepcopy(CASES[0])
    chosen = evaluate(case)["result"]["proposal"]["candidatePolicy"]
    for context, action in zip(case["contexts"], chosen):
        context["baseline"] = action
    result = evaluate(case)["result"]
    assert result["gainTotal"] == result["retentionGainTotal"] == 0
    for suite in ("evaluation", "retention"):
        for episode in result[suite]["episodes"]:
            assert episode["candidate"] == episode["baseline"]


def test_seed_stream_and_grounded_reward_have_exact_oracles() -> None:
    stream = Random(1)
    assert [stream.next() for _ in range(5)] == [270369, 67634689, 2647435461, 307599695, 2398689233]
    assert observe(
        {"successBps": 5000, "incidentBps": 100, "cost": 30, "proxy": 4},
        (4999, 99),
        {"costWeight": 2, "incidentPenalty": 100, "proxyWeight": 3},
    ) == {"success": 1, "incident": 1, "cost": 30, "proxy": 4, "reward": 852}


@pytest.mark.parametrize(
    "change",
    [
        "schema",
        "unknown",
        "seed",
        "bool",
        "negative",
        "overflow",
        "shift",
        "duplicate",
        "matrix",
        "unicode",
        "control",
        "empty",
    ],
)
def test_invalid_scenarios_fail_closed(change: str) -> None:
    case = deepcopy(CASES[0])
    if change == "schema":
        case["schema"] = "future"
    elif change == "unknown":
        case["liveUrl"] = "https://example.com"
    elif change == "seed":
        case["seed"] = 0
    elif change == "bool":
        case["training"]["steps"] = True
    elif change == "negative":
        case["reward"]["incidentPenalty"] = -1
    elif change == "overflow":
        case["training"]["steps"] = 601
    elif change == "shift":
        case["training"]["shiftAt"] = 241
    elif change == "duplicate":
        case["actions"][1]["id"] = case["actions"][0]["id"]
    elif change == "matrix":
        case["contexts"][0]["initial"].pop()
    elif change == "unicode":
        case["note"] = "\ud800"
    elif change == "control":
        case["title"] = "hidden\nfield"
    elif change == "empty":
        case["contexts"] = []
    with pytest.raises(ValueError):
        validate(case)


@pytest.mark.parametrize(
    "raw",
    [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1e999}', b'"\\ud800"', b"\xff", b"[" * 30 + b"]" * 30, b" " * 1000001],
)
def test_ambiguous_or_unbounded_json_is_rejected(raw: bytes) -> None:
    with pytest.raises(ValueError):
        parse(raw)


def test_every_result_field_is_recomputed_even_after_rehashing() -> None:
    report = evaluate(CASES[0])
    for field in ("memory", "training", "gates", "proposal", "evaluation", "jobs"):
        forged = deepcopy(report)
        forged["result"][field] = []
        forged["sha256"] = digest({key: value for key, value in forged.items() if key != "sha256"})
        with pytest.raises(ValueError, match="recomputation"):
            verify(forged)


def test_bundle_is_exact_and_never_overwrites_edited_runs(tmp_path: Path) -> None:
    report = evaluate(CASES[0])
    folder = write_bundle(report, tmp_path)
    assert write_bundle(report, tmp_path) == folder
    files = artifacts(report)
    assert {p.name for p in folder.iterdir()} == set(files)
    for line in files["SHA256SUMS"].decode().splitlines():
        sha, name = line.split("  ")
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == sha
    path = folder / "run.json"
    path.write_text("retain this edit")
    with pytest.raises(ValueError, match="differs"):
        write_bundle(report, tmp_path)
    assert path.read_text() == "retain this edit"


def test_native_cli_runs_with_only_the_standard_library(tmp_path: Path) -> None:
    code = (
        f"import sys; sys.path.insert(0,{str(ROOT)!r}); "
        "from alpha_factory_v1.demos.era_of_experience.lab_cli import main; "
        f"raise SystemExit(main(['--json','--output',{str(tmp_path)!r}]))"
    )
    run = subprocess.run(
        [sys.executable, "-I", "-S", "-c", code], capture_output=True, text=True, timeout=30, check=True
    )
    report = json.loads(run.stdout)
    assert canonical(report) == canonical(evaluate(CASES[0]))


def test_largest_supported_run_remains_importable() -> None:
    case = deepcopy(CASES[3])
    case["training"].update(steps=600, evaluationSteps=600, memoryWindow=200)
    report = evaluate(case)
    assert len(canonical(report)) < 1000000
    assert verify(parse(canonical(report))) == report
