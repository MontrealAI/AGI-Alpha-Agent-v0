#!/usr/bin/env python3
"""Bounded development challenger using the original task and schedule.

Reports candidate criticisms, not final proof. No checker or solver imports.
"""
from __future__ import annotations
import hashlib
import json


def challenge(task, result, limit=4):
    raw = json.dumps(dict(task=task, result=result), sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(raw).hexdigest()
    findings, operations = [], len(raw)
    jobs = {job["id"]: job for job in task["jobs"]}
    rows = {row["id"]: row for row in result["schedule"]}
    operations += len(jobs) + len(rows)
    def emit(kind, witness, consequence):
        if len(findings) < limit:
            findings.append(dict(schema="release-plan-challenge/v1",
                                 id=f"challenge-{len(findings)+1}", type=kind,
                                 evidence_digest=digest, witness=witness,
                                 consequence=consequence))
    for jid, job in jobs.items():
        operations += 1
        if jid not in rows:
            emit("missing_job", dict(job=jid), "The result omits required work.")
            continue
        row = rows[jid]
        operations += 2
        if row["end"] - row["start"] != job["duration"]:
            emit("duration", dict(job=jid), "The result budgets the wrong execution duration.")
        if jid in task.get("locked", {}) and row["start"] != task["locked"][jid]:
            emit("locked_start", dict(job=jid), "The repair changes work declared already fixed.")
        for d in job["deps"]:
            operations += 2
            if d in rows and rows[d]["end"] > row["start"]:
                emit("dependency", dict(job=jid, predecessor=d), "A dependent task begins before its prerequisite is complete.")
    for slot, available in enumerate(task["capacity"]):
        demand = 0
        operations += 1
        for jid, row in rows.items():
            operations += 2
            if jid in jobs and row["start"] <= slot < row["end"]:
                demand += jobs[jid]["crew"]
                operations += 1
        operations += 1
        if demand > available:
            emit("capacity", dict(slot=slot), "The promised work requires more crew than the actual calendar permits.")
    return dict(challenges=findings, counts=dict(reference_operations=operations, total=operations),
                scope="development_only", final_proof=False)
