# SPDX-License-Identifier: Apache-2.0
"""Actual installed server SIGKILL/restart; no replay or clock substitution."""
from __future__ import annotations

import concurrent.futures
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

import httpx

if os.environ.get("STRATEGY_INSTALLED_ACCEPTANCE") == "1":
    from strategy_succession_engineering.serve import ROOT
else:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from serve import ROOT

from alpha_factory_v1.core.runtime.store import Journal
from test_integration import sample


from proc_namespace import (
    current_proc_pid,
    namespace_pid_to_proc,
    proc_pid_to_namespace,
    proc_children,
    _state,
    _running,
)


def descendants(proc_pid: int) -> set[int]:
    found = proc_children(proc_pid)
    for child in list(found):
        found.update(descendants(child))
    return found


def active(proc_pid: int, original: dict) -> bool:
    return _running(_state(proc_pid), original)


def test_real_server_crash_restart_preserves_uncertain_work(tmp_path):
    journal = Journal.initialize(tmp_path / "private-crash-home")
    token = (journal.root / "api.token").read_text().strip()
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    commands = [sys.executable, str(ROOT / "serve.py"), "--home", str(journal.root), "--port", str(port), "--native"]
    process = None
    survivors: dict[int, dict] = {}
    output = Path(os.environ.get("STRATEGY_EVIDENCE_DIR", Path(__file__).resolve().parents[1] / "acceptance-public"))
    output.mkdir(parents=True, exist_ok=True)

    def launch():
        server = subprocess.Popen(
            commands, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True
        )
        for _ in range(400):
            if server.poll() is not None:
                raise AssertionError("Reviewed installed server refused startup")
            try:
                if client.get("/api/strategy-executor/status").status_code == 200:
                    return server
            except httpx.TransportError:
                pass
            time.sleep(0.025)
        server.kill()
        server.wait(timeout=5)
        raise AssertionError("Reviewed server did not become ready")

    with httpx.Client(
        base_url=origin, headers={"Authorization": "Bearer " + token}, timeout=130, trust_env=False
    ) as client:
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        try:
            process = launch()
            response = client.post(
                "/api/strategy-executor/prepare",
                json={"method": "run-journey", "input": sample(), "request_id": "crash-after-committed-phase"},
            )
            response.raise_for_status()
            plan = response.json()
            binding = {"plan_id": plan["plan_id"], "plan_digest": plan["plan_digest"]}
            assert client.post("/api/strategy-executor/approve", json=binding).status_code == 200
            pending = pool.submit(client.post, "/api/strategy-executor/run", json=binding)
            for _ in range(2000):
                before = client.get("/api/strategy-executor/status").json()
                retained = before["plans"][plan["plan_id"]]
                if retained.get("partial_receipts"):
                    break
                assert not pending.done(), "Journey finished before the crash checkpoint was observed"
                time.sleep(0.01)
            assert retained["state"] == "running" and retained.get("partial_receipts")
            server_proc_pid = namespace_pid_to_proc(process.pid, parent_proc_pid=current_proc_pid())
            assert proc_pid_to_namespace(server_proc_pid) == process.pid
            survivors = {pid: _state(pid) for pid in descendants(server_proc_pid)}
            assert survivors, "The actual fixed worker process must be observed"
            crashed_at = time.perf_counter()
            os.kill(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
            try:
                pending.result(timeout=10)
            except httpx.TransportError:
                pass
            # SIGKILL cannot run Python finally. Pipe EOF fences Node at its next
            # checkpoint; an already active native call has an 8s outer bound.
            for _ in range(500):
                if not any(active(pid, old) for pid, old in survivors.items()):
                    break
                time.sleep(0.025)
            assert not any(
                active(pid, old) for pid, old in survivors.items()
            ), "A fixed worker descendant outlived its documented crash bound"
            descendant_stop_seconds = time.perf_counter() - crashed_at
            process = launch()
            restarted = client.get("/api/strategy-executor/status").json()
            recovered = restarted["plans"][plan["plan_id"]]
            assert recovered["state"] in {"running", "unknown"}
            assert recovered["partial_receipts"][: len(retained["partial_receipts"])] == retained["partial_receipts"]
            assert restarted["reserved"] == before["reserved"]
            assert recovered.get("outcome") is None
            replay_code = client.post("/api/strategy-executor/run", json=binding).status_code
            assert replay_code == 409
            reconcile_code = client.post(
                "/api/strategy-executor/reconcile",
                json={
                    "plan_id": plan["plan_id"],
                    "record_digest": restarted["digest"],
                    "note": "Test operator inspected a killed executor. No replay is permitted.",
                },
            ).status_code
            assert reconcile_code in {200, 409}
            if recovered["state"] == "running":
                assert reconcile_code == 409, "An unexpired active lease cannot be cleared"
            assert client.post("/api/strategy-executor/control", json={"state": "stopped"}).status_code == 200
            stopped = client.get("/api/strategy-executor/status").json()
            assert stopped["reserved"] == before["reserved"]
            assert stopped["plans"][plan["plan_id"]]["partial_receipts"] == recovered["partial_receipts"]
            assert client.post("/api/strategy-executor/control", json={"state": "ready"}).status_code == 409
            exported = client.get("/api/strategy-executor/export/" + plan["plan_id"]).json()
            assert token not in json.dumps(exported) and str(journal.root) not in json.dumps(exported)
            assert journal.verify()["valid"] is True
            record = {
                "schema": "strategy-engineering-crash-recovery/v1",
                "passed": True,
                "actual_supervisor_signal": "SIGKILL",
                "source_hash": plan["source_hash"],
                "descendants_observed": len(survivors),
                "descendants_inactive": True,
                "descendant_stop_seconds": descendant_stop_seconds,
                "restarted_state": recovered["state"],
                "reserved_before": before["reserved"],
                "reserved_after": stopped["reserved"],
                "retained_partial_hashes": [x["receipt_hash"] for x in recovered["partial_receipts"]],
                "duplicate_run_http": replay_code,
                "early_reconciliation_http": reconcile_code,
                "no_automatic_replay": True,
                "unknown_work_refunded": False,
                "operator_interventions": [
                    "ephemeral test-home setup",
                    "prepare",
                    "exact approval",
                    "start",
                    "SIGKILL injection after checked phase",
                    "restart unchanged installed source",
                    "inspect status",
                    "refused duplicate",
                    "inspect reconciliation",
                    "permanent STOP",
                    "export",
                ],
                "export": exported,
                "production_authority": False,
            }
            (output / "crash-recovery.json").write_text(json.dumps(record, indent=2) + "\n")
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            for proc_pid, old in survivors.items():
                if active(proc_pid, old):
                    os.kill(proc_pid_to_namespace(proc_pid), signal.SIGKILL)
            pool.shutdown(wait=True)
