# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import hashlib
import json
import resource
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit("Campaign output exists")
    freeze_path = ROOT / "protocol/production-freeze.json"
    freeze = json.loads(freeze_path.read_text())
    for item in freeze["files"]:
        if hashlib.sha256((ROOT.parents[1] / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
            raise SystemExit("FROZEN_SOURCE_DRIFT:" + item["path"])
    jobs = sorted(args.inputs.rglob("job.json"))
    if len(jobs) != 30:
        raise SystemExit("Expected 24 primary and 6 separate stress jobs")
    args.out.mkdir(parents=True)
    records = []
    for i, jobpath in enumerate(jobs):
        job = json.loads(jobpath.read_text())
        source_path = jobpath.parent / job["source"]["file"]
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest()
        for generation in [(i + j) % 3 for j in range(3)]:
            for item in freeze["files"]:
                if hashlib.sha256((ROOT.parents[1] / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                    raise SystemExit("FROZEN_SOURCE_DRIFT:" + item["path"])
            output = args.out / job["id"] / ("G" + str(generation))
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            start = time.perf_counter()
            try:
                proc = subprocess.run([sys.executable, str(ROOT / "src/deliver.py"), "--job", str(jobpath),
                                       "--generation", str(generation), "--out", str(output)],
                                      capture_output=True, text=True, timeout=90, check=False)
                stdout, stderr, exit_code = proc.stdout, proc.stderr, proc.returncode
            except subprocess.TimeoutExpired as exc:
                stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
                stderr += "\nCAMPAIGN_TIMEOUT; no retry\n"
                exit_code = 124
            elapsed = time.perf_counter() - start
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            output.mkdir(parents=True, exist_ok=True)
            (output / "process.stdout").write_text(stdout)
            (output / "process.stderr").write_text(stderr)
            summary_path = output / "summary.json"
            summary = json.loads(summary_path.read_text()) if summary_path.exists() else {"status": "FAILED"}
            record = {**summary, "job_id": job["id"], "generation": generation,
                      "output_dir": str(output.relative_to(ROOT)), "source_path": str(source_path.relative_to(ROOT)),
                      "source_sha256": source_hash, "declared_source_sha256": job["source"]["sha256"],
                      "process_exit_code": exit_code, "elapsed_seconds": elapsed,
                      "cpu_seconds": after.ru_utime + after.ru_stime - before.ru_utime - before.ru_stime}
            records.append(record)
            (args.out / "attempts-checkpoint.json").write_text(json.dumps(records, sort_keys=True, indent=2) + "\n")
            for item in freeze["files"]:
                if hashlib.sha256((ROOT.parents[1] / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                    raise SystemExit("FROZEN_SOURCE_DRIFT:" + item["path"])
    index = {"schema": "human-market-production/v1", "status": "PREDICTIONS_SEALED_BEFORE_ORACLE",
             "source_freeze_sha256": hashlib.sha256(freeze_path.read_bytes()).hexdigest(), "records": records}
    raw = json.dumps(index, sort_keys=True, indent=2) + "\n"
    (args.out / "index.json").write_text(raw)
    (args.out / "prediction-seal.json").write_text(json.dumps({"index_sha256": hashlib.sha256(raw.encode()).hexdigest(),
                                                              "records": len(records)}, indent=2) + "\n")
    print(json.dumps({"records": len(records), "index_sha256": hashlib.sha256(raw.encode()).hexdigest()}))


if __name__ == "__main__":
    main()
