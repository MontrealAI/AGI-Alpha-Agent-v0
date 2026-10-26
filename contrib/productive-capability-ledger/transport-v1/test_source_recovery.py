# SPDX-License-Identifier: Apache-2.0
"""Finite source recovery through the existing journal, runtime and candidate route."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import sys
import time

import pytest
from fastapi.testclient import TestClient
from alpha_factory_v1.core.runtime.store import Conflict, Journal

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("source_recovery_launcher", HERE / "serve_candidate.py")
assert spec is not None and spec.loader is not None
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)
PUBLIC_COMMIT = "443246db37b30b83f4b9c8a854ceb226601e0155"
MANIFEST = "contrib/productive-capability-ledger/completion-v3/previous-published-source.json"


def app_for(journal, registry):
    return launcher.create_candidate_app(
        journal, registry, node=Path(shutil.which("node")), git=Path(shutil.which("git")), python=Path(sys.executable)
    )


@pytest.fixture
def rig(tmp_path):
    registry = tmp_path / "scopes.json"
    registry.write_text(
        json.dumps(
            {
                "schema": "alpha-source-assurance-candidate-profile/v1",
                "maxSeconds": 20,
                "maxAttempts": 2,
                "scopes": {"public-five-paths": {"sourceRef": PUBLIC_COMMIT, "manifestPath": MANIFEST}},
            }
        )
    )
    journal = Journal.initialize(tmp_path / "journal")
    app = app_for(journal, registry)
    worker, executor = app.state.source_assurance_worker, app.state.strategy_executor
    now = datetime.now(timezone.utc)

    def fmt(dt):
        return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

    payload = worker.prepare_input(
        "public-five-paths", "recovery-one-job", created_at=fmt(now), expires_at=fmt(now + timedelta(minutes=10))
    )
    plan = executor.prepare({"method": "run-mission", "input": payload, "request_id": "recovery-one-job"})
    ref = {k: plan[k] for k in ("plan_id", "plan_digest")}
    executor.approve(ref)
    headers = {
        "Authorization": "Bearer " + (journal.root / "api.token").read_text().strip(),
        "Origin": "http://testserver",
    }
    return app, journal, registry, worker, executor, ref, headers


def interrupt_after_preparation(rig):
    _app, journal, _registry, worker, executor, ref, _headers = rig
    prepared = worker.output_root / "recovery-one-job" / "stage-preparation.json"
    original, killed = executor._checkpoint, []

    def checkpoint(*args, **kwargs):
        if prepared.exists() and not killed:
            os.killpg(worker.last_pid, signal.SIGKILL)
            killed.append(worker.last_pid)
        return original(*args, **kwargs)

    executor._checkpoint = checkpoint
    with pytest.raises(ValueError, match="child refused"):
        executor.run(ref)
    executor._checkpoint = original
    assert killed and prepared.is_file()
    before = executor.status()["plans"][ref["plan_id"]]
    assert before["state"] == "unknown" and before["observed"]["service_work"] == 1
    assert len(before["recovery_attempts"]) == 1
    journal.verify()
    return before, prepared.read_bytes()


def test_actual_sigkill_checkpoint_and_startup_recovery_same_original_envelope(rig):
    _app, journal, registry, worker, executor, ref, headers = rig
    before, checkpoint = interrupt_after_preparation(rig)
    executor.close()
    reopened = app_for(Journal(journal.root), registry)
    with TestClient(reopened) as client:
        end = time.monotonic() + 10
        while time.monotonic() < end:
            status = client.get("/api/strategy-executor/status", headers=headers).json()
            after = status["plans"][ref["plan_id"]]
            if after["state"] == "completed":
                break
            time.sleep(0.02)
        assert after["state"] == "completed", after
        duplicate = client.post("/api/strategy-executor/run", json=ref, headers=headers).json()
        assert duplicate["outcome_hash"] == after["outcome_hash"]
        exported = client.get("/api/strategy-executor/export/" + ref["plan_id"], headers=headers).json()
    assert all(
        after[k] == before[k] for k in ("lease_id", "lease_expires_at", "expires_at", "approved_at", "started_at")
    )
    assert (worker.output_root / "recovery-one-job/stage-preparation.json").read_bytes() == checkpoint
    assert after["observed"]["service_work"] == status["spent"]["service_work"] == 2
    assert status["reserved"]["service_work"] == 0 and len(after["recovery_attempts"]) == 2
    result = after["outcome"]["result"]
    assert result["independentAcceptance"]["accepted"]
    assert result["accounting"]["schema"] == "alpha-automated-costs/v1"
    assert all(s["costs"]["fullyLoadedMicrosPerAccepted"] is None for s in result["costSummary"]["scenarios"])
    assert all(s["attemptsPerRequestPpm"]["value"] == 2_000_000 for s in result["accounting"]["scenarios"])
    assert (journal.root / "api.token").read_text().strip() not in json.dumps(exported)
    output = os.environ.get("SOURCE_ASSURANCE_EVIDENCE_DIR")
    if output:
        root = Path(output)
        root.mkdir(parents=True, exist_ok=True)
        run_name = "recovery-run-" + result["download"]["sha256"][:16]
        run_evidence = root / run_name
        run_evidence.mkdir()
        for artifact in (worker.output_root / "recovery-one-job").iterdir():
            if artifact.is_file() and not artifact.is_symlink() and artifact.suffix in {".json", ".csv", ".md"}:
                body = artifact.read_bytes()
                assert str(journal.root).encode() not in body
                assert (journal.root / "api.token").read_bytes().strip() not in body
                (run_evidence / artifact.name).write_bytes(body)
        (root / "unattended-recovery.json").write_text(
            json.dumps(
                {
                    "schema": "alpha-source-recovery-acceptance/v1",
                    "passed": True,
                    "scope": "Isolated candidate; same five public paths as earlier route qualification, not fresh diversity or customer demand.",
                    "actualWorkerSignal": "SIGKILL",
                    "recoveryTrigger": "ASGI startup without another approval/run call",
                    "originalLeaseUnchanged": True,
                    "checkpointBytesUnchanged": True,
                    "checkpointSha256": hashlib.sha256(checkpoint).hexdigest(),
                    "runEvidenceDirectory": run_name,
                    "attempts": after["recovery_attempts"],
                    "conservativeServiceCharge": 2,
                    "source_hash": after["source_hash"],
                    "result": result,
                    "approvedOperator": "NOT RUN",
                    "operationalAdoption": "NOT APPROVED",
                },
                indent=2,
            )
            + "\n"
        )
    journal.verify()


@pytest.mark.parametrize("guard", ["expiry", "attempts", "cancel", "stop", "corrupt", "missing"])
def test_interrupted_work_stops_accurately_without_renewal_or_refund(rig, guard):
    _app, journal, registry, worker, executor, ref, headers = rig
    before, _checkpoint = interrupt_after_preparation(rig)
    if guard == "cancel":
        executor.cancel(ref)
    elif guard == "stop":
        executor.control("stopped")
    elif guard == "expiry":
        executor.clock = lambda: before["lease_expires_at"] + 1
    elif guard == "attempts":
        with journal.transaction() as cx:
            value = executor._load(cx)
            plan = value["plans"][ref["plan_id"]]
            plan["recovery_attempts"].append(
                {
                    "ordinal": 2,
                    "reserved_service_work": 1,
                    "started_at": executor.clock(),
                    "original_lease_id": before["lease_id"],
                }
            )
            plan["observed"]["service_work"] = 2
            executor._save(cx, value)
    else:
        target = worker.output_root / "recovery-one-job" / "declared-inventory.csv"
        if guard == "missing":
            target.unlink()
        else:
            target.write_text("corrupted\n")
    assert executor.recover_pending() == []
    after = executor.status()["plans"][ref["plan_id"]]
    assert after["state"] in {"unknown", "cancelled"}
    assert after["lease_id"] == before["lease_id"] and after["lease_expires_at"] == before["lease_expires_at"]
    assert after["observed"]["service_work"] >= before["observed"]["service_work"]
    assert executor.status()["reserved"]["service_work"] == 2
    assert "outcome" not in after
    journal.verify()


def test_inflight_cancel_and_stop_are_distinct_and_durable(rig):
    _app, journal, registry, worker, executor, ref, headers = rig
    original = executor._checkpoint
    cancelled = []

    def checkpoint(*args, **kwargs):
        if not cancelled:
            executor.cancel(ref)
            cancelled.append(True)
        return original(*args, **kwargs)

    executor._checkpoint = checkpoint
    with pytest.raises(Conflict):
        executor.run(ref)
    executor._checkpoint = original
    assert executor.status()["plans"][ref["plan_id"]]["state"] == "cancelled"
    assert executor.recover_pending() == []
    assert executor.status()["state"] == "ready"
    executor.control("stopped")
    with pytest.raises(Conflict):
        executor.control("ready")
    assert app_for(Journal(journal.root), registry).state.strategy_executor.status()["state"] == "stopped"


def test_competing_writer_and_lost_reply_never_add_an_attempt(rig):
    app, journal, registry, worker, executor, ref, headers = rig
    peer = app_for(Journal(journal.root), registry).state.strategy_executor
    assert executor.execution_lock.acquire(False)
    try:
        with pytest.raises(Conflict):
            peer.run(ref)
    finally:
        executor.execution_lock.release()
    assert "recovery_attempts" not in executor.status()["plans"][ref["plan_id"]]
    completed = executor.run(ref)  # Drop this acknowledgement, then reconnect/replay.
    assert peer.run(ref)["outcome_hash"] == completed["outcome_hash"]
    plan = peer.status()["plans"][ref["plan_id"]]
    assert len(plan["recovery_attempts"]) == 1 and plan["observed"]["service_work"] == 1
    journal.verify()


def test_separate_process_lock_refuses_without_charging(rig):
    import fcntl
    import multiprocessing

    _app, journal, _registry, _worker, executor, ref, _headers = rig
    context = multiprocessing.get_context("fork")  # The only qualified profile is Linux.
    ready, release = context.Event(), context.Event()

    def hold():
        descriptor = os.open(journal.root / ".strategy-execution.lock", os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            ready.set()
            release.wait(10)
        finally:
            os.close(descriptor)

    child = context.Process(target=hold)
    child.start()
    try:
        assert ready.wait(5)
        with pytest.raises(Conflict, match="another executor process"):
            executor.run(ref)
        assert "recovery_attempts" not in executor.status()["plans"][ref["plan_id"]]
        assert executor.status()["reserved"]["service_work"] == 0
    finally:
        release.set()
        child.join(5)
        if child.is_alive():
            child.kill()
            child.join(5)
    assert child.exitcode == 0


def test_lock_symlink_is_refused_without_reading_target_or_charging(rig, tmp_path):
    _app, journal, _registry, _worker, executor, ref, _headers = rig
    target = tmp_path / "untouched.txt"
    target.write_text("unchanged")
    (journal.root / ".strategy-execution.lock").symlink_to(target)
    with pytest.raises(OSError):
        executor.run(ref)
    assert target.read_text() == "unchanged"
    assert "recovery_attempts" not in executor.status()["plans"][ref["plan_id"]]


@pytest.mark.parametrize("cancel_during_wait", [False, True, "stop"])
def test_server_sigkill_waits_for_surviving_original_writer_without_spending_attempt(rig, cancel_during_wait):
    import multiprocessing

    _app, journal, registry, _worker, executor, ref, headers = rig
    context = multiprocessing.get_context("fork")
    notice = context.Queue()

    def server():
        application = app_for(Journal(journal.root), registry)
        active = application.state.strategy_executor
        worker = application.state.source_assurance_worker
        checkpoint = active._checkpoint
        signalled = False

        def barrier(*args, **kwargs):
            nonlocal signalled
            prepared = worker.output_root / "recovery-one-job/stage-preparation.json"
            if prepared.exists() and not signalled:
                signalled = True
                os.killpg(worker.last_pid, signal.SIGSTOP)
                notice.put(worker.last_pid)
                # Test-only parent barrier: the test kills this server, leaving
                # its real owned Node child alive with the canonical writer lock.
                time.sleep(10)
            return checkpoint(*args, **kwargs)

        active._checkpoint = barrier
        active.run(ref)

    process = context.Process(target=server)
    process.start()
    node_pid = None
    try:
        node_pid = notice.get(timeout=10)
        process.kill()
        process.join(5)
        assert process.exitcode == -signal.SIGKILL
        before = executor.status()["plans"][ref["plan_id"]]
        assert before["state"] == "running" and len(before["recovery_attempts"]) == 1
        reopened = app_for(Journal(journal.root), registry)
        failures = []
        real_run = reopened.state.strategy_executor.run

        def capture(*args, **kwargs):
            try:
                return real_run(*args, **kwargs)
            except Exception as error:
                failures.append(repr(error))
                raise

        reopened.state.strategy_executor.run = capture
        with TestClient(reopened) as client:
            # The survivor is deliberately stopped. A restart must monitor it
            # without consuming the second and final lifetime attempt.
            end = time.monotonic() + 0.2
            while time.monotonic() < end:
                current = client.get("/api/strategy-executor/status", headers=headers).json()["plans"][ref["plan_id"]]
                assert len(current["recovery_attempts"]) == 1
                time.sleep(0.02)
            if cancel_during_wait == "stop":
                response = client.post("/api/strategy-executor/control", json={"state": "stopped"}, headers=headers)
                assert response.status_code == 200 and response.json()["state"] == "stopped"
            elif cancel_during_wait:
                response = client.post("/api/strategy-executor/cancel", json=ref, headers=headers)
                assert response.status_code == 200
                assert response.json()["cancel_requested"]
            os.killpg(node_pid, signal.SIGCONT)
            end = time.monotonic() + 10
            while time.monotonic() < end:
                current = client.get("/api/strategy-executor/status", headers=headers).json()["plans"][ref["plan_id"]]
                if current["state"] in {"completed", "unknown", "cancelled", "rejected"}:
                    break
                time.sleep(0.02)
            if cancel_during_wait == "stop":
                marker = journal.root / "source-assurance/recovery-one-job/CANCELLED.json"
                end = time.monotonic() + 5
                while not marker.exists() and time.monotonic() < end:
                    time.sleep(0.02)
                assert current["state"] in {"running", "unknown"}
                assert current["observed"]["service_work"] == len(current["recovery_attempts"]) == 1
                assert reopened.state.strategy_executor.status()["state"] == "stopped"
                with pytest.raises(Conflict):
                    reopened.state.strategy_executor.control("ready")
                assert (journal.root / "source-assurance/recovery-one-job/CANCELLED.json").is_file()
                output = os.environ.get("SOURCE_ASSURANCE_EVIDENCE_DIR")
                if output:
                    path = Path(output) / "server-stop-recovery.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(
                        json.dumps(
                            {
                                "passed": True,
                                "serverSignal": "SIGKILL",
                                "permanentStop": True,
                                "orphanSawCancellationMarker": True,
                                "chargedAttempts": 1,
                                "reservationRetained": 2,
                                "originalLeaseUnchanged": current["lease_expires_at"] == before["lease_expires_at"],
                                "source_hash": current["source_hash"],
                                "approvedOperator": "NOT RUN",
                            },
                            indent=2,
                        )
                        + "\n"
                    )
                return
            if cancel_during_wait:
                assert current["state"] == "cancelled", failures or current
                assert current["observed"]["service_work"] == len(current["recovery_attempts"]) == 1
                assert "outcome" not in current
                status = reopened.state.strategy_executor.status()
                assert status["reserved"]["service_work"] == 2
                assert current["lease_id"] == before["lease_id"]
                assert current["lease_expires_at"] == before["lease_expires_at"]
                assert (journal.root / "source-assurance/recovery-one-job/CANCELLED.json").is_file()
                now = datetime.now(timezone.utc)

                def fmt(dt):
                    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")

                next_input = reopened.state.source_assurance_worker.prepare_input(
                    "public-five-paths",
                    "next-after-cancel",
                    created_at=fmt(now),
                    expires_at=fmt(now + timedelta(minutes=10)),
                )
                next_plan = reopened.state.strategy_executor.prepare(
                    {"method": "run-mission", "input": next_input, "request_id": "next-after-cancel"}
                )
                next_ref = {k: next_plan[k] for k in ("plan_id", "plan_digest")}
                reopened.state.strategy_executor.approve(next_ref)
                assert reopened.state.strategy_executor.run(next_ref)["state"] == "completed"
                output = os.environ.get("SOURCE_ASSURANCE_EVIDENCE_DIR")
                if output:
                    path = Path(output) / "server-cancel-recovery.json"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text(
                        json.dumps(
                            {
                                "passed": True,
                                "serverSignal": "SIGKILL",
                                "cancelledAfterOriginalWriterExit": True,
                                "chargedAttempts": 1,
                                "reservationRetained": 2,
                                "nextSeparatelyApprovedMissionAccepted": True,
                                "originalLeaseUnchanged": True,
                                "source_hash": current["source_hash"],
                                "approvedOperator": "NOT RUN",
                            },
                            indent=2,
                        )
                        + "\n"
                    )
                return
            assert current["state"] == "completed", failures or current
            assert current["outcome"]["result"]["independentAcceptance"]["accepted"]
            assert current["observed"]["service_work"] == len(current["recovery_attempts"]) == 2
            assert all(current[k] == before[k] for k in ("lease_id", "lease_expires_at", "approved_at", "started_at"))
            output = os.environ.get("SOURCE_ASSURANCE_EVIDENCE_DIR")
            if output:
                root = Path(output)
                root.mkdir(parents=True, exist_ok=True)
                (root / "server-sigkill-recovery.json").write_text(
                    json.dumps(
                        {
                            "schema": "alpha-source-server-crash-acceptance/v1",
                            "passed": True,
                            "serverSignal": "SIGKILL",
                            "originalSourceChildSurvived": True,
                            "waitingConsumedNoAttempt": True,
                            "originalLeaseUnchanged": True,
                            "accepted": True,
                            "attemptsCharged": 2,
                            "outcomeHash": current["outcome_hash"],
                            "source_hash": current["source_hash"],
                            "approvedOperator": "NOT RUN",
                        },
                        indent=2,
                    )
                    + "\n"
                )
    finally:
        if process.is_alive():
            process.kill()
        process.join(5)
        if node_pid is not None:
            try:
                os.killpg(node_pid, signal.SIGCONT)
                os.killpg(node_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
