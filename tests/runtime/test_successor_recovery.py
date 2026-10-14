# SPDX-License-Identifier: Apache-2.0
"""An interrupted final inspection recovers truthfully without replaying its effect."""

from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import mission
from alpha_factory_v1.core.runtime.successor.orchestration import rehearse, retained_result, show_run
from alpha_factory_v1.core.runtime.successor.protocol import RehearsalRequest
from alpha_factory_v1.core.runtime.successor.state import ActionGateway, ActionRequest, SuccessorStore


@pytest.mark.parametrize("failure", [KeyboardInterrupt, RuntimeError])
def test_interrupted_final_inspection_recovers_without_effect_replay(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: type[BaseException]
) -> None:
    request = RehearsalRequest(
        request_id="44444444-4444-4444-8444-444444444444", max_events=64, max_candidates=2, formation_trials=1
    )
    home = tmp_path / "home"
    calls = []
    original = ActionGateway.execute

    def interrupted(gateway: ActionGateway, action: ActionRequest) -> Any:
        calls.append(action.action_id)
        original(gateway, action)
        raise failure()

    monkeypatch.setattr(ActionGateway, "execute", interrupted)
    with pytest.raises((KeyboardInterrupt, ValueError)):
        rehearse(home, request)
    journal = Journal(home)
    before = show_run(journal, request.request_id)
    assert before["state"] in {"interrupted", "failed"}
    with pytest.raises(Conflict, match="explicitly"):
        rehearse(home, request)

    def observed(gateway: ActionGateway, action: ActionRequest) -> Any:
        calls.append(action.action_id)
        return original(gateway, action)

    monkeypatch.setattr(ActionGateway, "execute", observed)
    result = rehearse(home, request, resume=True)
    lifecycle = result["evidence"]["lifecycle"]
    assert calls == ["inspect-current-report"]
    assert lifecycle["fixture"]["action"] == ("uncertain" if failure is KeyboardInterrupt else "failed")
    assert lifecycle["fixture"]["inspection_success"] is False
    assert lifecycle["fixture"]["revocation_before_action"] == "not_exercised_after_interruption"
    state = lifecycle["state"]
    assert state["stopped"] is True
    assert state["resources"]["reserved"].get("action_units", 0) == 0
    assert state["resources"]["spent"]["action_units"] == 1
    assert state["grants"]["current-inspection"]["status"] == "revoked"
    assert "recover-interrupted-inspection" in state["operations"]
    if failure is KeyboardInterrupt:
        assert state["resources"]["unknown"] == ["inspect-current-report"]
        assert state["proofs"]["current-correctness"]["status"] == "impaired"
    assert lifecycle["restoration"]["active_proofs"] == lifecycle["restoration"]["active_grants"] == []
    assert result["evidence"]["production_authority"] is False
    assert show_run(journal, request.request_id)["state"] == "completed"
    head = journal.verify()
    assert retained_result(journal, request.request_id) == result
    assert rehearse(home, request) == result
    assert journal.verify() == head


@pytest.mark.parametrize("interruption", ["recovery", "portable-export"])
def test_finalization_resume_after_stop_never_remeasures_or_replays(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interruption: str
) -> None:
    request = RehearsalRequest(
        request_id="55555555-5555-4555-8555-555555555555", max_events=64, max_candidates=2, formation_trials=1
    )
    home = tmp_path / "home"
    original_recover, original_export = SuccessorStore.recover, SuccessorStore.export_portable

    def interrupted_recovery(store: SuccessorStore, *args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original_recover(store, *args, **kwargs)
        if kwargs.get("request_id") == "recover-queued":
            raise KeyboardInterrupt()
        return result

    def interrupted_export(store: SuccessorStore, *args: Any, **kwargs: Any) -> dict[str, Any]:
        original_export(store, *args, **kwargs)
        raise KeyboardInterrupt()

    if interruption == "recovery":
        monkeypatch.setattr(SuccessorStore, "recover", interrupted_recovery)
    else:
        monkeypatch.setattr(SuccessorStore, "export_portable", interrupted_export)
    with pytest.raises(KeyboardInterrupt):
        rehearse(home, request)
    journal = Journal(home)
    interrupted_run = show_run(journal, request.request_id)
    interrupted_state = journal.latest("@successor:mission-" + request.request_id)
    assert interrupted_run["state"] == "interrupted"
    assert interrupted_run["finalization"]["study_digest"]
    assert interrupted_state["stopped"] is True
    assert interrupted_state["actions"]["inspect-current-report"]["state"] == "completed"
    monkeypatch.setattr(SuccessorStore, "recover", original_recover)
    monkeypatch.setattr(SuccessorStore, "export_portable", original_export)

    def forbidden_reexecution(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("evidence finalization cannot remeasure or replay a completed effect")

    monkeypatch.setattr(mission, "run_study", forbidden_reexecution)
    monkeypatch.setattr(ActionGateway, "execute", forbidden_reexecution)
    result = rehearse(home, request, resume=True)
    lifecycle = result["evidence"]["lifecycle"]
    assert result["evidence"]["study"] == interrupted_run["study"]
    assert lifecycle["fixture"]["action"] == "completed"
    assert lifecycle["state"]["resources"] == interrupted_state["resources"]
    assert lifecycle["state"]["actions"] == interrupted_state["actions"]
    assert lifecycle["state"]["grants"]["current-inspection"]["status"] == "revoked"
    assert lifecycle["state"]["stopped"] is True
    assert lifecycle["restoration"]["active_proofs"] == lifecycle["restoration"]["active_grants"] == []
    assert lifecycle["portable"]["payload"]["active_proofs"] == lifecycle["portable"]["payload"]["active_grants"] == []


@pytest.mark.parametrize("interruption", ["tool-completion", "acceptance"])
def test_completed_phase_resume_preserves_measurements_without_new_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, interruption: str
) -> None:
    from alpha_factory_v1.core.runtime.successor.jobs import JobDispatcher

    request = RehearsalRequest(
        request_id="66666666-6666-4666-8666-666666666666", max_events=64, max_candidates=2, formation_trials=1
    )
    home = tmp_path / "home"
    original_execute, original_complete = JobDispatcher.execute_tool, JobDispatcher.complete
    original_examine = mission.examine
    measurements: list[dict[str, Any]] = []

    def measured(*args: Any, **kwargs: Any) -> dict[str, Any]:
        result = original_examine(*args, **kwargs)
        measurements.append(result)
        return result

    def interrupted_tool(dispatcher: JobDispatcher, job_id: str, **kwargs: Any) -> Any:
        result = original_execute(dispatcher, job_id, **kwargs)
        if job_id == "verification":
            raise KeyboardInterrupt()
        return result

    def interrupted_acceptance(dispatcher: JobDispatcher, envelope: Any) -> dict[str, Any]:
        result = original_complete(dispatcher, envelope)
        if envelope.payload["job_id"] == "verification":
            raise KeyboardInterrupt()
        return result

    monkeypatch.setattr(mission, "examine", measured)
    if interruption == "tool-completion":
        monkeypatch.setattr(JobDispatcher, "execute_tool", interrupted_tool)
    else:
        monkeypatch.setattr(JobDispatcher, "complete", interrupted_acceptance)
    with pytest.raises(KeyboardInterrupt):
        rehearse(home, request)
    assert len(measurements) == 1
    journal = Journal(home)
    phases = show_run(journal, request.request_id)["phases"]
    assert "verification" not in phases
    completed_subject = phases["formation"]["freeze"]
    monkeypatch.setattr(JobDispatcher, "execute_tool", original_execute)
    monkeypatch.setattr(JobDispatcher, "complete", original_complete)

    def forbidden_remeasurement(*args: Any, **kwargs: Any) -> Any:
        if args[0] == completed_subject:
            raise AssertionError("completed proof measurements must be retained without reexecution")
        return original_examine(*args, **kwargs)

    monkeypatch.setattr(mission, "examine", forbidden_remeasurement)
    result = rehearse(home, request, resume=True)
    lifecycle = result["evidence"]["lifecycle"]
    assert result["evidence"]["study"]["generation_one"]["proof"] == measurements[0]
    assert len(lifecycle["job_graph"]["runs"]["verification"]) == 1
    assert lifecycle["state"]["resources"]["spent"]["job_units"] == 7
    assert lifecycle["state"]["resources"]["reserved"]["job_units"] == 0
    assert lifecycle["state"]["resources"]["unknown"] == ["revoked-queued-inspection"]
    assert result["evidence"]["production_authority"] is False
    assert journal.verify()["valid"]
