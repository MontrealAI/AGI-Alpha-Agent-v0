# SPDX-License-Identifier: Apache-2.0
"""Adversarial regressions for the integrated compounding-discovery boundary."""

from __future__ import annotations

import copy
from itertools import product
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.compounding_discovery import engine
from alpha_factory_v1.core.runtime.compounding_discovery.programs import validate_program
from alpha_factory_v1.core.runtime.structural_transfer import adaptations, eadarp_check
from alpha_factory_v1.core.runtime.structural_transfer.engine import validate_mapping
from contrib.compounding_discovery.audit import (
    AuditError,
    audit_costs,
    audit_frozen_files,
    audit_matched_budgets,
    audit_memory,
    audit_result,
    audit_storage_receipts,
    digest,
)

HERE = Path(__file__).resolve().parent


def request(a: bool = False, s: bool = False, c: bool = False) -> dict[str, Any]:
    """Use real public passenger task bytes, not an arithmetic-success fixture."""
    return {
        "schema": "agialpha/discovery-request/v1",
        "id": "regression-public-route",
        "target": json.loads((HERE / "base-target.json").read_text()),
        "capabilities": {"A": a, "S": s, "C": c},
        "budget": {"operations": 200, "solver_calls": 32, "cpu_seconds": 60},
        "seed": 19,
    }


@pytest.fixture(scope="module")
def successful() -> tuple[dict[str, Any], dict[str, Any]]:
    value = request()
    result = engine.execute(value)
    assert result["acceptance"]["accepted"] is True
    assert result["artifact"]["status"] == "FEASIBLE"
    return value, result


def rejected(value: dict[str, Any]) -> None:
    """Require an explicit refusal, never an exception silently coerced to success."""
    try:
        result = engine.execute(value)
    except ValueError:
        return
    assert result["acceptance"]["accepted"] is False


@pytest.mark.parametrize("change", ["reverse-role", "unit", "numerical-conversion", "missing-role"])
def test_invalid_structural_mapping_is_not_promoted(change: str) -> None:
    principle = adaptations.adapter_spec("reserve-experience/v1")
    target = request()["target"]
    mapping: dict[str, Any] = {
        "variables": {"cash": "total_energy", "obligations": "consumed_energy", "free": "terminal_energy"},
        "bindings": [
            {
                "source_dimension": "currency",
                "source_unit": "microUSD",
                "target_dimension": "energy",
                "target_unit": "kWh",
                "mode": "structural-instantiation",
            }
        ],
    }
    assert validate_mapping(principle, target, mapping)["valid"] is True
    if change == "reverse-role":
        mapping["variables"]["cash"], mapping["variables"]["free"] = (
            mapping["variables"]["free"],
            mapping["variables"]["cash"],
        )
    elif change == "unit":
        mapping["bindings"][0]["target_unit"] = "joule"
    elif change == "numerical-conversion":
        mapping["bindings"][0]["mode"] = "currency-to-energy-conversion"
    else:
        del mapping["variables"]["obligations"]
    with pytest.raises(ValueError):
        validate_mapping(principle, target, mapping)


def test_negative_transfer_rejects_station_independence_outside_scope(successful: Any) -> None:
    value, result = copy.deepcopy(successful)
    value["target"]["assumptions"].remove("independent-vehicles-unlimited-station-concurrency")
    value["target"]["assumptions"].append("single-shared-charger-mutual-exclusion")
    assert eadarp_check.check(value["target"], result["artifact"])["accepted"] is False
    rejected(value)


@pytest.mark.parametrize("location", ["request", "target", "updates"])
def test_hidden_answer_fields_cannot_be_operational_inputs(location: str) -> None:
    value = request()
    destination = (
        value if location == "request" else value["target"] if location == "target" else value["target"]["updates"]
    )
    destination["hidden_labels"] = {"status": "FEASIBLE", "objective": "1"}
    rejected(value)


@pytest.mark.parametrize("field", ["arrival_kwh", "start_min", "charge_min", "objective"])
def test_final_independent_acceptance_rejects_corrupted_target_artifact(successful: Any, field: str) -> None:
    value, result = copy.deepcopy(successful)
    artifact = result["artifact"]
    if field == "objective":
        artifact[field] = "-1000000"
    else:
        artifact["vehicles"][0][field][1] = "-1000000"
    assert eadarp_check.check(value["target"], artifact)["accepted"] is False
    result["acceptance"]["accepted"] = True
    with pytest.raises(AuditError):
        audit_result(value, result, engine.source_hashes())


@pytest.mark.parametrize("field", ["accepted", "source_hashes", "request_hash"])
def test_evaluator_claim_and_source_tampering_are_detected(successful: Any, field: str) -> None:
    value, result = copy.deepcopy(successful)
    if field == "accepted":
        result["acceptance"][field] = "true"
    elif field == "source_hashes":
        key = next(iter(result[field]))
        result[field][key] = "0" * 64
    else:
        result[field] = "0" * 64
    with pytest.raises(AuditError):
        audit_result(value, result, engine.source_hashes())


def test_cost_duplication_and_claimed_line_totals_are_rejected(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    assert audit_costs(result["costs"], result["cost_total"])["events"] > 0
    result["costs"].append(copy.deepcopy(result["costs"][0]))
    with pytest.raises(AuditError, match="duplicate"):
        audit_costs(result["costs"], result["cost_total"])


def test_cost_line_multiplication_is_independent(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    result["costs"][0]["amount"] = "1000000"
    with pytest.raises(AuditError, match="quantity-times-rate"):
        audit_costs(result["costs"], result["cost_total"])


def test_all_eight_allocations_match_and_unequal_budgets_are_detected() -> None:
    rows = [{"request": request(a, s, c)} for a, s, c in product((False, True), repeat=3)]
    assert audit_matched_budgets(rows)["paired_blocks"] == 1
    rows[-1]["request"]["budget"]["solver_calls"] += 1
    with pytest.raises(AuditError, match="unequal permitted resource budgets"):
        audit_matched_budgets(rows)


def test_duplicate_arm_cannot_replace_missing_configuration() -> None:
    rows = [{"request": request(a, s, c)} for a, s, c in product((False, True), repeat=3)]
    rows[-1] = copy.deepcopy(rows[-2])
    with pytest.raises(AuditError):
        audit_matched_budgets(rows)


def test_false_earned_funding_rejected_even_with_positive_seed_cash(successful: Any) -> None:
    value, result = copy.deepcopy(successful)
    result["funding"] = {"earned": True, "source": "opening-seed-equity", "cash": "1000000"}
    with pytest.raises(AuditError, match="earned-funding"):
        audit_result(value, result, engine.source_hashes())


@pytest.mark.parametrize(
    "program",
    [
        {"op": "eval", "method": "highs", "presolve": True},
        {"op": "per-vehicle-lp", "method": "highs", "presolve": "true"},
        {"op": "per-vehicle-lp", "method": "highs", "presolve": True, "code": "raise SystemExit"},
    ],
)
def test_strategy_programs_cannot_add_code_or_evaluator_authority(program: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        validate_program(program)


def test_memory_corruption_cannot_be_loaded() -> None:
    memory = engine.empty_memory()
    memory["injected-future-label"] = {"accepted": True}
    with pytest.raises(ValueError):
        engine.validate_memory(memory)


def test_unsupported_memory_promotion_replays_acceptance(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    result["artifact"]["vehicles"][0]["arrival_kwh"][1] = "-1000000"
    result["acceptance"]["accepted"] = True
    with pytest.raises(ValueError):
        engine.learn(engine.empty_memory(), result)


def test_restart_recovery_preserves_result_and_rejects_changed_request(tmp_path: Path) -> None:
    value = request()
    root = tmp_path / "recovery"
    first = engine.resume(value, root)
    second = engine.resume(copy.deepcopy(value), root)
    assert first == second
    modified = copy.deepcopy(value)
    modified["seed"] += 1
    with pytest.raises((ValueError, FileExistsError)):
        engine.resume(modified, root)


def test_independent_audit_accepts_genuine_record(successful: Any) -> None:
    value, result = successful
    assert audit_result(value, result, engine.source_hashes())["target_accepted"] is True


def test_reviewer_freeze_detects_evaluator_byte_tampering(tmp_path: Path) -> None:
    import hashlib

    evaluator = tmp_path / "reviewer_evaluator.py"
    evaluator.write_text("def accepted(): return False\n")
    freeze = {str(evaluator): hashlib.sha256(evaluator.read_bytes()).hexdigest()}
    assert audit_frozen_files(freeze)["files"] == 1
    evaluator.write_text("def accepted(): return True\n")
    with pytest.raises(AuditError, match="altered"):
        audit_frozen_files(freeze)


def test_solver_call_exhaustion_never_escapes_resource_cap() -> None:
    value = request()
    value["budget"]["solver_calls"] = 1
    try:
        result = engine.execute(value)
    except ValueError:
        return
    assert result["resources"]["solver_calls"] <= 1
    assert result["acceptance"]["accepted"] is False


def test_restart_rejects_corrupt_completed_artifact(tmp_path: Path) -> None:
    value = request()
    root = tmp_path / "tampered-recovery"
    engine.resume(value, root)
    path = root / "result.json"
    saved = json.loads(path.read_text())
    saved["artifact"]["vehicles"][0]["arrival_kwh"][1] = "-1000000"
    saved["acceptance"]["accepted"] = True
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError):
        engine.resume(value, root)


def test_rehashed_memory_with_fabricated_parent_is_rejected(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    memory = engine.learn(engine.empty_memory(), result)
    memory["parent_hash"] = "0" * 64
    memory["memory_hash"] = digest({key: value for key, value in memory.items() if key != "memory_hash"})
    with pytest.raises(ValueError, match="parent|chronolog|lineage"):
        engine.validate_memory(memory)


@pytest.mark.parametrize("field,value", [("solver_calls", -1), ("cpu_seconds", "-1"), ("cpu_seconds", "0")])
def test_rehashed_underreported_resource_totals_cannot_be_promoted(successful: Any, field: str, value: Any) -> None:
    _, result = copy.deepcopy(successful)
    result["resources"][field] = value
    result["result_hash"] = digest({key: item for key, item in result.items() if key != "result_hash"})
    with pytest.raises(ValueError):
        engine.learn(engine.empty_memory(), result)


def test_chronological_promotion_cannot_attach_to_wrong_parent(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    memory = engine.learn(engine.empty_memory(), result)
    next_request = request()
    next_request["target"]["id"] = "regression-next-unrelated-order"
    stale = engine.execute(next_request, engine.empty_memory())
    with pytest.raises(ValueError, match="out-of-order"):
        engine.learn(memory, stale)


def test_retained_program_does_not_replay_old_feasible_answer_on_energy_failure(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    memory = engine.learn(engine.empty_memory(), result)
    next_request = request()
    next_request["target"]["id"] = "regression-new-energy-demand"
    next_request["target"]["updates"]["consumption_multiplier"] = "100"
    updated = engine.execute(next_request, memory)
    assert updated["memory_used"]
    assert updated["artifact"]["task_hash"] == digest(next_request["target"])
    assert updated["artifact"]["status"] == "INFEASIBLE"
    assert eadarp_check.check(next_request["target"], updated["artifact"])["accepted"] is True


def test_discovery_ordinary_mission_requires_review_before_signed_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alpha_factory_v1.core.runtime import engine as mission_engine
    from alpha_factory_v1.core.runtime.models import Mission
    from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest as journal_digest

    def forbidden_provider(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("offline discovery cannot call a model provider")

    monkeypatch.setattr(mission_engine, "synthesize", forbidden_provider)
    monkeypatch.setattr(mission_engine, "generate_code", forbidden_provider)
    value = request(s=True, c=True)
    mission = Mission.model_validate(
        {
            "goal": "Independently certify the public fixed passenger route through bounded discovery",
            "work": {"kind": "compounding-discovery", "request": value},
        }
    )
    journal = Journal.initialize(tmp_path / "mission-journal")
    runtime = mission_engine.Engine(journal)
    queued = journal.submit(mission)
    with pytest.raises(Conflict, match="approved"):
        runtime.export(queued["id"])
    review = runtime.execute(queued["id"])
    assert review["state"] == "review"
    assert review["result"]["acceptance"]["accepted"] is True
    assert eadarp_check.check(value["target"], review["result"]["artifact"])["accepted"] is True
    with pytest.raises(Conflict, match="approved"):
        runtime.export(review["id"])
    with pytest.raises(Conflict, match="hash"):
        runtime.review(review["id"], review["revision"], "0" * 64, True, "Attempted wrong output identity")
    completed = runtime.review(
        review["id"],
        review["revision"],
        journal_digest(review["result"]),
        True,
        "Reviewed exact independently checked sixteen-passenger mathematical certificate",
    )
    assert completed["state"] == "completed"
    exported = runtime.export(review["id"])
    assert mission_engine.verify_export(exported, journal.public)["valid"] is True
    tampered = copy.deepcopy(exported)
    tampered["receipt"]["body"]["document"]["result"]["artifact"]["objective"] = "-1000000"
    with pytest.raises(ValueError):
        mission_engine.verify_export(tampered, journal.public)


def test_independent_memory_audit_reconstructs_actual_promoted_state(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    memory = engine.learn(engine.empty_memory(), result)
    assert audit_memory(memory, engine.source_hashes())["version"] == 1
    next_request = request()
    next_request["target"]["id"] = "second-memory-audit-request"
    memory = engine.learn(memory, engine.execute(next_request, memory))
    assert audit_memory(memory, engine.source_hashes())["version"] == 2
    memory["parent_hash"] = "0" * 64
    memory["memory_hash"] = digest({key: value for key, value in memory.items() if key != "memory_hash"})
    with pytest.raises(AuditError, match="lineage"):
        audit_memory(memory, engine.source_hashes())


def test_rehashed_claim_of_unexecuted_invalid_transfer_cannot_be_promoted(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    result["request"]["capabilities"]["A"] = True
    result["request"]["mapping"] = {"variables": {}, "bindings": []}
    result["request_hash"] = digest(result["request"])
    result["result_hash"] = digest({key: item for key, item in result.items() if key != "result_hash"})
    with pytest.raises(ValueError):
        engine.learn(engine.empty_memory(), result)


def test_rehashed_unexecuted_programme_cannot_be_promoted(successful: Any) -> None:
    _, result = copy.deepcopy(successful)
    result["program"] = {"op": "eval", "method": "highs", "presolve": True}
    result["result_hash"] = digest({key: item for key, item in result.items() if key != "result_hash"})
    with pytest.raises(ValueError):
        engine.learn(engine.empty_memory(), result)


def test_rehashed_false_counterexample_acceptance_cannot_be_promoted() -> None:
    result = engine.execute(request(c=True))
    critique = next(item for item in result["critiques"] if "acceptance" in item)
    critique["artifact"]["objective"] = "-1000000"
    critique["acceptance"]["accepted"] = True
    result["result_hash"] = digest({key: item for key, item in result.items() if key != "result_hash"})
    with pytest.raises(ValueError):
        engine.learn(engine.empty_memory(), result)


def test_genuine_structural_transfer_execute_verify_learn_and_independent_audit() -> None:
    value = request(a=True, s=True, c=True)
    value["captures"] = [json.loads((HERE / "capture.json").read_text())]
    value["mapping"] = json.loads((HERE / "mapping.json").read_text())
    result = engine.execute(value)
    assert engine.verify_result(value, result)["accepted"] is True
    memory = engine.learn(engine.empty_memory(), result)
    assert memory["principles"] == value["captures"]
    assert memory["history"][0]["counterexamples"] == result["critiques"]
    assert audit_result(value, result, engine.source_hashes())["target_accepted"] is True
    assert audit_memory(memory, engine.source_hashes())["version"] == 1


def test_twelve_chronological_asc_tasks_preserve_full_evidence_within_memory_bound() -> None:
    from alpha_factory_v1.core.runtime.structural_transfer.contracts import MAX_BYTES, bounded, canonical

    memory = engine.empty_memory()
    captures = [json.loads((HERE / "capture.json").read_text())]
    mapping = json.loads((HERE / "mapping.json").read_text())
    for index in range(12):
        value = request(a=True, s=True, c=True)
        value["target"]["id"] = f"memory-bound-development-{index}"
        value["captures"], value["mapping"] = captures, mapping
        memory = engine.learn(memory, engine.execute(value, memory))
    assert memory["version"] == 12
    assert len(canonical(memory)) <= MAX_BYTES
    loaded = json.loads(canonical(memory))
    assert engine.validate_memory(loaded) == loaded
    assert audit_memory(loaded, engine.source_hashes())["independently_checked_history"] == 12
    bounded(loaded)
    for record, asset in zip(loaded["history"], loaded["assets"]):
        assert len(record["counterexamples"]) == 3
        assert asset["counterexamples"] == [
            {"kind": item["kind"], "record_hash": digest(item)} for item in record["counterexamples"]
        ]
        assert all("artifact" in item for item in record["counterexamples"])
    loaded["assets"][0]["counterexamples"][0]["record_hash"] = "0" * 64
    loaded["memory_hash"] = digest({key: value for key, value in loaded.items() if key != "memory_hash"})
    with pytest.raises(ValueError):
        engine.validate_memory(loaded)
    with pytest.raises(AuditError, match="references"):
        audit_memory(loaded, engine.source_hashes())


@pytest.mark.parametrize("free,accepted", [(199_999_999, False), (200_000_000, True)])
def test_prospective_storage_guard_enforces_exact_declared_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, free: int, accepted: bool
) -> None:
    from types import SimpleNamespace
    from contrib.compounding_discovery import experiment

    monkeypatch.setattr(experiment.shutil, "disk_usage", lambda _: SimpleNamespace(free=free))
    if accepted:
        record = experiment.storage_guard(tmp_path, "observation", "known-request")
        assert record["qualified"] is True
    else:
        with pytest.raises(experiment.StorageBoundary):
            experiment.storage_guard(tmp_path, "observation", "known-request")
        assert len(list(tmp_path.glob("resource-failure-*.json"))) == 1
    saved = json.loads((tmp_path / "resource-observations.jsonl").read_text())
    assert saved["free_bytes"] == free and saved["qualified"] is accepted


def test_low_storage_pauses_before_candidate_execution_preserving_incurred_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    from contrib.compounding_discovery import experiment

    monkeypatch.setattr(experiment.shutil, "disk_usage", lambda _: SimpleNamespace(free=199_999_999))
    prefix = tmp_path / "prior-incurred-cost.json"
    prefix.write_text('{"amount":"7/100"}\n')
    calls: list[str] = []

    def candidate(*args: Any, **kwargs: Any) -> None:
        calls.append("executed")
        raise AssertionError("candidate must not start below the storage reserve")

    with pytest.raises(experiment.StorageBoundary):
        experiment.observation(tmp_path / "next.json", request(), engine.empty_memory(), {}, candidate, tmp_path)
    assert calls == []
    assert prefix.read_text() == '{"amount":"7/100"}\n'
    assert not (tmp_path / "next.json.gz").exists()


def test_forged_or_unrelated_storage_receipts_cannot_qualify_executed_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace
    from contrib.compounding_discovery import experiment

    monkeypatch.setattr(experiment.shutil, "disk_usage", lambda _: SimpleNamespace(free=200_000_000))
    record = experiment.storage_guard(tmp_path, "observation", "known-request")
    freeze = {
        "resource_policy": {
            "preserve_free_disk_bytes": 200_000_000,
            "guard_version": "pre-observation-and-promotion/v1",
        }
    }
    observations = [{"request": {"id": "known-request"}, "storage_guard_id": record["id"]}]
    assert audit_storage_receipts(tmp_path, freeze, observations)["executed_edges_qualified"] is True
    observations[0]["request"]["id"] = "different-request"
    with pytest.raises(AuditError, match="matching"):
        audit_storage_receipts(tmp_path, freeze, observations)
    observations[0]["request"]["id"] = "known-request"
    record["free_bytes"] = 199_999_999
    (tmp_path / "resource-observations.jsonl").write_text(json.dumps(record) + "\n")
    with pytest.raises(AuditError, match="forged"):
        audit_storage_receipts(tmp_path, freeze, observations)
