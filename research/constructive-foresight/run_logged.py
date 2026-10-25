# SPDX-License-Identifier: Apache-2.0
"""Record a bounded subprocess's start before execution and its actual resource use."""
from __future__ import annotations
import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        raise ValueError("A command is required")
    if args.record.exists():
        raise FileExistsError("Invocation records are immutable")
    files = {"numerics.py", "decision.py", "protocol.json", "decision_protocol.json", "data/manifest.json",
             "results/primitives.json", "results/forecast_freeze.json"}
    files.update(str(Path(value).resolve().relative_to(ROOT)) for value in command
                 if Path(value).is_file() and Path(value).resolve().is_relative_to(ROOT))
    hashes = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
              for name in sorted(files) if (ROOT / name).is_file()}
    args.record.parent.mkdir(parents=True, exist_ok=True)
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter()
    record = {"issued_utc": datetime.now(timezone.utc).isoformat(), "command": command,
              "hashes": hashes, "timeout_seconds": args.timeout, "state": "issued before child execution"}
    args.record.write_text(json.dumps(record, indent=2) + "\n")
    try:
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=args.timeout, check=False)
        record.update({"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
    except subprocess.TimeoutExpired as error:
        record.update({"returncode": 124, "timeout": True, "stdout": str(error.stdout), "stderr": str(error.stderr)})
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    record.update({"completed_utc": datetime.now(timezone.utc).isoformat(), "wall_seconds": time.perf_counter() - start,
                   "child_cpu_seconds": (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime),
                   "max_rss_kib": after.ru_maxrss, "state": "completed"})
    args.record.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps({k: record[k] for k in ("returncode", "wall_seconds", "child_cpu_seconds", "stdout", "stderr")}, indent=2))
    sys.exit(record["returncode"])


if __name__ == "__main__":
    main()
