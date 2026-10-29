# SPDX-License-Identifier: Apache-2.0
"""Separate read-only judge for exposed dynamic software qualification cases."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
from pathlib import Path
from typing import Any


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def expected_outputs(case: dict[str, Any]) -> list[dict[str, str]]:
    allowed = {
        "voltage": frozenset(("V", "kV")),
        "apparent_power": frozenset(("VA", "kVA", "MVA")),
        "frequency": frozenset(("Hz",)),
    }
    if not case["requirements"] or set(case["requirements"].values()) - set(allowed):
        raise ValueError("oracle requirement dimensions")
    output = []
    seen = set()
    for record in case["records"]:
        if record["id"] in seen:
            raise ValueError("duplicate record")
        seen.add(record["id"])
        consistent = all(
            isinstance(record["fields"].get(field), dict) and record["fields"][field].get("unit") in allowed[dimension]
            for field, dimension in case["requirements"].items()
        )
        output.append({"id": record["id"], "status": "CONSISTENT" if consistent else "ABSTAIN"})
    if not output or len(output) > 64:
        raise ValueError("oracle cohort bound")
    return output


def judge(case: dict[str, Any], result: dict[str, Any], image: str) -> dict[str, Any]:
    if result.get("executed") is not True or result.get("status") != "EXECUTED_UNVERIFIED":
        return {"verdict": "REJECTED", "reason": "actual native execution is required"}
    if result.get("image") != image:
        return {"verdict": "REJECTED", "reason": "execution image differs from freeze"}
    artifact = result.get("artifact")
    if not isinstance(artifact, dict) or set(artifact) != {"outputs", "trace", "operations"}:
        return {"verdict": "REJECTED", "reason": "actual output contract"}
    if artifact["outputs"] != expected_outputs(case):
        return {"verdict": "REJECTED", "reason": "actual record consequences differ from separate oracle"}
    operations = artifact["operations"]
    trace = artifact["trace"]
    if type(operations) is not int or not isinstance(trace, list) or not 1 <= operations == len(trace) <= 16384:
        return {"verdict": "REJECTED", "reason": "operation and trace bounds"}
    record_ids = {record["id"] for record in case["records"]}
    if any(
        not isinstance(event, dict)
        or set(event) != {"record", "op"}
        or event["record"] not in record_ids
        or event["op"] not in {"observe", "sequence", "if", "emit"}
        for event in trace
    ):
        return {"verdict": "REJECTED", "reason": "trace identity or operator"}
    if {event["record"] for event in trace} != record_ids:
        return {"verdict": "REJECTED", "reason": "record omitted from actual trace"}
    return {"verdict": "PASS", "records_checked": len(record_ids), "operations": operations}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--freeze", type=Path, required=True)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    from contrib.invention_automation.readonly import enforce

    boundary = enforce()
    denied = {}
    try:
        descriptor = os.open(args.candidate, os.O_WRONLY)
    except PermissionError:
        denied["candidate_write"] = True
    else:
        os.close(descriptor)
        raise RuntimeError("verifier can modify candidate")
    try:
        connection = socket.socket()
    except PermissionError:
        denied["socket"] = True
    else:
        connection.close()
        raise RuntimeError("verifier socket restriction absent")
    freeze = json.loads(args.freeze.read_text())
    for relative, identity in freeze["source_sha256"].items():
        if sha(args.root / relative) != identity:
            raise ValueError("frozen source drift: " + relative)
    if sha(args.case) != freeze["case_sha256"] or sha(args.candidate) not in freeze["candidate_sha256"].values():
        raise ValueError("unfrozen case or candidate")
    result = judge(json.loads(args.case.read_text()), json.loads(args.result.read_text()), freeze["image"])
    result.update({"boundary": boundary, "tested_denials": denied, "confirmation": False})
    print(json.dumps(result, sort_keys=True))
    return 0 if result["verdict"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
