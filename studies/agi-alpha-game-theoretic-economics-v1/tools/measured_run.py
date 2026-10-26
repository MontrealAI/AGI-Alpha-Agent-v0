# SPDX-License-Identifier: Apache-2.0
"""Meter one declared local command and bind its inputs before execution."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import signal
import subprocess
import time


def identity(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--bind", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, action="append", default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.record.exists() or not 0 < args.timeout <= 60:
        raise ValueError("RECORD_EXISTS_OR_UNSUPPORTED_TIMEOUT")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("COMMAND_REQUIRED")
    args.record.parent.mkdir(parents=True, exist_ok=True)
    wall, cpu = time.perf_counter(), time.process_time()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    inputs = []
    receipt = {"schema": "alpha-measured-command/v1", "phase": args.phase,
               "started_at": started, "command": command, "input_identities_before": inputs,
               "platform": platform.platform(), "meter_python": platform.python_version(),
               "timeout_seconds": args.timeout, "timed_out": False, "command_started": False,
               "runtime_model_calls": None, "meter_model_calls": 0,
               "inference_cost_usd": None, "money_usd": None,
               "human_minutes": None, "customer_minutes": None}
    stdout_path = args.record.with_suffix(".stdout.txt")
    stderr_path = args.record.with_suffix(".stderr.txt")
    process = None
    try:
        inputs = [identity(path) for path in args.bind]
        receipt["input_identities_before"] = inputs
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            receipt["command_started"] = True
            try:
                receipt["exit_code"] = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                receipt["timed_out"] = True
                os.killpg(process.pid, signal.SIGKILL)
                receipt["exit_code"] = process.wait()
    except Exception as exc:
        receipt["launcher_error"] = f"{type(exc).__name__}: {exc}"
        receipt["exit_code"] = None
    finally:
        after = resource.getrusage(resource.RUSAGE_CHILDREN)
        receipt["input_identities_after"] = [identity(path) for path in args.bind if path.is_file()]
        receipt["inputs_unchanged"] = receipt["input_identities_after"] == inputs
        receipt["output_identities"] = [identity(path) for path in args.output if path.is_file()]
        receipt["missing_outputs"] = [str(path) for path in args.output if not path.is_file()]
        receipt["stdout"] = identity(stdout_path) if stdout_path.exists() else None
        receipt["stderr"] = identity(stderr_path) if stderr_path.exists() else None
        receipt["child_cpu_seconds"] = after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime
        receipt["child_peak_rss_kib"] = after.ru_maxrss
        receipt["meter_cpu_seconds"] = time.process_time() - cpu
        receipt["wall_seconds"] = time.perf_counter() - wall
        receipt["ended_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        receipt["complete_success"] = (receipt["exit_code"] == 0 and receipt["inputs_unchanged"]
                                       and not receipt["missing_outputs"])
        args.record.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"record": str(args.record), "success": receipt["complete_success"],
                      "wall_seconds": receipt["wall_seconds"],
                      "child_cpu_seconds": receipt["child_cpu_seconds"]}))
    if not receipt["complete_success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
