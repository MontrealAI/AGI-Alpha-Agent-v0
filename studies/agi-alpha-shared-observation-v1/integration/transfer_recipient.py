# SPDX-License-Identifier: Apache-2.0
"""Transfer exact retained bytes and execute a fresh synthetic mission in another process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from bridge import ROOT, verify_sources
from bundle import make_bundle, regular_bytes, sha256, unpack_bundle
from run_integration import run as run_conformance


def verify_custody() -> dict[str, Any]:
    """Check both the original vendor manifest and unchanged adapter source bytes."""
    verify_sources()
    record = json.loads((ROOT / "custody.json").read_text())
    for row in record["copied_files"]:
        data = regular_bytes(ROOT / row["local_path"])
        if len(data) != row["bytes"] or sha256(data) != row["sha256"]:
            raise ValueError("predecessor integration drift: " + row["local_path"])
    return record


def run(
    compiler: Path,
    profile: Path,
    mission: Path,
    output: Path,
    prepared: Path | None = None,
    checker: Path | None = None,
) -> dict[str, Any]:
    """Keep scientific checking, local execution and fixture access separately visible."""
    if output.exists():
        raise ValueError("new transfer evidence directory required")
    custody = verify_custody()
    mission_bytes = regular_bytes(mission)
    request = json.loads(mission_bytes)
    if request.get("schema") != "shared-observation-mission/v1" or request.get("evidence_type") != "synthetic":
        raise ValueError("only the declared synthetic research mission is supported")
    output.mkdir(parents=True, exist_ok=False)
    artifact = output / "retained-capability.zip"
    packaged = make_bundle(compiler, profile, artifact)
    if prepared is None:
        conformance_directory = output / "conformance"
        conformance = run_conformance(artifact, conformance_directory)
    else:
        conformance_directory = prepared
        conformance = json.loads(regular_bytes(prepared / "summary.json"))
        if conformance.get("artifact_sha256") != packaged["sha256"]:
            raise ValueError("prepared conformance belongs to a different retained bundle")
        if conformance.get("passed") != conformance.get("total"):
            raise ValueError("prepared fixture conformance is incomplete")
    received = conformance_directory / "received-v2.zip"
    received_bytes = regular_bytes(received)
    if sha256(received_bytes) != packaged["sha256"]:
        raise ValueError("network retrieval did not return the exact retained bundle")
    recipient = output / "recipient"
    unpacked = recipient / "capability"
    manifest = unpack_bundle(received, packaged["sha256"], unpacked)
    compiler_bytes = regular_bytes(compiler)
    if regular_bytes(unpacked / "compiler.py") != compiler_bytes:
        raise ValueError("recipient compiler differs from originating retained source")
    recipient_mission = recipient / "mission.json"
    recipient_mission.write_bytes(mission_bytes)
    result_path = recipient / "result.json"
    command = [
        sys.executable,
        "-I",
        str((unpacked / "compiler.py").resolve()),
        "--mission",
        str(recipient_mission.resolve()),
        "--output",
        str(result_path.resolve()),
        "--profile",
        str((unpacked / "sensor_profile.json").resolve()),
    ]
    start = time.perf_counter_ns()
    process = subprocess.Popen(command, cwd=recipient, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    timeout = False
    try:
        stdout, stderr = process.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        timeout = True
        process.kill()
        stdout, stderr = process.communicate()
    elapsed = time.perf_counter_ns() - start
    (recipient / "stdout.txt").write_bytes(stdout)
    (recipient / "stderr.txt").write_bytes(stderr)
    result: dict[str, Any] | None = None
    output_error = None
    if result_path.exists():
        try:
            result = json.loads(regular_bytes(result_path))
        except (ValueError, OSError) as exc:
            output_error = str(exc)
    checked_result = result or {}
    ordinary = output / "ordinary-library"
    ordinary.mkdir()
    (ordinary / "compiler.py").write_bytes(compiler_bytes)
    (ordinary / "sensor_profile.json").write_bytes(regular_bytes(profile))
    ordinary_result_path = ordinary / "result.json"
    ordinary_command = [
        sys.executable,
        "-I",
        str((ordinary / "compiler.py").resolve()),
        "--mission",
        str(recipient_mission.resolve()),
        "--output",
        str(ordinary_result_path.resolve()),
        "--profile",
        str((ordinary / "sensor_profile.json").resolve()),
    ]
    ordinary_process = subprocess.run(ordinary_command, cwd=ordinary, capture_output=True, timeout=30)
    (ordinary / "stdout.txt").write_bytes(ordinary_process.stdout)
    (ordinary / "stderr.txt").write_bytes(ordinary_process.stderr)
    ordinary_result = json.loads(regular_bytes(ordinary_result_path)) if ordinary_result_path.exists() else None
    independent_check = None
    checker_returncode = None
    checker_sha256 = None
    if checker is not None and result is not None:
        checker_sha256 = sha256(regular_bytes(checker))
        check_path = recipient / "independent-check.json"
        check_process = subprocess.run(
            [
                sys.executable,
                "-I",
                str(checker.resolve()),
                "--mission",
                str(recipient_mission.resolve()),
                "--candidate",
                str(result_path.resolve()),
                "--output",
                str(check_path.resolve()),
            ],
            cwd=recipient,
            capture_output=True,
            timeout=30,
        )
        checker_returncode = check_process.returncode
        (recipient / "checker.stdout.txt").write_bytes(check_process.stdout)
        (recipient / "checker.stderr.txt").write_bytes(check_process.stderr)
        independent_check = json.loads(regular_bytes(check_path)) if check_path.exists() else None
    checks = [
        {"name": "unchanged-predecessor-integration", "passed": True},
        {"name": "fixture-lifecycle-controls", "passed": conformance["passed"] == conformance["total"]},
        {"name": "identical-transferred-bundle", "passed": sha256(received_bytes) == packaged["sha256"]},
        {"name": "identical-transferred-compiler", "passed": regular_bytes(unpacked / "compiler.py") == compiler_bytes},
        {"name": "separate-recipient-process", "passed": process.pid != os.getpid()},
        {"name": "recipient-process-completed", "passed": process.returncode == 0 and not timeout},
        {"name": "result-schema", "passed": checked_result.get("schema") == "shared-observation-result/v1"},
        {"name": "fresh-input-binding", "passed": checked_result.get("input_sha256") == sha256(mission_bytes)},
        {"name": "mission-identity-binding", "passed": checked_result.get("mission_id") == request["mission_id"]},
        {"name": "execution-authority-remains-false", "passed": checked_result.get("execution_authorized") is False},
        {"name": "ordinary-library-process-completed", "passed": ordinary_process.returncode == 0},
        {"name": "identical-content-ordinary-library-parity", "passed": result is not None and ordinary_result == result},
    ]
    if checker is not None:
        check_record = independent_check or {}
        checks.append(
            {
                "name": "fresh-independent-semantic-check",
                "passed": checker_returncode == 0
                and check_record.get("conforms_to_independent_reference") is True
                and check_record.get("input_sha256") == sha256(mission_bytes),
            }
        )
    record = {
        "schema": "shared-observation-recipient-transfer/v1",
        "evidence_type": "ACTUAL_LOCAL_COMPUTATION_ON_SYNTHETIC_MISSION_WITH_FIXTURE_IDENTITY",
        "artifact": packaged,
        "recipient_manifest": manifest,
        "predecessor_source_commit": custody["source_commit"],
        "source_files_verified": len(custody["copied_files"]),
        "compiler_sha256": sha256(compiler_bytes),
        "profile_sha256": sha256(regular_bytes(profile)),
        "mission_id": request["mission_id"],
        "mission_input_sha256": sha256(mission_bytes),
        "source_mission_path": str(mission),
        "received_bundle_sha256": sha256(received_bytes),
        "conformance_directory": str(conformance_directory),
        "conformance_reused": prepared is not None,
        "conformance_summary_sha256": sha256(regular_bytes(conformance_directory / "summary.json")),
        "recipient_command": command,
        "recipient_pid": process.pid,
        "controller_pid": os.getpid(),
        "elapsed_ns": elapsed,
        "exit_code": process.returncode,
        "timed_out": timeout,
        "output_error": output_error,
        "checks": checks,
        "passed": sum(row["passed"] for row in checks),
        "total": len(checks),
        "recipient_result": result,
        "ordinary_library_result": ordinary_result,
        "ordinary_library_command": ordinary_command,
        "ordinary_library_exit_code": ordinary_process.returncode,
        "ordinary_library_same_rights_and_inputs": True,
        "graph_specific_advantage": "None observed with identical contents and research execution permissions.",
        "checker_sha256": checker_sha256,
        "independent_check": independent_check,
        "semantic_acceptance": "RECORDED_SEPARATELY" if checker is not None else "SEPARATE_INDEPENDENT_CHECK_REQUIRED",
        "buyer_acceptance": "NOT_OBSERVED",
        "execution_authorized": False,
        "authority_boundary": "Authorized local research execution does not grant live sensor or spacecraft authority.",
        "live_ens_authentications": 0,
        "actual_customer_collections_usd": 0,
        "empirical_alpha_admission": False,
        "production_admission": False,
        "fixture_admission": "Artificial monetary controls exercise existing lifecycle only.",
        "copy_boundary": "Revocation blocks future mediated access; it does not erase bytes already retrieved.",
    }
    (output / "summary.json").write_text(json.dumps(record, indent=2, allow_nan=False) + "\n")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiler", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--mission", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--checker", type=Path)
    args = parser.parse_args()
    summary = run(args.compiler, args.profile, args.mission, args.out, args.prepared, args.checker)
    print(json.dumps({key: summary[key] for key in ("passed", "total", "compiler_sha256", "mission_id")}))
    raise SystemExit(0 if summary["passed"] == summary["total"] else 1)
