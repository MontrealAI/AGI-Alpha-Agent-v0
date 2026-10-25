# SPDX-License-Identifier: Apache-2.0
"""Authored transport-stub tests; these do not qualify scientific outcomes."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import time

import pytest

from fixed_worker import FixedWorker, WorkerError

SOURCE = "a" * 64


def limits(**changes):
    return dict(
        service_work=100,
        improvement_work=100,
        native_calls=0,
        native_solve_seconds=0,
        wall_seconds=2,
        allow_native=False,
        source_hash=SOURCE,
        **changes,
    )


def worker_root(tmp_path: Path, source: str) -> Path:
    (tmp_path / "fixed_worker.mjs").write_text(source)
    manifest = {
        "scientific_source_hash": "b" * 64,
        "files": [{"path": "fixed_worker.mjs", "sha256": hashlib.sha256(source.encode()).hexdigest()}],
    }
    (tmp_path / "SOURCE_FILES.json").write_text(json.dumps(manifest))
    return tmp_path


def success_source(*, cost=7, source_hash=SOURCE, final_cost=None):
    final_cost = cost if final_cost is None else final_cost
    return f"""import readline from 'node:readline';
const lines=readline.createInterface({{input:process.stdin}});let phase=0;
lines.on('line',line=>{{const input=JSON.parse(line);if(phase===0){{phase=1;console.log(JSON.stringify({{type:'checkpoint',seq:0,phase:'fixed-phase',increments:{{service_work:{cost}}}}}));}}
else{{console.log(JSON.stringify({{type:'result',source_hash:'{source_hash}',verified:true,result:{{kind:'AUTHORED_STUB',secret:process.env.TEST_SECRET??null,python:process.env.FIXED_PYTHON}},costs:{{service_work:{final_cost},improvement_work:0,native_calls:0,native_solve_seconds:0,unknown_costs:[]}}}}));lines.close();}}}});
"""


def test_fixed_success_charges_once_and_sanitizes_environment(tmp_path, monkeypatch):
    root = worker_root(tmp_path, success_source())
    monkeypatch.setenv("TEST_SECRET", "must-not-leave-parent")
    debits = []
    worker = FixedWorker(root)
    first_manifest = worker.verify_sources()
    result = worker.execute("run-mission", {"authored": True}, limits(), lambda **values: debits.append(values))
    assert debits == [{}, {"service_work": 7}]
    assert result["costs"]["service_work"] == 7 and result["verified"]
    assert result["result"]["secret"] is None
    assert result["result"]["python"] == str(Path(sys.executable).resolve())
    assert worker.last_progress["phase"] == "fixed-phase"
    assert worker.verify_sources() == first_manifest


def test_source_tamper_refuses_before_checkpoint(tmp_path):
    root = worker_root(tmp_path, success_source())
    (root / "fixed_worker.mjs").write_text("throw Error('tampered')")
    debits = []
    with pytest.raises(WorkerError, match="SOURCE_IDENTITY_CHANGED"):
        FixedWorker(root).execute("run-mission", {}, limits(), lambda **values: debits.append(values))
    assert debits == []


@pytest.mark.parametrize(
    "path", ["../fixed_worker.mjs", "/fixed_worker.mjs", "./fixed_worker.mjs", "folder/../fixed_worker.mjs"]
)
def test_manifest_paths_cannot_escape_or_alias_root(tmp_path, path):
    worker_root(tmp_path, success_source())
    manifest = json.loads((tmp_path / "SOURCE_FILES.json").read_text())
    manifest["files"][0]["path"] = path
    (tmp_path / "SOURCE_FILES.json").write_text(json.dumps(manifest))
    with pytest.raises(WorkerError, match="SOURCE_PATH_SCOPE"):
        FixedWorker(tmp_path).verify_sources()


def test_manifest_symlink_is_rejected(tmp_path):
    root = worker_root(tmp_path, success_source())
    target = tmp_path / "actual.mjs"
    (root / "fixed_worker.mjs").rename(target)
    (root / "fixed_worker.mjs").symlink_to(target)
    with pytest.raises(WorkerError, match="SOURCE_SYMLINK_REFUSED"):
        FixedWorker(root).verify_sources()


def test_report_cannot_understate_checkpoint_cost(tmp_path):
    root = worker_root(tmp_path, success_source(final_cost=0))
    debits = []
    with pytest.raises(WorkerError, match="RESULT_CHECKPOINT_COST_MISMATCH") as caught:
        FixedWorker(root).execute("construct", {}, limits(), lambda **values: debits.append(values))
    assert debits == [{}, {"service_work": 7}]
    assert caught.value.costs["service_work"] == 7
    assert caught.value.costs["unknown_costs"]


def test_report_source_identity_must_match_operator_source(tmp_path):
    root = worker_root(tmp_path, success_source(source_hash="c" * 64))
    with pytest.raises(WorkerError, match="RESULT_SOURCE_HASH_MISMATCH"):
        FixedWorker(root).execute("run-journey", {}, limits(), lambda **values: None)


def test_overbudget_checkpoint_does_not_reach_transport(tmp_path):
    root = worker_root(tmp_path, success_source(cost=101))
    debits = []
    with pytest.raises(WorkerError, match="CHECKPOINT_COST_EXCEEDS_CAP"):
        FixedWorker(root).execute("run-mission", {}, limits(), lambda **values: debits.append(values))
    assert debits == [{}]


def test_timeout_retains_unknown_costs_and_reaps_child(tmp_path):
    root = worker_root(tmp_path, "setInterval(()=>{},100);")
    cap = limits()
    cap["wall_seconds"] = 0.15
    before = time.monotonic()
    with pytest.raises(WorkerError, match="WORKER_WALL_TIMEOUT") as caught:
        FixedWorker(root).execute("run-mission", {}, cap, lambda **values: None)
    assert time.monotonic() - before < 2
    assert caught.value.interrupted and caught.value.costs["unknown_costs"]


def test_stop_kills_descendant_process_group(tmp_path):
    root = worker_root(
        tmp_path,
        """import {spawn} from 'node:child_process';import fs from 'node:fs';
const child=spawn(process.execPath,['-e','setInterval(()=>{},100)'],{stdio:'ignore'});fs.writeFileSync('child.pid',String(child.pid));
setTimeout(()=>console.log(JSON.stringify({type:'checkpoint',seq:0,phase:'STOP_BOUNDARY',increments:{}})),30);setInterval(()=>{},100);
""",
    )
    calls = []

    def checkpoint(**values):
        calls.append(values)
        if len(calls) == 2:
            raise RuntimeError("OPERATOR_STOP")

    with pytest.raises(WorkerError, match="CHECKPOINT_REFUSED") as caught:
        FixedWorker(root).execute("run-journey", {}, limits(), checkpoint)
    assert caught.value.interrupted
    pid = int((root / "child.pid").read_text())
    state = Path(f"/proc/{pid}/stat")
    for _ in range(20):
        if not state.exists() or state.read_text().split()[2] == "Z":
            break
        time.sleep(0.02)
    assert not state.exists() or state.read_text().split()[2] == "Z"


def test_output_flood_is_bounded(tmp_path, monkeypatch):
    import fixed_worker

    root = worker_root(tmp_path, "console.log('x'.repeat(10000));")
    monkeypatch.setattr(fixed_worker, "MAX_OUTPUT_BYTES", 1000)
    with pytest.raises(WorkerError, match="WORKER_OUTPUT_LIMIT"):
        FixedWorker(root).execute("run-mission", {}, limits(), lambda **values: None)


def test_payload_cannot_select_method_or_interpreter(tmp_path):
    root = worker_root(tmp_path, success_source())
    worker = FixedWorker(root)
    with pytest.raises(WorkerError, match="REQUEST_SCOPE"):
        worker.execute("shell", {"command": "anything"}, limits(), lambda **values: None)
    with pytest.raises(WorkerError, match="OPERATOR_NODE_ABSOLUTE_PATH_REQUIRED"):
        FixedWorker(root, node="node")
    with pytest.raises(WorkerError, match="NATIVE_ALLOWANCE_WITHOUT_APPROVAL"):
        cap = limits()
        cap["native_calls"] = 1
        worker.execute("run-mission", {}, cap, lambda **values: None)


def test_request_nan_is_rejected_before_process(tmp_path):
    root = worker_root(tmp_path, success_source())
    with pytest.raises(WorkerError, match="REQUEST_JSON_SCOPE"):
        FixedWorker(root).execute("run-mission", {"value": float("nan")}, limits(), lambda **values: None)


def phase_receipt():
    return {
        "phase_index": 0,
        "receipt_hash": "d" * 64,
        "task": {"id": "authored-transport-only"},
        "result": {"schedule": []},
        "checker": {"valid": True},
        "selectedmethod": "AUTHORED_TRANSPORT_STUB",
    }


def receipt_source(receipt, outer_source=SOURCE):
    source = success_source()
    return source.replace(
        "increments:{service_work:7}",
        "increments:{service_work:7},source_hash:" + json.dumps(outer_source) + ",receipt:" + json.dumps(receipt),
    )


def test_receipt_is_forwarded_once_before_ack_without_double_debit(tmp_path):
    receipt = phase_receipt()
    root = worker_root(tmp_path, receipt_source(receipt))
    calls, progress = [], []
    worker = FixedWorker(root, on_progress=progress.append)
    outcome = worker.execute("run-journey", {}, limits(), lambda **values: calls.append(values))
    assert calls == [{}, {"receipt": receipt, "service_work": 7}]
    assert outcome["costs"]["service_work"] == 7
    assert progress == [{"seq": 0, "phase": "fixed-phase", "increments": {"service_work": 7}, "receipt": receipt}]


def test_receipt_source_forgery_refuses_before_callback_or_ack(tmp_path):
    root = worker_root(tmp_path, receipt_source(phase_receipt(), "e" * 64))
    calls = []
    with pytest.raises(WorkerError, match="RECEIPT_SOURCE_HASH_MISMATCH"):
        FixedWorker(root).execute("run-journey", {}, limits(), lambda **values: calls.append(values))
    assert calls == [{}]


@pytest.mark.parametrize(
    "change,code",
    [
        ({"extra": "not-an-allowed-field"}, "RECEIPT_SCHEMA"),
        ({"phase_index": True}, "RECEIPT_PHASE_SCOPE"),
        ({"phase_index": 3}, "RECEIPT_PHASE_SCOPE"),
        ({"receipt_hash": "unknown"}, "RECEIPT_IDENTITY_SCOPE"),
        ({"task": []}, "RECEIPT_DATA_SCOPE"),
        ({"checker": {"valid": False}}, "RECEIPT_NOT_INDEPENDENTLY_VERIFIED"),
        ({"selectedmethod": ""}, "RECEIPT_METHOD_SCOPE"),
    ],
)
def test_invalid_receipt_never_reaches_journal_callback(tmp_path, change, code):
    receipt = {**phase_receipt(), **change}
    root = worker_root(tmp_path, receipt_source(receipt))
    calls = []
    with pytest.raises(WorkerError, match=code):
        FixedWorker(root).execute("run-journey", {}, limits(), lambda **values: calls.append(values))
    assert calls == [{}]


def test_known_rejection_preserves_measured_cost_instead_of_claiming_uncertainty(tmp_path):
    source = success_source().replace("verified:true", "verified:false")
    root = worker_root(tmp_path, source)
    outcome = FixedWorker(root).execute("construct", {}, limits(), lambda **values: None)
    assert outcome["verified"] is False and outcome["costs"]["service_work"] == 7
    assert outcome["costs"]["unknown_costs"] == []


def test_nonboolean_verification_flag_is_refused(tmp_path):
    source = success_source().replace("verified:true", "verified:'true'")
    root = worker_root(tmp_path, source)
    with pytest.raises(WorkerError, match="RESULT_VERIFICATION_TYPE"):
        FixedWorker(root).execute("construct", {}, limits(), lambda **values: None)
