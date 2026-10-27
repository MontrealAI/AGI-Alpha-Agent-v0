# SPDX-License-Identifier: Apache-2.0
"""Execute each frozen primary confirmation request once with a deadline."""

from __future__ import annotations

import datetime as dt
import gzip
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from checker_v0_1_1 import evaluate
from source_oracle import sha256

ROOT = Path(__file__).resolve().parent
STUDY = ROOT.parent


def main() -> None:
    """Preserve first-pass outcomes, including timeouts and rejected reports."""
    freeze_path = ROOT / "PROSPECTIVE_EVALUATOR_FREEZE.json"
    freeze = json.loads(freeze_path.read_text())
    for name, expected in freeze["files"].items():
        if sha256(ROOT / name) != expected:
            raise ValueError("evaluator/protected source drift: " + name)
    core_freeze = STUDY / "instrument_v0_1_1" / "freeze.json"
    if sha256(core_freeze) != freeze["instrument_freeze_sha256"]:
        raise ValueError("instrument freeze changed")
    core = json.loads(core_freeze.read_text())
    for name, expected in core["files"].items():
        if sha256(STUDY / name) != expected:
            raise ValueError("instrument source drift: " + name)
    jobs = json.loads((ROOT / "prospective-v1" / "FREEZE.json").read_text())["jobs"]
    output = ROOT / "prospective-v1" / "results" / "confirmation-v1"
    output.mkdir(parents=True, exist_ok=False)
    receipts: list[dict[str, Any]] = []
    for job in jobs:
        if job.get("reserved_for_recipient", False):
            continue
        request, oracle = ROOT / job["request"], ROOT / job["oracle"]
        report = output / (job["id"] + ".report.json")
        started = time.perf_counter()
        command = [
            sys.executable,
            str(STUDY / "instrument_v0_1_1" / "cli.py"),
            "--request",
            str(request),
            "--output",
            str(report),
        ]
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=60, check=False)
            execution: dict[str, Any] = {
                "returncode": process.returncode,
                "stdout": process.stdout,
                "stderr": process.stderr,
                "timeout": False,
            }
        except subprocess.TimeoutExpired as exc:
            execution = {"returncode": None, "stdout": str(exc.stdout), "stderr": str(exc.stderr), "timeout": True}
        execution["wall_seconds"] = time.perf_counter() - started
        execution["command"] = command
        execution["deadline_seconds"] = 60
        (output / (job["id"] + ".execution.json")).write_text(json.dumps(execution, indent=2) + "\n")
        if execution["returncode"] == 0 and report.exists():
            try:
                check = evaluate(request, report, oracle)
            except Exception as exc:
                check = {"accepted": False, "checker_error": type(exc).__name__ + ": " + str(exc)}
            raw = report.read_bytes()
            with gzip.open(report.with_suffix(".json.gz"), "wb") as stream:
                stream.write(raw)
            report_sha = sha256(report)
            candidate = json.loads(raw)
            report.unlink()  # Original bytes preserved losslessly in the gzip artifact.
        else:
            check = {"accepted": False, "execution_failure": True}
            candidate, report_sha = {}, None
        (output / (job["id"] + ".check.json")).write_text(json.dumps(check, indent=2) + "\n")
        row = {
            "job_id": job["id"],
            "purpose": job["purpose"],
            "accepted_audit": check["accepted"],
            "mission_result": candidate.get("mission_result"),
            "report_sha256": report_sha,
            "core_wall_seconds": execution["wall_seconds"],
            "checker_wall_seconds": check.get("elapsed_seconds"),
            "failed_checks": check.get("failed_checks_by_category", {}),
            "checker_error": check.get("checker_error"),
            "findings": len(candidate.get("findings", [])),
            "traces": len(candidate.get("traces", [])),
            "geometry_status": candidate.get("geometry", {}).get("status"),
            "family_proofs": [
                {
                    key: proof.get(key)
                    for key in [
                        "basis",
                        "status",
                        "all_source_intervals_subset",
                        "all_observed_values_satisfy_destination",
                        "family_cardinality_consistent",
                        "family_all_recorded_values_pass",
                    ]
                }
                for proof in candidate.get("family_proofs", [])
            ],
            "physical_reuse_admitted": candidate.get("mission_result", {}).get("physical_reuse_admitted", False),
        }
        receipts.append(row)
        print(
            json.dumps(
                {
                    "job_id": row["job_id"],
                    "accepted_audit": row["accepted_audit"],
                    "failed_checks": row["failed_checks"],
                    "checker_error": row["checker_error"],
                }
            ),
            flush=True,
        )
    summary = {
        "schema": "prospective-four-request-confirmation-v1",
        "completed_utc": dt.datetime.now(dt.UTC).isoformat(),
        "instrument_freeze_sha256": sha256(core_freeze),
        "evaluator_freeze_sha256": sha256(freeze_path),
        "executed_jobs": len(receipts),
        "accepted_audits": sum(r["accepted_audit"] for r in receipts),
        "candidate_subprocess_calls": len(receipts),
        "retries": 0,
        "rows": receipts,
        "reserved_recipient_job": None,
        "actual_complete_cost": None,
        "actual_tokens": None,
        "actual_collections": 0,
        "claim_scope": "four fresh requests on previously used sources; supplements immutable first pass; no physical/customer acceptance",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


if __name__ == "__main__":
    main()
