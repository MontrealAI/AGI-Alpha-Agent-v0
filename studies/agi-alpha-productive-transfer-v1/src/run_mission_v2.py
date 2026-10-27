# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import argparse
import datetime as dt
import json
import resource
import time
from pathlib import Path

from intake import assess_extraction, canonical, core, digest, validate_raw


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--arm", choices=["A", "B", "C"], required=True)
    parser.add_argument("--proposal")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    raw = json.loads(Path(args.raw).read_text())
    start, wall, cpu = dt.datetime.now(dt.UTC).isoformat(), time.perf_counter_ns(), time.process_time_ns()
    validate_raw(raw)
    if args.arm == "C":
        from conventional_v2 import extract

        proposal = extract(raw)
    else:
        if not args.proposal:
            raise ValueError("A/B require their separately recorded prospective curator/model response")
        proposal = json.loads(Path(args.proposal).read_text())
    (out / "proposal.json").write_bytes(canonical(proposal))
    if args.arm == "A":
        if proposal.get("schema") != core.SCHEMA:
            raise ValueError("incumbent requires the actual prepared call request")
        if proposal.get("sources") != raw["sources"] or proposal.get("id") != raw["id"]:
            raise ValueError("incumbent input must retain exact captured source bodies and mission ID")
        record = core.assess(proposal)
        result = {
            "schema": "alpha-transfer-intake-result/v1",
            "inputSha256": digest(raw),
            "extractionSha256": digest(proposal),
            "request": proposal,
            "coreRecord": record,
            "unresolvedIntake": [],
            "nextAction": record["nextAction"],
            "scope": raw["consumer"],
            "completeScopeAccepted": None,
            "productionApproved": False,
            "actualCollectionsUsd": 0,
            "scopeAcceptance": "Independent fresh-scope audit required; curated calls do not prove complete intake.",
            "limits": record["limits"],
        }
    else:
        result = assess_extraction(raw, proposal)
    result["arm"] = args.arm
    result["resources"] = {
        "startedAt": start,
        "endedAt": dt.datetime.now(dt.UTC).isoformat(),
        "wallNs": time.perf_counter_ns() - wall,
        "cpuNs": time.process_time_ns() - cpu,
        "peakResidentKiB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "localRuntimeModelCalls": 0,
        "recordedCurrentSessionModelExtraction": args.arm in ["A", "B"],
        "inferenceMoneyUsd": None if args.arm in ["A", "B"] else 0,
        "completeDeliveryMoneyUsd": None,
        "customerMinutes": None,
        "scope": "Execution of stored prospective input plus exact checks. A/B model extraction occurs outside this process and is not included in timing.",
    }
    from delivery_v2 import write_package

    result["handoff"] = write_package(out, raw, result)
    result["experiment"] = "separately-registered-fresh-followup"
    result["resources"]["wallNs"] = time.perf_counter_ns() - wall
    result["resources"]["cpuNs"] = time.process_time_ns() - cpu
    (out / "result.json").write_bytes(canonical(result))
    if result["request"]:
        (out / "request.json").write_bytes(canonical(result["request"]))
    summary = {
        "id": raw["id"],
        "arm": args.arm,
        "inputSha256": digest(raw),
        "resultSha256": digest(result),
        "nextAction": result["nextAction"],
        "selectedCalls": len(result["request"]["calls"]) if result["request"] else 0,
        "unresolvedIntake": len(result["unresolvedIntake"]),
        "completeScopeAccepted": None,
        "selectedCoreAccepted": (
            result["coreRecord"]["engineeringAcceptance"] if result["coreRecord"] else None
        ),
        "resources": result["resources"],
    }
    (out / "receipt.json").write_bytes(canonical(summary))
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
