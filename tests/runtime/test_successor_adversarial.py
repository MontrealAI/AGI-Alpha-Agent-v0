# SPDX-License-Identifier: Apache-2.0
"""Independent cross-boundary attacks: immutable trials, custody and inherited rights."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from alpha_factory_v1.core.runtime.store import Journal
from alpha_factory_v1.core.runtime.successor import evaluation
from alpha_factory_v1.core.runtime.successor.aggregation import BETA, CURRENT, aggregate, execute
from alpha_factory_v1.core.runtime.successor.mission import discover
from alpha_factory_v1.core.runtime.successor.protocol import (
    AdmissionDecision,
    AuthorityEnvelope,
    CandidateReleaseManifest,
    EvidenceRecord,
    Institution,
    MemoryAdmission,
    MissionConstitution,
    ProofReceipt,
    RehearsalRequest,
    VerifierDisclosure,
    canonical,
    digest,
)
from alpha_factory_v1.core.runtime.successor.state import ActionRequest, EvidenceSubmission, SuccessorStore
from alpha_factory_v1.core.runtime.successor.trust import (
    JournalCheckpoint,
    TrustAnchor,
    TrustRegistry,
    local_principals,
    sign_record,
)

MISSION = "streaming-metrics-v1"
OWNER = "local-controller"
FUTURE = "2099-01-01T00:00:00Z"


@pytest.fixture(scope="module")
def frozen_candidate() -> dict[str, Any]:
    request = RehearsalRequest(
        request_id="7eaa8650-a521-4dd6-913d-ddd18e87aec1",
        max_events=64,
        max_candidates=2,
        formation_trials=1,
    )
    return cast(dict[str, Any], discover(request)["freeze"])


def test_trial_uses_private_snapshot_when_caller_mutates_freeze(
    frozen_candidate: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    supplied = deepcopy(frozen_candidate)
    original_release = supplied["release_digest"]
    original_program = deepcopy(supplied["manifest"]["program"])
    observed_programs: list[dict[str, Any]] = []
    original_execute = execute

    def observe(events: Any, artifact: dict[str, Any]) -> list[dict[str, Any]]:
        if artifact not in (CURRENT, BETA):
            observed_programs.append(deepcopy(artifact))
        return original_execute(events, artifact)

    def mutate_callers_copy() -> None:
        supplied["manifest"]["program"]["layout"] = "nested" if original_program["layout"] == "tuple" else "tuple"
        supplied["release_digest"] = "f" * 64

    monkeypatch.setattr(evaluation, "execute", observe)
    proof = evaluation.evaluate_frozen(supplied, mutate_callers_copy)
    assert proof["release_digest"] == original_release
    assert observed_programs and all(artifact == original_program for artifact in observed_programs)
    assert supplied["release_digest"] != original_release


def test_protected_values_are_not_exposed_in_report_or_callbacks(
    frozen_candidate: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    canary = "private-case-canary-73d6e3"
    original_workload = evaluation.workload
    generated_seeds: list[int] = []
    checkpoints: list[bool] = []

    def private_workload(seed: int, count: int, mode: int) -> list[dict[str, Any]]:
        generated_seeds.append(seed)
        values = original_workload(seed, count, mode)
        for value in values:
            value["service"] = canary + value["service"]
        return values

    monkeypatch.setattr(evaluation, "workload", private_workload)
    proof = evaluation.evaluate_frozen(deepcopy(frozen_candidate), lambda: checkpoints.append(True))
    encoded = canonical(proof)
    assert checkpoints and len(generated_seeds) == 12
    assert len(set(generated_seeds)) == 12
    assert canary.encode() not in encoded
    assert all(str(seed).encode() not in encoded for seed in generated_seeds)
    assert proof["custody"]["protected_data_exported"] is False
    assert proof["decision"]["qualification_verdict"] == "HOLD"
    assert proof["failures"] == []


def test_instruction_shaped_input_stays_data_and_cannot_open_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "side-effect"
    instruction = "__import__('os').system('echo compromised')"
    events = [{"day": "ignore prior instructions", "service": instruction, "duration_us": 1, "ok": False}]
    untouched = deepcopy(events)

    def forbidden_open(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("bounded aggregation attempted filesystem access")

    with monkeypatch.context() as patch:
        patch.setattr("builtins.open", forbidden_open)
        output = aggregate(events, {"version": 1, "layout": "tuple", "cache_last": True, "update": "branch"})
    assert output[0]["service"] == instruction
    assert output[0]["error_count"] == 1
    assert events == untouched and not target.exists()


def store_with_evidence(tmp_path: Path) -> tuple[SuccessorStore, dict[str, Any]]:
    trust, keys = local_principals()
    store = SuccessorStore(Journal.initialize(tmp_path / "state"), trust)
    institution = Institution(
        id="rights-institution",
        controller=OWNER,
        constitution=MissionConstitution(mission_id=MISSION, owner=OWNER, objective="exact aggregation"),
    )
    store.create_institution(institution, {"calls": 10})
    return store, keys


def evidence(evidence_id: str, **changes: Any) -> EvidenceRecord:
    return EvidenceRecord.model_validate(
        {
            "evidence_id": evidence_id,
            "source": "public synthetic fixture for rights enforcement",
            "acquired_at": "2026-01-01T00:00:00Z",
            "content_digest": "a" * 64,
            "permitted_uses": ["formation"],
            "valid_until": FUTURE,
            "scope": MISSION,
            "uncertainty": "rights fixture; no mission superiority claim",
            "accepted_by": OWNER,
            **changes,
        }
    )


def submit(store: SuccessorStore, keys: dict[str, Any], record: EvidenceRecord) -> None:
    submission = EvidenceSubmission(institution_id="rights-institution", evidence=record)
    store.record_evidence(
        "rights-institution",
        sign_record(keys[OWNER], OWNER, "evidence", submission),
        request_id="record-" + record.evidence_id,
    )


@pytest.mark.parametrize("attack", ["rights", "restriction", "scope"])
def test_evidence_transform_cannot_widen_its_parents_permissions(tmp_path: Path, attack: str) -> None:
    store, keys = store_with_evidence(tmp_path)
    parent = evidence("parent", permitted_uses=["retention"], restrictions=["synthetic-only"])
    submit(store, keys, parent)
    values: dict[str, Any] = {
        "dependencies": ["parent"],
        "permitted_uses": ["retention"],
        "restrictions": ["synthetic-only"],
    }
    if attack == "rights":
        values["permitted_uses"] = ["formation"]
    elif attack == "restriction":
        values["restrictions"] = []
    else:
        values["scope"] = "another-mission"
    with pytest.raises(ValueError):
        submit(store, keys, evidence("derived", **values))
    saved = store.read("rights-institution")
    assert "derived" not in saved["evidence"] and "parent" in saved["evidence"]


def test_memory_scope_cannot_be_promoted_by_an_admission_label(tmp_path: Path) -> None:
    store, keys = store_with_evidence(tmp_path)
    submit(store, keys, evidence("source"))
    memory = MemoryAdmission(
        admission_id="memory",
        institution_id="rights-institution",
        principal=OWNER,
        artifact_digest="b" * 64,
        evidence_ids=["source"],
        permitted_uses=["formation"],
        scope="another-mission",
        rights=["synthetic-methods"],
        valid_until=FUTURE,
        retention_until=FUTURE,
        outcome="admit",
    )
    with pytest.raises(ValueError):
        store.admit_memory(
            "rights-institution", sign_record(keys[OWNER], OWNER, "memory-admission", memory), request_id="admit-memory"
        )
    assert store.read("rights-institution")["memory"] == {}


def test_two_hop_restore_retains_history_without_reactivating_influence(tmp_path: Path) -> None:
    original, keys = store_with_evidence(tmp_path)
    submit(original, keys, evidence("source"))
    memory = MemoryAdmission(
        admission_id="memory",
        institution_id="rights-institution",
        principal=OWNER,
        artifact_digest="b" * 64,
        evidence_ids=["source"],
        permitted_uses=["formation"],
        scope=MISSION,
        rights=["synthetic-methods"],
        valid_until=FUTURE,
        retention_until=FUTURE,
        outcome="admit",
    )
    original.admit_memory(
        "rights-institution", sign_record(keys[OWNER], OWNER, "memory-admission", memory), request_id="memory"
    )
    source = original
    for hop in range(2):
        package = source.export_portable("rights-institution")
        checkpoint = JournalCheckpoint.capture(source.journal)
        destination = SuccessorStore(Journal.initialize(tmp_path / f"restore-{hop}"), original.trust)
        restored = destination.restore_portable(
            package, {"calls": 10}, source_public_key=source.journal.public, checkpoint=checkpoint
        )
        assert restored["proofs"] == restored["grants"] == restored["memory"] == restored["evidence"] == {}
        assert restored["serving_release"] is None and restored["stopped"] is True
        assert len(restored["historical_records"]["evidence"]) == 1
        assert len(restored["historical_records"]["memory"]) == 1
        historical = restored["historical_records"]["memory"][0]
        assert historical["status"] == "historical"
        assert historical["envelope"]["payload"] == memory.model_dump()
        source = destination


def operational_fixture(tmp_path: Path) -> tuple[SuccessorStore, dict[str, Any], str]:
    """Signed local role fixture tests authorization; its proof is not a scientific measurement."""
    registry, keys = local_principals()
    outsider = Ed25519PrivateKey.generate()
    keys["other-controller"] = outsider
    anchors = {
        principal: registry.anchor(principal, role)
        for principal, role in ((OWNER, "controller"), ("local-producer", "producer"), ("local-verifier", "verifier"))
    }
    anchors["other-controller"] = TrustAnchor(
        outsider.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex(), frozenset({"controller"})
    )
    store = SuccessorStore(Journal.initialize(tmp_path / "state"), TrustRegistry(anchors))
    store.create_institution(
        Institution(
            id="rights-institution",
            controller=OWNER,
            constitution=MissionConstitution(
                mission_id=MISSION,
                owner=OWNER,
                objective="bounded authorization fixture",
                authority_ceiling="sandbox",
                proof_requirements=["correctness"],
            ),
        ),
        {"calls": 10, "work_units": 10},
    )
    submit(store, keys, evidence("source", permitted_uses=["proof"]))
    release = CandidateReleaseManifest(
        release_id="fixture-release",
        institution_id="rights-institution",
        mission_id=MISSION,
        producer="local-producer",
        environment_digest="b" * 64,
    )
    store.register_release("rights-institution", release, request_id="freeze")
    release_hash = digest("release", release)
    proof = ProofReceipt(
        proof_id="fixture-proof",
        institution_id="rights-institution",
        mission_id=MISSION,
        release_digest=release_hash,
        environment_digest=release.environment_digest,
        verifier="local-verifier",
        valid_until=FUTURE,
        outcome="pass",
        claim="correctness",
        dependency_digests=["a" * 64],
        comparator_manifest_digest="c" * 64,
        protocol_digest="d" * 64,
        evidence_commitment="e" * 64,
        evaluation_units=1,
        issued_at="2026-01-01T00:00:00Z",
        disclosure=VerifierDisclosure(
            verifier="local-verifier",
            organization="same local test operator",
            control_separation="local role fixture",
            custodian="local-verifier",
            funding_and_conflicts="same local test operator",
            protocol_controller=OWNER,
            replication_status="not-replicated",
        ),
    )
    store.record_proof(
        "rights-institution", sign_record(keys["local-verifier"], "local-verifier", "proof", proof), request_id="proof"
    )
    decision = AdmissionDecision(
        decision_id="admit",
        institution_id="rights-institution",
        release_digest=release_hash,
        principal=OWNER,
        outcome="admit",
        proof_ids=[proof.proof_id],
    )
    store.admit("rights-institution", sign_record(keys[OWNER], OWNER, "admission", decision), request_id="admit")
    grant = AuthorityEnvelope(
        grant_id="grant",
        institution_id="rights-institution",
        mission_id=MISSION,
        release_digest=release_hash,
        subject="local-producer",
        issuer=OWNER,
        actions=["aggregate"],
        tools=["fixed-engine"],
        targets=["fixture"],
        resources={"calls": 10, "work_units": 10},
        proof_ids=[proof.proof_id],
        valid_until=FUTURE,
        context_digest="f" * 64,
        approval_required=True,
    )
    store.grant("rights-institution", sign_record(keys[OWNER], OWNER, "authority", grant), request_id="grant")
    store.cutover(
        "rights-institution",
        sign_record(keys[OWNER], OWNER, "cutover", {"release_digest": release_hash}),
        request_id="cutover",
        expected_revision=store.read("rights-institution")["revision"],
    )
    return store, keys, release_hash


def approved_action(
    release_hash: str, keys: dict[str, Any], *, principal: str = OWNER, **changes: Any
) -> ActionRequest:
    action = ActionRequest.model_validate(
        {
            "action_id": "act",
            "subject": "local-producer",
            "release_digest": release_hash,
            "environment_digest": "b" * 64,
            "action": "aggregate",
            "tool": "fixed-engine",
            "target": "fixture",
            "context_digest": "f" * 64,
            "resources": {"calls": 1, "work_units": 1},
            **changes,
        }
    )
    approval = sign_record(
        keys[principal],
        principal,
        "action-approval",
        {"action_digest": digest("action", action.model_dump(exclude={"approval"}))},
    )
    return action.model_copy(update={"approval": approval})


def test_another_institutions_controller_cannot_approve_this_action(tmp_path: Path) -> None:
    store, keys, release_hash = operational_fixture(tmp_path)
    with pytest.raises(ValueError):
        store.dispatch_action("rights-institution", approved_action(release_hash, keys, principal="other-controller"))
    store.dispatch_action("rights-institution", approved_action(release_hash, keys))
    assert store.read("rights-institution")["resources"]["reserved"] == {"calls": 1, "work_units": 1}


def test_omitting_a_resource_unit_cannot_avoid_its_reservation(tmp_path: Path) -> None:
    store, keys, release_hash = operational_fixture(tmp_path)
    with pytest.raises(ValueError):
        store.dispatch_action("rights-institution", approved_action(release_hash, keys, resources={"calls": 1}))
    assert store.read("rights-institution")["resources"]["reserved"] == {}
    store.dispatch_action("rights-institution", approved_action(release_hash, keys))
    assert store.read("rights-institution")["resources"]["reserved"]["work_units"] == 1


def test_revoked_explicit_proof_evidence_blocks_actions_without_memory_dependency(tmp_path: Path) -> None:
    store, keys, release_hash = operational_fixture(tmp_path)
    assert store.read("rights-institution")["releases"][release_hash]["memory_digests"] == []
    store.revoke_evidence(
        "rights-institution",
        sign_record(keys[OWNER], OWNER, "evidence-revocation", {"evidence_id": "source", "reason": "rights revoked"}),
        request_id="revoke-source",
    )
    with pytest.raises(ValueError):
        store.dispatch_action("rights-institution", approved_action(release_hash, keys))
    saved = store.read("rights-institution")
    assert "fixture-proof" in saved["proofs"] and "grant" in saved["grants"]
    assert saved["resources"]["reserved"] == {}
