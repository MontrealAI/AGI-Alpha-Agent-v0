# SPDX-License-Identifier: Apache-2.0
"""Execute received audit code under a separately configured local research grant."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from binding import (
    bind_request,
    check_grant,
    digest,
    file_sha,
    load_json,
    native_trust,
    save,
    verify_installed_bundle,
)


def consume_authority(journal_path: Path, signed: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    """Record one-use grants in the existing signed native Journal, not a new registry."""
    native_trust()
    from alpha_factory_v1.core.runtime.store import Journal

    journal = Journal(journal_path)
    journal.verify()
    name = "@v4-research-grant:" + digest(payload["nonce"])
    with journal.transaction() as connection:
        try:
            journal.latest(name, connection)
        except KeyError:
            journal.append(connection, name, {"signed_grant": signed, "state": "consumed-before-computation"})
        else:
            raise ValueError("local research grant already consumed")
    return journal.verify()


def run(
    bundle_root: Path,
    expected_manifest: Path,
    identity_path: Path,
    request_path: Path,
    grant_path: Path,
    context_path: Path,
    journal_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    """Recheck identity, current sources and current authority before separate CLI execution."""
    started = time.perf_counter()
    if report_path.exists():
        raise ValueError("refusing to overwrite a prior recipient report")
    manifest = load_json(expected_manifest)
    inventory = verify_installed_bundle(bundle_root, manifest)
    identity = load_json(identity_path)
    if identity["artifact"]["manifest_sha256"] != digest(manifest) or identity["scope"] != manifest["scope"]:
        raise ValueError("qualification artifact or scope identity changed")
    if identity["source"] != manifest["closure"]["files"] or identity["dependencies"] != inventory["identity"]:
        raise ValueError("qualification identity does not bind current received runtime")
    if identity["schema"] != manifest["closure"]["schema_identity"]:
        raise ValueError("qualification schema identity changed")
    if identity["policy"]["instrument_policy"] != manifest["closure"]["policy_identity"]:
        raise ValueError("qualification policy identity changed")
    before = bind_request(request_path)
    signed, context = load_json(grant_path), load_json(context_path)
    authority = check_grant(signed, context, identity, before, int(time.time()))
    journal_before = consume_authority(journal_path, signed, authority)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    environment = {
        "PATH": os.defpath,
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONPATH": str(bundle_root),
        "LANG": "C.UTF-8",
    }
    command = [
        sys.executable,
        "-B",
        str(bundle_root / manifest["closure"]["entrypoint"]),
        "--request",
        str(request_path),
        "--output",
        str(report_path),
    ]
    call_started = time.perf_counter()
    process = subprocess.run(
        command, cwd=bundle_root, env=environment, capture_output=True, text=True, timeout=120, check=False
    )
    call_seconds = time.perf_counter() - call_started
    after = bind_request(request_path)
    if before != after:
        raise ValueError("mission sources or semantics changed during recipient execution")
    for name, expected_sha in manifest["closure"]["files"].items():
        if file_sha(bundle_root / name) != expected_sha:
            raise ValueError("application source changed during execution")
    report_exists = report_path.is_file()
    report = load_json(report_path) if report_exists else None
    if report is not None and report.get("mission") != load_json(request_path)["mission"]:
        raise ValueError("received capability changed the requested mission")
    return {
        "schema": "inspection-evidence-recipient-execution/v1",
        "pid": os.getpid(),
        "separate_cli_process": True,
        "command": command,
        "request": before,
        "authority": authority,
        "journal_after_consumption": journal_before,
        "dependency_inventory_seconds": inventory["seconds"],
        "dependency_bytes_rehashed": inventory["hashed_bytes"],
        "cli_seconds": call_seconds,
        "total_seconds": time.perf_counter() - started,
        "returncode": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "report_sha256": file_sha(report_path) if report_exists else None,
        "report_bytes": report_path.stat().st_size if report_exists else 0,
        "mission_result": report.get("mission_result") if report is not None else None,
        "source_integrity_before_after": before == after,
        "independent_acceptance": None,
        "authority_scope": "computational audit only; no manufacturing, physical release or live ENS permission",
        "actual_model_calls_in_this_execution": 0,
        "model_tokens": None,
        "complete_cost_usd": None,
        "customer_collections_usd": 0,
        "isolation": "new local processes and explicit files; not a production sandbox or independent organization",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    for option in (
        "bundle-root",
        "manifest",
        "identity",
        "request",
        "grant",
        "context",
        "journal",
        "report",
        "receipt",
    ):
        parser.add_argument("--" + option, type=Path, required=True)
    arguments = parser.parse_args()
    try:
        result = run(
            arguments.bundle_root.resolve(),
            arguments.manifest.resolve(),
            arguments.identity.resolve(),
            arguments.request.resolve(),
            arguments.grant.resolve(),
            arguments.context.resolve(),
            arguments.journal.resolve(),
            arguments.report.resolve(),
        )
        save(arguments.receipt, result)
        print(json.dumps({key: result[key] for key in ("returncode", "report_sha256", "cli_seconds")}))
        raise SystemExit(0 if result["returncode"] == 0 else 2)
    except (ValueError, KeyError, OSError, ImportError, subprocess.SubprocessError) as error:
        result = {"schema": "inspection-evidence-recipient-refusal/v1", "refused": True, "reason": str(error)}
        save(arguments.receipt, result)
        print(json.dumps(result))
        raise SystemExit(2)
