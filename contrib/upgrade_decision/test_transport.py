# SPDX-License-Identifier: Apache-2.0
"""Finite fixture qualification over the existing journal and HTTP routes."""

from __future__ import annotations

import base64
import json
import shutil
import sys
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from contrib.upgrade_decision.worker import HERE, UpgradeDecisionWorker, create_app, source_inventory, source_worker


@pytest.fixture
def rig(tmp_path: Path) -> Any:
    for name in ("catalog.json", "historical.json", "native-component.json"):
        shutil.copyfile(HERE / "examples" / name, tmp_path / name)
    worker = UpgradeDecisionWorker(
        tmp_path / "catalog.json",
        python=Path(sys.executable),
        node=Path(str(shutil.which("node"))),
        git=Path(str(shutil.which("git"))),
    )
    transport = source_worker.load_transport()
    journal = Journal.initialize(tmp_path / "test-only-journal")
    policy = transport.ExecutorPolicy(
        "upgrade-isolated-fixture-v1",
        source_inventory(worker),
        {"run-mission": transport.Limits(2)},
        transport.Limits(4),
        max_requests=4,
        grant_seconds=180,
        request_seconds=60,
        max_output_bytes=1_000_000,
        recovery_attempts=2,
    )
    executor = transport.StrategyExecutor(journal, worker, policy)
    return worker, journal, policy, executor, transport


def prepare(rig: Any, ident: str = "upgrade-one") -> tuple[dict[str, Any], dict[str, Any]]:
    worker, _, _, executor, _ = rig
    prepared = executor.prepare(
        {"method": "run-mission", "input": worker.prepare_input("starlette-httpx-historical"), "request_id": ident}
    )
    return prepared, {k: prepared[k] for k in ("plan_id", "plan_digest")}


def test_actual_http_auth_approval_download_and_signed_history(rig: Any) -> None:
    worker, journal, policy, _, _ = rig
    app = create_app(journal, worker, policy)
    token = (journal.root / "api.token").read_text().strip()
    headers = {"Authorization": "Bearer " + token, "Origin": "http://testserver"}
    with TestClient(app) as client:
        assert client.get("/api/strategy-executor/status").status_code == 401
        assert client.get("/menu.json").status_code == 404
        assert "Review this update" in client.get("/").text
        assert (
            client.post(
                "/api/strategy-executor/prepare", json={}, headers={**headers, "Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        value = client.post(
            "/api/strategy-executor/prepare",
            json={
                "method": "run-mission",
                "input": worker.prepare_input("starlette-httpx-historical"),
                "request_id": "api-one",
            },
            headers=headers,
        )
        assert value.status_code == 200, value.text
        ref = {k: value.json()[k] for k in ("plan_id", "plan_digest")}
        assert client.post("/api/strategy-executor/run", json=ref, headers=headers).status_code == 409
        assert client.post("/api/strategy-executor/approve", json=ref, headers=headers).status_code == 200
        reply = client.post("/api/strategy-executor/run", json=ref, headers=headers)
        assert reply.status_code == 200, reply.text
        completed = reply.json()
        assert (
            completed["state"] == "completed" and completed["outcome"]["result"]["nextAction"] == "HOLD_UPDATE_AND_TEST"
        )
        item = completed["outcome"]["result"]["download"]
        assert len(base64.b64decode(item["base64"])) == item["bytes"]
        exported = client.get("/api/strategy-executor/export/" + ref["plan_id"], headers=headers).json()
        assert exported["body"]["production_authority"] is False and token not in json.dumps(exported)
    journal.verify()


def test_duplicate_submit_and_reconnect_do_not_repeat_work(rig: Any) -> None:
    worker, journal, policy, executor, transport = rig
    prepared, ref = prepare(rig)
    executor.approve(ref)
    completed = executor.run(ref)
    restored = transport.StrategyExecutor(Journal(journal.root), worker, policy)
    assert restored.run(ref)["outcome_hash"] == completed["outcome_hash"]
    assert (
        restored.prepare({"method": "run-mission", "input": prepared["input"], "request_id": "upgrade-one"})["plan_id"]
        == prepared["plan_id"]
    )
    assert len(restored.status()["plans"][prepared["plan_id"]]["recovery_attempts"]) == 1
    assert restored.status()["spent"]["service_work"] == 1


def test_cancel_and_stop_are_durable_and_do_not_renew(rig: Any) -> None:
    _, journal, _, executor, _ = rig
    _, ref = prepare(rig)
    executor.approve(ref)
    executor.cancel(ref)
    assert executor.run(ref)["state"] == "cancelled"
    executor.control("stopped")
    with pytest.raises(Conflict):
        executor.control("ready")
    journal.verify()


def test_exhausted_total_budget_refuses_without_extra_attempt(rig: Any) -> None:
    worker, journal, policy, _, transport = rig
    policy = replace(policy, total=transport.Limits(2))
    other = Journal.initialize(journal.root.parent / "bounded-test-only")
    executor = transport.StrategyExecutor(other, worker, policy)
    narrower = worker, other, policy, executor, transport
    _, ref = prepare(narrower)
    executor.approve(ref)
    executor.run(ref)
    _, second = prepare(narrower, "second")
    executor.approve(second)
    with pytest.raises(Conflict):
        executor.run(second)
    assert executor.status()["spent"]["service_work"] == 1


def test_interruption_recovers_only_under_original_lease_and_charges_both(rig: Any) -> None:
    worker, journal, policy, executor, transport = rig
    prepared, ref = prepare(rig)
    executor.approve(ref)
    original = worker._process
    once = [True]

    def interrupted(*args: Any, **kwargs: Any) -> Any:
        if once[0]:
            once[0] = False
            raise RuntimeError("injected interruption after precharge, before child")
        return original(*args, **kwargs)

    worker._process = interrupted
    with pytest.raises(RuntimeError):
        executor.run(ref)
    pending = executor.status()["plans"][prepared["plan_id"]]
    original_lease = pending["lease_id"], pending["lease_expires_at"], pending["expires_at"]
    assert pending["observed"]["service_work"] == 1
    restored = transport.StrategyExecutor(Journal(journal.root), worker, policy)
    assert prepared["plan_id"] in restored.recover_pending()
    completed = restored.status()["plans"][prepared["plan_id"]]
    assert completed["state"] == "completed" and len(completed["recovery_attempts"]) == 2
    assert (completed["lease_id"], completed["lease_expires_at"], completed["expires_at"]) == original_lease
    assert restored.status()["spent"]["service_work"] == 2


def test_expired_approval_never_starts_worker(rig: Any) -> None:
    _, _, _, executor, _ = rig
    prepared, ref = prepare(rig)
    executor.approve(ref)
    executor.clock = lambda: prepared["expires_at"] + 1
    with pytest.raises(Conflict):
        executor.run(ref)
    assert executor.status()["spent"]["service_work"] == 0


def test_changed_pack_is_not_recovered_as_same_approval(rig: Any) -> None:
    worker, _, _, executor, _ = rig
    _, ref = prepare(rig)
    executor.approve(ref)
    worker.paths[1].write_bytes(b"{}")
    with pytest.raises(ValueError):
        executor.run(ref)


def test_component_refuses_policy_that_expands_native_authority(rig: Any) -> None:
    worker, journal, policy, _, _ = rig
    expanded = replace(policy, recovery_attempts=0, allow_native=True)
    with pytest.raises(ValueError):
        create_app(journal, worker, expanded)


def test_component_cannot_omit_existing_enforcement_source_bindings(rig: Any) -> None:
    worker, journal, policy, _, _ = rig
    incomplete = replace(policy, sources=policy.sources[:-1])
    with pytest.raises(ValueError):
        create_app(journal, worker, incomplete)


def test_actual_component_child_kill_recovers_with_both_attempts_charged(rig: Any, monkeypatch: Any) -> None:
    worker, journal, policy, executor, transport = rig
    prepared = executor.prepare(
        {
            "method": "run-mission",
            "input": worker.prepare_input("native-component-refresh-development"),
            "request_id": "actual-child-kill",
        }
    )
    ref = {k: prepared[k] for k in ("plan_id", "plan_digest")}
    executor.approve(ref)
    real_launch = source_worker.subprocess.Popen
    killed = []
    timers = []

    def launch(*args: Any, **kwargs: Any) -> Any:
        child = real_launch(*args, **kwargs)
        if not timers:

            def interrupt() -> None:
                if child.poll() is None:
                    child.kill()
                    killed.append(True)

            timer = threading.Timer(0.005, interrupt)
            timers.append(timer)
            timer.start()
        return child

    monkeypatch.setattr(source_worker.subprocess, "Popen", launch)
    with pytest.raises(ValueError):
        executor.run(ref)
    for timer in timers:
        timer.join(timeout=1)
    assert killed == [True]
    pending = executor.status()["plans"][prepared["plan_id"]]
    assert pending["state"] == "unknown" and pending["observed"]["service_work"] == 1
    restored = transport.StrategyExecutor(Journal(journal.root), worker, policy)
    assert prepared["plan_id"] in restored.recover_pending()
    final = restored.status()["plans"][prepared["plan_id"]]
    assert final["state"] == "completed" and final["outcome"]["result"]["nextAction"] == "ADVANCE_COMPONENT_KEEP_LOCK"
    assert final["lease_expires_at"] == pending["lease_expires_at"] and len(final["recovery_attempts"]) == 2
    assert restored.status()["spent"]["service_work"] == 2
