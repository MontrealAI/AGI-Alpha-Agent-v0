# SPDX-License-Identifier: Apache-2.0
"""Run the predeclared twenty-command native canary after verified publication."""

from __future__ import annotations

import argparse
import base64
import hashlib
import itertools
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_result(mission: dict, record: dict) -> dict:
    """Check original constraints using standard Python, independently of app verification."""
    work, result = mission["work"], record["result"]
    assert record["state"] == "review"
    assert record["request"]["goal"] == mission["goal"] and record["request"]["work"] == work
    assert all(
        record["request"][key] == mission[key] for key in ("seed", "population", "generations") if key in mission
    )
    assert record["verification"]["result_hash"] == sha(canonical(result))
    assert record.get("inference") is None
    if work["kind"] == "allocation":
        items = {x["id"]: x for x in work["items"]}
        selected = result["selected"]
        assert len(selected) == len(set(selected)) and set(selected) <= set(items)
        totals = {k: sum(items[i][k] for i in selected) for k in ("cost", "risk", "value")}
        assert totals["cost"] <= work["budget"] and totals["risk"] <= work["max_risk"]
        assert all(result[k] == value for k, value in totals.items())
        feasible = []
        for bits in itertools.product((0, 1), repeat=len(items)):
            subset = [i for bit, i in zip(bits, items) if bit]
            cost = sum(items[i]["cost"] for i in subset)
            risk = sum(items[i]["risk"] for i in subset)
            if cost <= work["budget"] and risk <= work["max_risk"]:
                feasible.append(sum(items[i]["value"] for i in subset))
        optimum = max(feasible)
        if result["optimality_proven"]:
            assert result["optimal_value"] == totals["value"] == optimum
        return {
            "family": "allocation",
            "valid": True,
            "totals": totals,
            "independent_optimal_value": optimum,
            "unit": work["unit"],
            "meaning": "Authored planning points, not monetary return",
        }
    assert work["kind"] == "schedule"
    jobs = {j["id"]: j for j in work["jobs"]}
    operations = result["operations"]
    expected = {(j["id"], i) for j in jobs.values() for i in range(len(j["operations"]))}
    by_id = {(op["job"], op["operation"]): op for op in operations}
    assert len(operations) == len(by_id) and set(by_id) == expected
    machines: dict[str, list] = {}
    tardiness = 0
    for job in jobs.values():
        previous = 0
        for i, spec in enumerate(job["operations"]):
            op = by_id[job["id"], i]
            assert op["machine"] == spec["machine"]
            assert op["start"] >= previous and op["end"] - op["start"] == spec["duration"]
            assert all(isinstance(op[k], int) and not isinstance(op[k], bool) for k in ("start", "end"))
            machines.setdefault(spec["machine"], []).append((op["start"], op["end"]))
            previous = op["end"]
        tardiness += max(0, previous - job["due"])
    for intervals in machines.values():
        intervals.sort()
        assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))
    assert result["makespan"] == max(op["end"] for op in operations)
    assert result["tardiness"] == tardiness
    assert len(result["order"]) == len(jobs) and set(result["order"]) == set(jobs)
    return {
        "family": "schedule",
        "valid": True,
        "makespan": result["makespan"],
        "tardiness": tardiness,
        "unit": work["unit"],
        "meaning": "Authored slots; no equipment actuated or global optimality assumed",
    }


def run(args: argparse.Namespace) -> None:
    proof = json.loads(args.publication_proof.read_bytes())
    assert proof["release_published"] is True and proof["version"] == "1.47.0"
    assert len(proof["source_commit"]) == 40 and len(proof["wheel_sha256"]) == 64
    assert args.confirm_released_execution
    source = args.source.resolve()
    freeze_bytes = (source / "FREEZE.json").read_bytes()
    freeze = json.loads(freeze_bytes)
    addendum = json.loads((source / "PRECONFIRMATION_ADDENDUM.json").read_bytes())
    assert addendum["schema"].endswith("/v2") and len(addendum["planned_child_processes"]) == 20
    assert addendum["original_freeze_sha256"] == sha(freeze_bytes)
    args.installed_python = args.installed_python.absolute()
    args.output = args.output.absolute()
    prefix = args.installed_python.parents[1]
    packages = list(prefix.glob("lib/python*/site-packages/alpha_factory_v1"))
    assert len(packages) == 1
    for path, expected in proof["runtime_sha256"].items():
        assert path.startswith("alpha_factory_v1/core/runtime/") and ".." not in Path(path).parts
        installed = packages[0].parent / path
        assert installed.is_file() and sha(installed.read_bytes()) == expected, path
    assert len(proof["runtime_sha256"]) == 75
    missions = {}
    for row in freeze["missions"]:
        data = (source / row["file"]).read_bytes()
        assert sha(data) == row["sha256"]
        missions[row["id"]] = json.loads(data)
    assert set(missions) == {"fresh-allocation", "fresh-schedule"}
    args.output.mkdir(exist_ok=False, parents=True)
    home = args.output / "private-home"
    low, normal = args.output / "initial-policy.json", args.output / "recovery-policy.json"
    low.write_text(json.dumps({"max_evaluations": 20}) + "\n")
    normal.write_text(json.dumps({"max_evaluations": 10000}) + "\n")
    records, acceptance = [], []
    started = time.monotonic()
    env = {k: v for k, v in os.environ.items() if k not in {"PYTHONPATH", "PYTHONHOME"}}
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    def call(label: str, *command: str, succeeds: bool = True) -> dict | list:
        assert len(records) < 20 and time.monotonic() - started < 120
        argv = [
            str(args.installed_python),
            "-I",
            "-m",
            "alpha_factory_v1.core.runtime.cli",
            "--home",
            str(home),
            *command,
        ]
        before = time.monotonic()
        record = {
            "sequence": len(records) + 1,
            "label": label,
            "argv": argv,
            "status": "started",
            "returncode": None,
            "wall_seconds": None,
            "stdout": "",
            "stderr": "",
        }
        records.append(record)

        def save_action() -> None:
            record["wall_seconds"] = time.monotonic() - before
            (args.output / "actions.json").write_text(json.dumps(records, indent=2) + "\n")

        save_action()
        try:
            result = subprocess.run(
                argv, cwd=args.output, env=env, capture_output=True, timeout=min(30, 120 - (before - started))
            )
        except subprocess.TimeoutExpired as error:

            def partial(value: bytes | str | None) -> str:
                return value.decode(errors="replace") if isinstance(value, bytes) else value or ""

            record.update(status="timeout", stdout=partial(error.stdout), stderr=partial(error.stderr))
            save_action()
            raise
        except OSError as error:
            record.update(status="spawn-failure", error_type=type(error).__name__)
            save_action()
            raise
        record.update(
            status="returned",
            returncode=result.returncode,
            stdout=result.stdout.decode(),
            stderr=result.stderr.decode(),
        )
        save_action()
        assert (result.returncode == 0) == succeeds, (label, result.returncode, record["stderr"])
        return json.loads(record["stdout"] if succeeds else record["stderr"])

    ident = call("initialize", "init", "--config", str(low))["identity"]
    public = ident.removeprefix("urn:agialpha:ed25519:")
    assert len(public) == 64
    allocation_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "agialpha:147:released-native:fresh-allocation"))
    schedule_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "agialpha:147:released-native:fresh-schedule"))
    failure = call(
        "bounded-budget-interruption",
        "run",
        str(source / "fresh-allocation.json"),
        "--request-id",
        allocation_id,
        succeeds=False,
    )
    assert failure == {"error": "ValueError", "message": "evaluation budget exhausted"}

    def mission_events(ident: str) -> list:
        with sqlite3.connect("file:" + str(home / "journal.sqlite3") + "?mode=ro", uri=True) as cx:
            return list(cx.execute("SELECT seq,hash FROM events WHERE mission=? ORDER BY seq", (ident,)))

    before_refusal = mission_events(allocation_id)
    call("pause", "pause")
    refusal = call("paused-execution-refusal", "execute", allocation_id, succeeds=False)
    assert refusal["error"] == "Conflict" and "paused" in refusal["message"]
    assert before_refusal == mission_events(allocation_id)
    call("configure-normal-budget", "configure", str(normal))
    call("resume", "resume")
    recovered = call("explicit-same-request-recovery", "recover", allocation_id)
    assert recovered["state"] == "queued" and recovered["id"] == allocation_id
    assert recovered["error"] == "ValueError" and recovered["recovered_from"]
    allocation = call("execute-unchanged-allocation", "execute", allocation_id)
    acceptance.append(check_result(missions["fresh-allocation"], allocation))
    accepted = call(
        "review-allocation",
        "review",
        allocation_id,
        "--revision",
        str(allocation["revision"]),
        "--result-hash",
        allocation["verification"]["result_hash"],
        "--approve",
        "--note",
        "Independent finite constraint checks passed; authored software canary, not buyer acceptance",
    )
    exports = [args.output / "allocation-export.json", args.output / "schedule-export.json"]
    call("export-allocation", "export", allocation_id, "--output", str(exports[0]))
    call("verify-allocation-export", "verify-export", str(exports[0]), "--public-key", public)
    duplicate = call(
        "idempotent-allocation", "run", str(source / "fresh-allocation.json"), "--request-id", allocation_id
    )
    assert duplicate["digest"] == accepted["digest"] and duplicate["revision"] == accepted["revision"]
    schedule = call("run-distinct-schedule", "run", str(source / "fresh-schedule.json"), "--request-id", schedule_id)
    acceptance.append(check_result(missions["fresh-schedule"], schedule))
    call(
        "review-schedule",
        "review",
        schedule_id,
        "--revision",
        str(schedule["revision"]),
        "--result-hash",
        schedule["verification"]["result_hash"],
        "--approve",
        "--note",
        "Independent original schedule checks passed; authored software canary, not buyer acceptance",
    )
    call("export-schedule", "export", schedule_id, "--output", str(exports[1]))
    call("verify-schedule-export", "verify-export", str(exports[1]), "--public-key", public)
    altered = json.loads(exports[0].read_bytes())
    altered["receipt"]["body"]["document"]["result"]["value"] += 1
    tampered = args.output / "altered-export.json"
    tampered.write_text(json.dumps(altered) + "\n")
    call("altered-export-refusal", "verify-export", str(tampered), "--public-key", public, succeeds=False)
    listing = call("persistent-mission-history", "list")
    assert {row["id"] for row in listing} == {allocation_id, schedule_id}
    assert all(row["state"] == "completed" for row in listing)
    verified = call("verify-complete-signed-journal", "verify")
    assert verified["valid"] is True and verified["identity"] == ident
    paused = call("pause-final", "pause")
    assert paused["state"] == "paused" and len(records) == 20
    with sqlite3.connect("file:" + str(home / "journal.sqlite3") + "?mode=ro", uri=True) as cx:
        events = [
            {"sequence": seq, "mission": mission, "body": json.loads(body), "hash": hashed, "signature": signature}
            for seq, mission, body, hashed, signature in cx.execute("SELECT * FROM events ORDER BY seq")
        ]
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    key, previous = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public)), "0" * 64
    for i, event in enumerate(events, 1):
        assert event["sequence"] == i and event["body"]["previous"] == previous
        assert sha(canonical(event["body"])) == event["hash"]
        key.verify(base64.b64decode(event["signature"]), bytes.fromhex(event["hash"]))
        previous = event["hash"]
    failed_events = [e for e in events if e["mission"] == allocation_id and e["body"]["document"]["state"] == "failed"]
    assert len(failed_events) == 1 and failed_events[0]["body"]["document"]["message"] == "evaluation budget exhausted"
    (args.output / "public-signed-history.json").write_text(json.dumps(events, indent=2) + "\n")
    elapsed = time.monotonic() - started
    assert elapsed <= 120
    report = {
        "schema": "released-native-canary-result/v1",
        "status": "passed",
        "publication": proof,
        "protocol_sha256": sha((source / "PRECONFIRMATION_ADDENDUM.json").read_bytes()),
        "mission_ids": [allocation_id, schedule_id],
        "acceptance": acceptance,
        "child_processes": len(records),
        "wall_seconds": elapsed,
        "model_calls": 0,
        "paid_api_usd": 0,
        "complete_actual_cost_usd": None,
        "cost_scope": "Attributable installation, execution/failure/recovery, verification and packaging remain unknown monetary A costs; no zero total, earned revenue or retained benefit inferred",
        "customer_acceptance": False,
        "customer_collections_usd": 0,
        "retention_admitted": False,
        "live_ens_authority": False,
        "frontier_handoff_tested": False,
        "interruption_scope": "Configured evaluation-budget interruption and paused refusal; no process-kill/network failure claim",
        "journal_events": len(events),
        "final_control": "paused",
        "public_key": public,
        "export_sha256": {p.name: sha(p.read_bytes()) for p in exports},
        "limitations": [
            "Two authored finite mission families; no buyer or generalized performance claim",
            "Protected CostLedger/frontier/ENS delivery needs separately provisioned current authority; no fixture grants it",
        ],
    }
    (args.output / "RESULT.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "child_processes", "wall_seconds", "mission_ids")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-python", type=Path, required=True)
    parser.add_argument("--publication-proof", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--confirm-released-execution", action="store_true")
    run(parser.parse_args())
