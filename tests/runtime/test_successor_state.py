# SPDX-License-Identifier: Apache-2.0
"""Adversarial authority, concurrency, recovery, lineage and trust tests."""

import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.protocol import (
    AdmissionDecision,
    AuthorityEnvelope,
    BehaviorArtifact,
    CandidateReleaseManifest,
    EvidenceRecord,
    Institution,
    MemoryAdmission,
    MissionConstitution,
    ProofReceipt,
    VerifierDisclosure,
    digest,
)
from alpha_factory_v1.core.runtime.successor.state import (
    ActionGateway,
    ActionRequest,
    EvidenceSubmission,
    SuccessorStore,
)
from alpha_factory_v1.core.runtime.successor.trust import (
    JournalCheckpoint,
    local_principals,
    retained_local_principals,
    sign_record,
)

PAST = "2020-01-01T00:00:00Z"
FUTURE = "2099-01-01T00:00:00Z"
ENVIRONMENT = "1" * 64
CONTEXT = "2" * 64


def build_store(tmp_path: Path, budget: int = 10):
    journal = Journal.initialize(tmp_path / "agent")
    trust, keys = local_principals()
    store = SuccessorStore(journal, trust)
    institution = Institution(
        id="institution",
        controller="local-controller",
        constitution=MissionConstitution(
            mission_id="aggregation",
            owner="local-controller",
            objective="preserve exact aggregation behavior",
            proof_requirements=["correctness"],
            authority_ceiling="sandbox",
            prohibited_actions=["deploy"],
        ),
    )
    store.create_institution(institution, {"calls": budget})
    return store, keys


def add_release(store, keys, name="release-one", *, claim="correctness", grant_resources=10, scope="sandbox"):
    release = CandidateReleaseManifest(
        release_id=name,
        institution_id="institution",
        mission_id="aggregation",
        producer="local-producer",
        environment_digest=ENVIRONMENT,
        artifacts=[BehaviorArtifact(name="aggregate", role="source", digest=digest("source", name))],
    )
    store.register_release("institution", release, request_id="freeze-" + name)
    release_digest = digest("release", release)
    proof = ProofReceipt(
        proof_id="proof-" + name,
        institution_id="institution",
        mission_id="aggregation",
        release_digest=release_digest,
        environment_digest=ENVIRONMENT,
        verifier="local-verifier",
        valid_until=FUTURE,
        issued_at=PAST,
        outcome="pass",
        claim=claim,
        comparator_manifest_digest="3" * 64,
        protocol_digest="4" * 64,
        evidence_commitment="5" * 64,
        evaluation_units=12,
        disclosure=VerifierDisclosure(
            verifier="local-verifier",
            organization="local operator",
            control_separation="local rehearsal role only",
            custodian="local-controller",
            funding_and_conflicts="same local operator",
            protocol_controller="local-controller",
            replication_status="local-replay",
        ),
    )
    store.record_proof(
        "institution", sign_record(keys["local-verifier"], "local-verifier", "proof", proof), request_id="proof-" + name
    )
    decision = AdmissionDecision(
        decision_id="admit-" + name,
        institution_id="institution",
        release_digest=release_digest,
        principal="local-controller",
        outcome="admit",
        proof_ids=[proof.proof_id],
    )
    store.admit(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "admission", decision),
        request_id="admit-" + name,
    )
    grant = AuthorityEnvelope(
        grant_id="grant-" + name,
        institution_id="institution",
        mission_id="aggregation",
        release_digest=release_digest,
        subject="local-producer",
        issuer="local-controller",
        actions=["inspect"],
        tools=["fixed"],
        targets=["report"],
        resources={"calls": grant_resources},
        proof_ids=[proof.proof_id],
        valid_until=FUTURE,
        context_digest=CONTEXT,
        approval_required=False,
        scope=scope,
    )
    store.grant(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "authority", grant),
        request_id="grant-" + name,
    )
    return release, release_digest, proof, grant


def install(store, keys, release_digest, request_id="cutover"):
    return store.cutover(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "cutover", {"release_digest": release_digest}),
        request_id=request_id,
        expected_revision=store.read("institution")["revision"],
    )


def action(release_digest, ident="act", **changes):
    return ActionRequest(
        **{
            "action_id": ident,
            "subject": "local-producer",
            "release_digest": release_digest,
            "environment_digest": ENVIRONMENT,
            "action": "inspect",
            "tool": "fixed",
            "target": "report",
            "context_digest": CONTEXT,
            "resources": {"calls": 1},
            **changes,
        }
    )


def test_real_boundary_revocation_and_idempotent_conservative_accounting(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, _, grant = add_release(store, keys)
    install(store, keys, release_digest)
    request = action(release_digest)
    first = store.dispatch_action("institution", request)
    assert store.dispatch_action("institution", request)["revision"] == first["revision"]
    store.revoke(
        "institution",
        sign_record(
            keys["local-controller"],
            "local-controller",
            "revocation",
            {"grant_id": grant.grant_id, "reason": "operator stop"},
        ),
        request_id="revoke",
    )
    calls = []
    with pytest.raises(ValueError, match="no single"):
        store.execute_action(
            "institution", "act", ActionGateway({("fixed", "inspect"): lambda request: calls.append(request.action_id)})
        )
    assert not calls
    assert store.read("institution")["resources"]["reserved"] == {"calls": 1}


def test_no_fragment_union_wrong_context_or_local_production(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, _, original = add_release(store, keys)
    install(store, keys, release_digest)
    for name, changes in [
        ("wrong-tool", {"tool": "other"}),
        ("wrong-target", {"target": "elsewhere"}),
        ("wrong-context", {"context_digest": "f" * 64}),
        ("wrong-env", {"environment_digest": "f" * 64}),
    ]:
        with pytest.raises(ValueError):
            store.dispatch_action("institution", action(release_digest, name, **changes))
    fragment = original.model_copy(update={"grant_id": "fragment", "actions": ["other-action"], "tools": ["other"]})
    store.grant(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "authority", fragment),
        request_id="fragment",
    )
    with pytest.raises(ValueError, match="no single"):
        store.dispatch_action("institution", action(release_digest, "mixed", tool="other"))
    production = original.model_copy(update={"grant_id": "production", "scope": "production"})
    with pytest.raises(ValueError, match="ceiling"):
        store.grant(
            "institution",
            sign_record(keys["local-controller"], "local-controller", "authority", production),
            request_id="prod",
        )


def test_parallel_reservations_never_overspend(tmp_path):
    store, keys = build_store(tmp_path, budget=3)
    _, release_digest, _, _ = add_release(store, keys)
    install(store, keys, release_digest)

    def dispatch(index):
        try:
            store.dispatch_action("institution", action(release_digest, "parallel-" + str(index)))
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        accepted = list(pool.map(dispatch, range(12)))
    assert sum(accepted) == 3
    assert store.read("institution")["resources"]["reserved"] == {"calls": 3}
    assert store.journal.verify()["valid"]


def test_grant_budget_cumulative_and_operator_zero_cannot_refund(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, _, _ = add_release(store, keys, grant_resources=1)
    install(store, keys, release_digest)
    store.dispatch_action("institution", action(release_digest))
    counter = []
    gateway = ActionGateway({("fixed", "inspect"): lambda request: counter.append("effect")})
    result = store.execute_action("institution", "act", gateway, actual_resources={"calls": 0})
    replay = store.execute_action("institution", "act", gateway, actual_resources={"calls": 0})
    assert replay["revision"] == result["revision"]
    assert counter == ["effect"]
    assert result["resources"]["spent"] == {"calls": 1}
    with pytest.raises(ValueError, match="no single"):
        store.dispatch_action("institution", action(release_digest, "second"))


def test_crash_after_effect_never_replays_and_recovery_charges_once(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, _, _ = add_release(store, keys)
    install(store, keys, release_digest)
    store.dispatch_action("institution", action(release_digest))
    counter = []

    def crash(request):
        counter.append("external effect")
        raise SystemExit("simulated process loss")

    with pytest.raises(SystemExit):
        store.execute_action("institution", "act", ActionGateway({("fixed", "inspect"): crash}))
    assert store.read("institution")["actions"]["act"]["state"] == "executing"
    restarted = SuccessorStore(Journal(store.journal.root), store.trust)
    with pytest.raises(Conflict, match="already started"):
        restarted.execute_action("institution", "act", ActionGateway({("fixed", "inspect"): crash}))
    recovery = sign_record(keys["local-controller"], "local-controller", "recovery", {"institution_id": "institution"})
    recovered = restarted.recover("institution", recovery, request_id="recover")
    replay = restarted.recover("institution", recovery, request_id="recover")
    assert recovered["revision"] == replay["revision"]
    assert recovered["resources"]["spent"] == {"calls": 1}
    assert recovered["resources"]["reserved"] == {"calls": 0}
    assert recovered["stopped"] and recovered["actions"]["act"]["state"] == "uncertain"
    assert counter == ["external effect"]


def test_receipt_identity_independence_expiry_and_claim_guards(tmp_path):
    store, keys = build_store(tmp_path)
    release, release_digest, proof, _ = add_release(store, keys)
    false_independent = proof.model_copy(update={"proof_id": "fake-independent", "evidence_scope": "independent"})
    with pytest.raises(ValueError, match="independence"):
        store.record_proof(
            "institution",
            sign_record(keys["local-verifier"], "local-verifier", "proof", false_independent),
            request_id="false-independent",
        )
    forged = sign_record(keys["local-producer"], "local-verifier", "proof", proof)
    with pytest.raises(ValueError, match="signature"):
        store.record_proof("institution", forged, request_id="forged")
    successor = release.model_copy(update={"release_id": "descendant", "parent_release_digest": release_digest})
    state = store.descendant("institution", successor, request_id="descendant")
    successor_digest = digest("release", successor)
    assert all(entry["envelope"]["payload"]["release_digest"] != successor_digest for entry in state["proofs"].values())
    with pytest.raises(ValueError, match="admission"):
        install(store, keys, successor_digest)


def test_claim_impairment_keeps_history_and_blocks_action(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, proof, grant = add_release(store, keys)
    install(store, keys, release_digest)
    impaired = store.impair(
        "institution",
        sign_record(
            keys["local-controller"],
            "local-controller",
            "impairment",
            {"release_digest": release_digest, "claims": ["correctness"], "reason": "supplier behavior changed"},
        ),
        request_id="impair",
    )
    assert impaired["proofs"][proof.proof_id]["status"] == "impaired"
    assert impaired["grants"][grant.grant_id]["status"] == "impaired"
    with pytest.raises(ValueError, match="admission"):
        store.dispatch_action("institution", action(release_digest))


def test_portable_restore_uses_separate_anchor_and_empty_permission(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, _, _ = add_release(store, keys)
    install(store, keys, release_digest)
    checkpoint = JournalCheckpoint.capture(store.journal)
    package = store.export_portable("institution")
    other = SuccessorStore(Journal.initialize(tmp_path / "restored"), store.trust)
    restored = other.restore_portable(
        package, {"calls": 10}, source_public_key=store.journal.public, checkpoint=checkpoint
    )
    assert restored["institution"]["id"] == "institution"
    assert (
        restored["stopped"]
        and not restored["proofs"]
        and not restored["grants"]
        and restored["serving_release"] is None
    )
    assert "identity.key" not in str(package) and "api.token" not in str(package)
    package["payload"]["source_digest"] = "e" * 64
    package["digest"] = digest("portable", package["payload"])
    with pytest.raises(ValueError, match="signature"):
        other.restore_portable(package, {"calls": 10}, source_public_key=store.journal.public, checkpoint=checkpoint)


def test_checkpoint_detects_valid_signed_rollback(tmp_path):
    store, keys = build_store(tmp_path)
    before = JournalCheckpoint.capture(store.journal)
    add_release(store, keys)
    after = JournalCheckpoint.capture(store.journal)
    with sqlite3.connect(store.journal.path) as connection:
        connection.execute("DELETE FROM events WHERE seq > ?", (before.sequence,))
    assert store.journal.verify()["valid"]
    with pytest.raises(ValueError, match="older"):
        after.verify(store.journal)


def test_private_roles_survive_restart_and_missing_key_fails(tmp_path):
    root = tmp_path / "roles"
    first, _ = retained_local_principals(root)
    second, _ = retained_local_principals(root)
    assert first.anchor("local-controller", "controller") == second.anchor("local-controller", "controller")
    (root / "local-verifier.key").unlink()
    with pytest.raises(ValueError, match="incomplete"):
        retained_local_principals(root)


def test_memory_revocation_blocks_frozen_descendant_influence(tmp_path):
    store, keys = build_store(tmp_path)
    release, _, _, _ = add_release(store, keys)
    evidence = EvidenceRecord(
        evidence_id="evidence",
        source="synthetic licensed workload",
        acquired_at=PAST,
        content_digest="9" * 64,
        permitted_uses=["formation"],
        valid_until=FUTURE,
        retention_until=FUTURE,
        scope="aggregation",
        uncertainty="local development evidence",
        accepted_by="local-controller",
    )
    submission = EvidenceSubmission(institution_id="institution", evidence=evidence)
    store.record_evidence(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "evidence", submission),
        request_id="evidence",
    )
    memory = MemoryAdmission(
        admission_id="memory",
        institution_id="institution",
        principal="local-controller",
        artifact_digest="8" * 64,
        evidence_ids=["evidence"],
        permitted_uses=["formation"],
        scope="aggregation",
        rights=["public-synthetic"],
        valid_until=FUTURE,
        retention_until=FUTURE,
        outcome="admit",
    )
    store.admit_memory(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "memory-admission", memory),
        request_id="memory",
    )
    descendant = release.model_copy(update={"release_id": "memory-child", "memory_digests": [memory.artifact_digest]})
    store.descendant("institution", descendant, request_id="memory-child")
    store.revoke_evidence(
        "institution",
        sign_record(
            keys["local-controller"],
            "local-controller",
            "evidence-revocation",
            {"evidence_id": "evidence", "reason": "rights withdrawn"},
        ),
        request_id="evidence-revoke",
    )
    next_child = descendant.model_copy(update={"release_id": "next-child"})
    with pytest.raises(ValueError, match="revoked"):
        store.descendant("institution", next_child, request_id="next-child")
    assert (
        store.read("institution")["memory"]["memory"]["envelope"]["payload"]["artifact_digest"]
        == memory.artifact_digest
    )


def test_concurrent_cutover_has_one_compare_and_swap_winner(tmp_path):
    store, keys = build_store(tmp_path)
    _, original, _, _ = add_release(store, keys)
    install(store, keys, original)
    _, left, _, _ = add_release(store, keys, "left")
    _, right, _, _ = add_release(store, keys, "right")
    revision = store.read("institution")["revision"]

    def cutover(target):
        try:
            store.cutover(
                "institution",
                sign_record(keys["local-controller"], "local-controller", "cutover", {"release_digest": target}),
                request_id="cutover-" + target,
                expected_revision=revision,
            )
            return True
        except Conflict:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(cutover, [left, right]))
    final = store.read("institution")
    assert sum(results) == 1 and final["serving_release"] in {left, right}
    assert len(final["lineage"]) == 2


def test_new_refusal_contracts_authority_without_erasing_history(tmp_path):
    store, keys = build_store(tmp_path)
    _, release_digest, _, grant = add_release(store, keys)
    install(store, keys, release_digest)
    refusal = AdmissionDecision(
        decision_id="subsequent-refusal",
        institution_id="institution",
        release_digest=release_digest,
        principal="local-controller",
        outcome="refuse",
        rationale="new evidence does not support continuing admission",
    )
    state = store.admit(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "admission", refusal),
        request_id="refusal",
    )
    assert state["admissions"]["admit-release-one"]["status"] == "historical"
    assert state["grants"][grant.grant_id]["status"] == "impaired"
    with pytest.raises(ValueError, match="admission"):
        store.dispatch_action("institution", action(release_digest))


def test_local_proof_cannot_earn_specialist_designation(tmp_path):
    from alpha_factory_v1.core.runtime.successor.protocol import (
        Comparator,
        ComparatorManifest,
        ComparatorRequirement,
        SpecialistDesignationPolicy,
        Validity,
    )

    store, keys = build_store(tmp_path)
    _, release_digest, proof, _ = add_release(store, keys)
    policy = SpecialistDesignationPolicy(
        policy_id="specialist-aggregation-v1",
        mission_family="aggregation",
        validity=Validity(valid_from=PAST, valid_until=FUTURE),
        superiority_metric="alpha_lower_bound_bps",
        superiority_threshold_bps=1000,
        minimum_evaluation_units=10,
        required_independent_replications=2,
        comparator_requirements=[
            ComparatorRequirement(
                role=role,
                required=role in {"incumbent", "simple", "general"},
                rationale=(
                    "required measurable alternative"
                    if role in {"incumbent", "simple", "general"}
                    else "not applicable to this pure software benchmark"
                ),
            )
            for role in ["incumbent", "simple", "specialist", "general", "human", "hybrid"]
        ],
        uncertainty_requirement="paired independent workload lower confidence bound",
        accountable_policy_owner="local-controller",
    )
    comparators = ComparatorManifest(
        manifest_id="comparators",
        mission_id="aggregation",
        cost_rule_digest="c" * 64,
        selection_rule="best feasible fixed alternative",
        frozen_at=PAST,
        comparators=[
            Comparator(
                comparator_id=role,
                role=role,
                release_digest=release_digest,
                observed_at=PAST,
                selection_rationale="measured implementation",
                status="measured",
            )
            for role in ["incumbent", "simple"]
        ],
    )
    assessment = store.assess_designation(
        "institution",
        sign_record(keys["local-controller"], "local-controller", "designation-policy", policy),
        comparators,
        [proof.proof_id] * 5,
    )
    assert assessment["status"] == "HOLD" and assessment["designation"] is None
    assert not assessment["qualifying_proof_ids"] and assessment["production_authority"] is False


@pytest.mark.parametrize("mutation", ["source", "prompt", "routing", "policy", "environment", "configuration"])
def test_behavior_change_cannot_reuse_predecessor_proof(tmp_path, mutation):
    store, keys = build_store(tmp_path)
    release, _, proof, _ = add_release(store, keys)
    fields = {"release_id": "changed-" + mutation}
    if mutation in {"source", "prompt", "routing"}:
        fields["artifacts"] = [BehaviorArtifact(name="changed", role=mutation, digest="a" * 64)]
    elif mutation == "policy":
        fields["policy_digest"] = "b" * 64
    elif mutation == "environment":
        fields["environment_digest"] = "c" * 64
    else:
        fields["configuration"] = {"sampling": 2}
    changed = release.model_copy(update=fields)
    store.register_release("institution", changed, request_id="changed")
    decision = AdmissionDecision(
        decision_id="reuse",
        institution_id="institution",
        release_digest=digest("release", changed),
        principal="local-controller",
        outcome="admit",
        proof_ids=[proof.proof_id],
    )
    with pytest.raises(ValueError, match="exact execution"):
        store.admit(
            "institution",
            sign_record(keys["local-controller"], "local-controller", "admission", decision),
            request_id="reuse",
        )


@pytest.mark.parametrize(
    ("permitted_uses", "scope", "accepted"),
    [(["formation"], "aggregation", False), (["proof"], "another-mission", False), (["proof"], "aggregation", True)],
)
def test_proof_dependencies_require_proof_rights_and_exact_mission_scope(tmp_path, permitted_uses, scope, accepted):
    store, keys = build_store(tmp_path)
    _, release_digest, proof, _ = add_release(store, keys)
    evidence = EvidenceRecord(
        evidence_id="proof-dependency",
        source="public synthetic comparison",
        acquired_at=PAST,
        content_digest="d" * 64,
        permitted_uses=permitted_uses,
        valid_until=FUTURE,
        scope=scope,
        uncertainty="local measured comparison",
        accepted_by="local-controller",
    )
    store.record_evidence(
        "institution",
        sign_record(
            keys["local-controller"],
            "local-controller",
            "evidence",
            EvidenceSubmission(institution_id="institution", evidence=evidence),
        ),
        request_id="proof-dependency",
    )
    dependent = proof.model_copy(
        update={"proof_id": "dependent-proof", "dependency_digests": [evidence.content_digest]}
    )
    store.record_proof(
        "institution",
        sign_record(keys["local-verifier"], "local-verifier", "proof", dependent),
        request_id="dependent-proof",
    )
    decision = AdmissionDecision(
        decision_id="dependent-admission",
        institution_id="institution",
        release_digest=release_digest,
        principal="local-controller",
        outcome="admit",
        proof_ids=[dependent.proof_id],
    )
    signed = sign_record(keys["local-controller"], "local-controller", "admission", decision)
    if accepted:
        state = store.admit("institution", signed, request_id="dependent-admission")
        assert state["admissions"][decision.decision_id]["status"] == "active"
    else:
        with pytest.raises(ValueError, match="rights or scope"):
            store.admit("institution", signed, request_id="dependent-admission")
        assert decision.decision_id not in store.read("institution")["admissions"]
