# SPDX-License-Identifier: Apache-2.0
"""Actual integrated computation, interruption, signed history and empty-authority restoration."""

from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor import mission
from alpha_factory_v1.core.runtime.successor.orchestration import rehearse, retained_result, show_run, write_demo
from alpha_factory_v1.core.runtime.successor.protocol import RehearsalRequest, canonical, digest, safe_json_loads
from alpha_factory_v1.core.runtime.successor.transport import read_document, verify_result


def bounded_request() -> RehearsalRequest:
    return RehearsalRequest(
        request_id="12345678-1234-4234-8234-123456789012", max_events=64, max_candidates=2, formation_trials=1
    )


def test_actual_complete_lifecycle_and_idempotent_replay(tmp_path: Path) -> None:
    home, output = tmp_path / "home", tmp_path / "evidence"
    request = bounded_request()
    summary = write_demo(home, request, output)
    report = read_document(output / "result.json")
    journal = Journal(home)
    check = verify_result(report, request, journal.public)
    assert summary["qualification"] == "HOLD" and check["production_authority"] is False
    evidence = report["evidence"]
    study, lifecycle = evidence["study"], evidence["lifecycle"]
    assert study["generation_one"]["foundry"]["constructed"] >= 2
    assert len(study["generation_one"]["proof"]["units"]) == 12
    assert len(study["generation_two"]["trials"]) == 1
    assert lifecycle["fixture"]["revocation_before_action"] == "denied"
    assert lifecycle["restoration"]["identity_preserved"] is True
    assert lifecycle["restoration"]["active_proofs"] == lifecycle["restoration"]["active_grants"] == []
    portable = read_document(output / "portable.json")
    bundle = portable["payload"]["artifact_bundle"]
    restored_bundle = safe_json_loads(lifecycle["state"]["artifact_bundle_json"])
    assert bundle == restored_bundle
    assert bundle["entries"]["candidate"]["digest"] == study["generation_one"]["freeze"]["release_digest"]
    assert (
        bundle["entries"]["candidate"]["content"]["program"] == study["generation_one"]["foundry"]["selected_artifact"]
    )
    knowledge = bundle["entries"]["knowledge"]
    assert digest("memory", knowledge["content"]) == knowledge["digest"]
    assert lifecycle["restoration"]["restored_knowledge_digest"] == knowledge["digest"]
    assert lifecycle["restoration"]["canary_units"] == len(lifecycle["restoration"]["new_measurements"]) == 4
    assert lifecycle["restoration"]["supplier_equivalence"] is True
    assert lifecycle["restoration"]["knowledge_influence_admitted"] is False
    assert lifecycle["shadow_successor"]["active_grants"] == []
    assert len(lifecycle["job_graph"]["runs"]) == 7
    assert all(runs[-1]["result"]["accepted"] for runs in lifecycle["job_graph"]["runs"].values())
    head = journal.verify()
    assert rehearse(home, request) == report
    assert retained_result(Journal(home), request.request_id) == report
    assert journal.verify() == head
    assert not any(path.suffix == ".key" for path in output.iterdir())
    assert b"private_key" not in canonical(read_document(output / "portable.json"))
    changed = request.model_copy(update={"seed": 99})
    with pytest.raises(Conflict, match="different"):
        rehearse(home, changed)


def test_interrupted_verification_requires_explicit_recovery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home, request = tmp_path / "home", bounded_request()
    original = mission.examine

    def interrupted(*args: Any, **kwargs: Any) -> Any:
        raise KeyboardInterrupt()

    monkeypatch.setattr(mission, "examine", interrupted)
    with pytest.raises(KeyboardInterrupt):
        rehearse(home, request)
    journal = Journal(home)
    before = show_run(journal, request.request_id)
    assert before["state"] == "interrupted"
    assert set(before["phases"]) == {"constitution", "evidence", "formation", "challenge"}
    with pytest.raises(Conflict, match="explicitly"):
        rehearse(home, request)
    monkeypatch.setattr(mission, "examine", original)
    result = rehearse(home, request, resume=True)
    after = show_run(journal, request.request_id)
    assert after["state"] == "completed"
    assert after["phases"]["formation"] == before["phases"]["formation"]
    attempts = result["evidence"]["lifecycle"]["job_graph"]["runs"]["verification"]
    assert len(attempts) == 2
    assert attempts[0]["state"] == "uncertain" and attempts[1]["state"] == "completed"
    assert result["evidence"]["lifecycle"]["state"]["resources"]["spent"]["job_units"] == 8


def test_memory_evidence_revoked_after_admission_blocks_actual_generation_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alpha_factory_v1.core.runtime.successor.orchestration import CONTROLLER
    from alpha_factory_v1.core.runtime.successor.state import SuccessorStore
    from alpha_factory_v1.core.runtime.successor.trust import retained_local_principals, sign_record

    home, request = tmp_path / "home", bounded_request()
    original_renew, original_discover = mission.renew_study, mission.discover
    formation_seeds: list[int] = []

    def measured_discover(request: RehearsalRequest, *args: Any, **kwargs: Any) -> dict[str, Any]:
        formation_seeds.append(request.seed)
        return original_discover(request, *args, **kwargs)

    def revoke_before_influence(*args: Any, **kwargs: Any) -> dict[str, Any]:
        journal = Journal(home)
        trust, keys = retained_local_principals(home / "successor-principals")
        store = SuccessorStore(journal, trust)
        institution_id = "mission-" + request.request_id
        admitted = show_run(journal, request.request_id)["phases"]["admission"]
        assert admitted["memory_admission"]["outcome"] == "admit"
        store.revoke_evidence(
            institution_id,
            sign_record(
                keys[CONTROLLER],
                CONTROLLER,
                "evidence-revocation",
                {"evidence_id": "formation-methods", "reason": "rights revoked after admission before influence"},
            ),
            request_id="revoke-memory-before-renewal",
        )
        return original_renew(*args, **kwargs)

    monkeypatch.setattr(mission, "discover", measured_discover)
    monkeypatch.setattr(mission, "renew_study", revoke_before_influence)
    with pytest.raises(ValueError, match="bounded job tool failed") as rejected:
        rehearse(home, request)
    assert rejected.value.__cause__ is not None
    assert any(word in str(rejected.value.__cause__) for word in ("evidence", "memory", "revoked"))
    record = show_run(Journal(home), request.request_id)
    assert record["state"] == "failed"
    assert "admission" in record["phases"] and "renewal" not in record["phases"]
    assert "result" not in record
    assert formation_seeds == [request.seed]
