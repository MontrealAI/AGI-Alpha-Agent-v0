# SPDX-License-Identifier: Apache-2.0
"""Actual solver/certificate tests, plus falsification of the evidence boundary."""

from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.retained_experience import experiment, solver, verifier
from alpha_factory_v1.core.runtime.retained_experience.controls import WarmStart
from alpha_factory_v1.core.runtime.retained_experience.operator import check_seal
from alpha_factory_v1.core.runtime.structural_transfer import eadarp

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def base() -> dict[str, Any]:
    value: dict[str, Any] = verifier.read(ROOT / "contrib/compounding_discovery/base-target.json")
    return value


@pytest.fixture(scope="module")
def history(base: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for value in ("1", "0.9"):
        target = deepcopy(base)
        target["id"] = "training-" + value
        target["updates"]["window_scale"] = value
        output = solver.solve(target, eadarp.compile_model(target))
        assert verifier.check_output(target, output)["accepted"] is True
        result.append({"target": target, "output": output})
    return result


@pytest.mark.parametrize("method,presolve", list(experiment.METHODS.values()))
def test_real_competent_reference_has_independent_optimality_evidence(
    base: dict[str, Any],
    method: str,
    presolve: bool,
) -> None:
    output = solver.solve(base, eadarp.compile_model(base), method, presolve)
    assert verifier.check_output(base, output)["accepted"] is True
    assert output["artifact"]["status"] == "FEASIBLE"


def test_fresh_schedule_is_constructed_without_solver_and_memory_stays_frozen(
    base: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    memory = solver.learn(history)
    before = verifier.hash_value(memory)
    task = deepcopy(base)
    task["id"] = "fresh-travel-change"
    task["updates"]["travel_multiplier"] = "0.99"
    output = solver.PreparedExperience(memory).run(task, eadarp.compile_model(task))
    assert output["solver_calls"] == 0
    assert output["artifact"]["task_hash"] != history[0]["output"]["artifact"]["task_hash"]
    assert verifier.check_output(task, output)["accepted"] is True
    assert verifier.hash_value(memory) == before
    assert verifier.fingerprint(task) not in {verifier.fingerprint(row["target"]) for row in history}


def test_negative_experience_builds_a_fresh_infeasibility_proof(
    base: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    task = deepcopy(base)
    task["id"] = "fresh-tight-window"
    task["updates"]["window_scale"] = "0.87"
    output = solver.apply(task, eadarp.compile_model(task), solver.learn(history))
    assert output["solver_calls"] == 0
    assert output["artifact"]["status"] == "INFEASIBLE"
    assert verifier.check_output(task, output)["accepted"] is True


def test_changed_coefficient_matrix_cannot_reuse_primal_basis(
    base: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    task = deepcopy(base)
    task["id"] = "fresh-matrix-change"
    task["updates"]["charge_multiplier"] = "0.81"
    memory = solver.learn([history[0]])
    output = solver.apply(task, eadarp.compile_model(task), memory)
    assert output["solver_calls"] > 0
    assert output["reuse"] == []
    assert verifier.check_output(task, output)["accepted"] is True


def test_memory_tampering_and_false_dual_proofs_are_refused(history: list[dict[str, Any]]) -> None:
    memory = solver.learn(history)
    memory["assets"][0]["inverse"][0][0] = "900"
    with pytest.raises(ValueError, match="memory changed"):
        solver.PreparedExperience(memory)
    output = deepcopy(history[0]["output"])
    output["duals"] = []
    assert verifier.check_output(history[0]["target"], output)["accepted"] is False


def test_rehashed_false_learning_provenance_is_independently_refused(history: list[dict[str, Any]]) -> None:
    memory = solver.learn(history)
    verifier.check_memory(memory, history)
    memory["assets"][0]["inverse"][0][0] = "900"
    memory["memory_hash"] = verifier.hash_value({k: v for k, v in memory.items() if k != "memory_hash"})
    with pytest.raises(ValueError, match="does not invert"):
        verifier.check_memory(memory, history)
    output = deepcopy(history[0]["output"])
    name = next(iter(output["duals"][0]))
    output["duals"][0][name] = "1"
    assert verifier.check_output(history[0]["target"], output)["accepted"] is False


def test_renaming_and_decimal_reformatting_do_not_create_fresh_work(base: dict[str, Any]) -> None:
    renamed = deepcopy(base)
    renamed["id"], renamed["need"] = "different-name", "different prose"
    renamed["updates"] = {k: v + ".000" if "." not in v else v for k, v in renamed["updates"].items()}
    renamed["instance_text"] = "\n".join("  ".join(line.split()) for line in base["instance_text"].splitlines())
    renamed["instance_sha256"] = hashlib.sha256(renamed["instance_text"].encode()).hexdigest()
    assert verifier.fingerprint(renamed) == verifier.fingerprint(base)


def test_conventional_warm_start_gets_same_history_and_restores_its_basis(
    base: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    warm = WarmStart(history)
    first = warm.run(base, eadarp.compile_model(base), "highs", True)
    assert verifier.check_output(base, first)["accepted"] is True
    adverse = history[1]["target"]
    assert (
        verifier.check_output(adverse, warm.run(adverse, eadarp.compile_model(adverse), "highs", True))["accepted"]
        is True
    )
    final = warm.run(base, eadarp.compile_model(base), "highs", True)
    assert final["artifact"] == first["artifact"]


@pytest.mark.parametrize("count,repeats", [(0, 1), (17, 1), (1, 0), (True, 1)])
def test_invalid_resource_panels_fail_before_creating_work(count: int, repeats: int) -> None:
    with pytest.raises(ValueError):
        experiment.protocol(count, repeats)


def test_full_native_experiment_preserves_denominator_cost_unknowns_and_tampering(
    base: dict[str, Any],
    tmp_path: Path,
) -> None:
    directory = tmp_path / "trial"
    summary = experiment.run(base, directory, count=1, repeats=1)
    assert summary["audit"]["observed"] == 4 * len(experiment.ARMS)
    assert summary["audit"]["candidate_write_denied_by_os"] is True
    assert summary["audit"]["new_socket_denied_by_os"] is True
    assert summary["audit"]["candidate_imported"] is False
    assert summary["complete_cost_advantage"] is None
    assert summary["confirmation"] is False
    assert summary["profit_established"] is False
    seal = experiment.file_hash(directory / "evidence-seal.json")
    check_seal(directory, seal)
    observations = directory / "observations.jsonl"
    original_observations = observations.read_text()
    observations.write_text("\n".join(original_observations.splitlines()[:-1]) + "\n")
    with pytest.raises(ValueError, match="planned observations missing"):
        verifier.verify(directory, experiment.file_hash(directory / "freeze.json"))
    observations.write_text(original_observations)
    with pytest.raises(FileExistsError):
        experiment.run(base, directory, count=1, repeats=1)
    costs = directory / "cost-policy.json"
    costs.write_text(costs.read_text().replace('"shared_development_usd":null', '"shared_development_usd":"0"'))
    with pytest.raises(ValueError, match="sealed evidence changed"):
        check_seal(directory, seal)


def test_original_precision_failure_is_preserved_and_current_producer_is_checked() -> None:
    directory = ROOT / "evidence/retained-experience-20261029/development-smoke-v1"
    tasks = verifier.read(directory / "tasks.json")
    target = next(task for task in tasks if task["id"] == "fresh-continuity-0")
    original = next(
        __import__("json").loads(line)
        for line in (directory / "observations.jsonl").read_text().splitlines()
        if __import__("json").loads(line)["arm"] == "highs-ipm-0"
        and __import__("json").loads(line)["task_hash"] == verifier.hash_value(target)
    )
    assert original["acceptance"]["accepted"] is False
    output = solver.solve(target, eadarp.compile_model(target), "highs-ipm", False)
    assert verifier.check_output(target, output)["accepted"] is True


def test_completely_declared_large_candidate_cost_cannot_be_hidden(tmp_path: Path) -> None:
    policy = experiment.protocol(1, 1)
    experiment.write(tmp_path / "protocol.json", policy)
    costs = experiment.default_costs()
    costs["shared_development_usd"] = "0"
    costs["arm_fixed_usd"] = {arm: "0" for arm in experiment.ARMS}
    costs["arm_per_task_usd"] = {arm: "0" for arm in experiment.ARMS}
    costs["arm_fixed_usd"]["retained"] = "1000000"
    observations, events = [], []
    for arm in experiment.ARMS:
        observations.append({"task_hash": "one", "arm": arm, "repeat": 0, "output": {"solver_calls": 0}})
        events.append({"task_hash": "one", "arm": arm, "repeat": 0, "cpu_ns": 1 if arm == "retained" else 100000})
    (tmp_path / "observations.jsonl").write_bytes(b"\n".join(verifier.canonical(x) for x in observations))
    (tmp_path / "costs.jsonl").write_bytes(b"\n".join(verifier.canonical(x) for x in events))
    experiment.write(tmp_path / "freeze.json", {})
    experiment.write(tmp_path / "tasks.json", [])
    audit = {"rejected": [], "process_cpu_ns": 0, "arm_check_cpu_ns": {arm: 0 for arm in experiment.ARMS}}
    result = experiment.summarize(
        tmp_path, dict.fromkeys(experiment.ARMS, 0), dict.fromkeys(experiment.ARMS, 0), costs, audit
    )
    assert result["measured_cpu_advantage"] is True
    assert result["complete_cost_advantage"] is False
    assert result["overall_demonstration"] != "SUPPORTED_MODELED_PANEL"
