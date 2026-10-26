# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import resource
import subprocess
import time
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    start = dt.datetime.now(dt.UTC).isoformat()
    wall, cpu = time.perf_counter_ns(), time.process_time_ns()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    timed_out = False
    try:
        run = subprocess.run(command, capture_output=True, timeout=args.timeout, check=False)
        code, stdout, stderr = run.returncode, run.stdout, run.stderr
    except subprocess.TimeoutExpired as exc:
        timed_out, code, stdout, stderr = True, 124, exc.stdout or b"", exc.stderr or b""
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record = {
        "schema": "agi-alpha-command-resource/v1",
        "phase": args.phase,
        "command": command,
        "startedAt": start,
        "endedAt": dt.datetime.now(dt.UTC).isoformat(),
        "wallNs": time.perf_counter_ns() - wall,
        "meterParentCpuNs": time.process_time_ns() - cpu,
        "childCpuSeconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime,
        "exitCode": code,
        "timedOut": timed_out,
        "stdoutSha256": hashlib.sha256(stdout).hexdigest(),
        "stderrSha256": hashlib.sha256(stderr).hexdigest(),
        "moneyUsd": None,
        "modelInferenceUsd": None,
        "humanMinutes": None,
        "scope": "Measured local command resources; model authoring, provider billing and attention remain unknown.",
    }
    (out / "stdout.txt").write_bytes(stdout)
    (out / "stderr.txt").write_bytes(stderr)
    (out / "receipt.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
