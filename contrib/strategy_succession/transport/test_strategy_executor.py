"""Engineering boundary checks, deliberately separate from frozen confirmation."""
import hashlib
import json
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from alpha_factory_v1.core.runtime.store import Conflict, Journal, digest
from strategy_executor import ExecutorPolicy, KEY, Limits, SCIENTIFIC_SOURCE_HASH, SourceFile, StrategyExecutor, create_strategy_app


class Worker:
    def __init__(self):
        self.calls = 0
        self.hook = None

    def execute(self, method, payload, limits, checkpoint):
        self.calls += 1
        checkpoint()
        if self.hook:
            self.hook(checkpoint)
        service = 3 if method != "construct" else 0
        improvement = 2 if method != "run-mission" else 0
        checkpoint(service_work=service, improvement_work=improvement)
        return {"result": {"method": method, "received": payload}, "costs": {
            "service_work": service, "improvement_work": improvement, "native_calls": 0,
            "native_solve_seconds": 0.0, "unknown_costs": ["human effort"]},
            "source_hash": limits["source_hash"], "verified": True}


@pytest.fixture
def rig(tmp_path):
    source = tmp_path / "fixed-worker.py"
    source.write_text("reviewed fixed worker v1\n")
    journal = Journal.initialize(tmp_path / "journal")
    worker = Worker()
    policy = ExecutorPolicy("fixed-planning-v1", (SourceFile("worker.py", source, hashlib.sha256(source.read_bytes()).hexdigest()),),
        {"run-mission": Limits(8, 0, 0, 0), "construct": Limits(0, 6, 0, 0),
         "run-journey": Limits(8, 6, 0, 0)}, Limits(16, 12, 0, 0), max_requests=8, grant_seconds=60, request_seconds=30)
    now = [1000.0]
    executor = StrategyExecutor(journal, worker, policy, clock=lambda: now[0])
    return journal, worker, policy, executor, source, now


def plan(executor, method="run-journey", ident="mission-1", payload=None):
    return executor.prepare({"method": method, "input": payload or {"initial": {"jobs": []}}, "request_id": ident})


def ref(prepared):
    return {k: prepared[k] for k in ("plan_id", "plan_digest")}


def approved(executor, **kwargs):
    prepared = plan(executor, **kwargs)
    executor.approve(ref(prepared))
    return prepared


def test_approved_journey_commits_costs_separately_and_signs_export(rig):
    journal, worker, _, executor, _, _ = rig
    prepared = approved(executor)
    result = executor.run(ref(prepared))
    status = executor.status()
    assert worker.calls == 1 and result["state"] == "completed"
    assert status["spent"] == {"service_work": 3, "improvement_work": 2, "native_calls": 0, "native_solve_seconds": 0}
    assert not any(status["reserved"].values())
    exported = executor.export(prepared["plan_id"])
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    import base64
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(journal.public)).verify(
        base64.b64decode(exported["signature"]), bytes.fromhex(exported["sha256"]))
    assert exported["body"]["production_authority"] is False
    assert (journal.root / "api.token").read_text() not in json.dumps(exported)
    journal.verify()


def test_no_approval_and_forged_exact_plan_cannot_run(rig):
    _, worker, _, executor, _, _ = rig
    prepared = plan(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    with pytest.raises(Conflict):
        executor.approve({"plan_id": prepared["plan_id"], "plan_digest": "0" * 64})
    with pytest.raises(ValueError):
        executor.approve({**ref(prepared), "caps": {"service_work": 999999}})
    assert worker.calls == 0


def test_duplicate_request_is_exact_and_commit_survives_lost_ack(rig):
    journal, worker, policy, executor, _, now = rig
    prepared = approved(executor)
    committed = executor.run(ref(prepared))
    restored = StrategyExecutor(Journal(journal.root), worker, policy, clock=lambda: now[0])
    repeated = restored.run(ref(prepared))
    assert repeated["outcome_hash"] == committed["outcome_hash"] and worker.calls == 1
    assert plan(restored)["plan_id"] == prepared["plan_id"]
    with pytest.raises(Conflict):
        plan(restored, payload={"changed": True})


def test_separate_accounts_cannot_borrow(rig):
    journal, worker, policy, _, _, now = rig
    narrow = replace(policy, total=Limits(8, 1, 0, 0))
    other = Journal.initialize(journal.root.parent / "narrow")
    executor = StrategyExecutor(other, worker, narrow, clock=lambda: now[0])
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert worker.calls == 0 and not any(executor.status()["reserved"].values())
    service = approved(executor, method="run-mission", ident="service")
    assert executor.run(ref(service))["state"] == "completed"


def test_stop_during_worker_is_unknown_and_keeps_reservations(rig):
    _, worker, _, executor, _, _ = rig
    worker.hook = lambda checkpoint: (executor.control("stopped"), checkpoint())
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    status = executor.status()
    assert status["plans"][prepared["plan_id"]]["state"] == "unknown"
    assert status["reserved"]["service_work"] == 8 and status["reserved"]["improvement_work"] == 6
    with pytest.raises(Conflict):
        executor.control("ready")
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert worker.calls == 1


def test_lease_expiry_and_reconcile_never_refunds_or_replays(rig):
    _, worker, _, executor, _, now = rig
    worker.hook = lambda checkpoint: (now.__setitem__(0, 1040.0), checkpoint())
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    status = executor.status()
    with pytest.raises(Conflict):
        executor.reconcile({"plan_id": prepared["plan_id"], "record_digest": "0" * 64, "note": "inspected"})
    reconciled = executor.reconcile({"plan_id": prepared["plan_id"], "record_digest": status["digest"], "note": "Observed no committed reply; work remains unknown."})
    assert reconciled["state"] == "reconciled" and executor.status()["reserved"]["service_work"] == 8
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert worker.calls == 1


def test_stale_crash_lease_requires_inspection(rig):
    journal, worker, _, executor, _, now = rig
    prepared = approved(executor)
    with journal.transaction() as cx:
        value = executor._load(cx)
        stored = value["plans"][prepared["plan_id"]]
        stored.update(state="running", lease_id="prior-process", lease_expires_at=1010)
        value["reserved"] = dict(stored["caps"])
        executor._save(cx, value)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    with pytest.raises(Conflict):
        executor.reconcile({"plan_id": prepared["plan_id"], "record_digest": executor.status()["digest"], "note": "too early"})
    now[0] = 1011
    result = executor.reconcile({"plan_id": prepared["plan_id"], "record_digest": executor.status()["digest"], "note": "Inspected prior process loss."})
    assert result["state"] == "reconciled" and worker.calls == 0


def test_missing_or_changed_installed_source_fails_closed(rig):
    _, worker, _, executor, source, _ = rig
    prepared = approved(executor)
    source.unlink()
    assert executor.status()["source_available"] is False
    with pytest.raises(OSError):
        executor.run(ref(prepared))
    assert worker.calls == 0
    source.write_text("different code")
    with pytest.raises(ValueError):
        plan(executor, ident="new")


def test_cross_process_running_blocks_second_instance(rig):
    journal, worker, policy, executor, _, now = rig
    entered, release = threading.Event(), threading.Event()
    worker.hook = lambda checkpoint: (entered.set(), release.wait(5), checkpoint())
    prepared = approved(executor)
    outcomes = []
    thread = threading.Thread(target=lambda: outcomes.append(executor.run(ref(prepared))))
    thread.start()
    assert entered.wait(3)
    other = StrategyExecutor(Journal(journal.root), worker, policy, clock=lambda: now[0])
    with pytest.raises(Conflict):
        other.run(ref(prepared))
    release.set()
    thread.join(5)
    assert outcomes[0]["state"] == "completed" and worker.calls == 1


def test_auth_origin_and_fixed_fields(rig):
    journal, worker, policy, _, _, now = rig
    client = TestClient(create_strategy_app(journal, worker, policy, clock=lambda: now[0]), raise_server_exceptions=False)
    token = (journal.root / "api.token").read_text()
    headers = {"Authorization": "Bearer " + token}
    assert client.get("/api/strategy-executor/status").status_code == 401
    assert client.get("/api/strategy-executor/status", headers=headers).status_code == 200
    assert client.post("/api/strategy-executor/control", json={"state": "stopped"}, headers={**headers, "Origin": "https://evil.invalid"}).status_code == 403
    assert client.post("/api/strategy-executor/prepare", json={"method": "run-mission", "input": {}, "request_id": "good", "command": "host-command"}, headers=headers).status_code == 422
    assert client.post("/api/strategy-executor/prepare", json={"method": "shell", "input": {}, "request_id": "good"}, headers=headers).status_code == 422
    assert worker.calls == 0


def test_authenticated_api_roundtrip_exports_no_credentials(rig):
    journal, worker, policy, _, _, now = rig
    client = TestClient(create_strategy_app(journal, worker, policy, clock=lambda: now[0]))
    token = (journal.root / "api.token").read_text()
    headers = {"Authorization": "Bearer " + token}
    prepared = client.post("/api/strategy-executor/prepare", json={"method": "run-journey", "input": {"n": 1}, "request_id": "api1"}, headers=headers).json()
    assert client.post("/api/strategy-executor/approve", json=ref(prepared), headers=headers).status_code == 200
    reply = client.post("/api/strategy-executor/run", json=ref(prepared), headers=headers)
    assert reply.status_code == 200 and reply.json()["state"] == "completed"
    exported = client.get("/api/strategy-executor/export/" + prepared["plan_id"], headers=headers)
    assert exported.status_code == 200 and token not in exported.text
    assert exported.headers["cache-control"] == "no-store"


def test_bad_costs_and_source_are_unknown_not_zero(rig):
    _, worker, _, executor, _, _ = rig
    original = worker.execute
    def invalid(*args):
        result = original(*args)
        result["costs"]["improvement_work"] = 99999
        return result
    worker.execute = invalid
    prepared = approved(executor)
    with pytest.raises(ValueError):
        executor.run(ref(prepared))
    status = executor.status()
    assert status["plans"][prepared["plan_id"]]["state"] == "unknown"
    assert status["reserved"]["improvement_work"] == 6
    assert status["spent"]["improvement_work"] == 0


def test_expired_approval_does_not_execute(rig):
    _, worker, _, executor, _, now = rig
    prepared = approved(executor)
    now[0] = 1061
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert worker.calls == 0


def test_static_asset_query_cannot_select_host_file(rig, tmp_path):
    journal, worker, policy, _, _, now = rig
    page = tmp_path / "fixed.html"
    page.write_text("fixed page")
    app = create_strategy_app(journal, worker, policy, static_files={"/": page}, clock=lambda: now[0])
    client = TestClient(app)
    response = client.get("/?current=/etc/passwd")
    assert response.text == "fixed page"


def test_native_disabled_even_if_worker_claims_it(rig):
    _, worker, _, executor, _, _ = rig
    worker.hook = lambda checkpoint: checkpoint(native_calls=1)
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert executor.status()["plans"][prepared["plan_id"]]["state"] == "unknown"


def test_existing_global_pause_fences_new_and_active_work(rig):
    journal, worker, _, executor, _, _ = rig
    prepared = approved(executor)
    journal.control(True)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert worker.calls == 0
    journal.control(False)
    worker.hook = lambda checkpoint: (journal.control(True), checkpoint())
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert executor.status()["plans"][prepared["plan_id"]]["state"] == "unknown"
    assert executor.status()["reserved"]["service_work"] == 8


def test_restored_journal_does_not_inherit_local_execution_authority(rig, tmp_path):
    journal, worker, policy, executor, _, _ = rig
    approved(executor)
    journal.backup(tmp_path / "private-recovery.zip")
    restored = Journal.restore(tmp_path / "private-recovery.zip", tmp_path / "restored")
    with pytest.raises(Conflict):
        StrategyExecutor(restored, worker, policy)
    assert worker.calls == 0


def test_operator_method_mapping_is_detached_and_immutable(rig):
    _, _, policy, _, _, _ = rig
    with pytest.raises(TypeError):
        policy.methods["run-mission"] = Limits(99999, 0, 0, 0)


def test_failed_verification_is_retained_rejected_with_known_costs(rig):
    _, worker, _, executor, _, _ = rig
    original = worker.execute
    def reject(*args):
        outcome = original(*args)
        outcome["verified"] = False
        return outcome
    worker.execute = reject
    prepared = approved(executor)
    result = executor.run(ref(prepared))
    assert result["state"] == "rejected" and result["outcome"]["verified"] is False
    assert executor.status()["spent"]["service_work"] == 3
    assert not any(executor.status()["reserved"].values())
    assert executor.run(ref(prepared))["state"] == "rejected" and worker.calls == 1


def test_unexpected_callback_error_never_escapes_to_server_log(rig):
    journal, worker, policy, _, _, now = rig
    def secret_error(checkpoint):
        raise RuntimeError("CALLBACK_PRIVATE_MARKER")
    worker.hook = secret_error
    client = TestClient(create_strategy_app(journal, worker, policy, clock=lambda: now[0]))
    headers = {"Authorization": "Bearer " + (journal.root / "api.token").read_text()}
    prepared = client.post("/api/strategy-executor/prepare", json={"method": "run-journey", "input": {}, "request_id": "error"}, headers=headers).json()
    client.post("/api/strategy-executor/approve", json=ref(prepared), headers=headers)
    response = client.post("/api/strategy-executor/run", json=ref(prepared), headers=headers)
    assert response.status_code == 502 and "CALLBACK_PRIVATE_MARKER" not in response.text
    status = client.get("/api/strategy-executor/status", headers=headers).json()
    assert status["plans"][prepared["plan_id"]]["state"] == "unknown"
    assert "CALLBACK_PRIVATE_MARKER" not in json.dumps(status)


def phase(executor, index=0, task_id="JOURNEY-PHASE-0", value=10):
    task = {"id": task_id, "jobs": [{"id": "J1", "duration": value}]}
    result = {"task_id": task_id, "makespan": value, "proof": [], "authority": []}
    checker = {"valid": True, "qualified": True, "errors": []}
    original = {"source_hash": executor.source_hash, "scientific_source_hash": SCIENTIFIC_SOURCE_HASH,
                "task": task, "result": result, "checker": checker, "method": "ordinary-portfolio", "proof": [], "authority": []}
    return {"phase_index": index, "receipt_hash": digest(original), "task": task, "result": result,
            "checker": checker, "selectedmethod": "ordinary-portfolio"}


def test_partial_receipt_commits_before_stop_and_survives_restart_export(rig):
    journal, worker, policy, executor, _, now = rig
    prepared = approved(executor)
    partial = phase(executor)
    def first_then_stop(checkpoint):
        checkpoint(service_work=3)
        checkpoint(receipt=partial)
        retained = executor.status()["plans"][prepared["plan_id"]]["partial_receipts"]
        assert len(retained) == 1 and retained[0]["receipt_hash"] == partial["receipt_hash"]
        executor.control("stopped")
        checkpoint(receipt=phase(executor, index=1, task_id="SECOND"))
    worker.hook = first_then_stop
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    restored = StrategyExecutor(Journal(journal.root), worker, policy, clock=lambda: now[0])
    stored = restored.status()["plans"][prepared["plan_id"]]
    assert stored["state"] == "unknown" and stored["observed"]["service_work"] == 3
    retained = restored.export(prepared["plan_id"])["body"]["plan"]["partial_receipts"]
    assert retained[0]["source_hash"] == executor.source_hash
    assert retained[0]["proof"] == retained[0]["authority"] == []
    body = {k: v for k, v in retained[0].items() if k != "transport_digest"}
    assert digest(body) == retained[0]["transport_digest"]
    assert restored.status()["reserved"]["service_work"] == 8
    assert restored.status()["reserved"]["improvement_work"] == 6
    with pytest.raises(Conflict):
        restored.run(ref(prepared))
    assert worker.calls == 1


def test_exact_duplicate_partial_receipt_does_not_append_or_charge_again(rig):
    _, worker, _, executor, _, _ = rig
    partial = phase(executor)
    worker.hook = lambda checkpoint: (checkpoint(receipt=partial), checkpoint(receipt=partial))
    prepared = approved(executor)
    result = executor.run(ref(prepared))
    assert len(result["partial_receipts"]) == 1
    assert result["observed"]["service_work"] == 3
    assert result["state"] == "completed"


def test_duplicate_receipt_with_repeated_cost_increment_is_refused(rig):
    _, worker, _, executor, _, _ = rig
    partial = phase(executor)
    worker.hook = lambda checkpoint: (checkpoint(receipt=partial, service_work=1),
                                      checkpoint(receipt=partial, service_work=1))
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    stored = executor.status()["plans"][prepared["plan_id"]]
    assert len(stored["partial_receipts"]) == 1 and stored["observed"]["service_work"] == 1
    assert stored["state"] == "unknown"


def test_partial_receipt_order_substitution_and_hash_are_fenced(rig):
    _, worker, _, executor, _, _ = rig
    partial = phase(executor)
    different = phase(executor, value=11)
    worker.hook = lambda checkpoint: (checkpoint(receipt=partial), checkpoint(receipt=different))
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    assert executor.status()["plans"][prepared["plan_id"]]["partial_receipts"][0]["task"]["jobs"][0]["duration"] == 10
    worker.hook = lambda checkpoint: checkpoint(receipt=phase(executor, index=1))
    next_plan = approved(executor, ident="out-of-order")
    with pytest.raises(Conflict):
        executor.run(ref(next_plan))
    assert executor.status()["plans"][next_plan["plan_id"]]["partial_receipts"] == []


def test_partial_receipts_obey_installed_output_budget(rig):
    journal, worker, policy, _, _, now = rig
    small_policy = replace(policy, max_output_bytes=1000)
    executor = StrategyExecutor(Journal.initialize(journal.root.parent / "small-output"), worker, small_policy, clock=lambda: now[0])
    oversized = phase(executor)
    oversized["task"]["input_license"] = "x" * 1100
    worker.hook = lambda checkpoint: checkpoint(receipt=oversized)
    prepared = approved(executor)
    with pytest.raises(ValueError):
        executor.run(ref(prepared))
    assert executor.status()["plans"][prepared["plan_id"]]["partial_receipts"] == []


def test_partial_receipts_are_capped_at_three(rig):
    _, worker, _, executor, _, _ = rig
    def excessive(checkpoint):
        for index in range(4):
            checkpoint(receipt=phase(executor, index=index, task_id="PHASE-" + str(index)))
    worker.hook = excessive
    prepared = approved(executor)
    with pytest.raises(ValueError):
        executor.run(ref(prepared))
    retained = executor.status()["plans"][prepared["plan_id"]]["partial_receipts"]
    assert [p["phase_index"] for p in retained] == [0, 1, 2]


def test_partial_receipt_original_hash_must_bind_actual_source_and_bytes(rig):
    _, worker, _, executor, _, _ = rig
    wrong = phase(executor)
    wrong["result"]["makespan"] = 999
    worker.hook = lambda checkpoint: checkpoint(receipt=wrong)
    prepared = approved(executor)
    with pytest.raises(ValueError):
        executor.run(ref(prepared))
    assert executor.status()["plans"][prepared["plan_id"]]["partial_receipts"] == []


def test_partial_delivery_cannot_be_relabelled_as_a_distinct_phase(rig):
    _, worker, _, executor, _, _ = rig
    first = phase(executor)
    worker.hook = lambda checkpoint: (checkpoint(receipt=first), checkpoint(receipt={**first, "phase_index": 1}))
    prepared = approved(executor)
    with pytest.raises(Conflict):
        executor.run(ref(prepared))
    retained = executor.status()["plans"][prepared["plan_id"]]["partial_receipts"]
    assert len(retained) == 1 and retained[0]["phase_index"] == 0


def test_partial_receipt_requires_a_real_task_identity(rig):
    _, worker, _, executor, _, _ = rig
    missing = {"phase_index": 0, "receipt_hash": "0" * 64, "task": {}, "result": {}, "checker": {"valid": True}, "selectedmethod": "ordinary-portfolio"}
    worker.hook = lambda checkpoint: checkpoint(receipt=missing)
    prepared = approved(executor)
    with pytest.raises(ValueError):
        executor.run(ref(prepared))
    assert executor.status()["plans"][prepared["plan_id"]]["partial_receipts"] == []


def test_activity_distinguishes_owned_execution_from_another_instance(rig):
    journal, worker, policy, executor, _, now = rig
    entered, release = threading.Event(), threading.Event()
    worker.hook = lambda checkpoint: (entered.set(), release.wait(5), checkpoint())
    prepared = approved(executor)
    outcomes = []
    thread = threading.Thread(target=lambda: outcomes.append(executor.run(ref(prepared))))
    thread.start()
    try:
        assert entered.wait(3)
        owned = executor.status()
        assert owned["active_after_browser_close"] is True
        assert owned["execution_observation"] == "running-in-this-executor"
        assert owned["record_running"] is True and owned["lease_state"] == "current"
        other = StrategyExecutor(Journal(journal.root), worker, policy, clock=lambda: now[0])
        unobserved = other.status()
        assert unobserved["active_after_browser_close"] is None
        assert unobserved["execution_observation"] == "awaiting-evidence"
        assert unobserved["record_running"] is True and unobserved["lease_state"] == "current"
    finally:
        release.set()
        thread.join(5)
    assert outcomes[0]["state"] == "completed"
    assert executor.status()["active_after_browser_close"] is False
    assert executor.status()["execution_observation"] == "idle"


def test_restart_and_expired_lease_remain_unobserved_without_mutating_ledger(rig):
    journal, worker, policy, executor, _, now = rig
    prepared = approved(executor)
    with journal.transaction() as cx:
        value = executor._load(cx)
        stored = value["plans"][prepared["plan_id"]]
        stored.update(state="running", lease_id="lost-process", lease_expires_at=1010)
        value["reserved"] = dict(stored["caps"])
        executor._save(cx, value)
    restarted = StrategyExecutor(Journal(journal.root), worker, policy, clock=lambda: now[0])
    before = restarted.status()
    assert before["active_after_browser_close"] is None and before["lease_state"] == "current"
    now[0] = 1011
    after = restarted.status()
    assert after["active_after_browser_close"] is None
    assert after["record_running"] is True and after["lease_state"] == "expired"
    assert after["execution_observation"] == "awaiting-evidence"
    assert after["digest"] == before["digest"] and after["reserved"] == before["reserved"]
    assert after["plans"][prepared["plan_id"]]["state"] == "running"
    assert worker.calls == 0


def test_receipt_after_following_phase_failure_keeps_verified_first_result(rig):
    _, worker, _, executor, _, _ = rig
    partial = phase(executor)
    def fail(checkpoint):
        checkpoint(receipt=partial, service_work=2)
        raise RuntimeError("following phase failed")
    worker.hook = fail
    prepared = approved(executor)
    with pytest.raises(RuntimeError):
        executor.run(ref(prepared))
    stored = executor.status()["plans"][prepared["plan_id"]]
    assert stored["state"] == "unknown" and stored["partial_receipts"][0]["receipt_hash"] == partial["receipt_hash"]
    assert stored["observed"]["service_work"] == 2
    assert executor.status()["reserved"]["service_work"] == 8
