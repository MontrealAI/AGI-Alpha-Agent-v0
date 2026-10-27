# SPDX-License-Identifier: Apache-2.0
"""Actual two-process lost-acknowledgement recovery through the existing workbench."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(encode(value)).hexdigest()


def write(path, value):
    with Path(path).open("wb") as output:
        output.write(encode(value) + b"\n")
        output.flush()
        os.fsync(output.fileno())


def cpu_children_ms():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return 1000 * (usage.ru_utime + usage.ru_stime)


def execution(directory, mission):
    event = {"mission": mission, "pid": os.getpid(), "at_ns": time.time_ns()}
    with (directory / "execution-events.jsonl").open("ab") as output:
        output.write(encode(event) + b"\n")
        output.flush()
        os.fsync(output.fileno())


def worker(role, directory, source_hash):
    from companion.numerical import DEPENDENCIES, Factor, make_task, matrix, operator_id, with_load
    from review.checker import check
    from runtime.custody import Custody
    from runtime.workbench_client import WorkbenchClient

    config = json.loads((directory / "probe-config.json").read_text())
    if config["source_hash"] != source_hash:
        raise ValueError("PROBE_SOURCE_CHANGED")
    base = make_task(27104, side=24)
    task = base if role == "first" else with_load(base, 28104)
    request_a = {"mission": "A", "task_digest": sha(base), "operator_digest": operator_id(base)}
    with Custody(directory / "custody", source_hash, 2000, 300, 250, dependencies=DEPENDENCIES,
                 expires_at=config["expires_at"], deadline_at=config["deadline_at"]) as custody:
        if role == "second":
            historical = custody.reserve("A", "service", 500, sha(request_a))
            original = json.loads((directory / "A-terminal.json").read_text())
            if historical["execute"] or historical != original:
                raise AssertionError("LOST_ACK_RECOVERY_CHANGED_ACCEPTED_RESULT")
            write(directory / "duplicate-recovery.json", {"pid": os.getpid(), "execute": historical["execute"],
                "same_terminal": historical == original, "receipt_digest": historical["receipt_digest"],
                "historical_status": historical["status"], "active_proof": [], "active_authority": []})
        mid = "A" if role == "first" else "B"
        request = request_a if role == "first" else {"mission": "B", "task_digest": sha(task),
            "operator_digest": operator_id(task), "parent_receipt": historical["receipt_digest"]}
        reservation = custody.reserve(mid, "service", 500, sha(request))
        if not reservation["execute"]:
            raise AssertionError("UNEXPECTED_PRIOR_MISSION")
        cpu_start, child_start, wall_start = time.process_time_ns(), cpu_children_ms(), time.perf_counter_ns()
        details = {}

        def callback(inputs):
            if inputs != request or sha(task) != inputs["task_digest"]:
                raise AssertionError("INPUT_BINDING")
            execution(directory, mid)
            if role == "first":
                factor = Factor(matrix(base), operator_id(base), "COLAMD")
                factor_receipt = factor.save(directory / "parent.npz")
                write(directory / "parent-receipt.json", factor_receipt)
                construction = "fresh native COLAMD factor byproduct"
            else:
                factor_receipt = json.loads((directory / "parent-receipt.json").read_text())
                factor = Factor.load(directory / "parent.npz", factor_receipt, operator_id(base))
                construction = "portable sparse factors restored in a different OS process"
            before = factor.calls
            values = factor.solve(task["rhs"]).tolist()
            checked = check(task, values)
            if not checked["valid"]:
                raise AssertionError("NUMERICAL_CHECK_FAILED")
            details.update({"factor_identity": factor.identity, "parent_calls": factor.calls - before,
                "factor_native": factor.native, "construction": construction, "checker": checked,
                "solution_digest": sha(values), "values": values, "factor_receipt": factor_receipt})
            return {"valid": True, "qualified": True, "summary": "Fresh grounded-network response passed edge balance and energy checks.",
                "mission": mid, "task_digest": sha(task), "solution_digest": sha(values),
                "factor_identity": factor.identity, "parent_calls": factor.calls - before,
                "checker": checked, "proof": [], "authority": []}

        with WorkbenchClient() as client:
            result = client.run(mid, "Actual process recovery development probe", request, callback, source_hash)
            startup_wall_ms = client.startup_wall_ms
        if result["callback_calls"] != 1 or result["callback_failure"] is not None:
            raise AssertionError("CALLBACK_NOT_COMPLETED")
        write(directory / (mid + "-pack.json"), result["pack"])
        write(directory / (mid + "-task.json"), task)
        write(directory / (mid + "-solution.json"), details.pop("values"))
        cpu_ms = (time.process_time_ns() - cpu_start) / 1e6 + cpu_children_ms() - child_start
        wall_ms = (time.perf_counter_ns() - wall_start) / 1e6
        receipt = {"valid": True, "qualified": True, "source_hash": source_hash,
            "task_digest": sha(task), "solution_digest": details["solution_digest"],
            "factor_identity": details["factor_identity"], "pack_digest": result["pack"]["integrityDigest"]}
        terminal = custody.commit(mid, cpu_ms, receipt)
        if not terminal["accepted"]:
            raise AssertionError("PROBE_ACCOUNT_REFUSAL")
        if role == "first":
            custody.retain_asset("native-factor", details["factor_identity"], "A", scope=operator_id(base))
            custody.select_asset(details["factor_identity"])
        write(directory / (mid + "-terminal.json"), terminal)
        write(directory / (mid + "-worker.json"), {"pid": os.getpid(), "role": role, "source_hash": source_hash,
            "cpu_ms_before_commit": cpu_ms, "wall_ms_before_commit": wall_ms,
            "workbench_startup_wall_ms": startup_wall_ms, "node_run_cpu_us": result["node_cpu_us"],
            "inspection": result["inspection"], "details": details, "checkpoint": custody.checkpoint()})
        write(directory / "latest-custody-status.json", custody.status())
    if role == "first":
        os._exit(23)
    print(json.dumps({"kind": "acknowledged", "mission": "B", "pid": os.getpid(),
                      "receipt_digest": terminal["receipt_digest"]}), flush=True)


def supervise(directory, source_hash):
    directory.mkdir(parents=True, exist_ok=False)
    now = time.time()
    config = {"schema": "earned-turn-process-recovery/v1", "source_hash": source_hash,
        "scope": "operational development probe, not confirmatory efficacy",
        "seed": 27104, "side": 24, "fresh_load_seed": 28104, "expires_at": now + 120,
        "deadline_at": now + 100, "expected_first_exit": 23, "expected_second_exit": 0}
    write(directory / "probe-config.json", config)
    calls = []
    environment = {k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "WINDIR", "TMPDIR"}}
    environment.update({"OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    campaign_cpu, campaign_wall = cpu_children_ms(), time.perf_counter_ns()
    for role, expected in (("first", 23), ("second", 0)):
        start_cpu, start_wall = cpu_children_ms(), time.perf_counter_ns()
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker", role,
            "--out", str(directory), "--source-hash", source_hash], capture_output=True,
            env=environment, cwd=ROOT, timeout=60, check=False)
        (directory / (role + ".stdout")).write_bytes(process.stdout)
        (directory / (role + ".stderr")).write_bytes(process.stderr)
        record = {"role": role, "expected_exit": expected, "actual_exit": process.returncode,
            "children_cpu_ms": cpu_children_ms() - start_cpu, "wall_ms": (time.perf_counter_ns() - start_wall) / 1e6,
            "stdout_bytes": len(process.stdout), "stderr_bytes": len(process.stderr)}
        calls.append(record)
        write(directory / "process-calls.json", calls)
        if process.returncode != expected:
            write(directory / "OPERATIONAL_FAILURE.json", {"role": role, "record": record, "no_retry": True})
            raise RuntimeError("OPERATIONAL_WORKER_FAILED:" + role)
    a, b = (json.loads((directory / (mid + "-worker.json")).read_text()) for mid in ("A", "B"))
    duplicate = json.loads((directory / "duplicate-recovery.json").read_text())
    executions = [json.loads(line) for line in (directory / "execution-events.jsonl").read_text().splitlines()]
    checks = {"different_os_processes": a["pid"] != b["pid"], "first_acknowledgement_lost": calls[0]["stdout_bytes"] == 0,
        "historical_receipt_unchanged": duplicate["same_terminal"], "duplicate_never_reexecuted": not duplicate["execute"],
        "exactly_one_A_one_fresh_B": [x["mission"] for x in executions] == ["A", "B"],
        "portable_parent_used_on_fresh_work": not b["details"]["factor_native"] and b["details"]["parent_calls"] == 1,
        "parent_identity_preserved": a["details"]["factor_identity"] == b["details"]["factor_identity"],
        "fresh_B_independent_check_passed": b["details"]["checker"]["valid"],
        "no_proof_authority_inherited": b["inspection"]["activeProof"] == [] and b["inspection"]["activeAuthority"] == [],
        "new_load_not_previous_answer": a["details"]["solution_digest"] != b["details"]["solution_digest"]}
    report = {**config, "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks,
        "processes": calls, "pids": [a["pid"], b["pid"]], "actual_execution_events": executions,
        "total_children_cpu_ms": cpu_children_ms() - campaign_cpu,
        "total_wall_ms": (time.perf_counter_ns() - campaign_wall) / 1e6,
        "factor_identity": a["details"]["factor_identity"], "historical_receipt_digest": duplicate["receipt_digest"],
        "probe_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "source_identity_status": "DEVELOPMENT_UNFROZEN" if source_hash == "0" * 64 else "DECLARED_ENCLOSING_FREEZE_REQUIRES_MANIFEST_VERIFICATION",
        "limitations": ["Intentional first exit23 occurs after durable commit and clean Node close, before supervisor acknowledgement.",
            "This probes lost acknowledgement across actual OS processes, not every possible crash window.",
            "Pending-commit quarantine and corrupted/stale authority tests are separately source-bound component evidence.",
            "RUSAGE_CHILDREN includes both worker processes and their reaped Node children; do not add action CPU again.",
            "Reusing portable factors may be slower than the original native object; this probe makes no efficacy claim.",
            "No maintained native daemon, credentials, hosted executor or operational authority is created."]}
    write(directory / "PROCESS_RECOVERY.json", report)
    print(json.dumps({"status": report["status"], "pids": report["pids"], "checks": checks,
                      "total_children_cpu_ms": report["total_children_cpu_ms"], "record": str(directory / "PROCESS_RECOVERY.json")}))
    if report["status"] != "PASS":
        raise RuntimeError("RECOVERY_ASSERTION_FAILED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-hash", required=True)
    parser.add_argument("--worker", choices=("first", "second"))
    args = parser.parse_args()
    if len(args.source_hash) != 64 or any(c not in "0123456789abcdef" for c in args.source_hash):
        parser.error("source hash must have 64 lowercase hex digits")
    directory = Path(args.out).resolve()
    if args.worker:
        worker(args.worker, directory, args.source_hash)
    else:
        supervise(directory, args.source_hash)


if __name__ == "__main__":
    main()
