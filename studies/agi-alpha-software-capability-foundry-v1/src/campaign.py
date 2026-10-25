# SPDX-License-Identifier: Apache-2.0
"""Single prospective confirmation, independent oracles outside candidate workers."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
from constructor import ROOT
from measurement import measured, stamp, delta
from freeze import verify

def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def worker(request: dict) -> tuple[dict, dict]:
    def execute():
        try:
            run = subprocess.run([sys.executable, str(ROOT / "src/worker.py")], input=canonical(request),
                capture_output=True, timeout=30, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            if run.returncode:
                return {"status": "failed", "stderr": run.stderr.decode(errors="replace")[:2000]}
            return json.loads(run.stdout)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, OSError) as error:
            return {"status": "failed", "error": type(error).__name__, "message": str(error)[:500]}
    return measured(execute)

def run(cases_path: Path, destination: Path, order_seed: int) -> dict:
    freeze_before = verify(ROOT)
    if destination.exists():
        raise ValueError("Never overwrite or retry a confirmation boundary")
    destination.mkdir(parents=True)
    protocol = json.loads((ROOT / "protocol/protocol.json").read_text())
    cases_bytes = cases_path.read_bytes()
    cases_digest = hashlib.sha256(cases_bytes).hexdigest()
    cases = json.loads(cases_bytes)
    base = cases_path.parent
    protected = {"cases.json": cases_digest}
    for case in cases["cases"]:
        for key in ("oracle", "archive"):
            name = case[key]
            protected[name] = hashlib.sha256((base / name).read_bytes()).hexdigest()
    (destination / "TASKS_LOCK.json").write_text(json.dumps(protected, sort_keys=True, indent=2) + "\n")
    rng = random.Random(order_seed)
    tasks = [(case, arm) for case in cases["cases"] for arm in protocol["arms"]]
    rng.shuffle(tasks)
    outcomes, sequence = [], []
    for ordinal, (case, arm) in enumerate(tasks):
        instance_start = stamp()
        run_dir = destination / case["id"] / arm
        run_dir.mkdir(parents=True)
        request = {"arm": arm, "phase": "read", "work": str(run_dir.resolve()),
                   "repo": str((base / case["repository"]).resolve()), "commit": case["commit"],
                   "paths": case["paths"], "archive": str((base / case["archive"]).resolve()),
                   "repeats": protocol["confirmation_repeats"]}
        read, read_cost = worker(request)
        def verify_read():
            oracle = json.loads((base / case["oracle"]).read_text())
            accepted = read.get("status") == "completed" and len(read.get("records", [])) == protocol["confirmation_repeats"]
            accepted = accepted and all(row.get("files") == oracle["files"] for row in read.get("records", []))
            acceptance = {"passed": bool(accepted), "parent_sha256": read.get("source_sha256"),
                      "case": case["id"], "commit": case["commit"],
                      "checked_read_sha256": hashlib.sha256(canonical(read.get("records"))).hexdigest(),
                      "oracle_sha256": hashlib.sha256((base / case["oracle"]).read_bytes()).hexdigest()}
            return oracle, bool(accepted), acceptance
        (oracle, accepted, acceptance), read_verification_cost = measured(verify_read)
        (run_dir / "read.json").write_text(json.dumps(read, sort_keys=True, indent=2) + "\n")
        (run_dir / "acceptance.json").write_text(json.dumps(acceptance, sort_keys=True, indent=2) + "\n")
        if accepted:
            request.update(phase="child", acceptance=acceptance)
            child, child_cost = worker(request)
            def verify_child():
                passed = child.get("status") == "completed" and len(child.get("records", [])) == protocol["confirmation_repeats"]
                passed = passed and all(all(row["result"].get(k) == v for k,v in oracle["drift"].items())
                                        for row in child.get("records", []))
                trace_passed = True
                if arm in {"flywheel", "conventional", "equivalent", "reconstruction"}:
                    expected = {"selected_execution": True, "invocations": 1,
                        "parent_sha256": acceptance["parent_sha256"],
                        "acceptance_sha256": hashlib.sha256(canonical(acceptance)).hexdigest(),
                        "input_commit": case["commit"],
                        "input_paths_sha256": hashlib.sha256(json.dumps(sorted(case["paths"])).encode()).hexdigest(),
                        "output_inventory_sha256": hashlib.sha256(json.dumps({p:v["sha256"] for p,v in oracle["files"].items()},sort_keys=True).encode()).hexdigest()}
                    trace_passed = all(row["result"].get("parent_trace") == expected for row in child.get("records", []))
                return bool(passed), bool(trace_passed)
            (passed, trace_passed), child_verification_cost = measured(verify_child)
        else:
            child, child_cost, passed = {"status": "not-run", "reason": "parent refused"}, {}, False
            trace_passed, child_verification_cost = False, {}
        (run_dir / "child.json").write_text(json.dumps(child, sort_keys=True, indent=2) + "\n")
        source_use = [r["result"].get("parent_trace") for r in child.get("records", [])]
        accounted = read.get("costs", []) + child.get("costs", [])
        service = sum(r["wall_seconds"] for r in accounted if r["account"] == "service")
        improvement = sum(r["wall_seconds"] for r in accounted if r["account"] == "improvement")
        budgets = service <= protocol["budgets"]["service_seconds_per_arm_instance"] and improvement <= protocol["budgets"]["improvement_seconds_per_arm_instance"]
        instance_cost = delta(instance_start)
        instance_cost["total_cpu_seconds"] = instance_cost["parent_cpu_seconds"] + instance_cost["child_cpu_seconds"]
        outcome = {"case": case["id"], "arm": arm, "ordinal": ordinal, "read_passed": bool(accepted),
                   "child_passed": bool(passed), "trace_passed": trace_passed, "budget_passed": budgets, "read_outer": read_cost,
                   "child_outer": child_cost, "service_wall_seconds": service,
                   "read_verification": read_verification_cost, "child_verification": child_verification_cost,
                   "improvement_wall_seconds": improvement, "parent_traces": source_use,
                   "instance_cost": instance_cost,
                   "total_cpu_seconds": instance_cost["total_cpu_seconds"],
                   "wall_seconds": instance_cost["wall_seconds"]}
        outcomes.append(outcome)
        sequence.append({"ordinal": ordinal, "case": case["id"], "arm": arm})
        with (destination / "outcomes.jsonl").open("a") as stream:
            stream.write(json.dumps(outcome, sort_keys=True) + "\n")
        print(json.dumps({"completed": len(outcomes), "total": len(tasks), "case": case["id"], "arm": arm,
                          "passed": bool(accepted and passed and trace_passed and budgets)}), flush=True)
    if hashlib.sha256(cases_path.read_bytes()).hexdigest() != cases_digest:
        raise ValueError("Confirmation task manifest changed")
    for name, expected in protected.items():
        if hashlib.sha256((base / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Protected input/evaluator bytes changed: " + name)
    freeze_after = verify(ROOT)
    if freeze_after != freeze_before:
        raise ValueError("Freeze boundary changed during confirmation")
    summary = {"schema": "foundry-confirmation/v1", "order_seed": order_seed,
               "freeze_before": freeze_before, "freeze_after": freeze_after,
               "protected_inputs_unchanged": True, "protected_files": len(protected),
               "source_manifest_sha256": hashlib.sha256(cases_path.read_bytes()).hexdigest(),
               "protocol_sha256": hashlib.sha256((ROOT / "protocol/protocol.json").read_bytes()).hexdigest(),
               "outcomes": outcomes, "sequence": sequence}
    (destination / "campaign.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--order-seed", type=int, default=812953)
    options = parser.parse_args()
    run(options.cases, options.destination, options.order_seed)
