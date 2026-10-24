# SPDX-License-Identifier: Apache-2.0
"""Source-study operation continuity, authority and honest measurement boundaries."""

import copy
import uuid

import pytest
from pydantic import ValidationError

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import campaign_operation as module
from alpha_factory_v1.core.runtime.successor.campaign_operation import CampaignOperation, OperationSpec, example
from alpha_factory_v1.core.runtime.successor.orchestration import _operator_lock
from alpha_factory_v1.core.runtime.successor.protocol import canonical


def setup(tmp_path, monkeypatch, **changes):
    clock = [1_000_000]
    monkeypatch.setattr(module, "_now", lambda: clock[0])
    raw = example().model_dump()
    raw.update(changes)
    spec = OperationSpec.model_validate(raw)
    operation = CampaignOperation(Journal.initialize(tmp_path / "agent"))
    operation.start(spec)
    return operation, spec, clock


def drain(operation, spec, clock):
    clock[0] += 15_000
    for _ in range(20):
        if operation.advance(spec.operation_id)["state"] == "completed":
            break
    assert operation.show(spec.operation_id)["state"] == "completed"


def test_existing_queue_waits_for_arrivals_then_retains_frozen_policy_and_all_ancestors(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    for _ in range(3):
        operation.advance(spec.operation_id)
    parent = operation.experiment.show(spec.study.study_id)
    assert parent["state"] == "trained"
    assert parent["freeze"]["manifest"]["selected_policy"] == "direct-pair"
    before = operation.journal.verify()
    operation.advance(spec.operation_id)
    assert operation.journal.verify() == before
    drain(operation, spec, clock)
    exported = operation.export(spec.operation_id)
    assert len(exported["evidence"]["campaigns"]) == 12
    assert exported["active_authority"] == []
    assert exported["status"]["completed_mission_comparisons"] == 12
    assert exported["status"]["costs"]["search_units_including_ancestors"] > 0
    for child in exported["evidence"]["campaigns"].values():
        assert child["result"]["beats_unrestricted"] is False
    terminal = operation.show(spec.operation_id)
    assert operation.advance(spec.operation_id)["digest"] == terminal["digest"]
    assert operation.experiment.show(spec.study.study_id)["approval"] is None


def test_committed_child_is_reconciled_after_unclean_exit_without_remeasurement(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    original = operation.experiment._campaign
    completed = []

    def crash(*args):
        result = original(*args)
        completed.append(operation.experiment.loop.show(result["campaign_id"]))
        raise SystemExit("injected process death after child commit before parent attachment")

    monkeypatch.setattr(operation.experiment, "_campaign", crash)
    with pytest.raises(SystemExit):
        operation.advance(spec.operation_id)
    reopened = CampaignOperation(Journal(operation.journal.root))
    reopened.advance(spec.operation_id)
    retained = reopened.experiment.loop.show(completed[0]["request"]["campaign_id"])
    assert retained["digest"] == completed[0]["digest"]
    assert retained["revision"] == completed[0]["revision"]
    assert reopened.show(spec.operation_id)["attempts"][0]["unmeasured_crash_work"] is True
    drain(reopened, spec, clock)


def test_active_stop_fences_child_handoff_and_stale_worker(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    original = operation.experiment._campaign

    def stop_during_handoff(*args):
        result = original(*args)
        operation.stop(spec.operation_id)
        return result

    monkeypatch.setattr(operation.experiment, "_campaign", stop_during_handoff)
    with pytest.raises(Conflict):
        operation.advance(spec.operation_id)
    parent = operation.experiment.show(spec.study.study_id)
    assert parent["state"] == "canceled" and parent["approval"] is None
    assert operation.show(spec.operation_id)["state"] == "canceled"
    assert operation.advance(spec.operation_id)["state"] == "canceled"
    with pytest.raises(Conflict):
        CampaignOperation(Journal(operation.journal.root)).run(spec.operation_id)
    assert parent["training"]["runs"] == []


def test_operator_pause_is_durable_and_does_not_extend_deadline(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    deadline = operation.show(spec.operation_id)["expires_ms"]
    operation.journal.control(True)
    with pytest.raises(Conflict, match="STOP"):
        operation.advance(spec.operation_id)
    reopened = CampaignOperation(Journal(operation.journal.root))
    with pytest.raises(Conflict, match="STOP"):
        reopened.advance(spec.operation_id)
    reopened.journal.control(False)
    reopened.advance(spec.operation_id)
    assert reopened.show(spec.operation_id)["expires_ms"] == deadline
    clock[0] = deadline
    with pytest.raises(Conflict, match="expired"):
        reopened.advance(spec.operation_id)


def test_private_restore_preserves_history_but_cannot_restore_operation_permission(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    operation.advance(spec.operation_id)
    backup = tmp_path / "private.zip"
    operation.journal.backup(backup)
    restored = Journal.restore(backup, tmp_path / "restored")
    source = operation.journal.root / operation.show(spec.operation_id)["input_file"]
    target = restored.root / source.name
    target.write_bytes(source.read_bytes())
    other = CampaignOperation(restored)
    with pytest.raises(Conflict, match="restored elsewhere"):
        other.advance(spec.operation_id)
    assert other.experiment.show(spec.study.study_id)["training"]["runs"]


def test_submitted_file_replacement_and_changed_source_do_not_gain_permission(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    raw = spec.model_dump()
    raw["confirmation"][0]["unit"]["terminal"][0]["claims"][0]["text"] = "Changed input after submission."
    path = operation.journal.root / operation.show(spec.operation_id)["input_file"]
    path.write_bytes(canonical(raw))
    with pytest.raises(Conflict, match="changed"):
        operation.advance(spec.operation_id)
    path.write_bytes(canonical(spec.model_dump()))
    monkeypatch.setattr(module, "_driver", lambda: "f" * 64)
    with pytest.raises(Conflict, match="changed"):
        operation.advance(spec.operation_id)


@pytest.mark.parametrize(
    "change",
    [
        {"total_search_units": 1},
        {"max_concurrency": True},
        {"max_concurrency": 2},
        {"max_attempts": 4},
        {"horizon_seconds": 1},
        {"allowed_effects": "network-and-shell"},
    ],
)
def test_out_of_envelope_inputs_are_rejected_before_work(change):
    raw = example().model_dump()
    raw.update(change)
    with pytest.raises(ValidationError):
        OperationSpec.model_validate(raw)


def test_exhausted_task_keeps_negative_outcomes_and_subsequent_work(tmp_path, monkeypatch):
    raw = example().model_dump()
    raw["study"]["charter"]["budgets"]["execution_units"] = 0
    for phase in ("training", "confirmation"):
        for item in raw[phase]:
            item["unit"]["request"]["charter"] = copy.deepcopy(raw["study"]["charter"])
    operation, spec, clock = setup(tmp_path, monkeypatch, **raw)
    drain(operation, spec, clock)
    status = operation.status(spec.operation_id)
    assert status["inconclusive"] == 12
    assert status["improvement_evidence"] is None
    assert (
        operation.experiment.show(spec.study.study_id)["freeze"]["manifest"]["selected_policy"]
        == spec.study.incumbent_policy
    )


def test_existing_operator_lock_rejects_second_worker_before_new_session(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    with _operator_lock(operation.journal), pytest.raises(Conflict):
        operation.run(spec.operation_id)
    assert operation.show(spec.operation_id)["sessions"] == []


def test_same_identity_cannot_replace_approved_scope(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    raw = spec.model_dump()
    raw["horizon_seconds"] += 10
    with pytest.raises(Conflict):
        operation.start(OperationSpec.model_validate(raw))
    assert operation.show(spec.operation_id)["expires_ms"] == clock[0] + spec.horizon_seconds * 1000


def test_arrival_cannot_be_run_through_another_study_entry_point(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)
    operation.experiment._reserve(spec.study.study_id, [arrival.unit for arrival in spec.training], "training")
    with pytest.raises(Conflict, match="not the due"):
        operation.experiment._run(spec.study.study_id, "training")


def test_repeated_process_death_consumes_finite_attempt_allowance(tmp_path, monkeypatch):
    operation, spec, clock = setup(tmp_path, monkeypatch)

    def die(*args):
        raise SystemExit("injected precomputation death")

    monkeypatch.setattr(operation.experiment, "_campaign", die)
    for _ in range(spec.max_attempts):
        with pytest.raises(SystemExit):
            operation.advance(spec.operation_id)
    stopped = operation.advance(spec.operation_id)
    assert stopped["state"] == "hold"
    assert stopped["failure"]["type"] == "AttemptBudgetExhausted"
    assert len(stopped["attempts"]) == spec.max_attempts
    assert operation.status(spec.operation_id)["needs_attention"] is True
