#!/usr/bin/env python3
"""Check development-only, evidence-bound challenges to release plans.

This reviewer uses the independent artifact checker, never the creator solver.
Critic statements do not become evidence merely because the critic made them.
"""
from __future__ import annotations
import hashlib
import json
import sys
from check import check


def evidence_digest(task, result):
    raw = json.dumps(dict(task=task, result=result), sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest(), len(raw)


def adjudicate(task, result, challenge, phase="development"):
    out = dict(schema="release-plan-adjudication/v1", decision="UNSUPPORTED",
               substantiated=False, regression_eligible=False, phase=phase,
               evidence_digest=None, reason="", witness_check=None,
               artifact_check=None, counts=dict(evidence_hash_bytes=0, witness_operations=0,
                                                independent_checker=0, total=0))
    def finish(reason, substantiated=None, witness=None):
        out["reason"] = reason
        out["witness_check"] = witness
        if substantiated is not None:
            out["decision"] = "SUBSTANTIATED" if substantiated else "REFUTED"
            out["substantiated"] = substantiated
            out["regression_eligible"] = substantiated and phase == "development"
        out["counts"]["total"] = sum(v for k, v in out["counts"].items() if k != "total")
        return out
    if phase != "development":
        return finish("This regression-admission path accepts development evidence only; protected confirmation is not exposed to discovery.")
    if not isinstance(challenge, dict) or challenge.get("schema") != "release-plan-challenge/v1":
        return finish("Unsupported challenge schema.")
    try:
        digest, size = evidence_digest(task, result)
    except (TypeError, ValueError):
        return finish("Evidence must contain finite JSON values.")
    out["evidence_digest"] = digest
    out["counts"]["evidence_hash_bytes"] = size
    out["counts"]["witness_operations"] += 1
    if challenge.get("evidence_digest") != digest:
        return finish("Challenge is not bound to the supplied original task and result.")
    verdict = check(dict(task=task, result=result))
    out["artifact_check"] = verdict
    out["counts"]["independent_checker"] = verdict["counts"]["total"]
    if verdict["lower_bound"] is None:
        return finish("Original task scope is malformed or infeasible; no candidate-quality criticism is adjudicated against it.")
    witness = challenge.get("witness")
    if not isinstance(witness, dict):
        return finish("A specific reproducible witness is required.")
    schedule = result.get("schedule") if isinstance(result, dict) else None
    if not isinstance(schedule, list):
        return finish("Result has no inspectable schedule.")
    rows = {}
    for row in schedule:
        out["counts"]["witness_operations"] += 1
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            rows.setdefault(row["id"], []).append(row)
    jobs = {job["id"]: job for job in task["jobs"]}
    out["counts"]["witness_operations"] += len(jobs)
    kind, jid = challenge.get("type"), witness.get("job")
    if kind == "capacity":
        slot = witness.get("slot")
        if type(slot) is not int or not 0 <= slot < len(task["capacity"]):
            return finish("Capacity witness must identify an existing integer calendar slot.")
        demand = 0
        for row in schedule:
            out["counts"]["witness_operations"] += 4
            if not isinstance(row, dict) or row.get("id") not in jobs or type(row.get("start")) is not int or type(row.get("end")) is not int:
                return finish("Capacity witness cannot be evaluated against malformed schedule rows.")
            if row["start"] <= slot < row["end"]:
                demand += jobs[row["id"]]["crew"]
                out["counts"]["witness_operations"] += 2
        capacity = task["capacity"][slot]
        out["counts"]["witness_operations"] += 1
        return finish("Original calendar and exact active intervals independently determine the claimed overload.",
                      demand > capacity, dict(slot=slot, required_crew=demand, permitted_crew=capacity))
    if kind == "missing_job":
        out["counts"]["witness_operations"] += 2
        return finish("Checked the declared job against the complete artifact.",
                      jid in jobs and len(rows.get(jid, [])) == 0,
                      dict(job=jid, declared=jid in jobs, assignments=len(rows.get(jid, []))))
    if kind in ("duration", "locked_start", "dependency"):
        if jid not in jobs or len(rows.get(jid, [])) != 1:
            return finish("Witness must identify one declared, uniquely assigned job.")
        row = rows[jid][0]
        if type(row.get("start")) is not int or type(row.get("end")) is not int:
            return finish("Witness assignment times are malformed.")
        out["counts"]["witness_operations"] += 4
        if kind == "duration":
            observed, expected = row["end"] - row["start"], jobs[jid]["duration"]
            return finish("Checked duration against the original job definition.", observed != expected,
                          dict(job=jid, observed_duration=observed, declared_duration=expected))
        if kind == "locked_start":
            if jid not in task.get("locked", {}):
                return finish("The alleged locked job is not locked by the original task.", False, dict(job=jid, locked=False))
            expected = task["locked"][jid]
            return finish("Checked the executed prefix against its exact retained start.", row["start"] != expected,
                          dict(job=jid, observed_start=row["start"], locked_start=expected))
        predecessor = witness.get("predecessor")
        if predecessor not in jobs[jid]["deps"] or len(rows.get(predecessor, [])) != 1:
            return finish("Witness predecessor must be a declared dependency with one assignment.")
        end = rows[predecessor][0].get("end")
        if type(end) is not int:
            return finish("Predecessor endpoint is malformed.")
        return finish("Checked the original dependency and exact endpoint ordering.", end > row["start"],
                      dict(job=jid, predecessor=predecessor, predecessor_end=end, successor_start=row["start"]))
    if kind == "bound_claim":
        field = witness.get("field")
        if field not in ("value", "critical", "load", "locked") or not isinstance(result.get("lower_bound"), dict):
            return finish("Bound witness requires an explicit registered-bound field.")
        claimed = result["lower_bound"].get(field)
        independently_derived = verdict["lower_bound"][field]
        out["counts"]["witness_operations"] += 2
        return finish("Checked the registered certificate component, not an arbitrary claim about all possible lower bounds.",
                      type(claimed) is not int or claimed != independently_derived,
                      dict(field=field, claimed=claimed, independently_derived=independently_derived))
    if kind == "bound_optimality_flag":
        makespan = result.get("makespan")
        flag = result.get("optimal_by_lower_bound")
        if type(makespan) is not int:
            return finish("Makespan is malformed.")
        expected = makespan == verdict["lower_bound"]["value"]
        out["counts"]["witness_operations"] += 2
        return finish("This flag certifies equality with the registered independent bound; a gap does not prove nonoptimality.",
                      type(flag) is not bool or flag != expected,
                      dict(claimed_flag=flag, expected_flag=expected))
    return finish("Unknown criticism type; unsupported assertions do not compel a revision.")


def main():
    for line in sys.stdin:
        obj = json.loads(line)
        result = adjudicate(obj["task"], obj["result"], obj["challenge"], obj.get("phase", "development"))
        print(json.dumps(result, separators=(",", ":"), allow_nan=False), flush=True)


if __name__ == "__main__":
    main()
