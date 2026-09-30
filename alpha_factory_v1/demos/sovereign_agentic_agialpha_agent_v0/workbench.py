# SPDX-License-Identifier: Apache-2.0
"""Durable, review-gated enterprise workflow on the maintained signed mission runtime."""
from __future__ import annotations

import base64
from contextlib import closing
import itertools
import sqlite3
import threading
from typing import Any
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from alpha_factory_v1.core.runtime.engine import Engine, verify_export
from alpha_factory_v1.core.runtime.models import Allocation, Job, Mission, Opportunity, Research, Schedule
from alpha_factory_v1.core.runtime.store import Conflict, Journal, canonical, digest
from alpha_factory_v1.core.runtime import work

from .models import Mandate

STAGES = ("portfolio", "schedule", "brief")
MAX_WORKFLOWS = 100
SCOPE = "Local operator-reviewed planning; no ENS authentication, independent validator quorum or token settlement."


def workflow_key(ident: str) -> str:
    """Keep workflow control records separate from executable missions."""
    return "@sovereign:" + str(uuid.UUID(ident))


def mission_for(spec: Mandate, stage: str, results: dict[str, Any]) -> Mission:
    """Derive each immutable job from the mandate and approved predecessor output."""
    shared = {"seed": spec.seed, "population": 12, "generations": 8}
    if stage == "portfolio":
        return Mission(
            goal=f"{spec.goal} Select a feasible portfolio maximizing {spec.value_unit}.",
            work=Allocation(
                items=[Opportunity(id=p.id, cost=p.cost, value=p.value, risk=p.risk) for p in spec.projects],
                budget=spec.budget,
                max_risk=spec.max_risk,
                unit=spec.value_unit,
            ),
            **shared,
        )
    selected = results["portfolio"]["selected"]
    projects = [p for p in spec.projects if p.id in selected]
    if not projects:
        raise ValueError("A nonempty approved portfolio is required")
    if stage == "schedule":
        return Mission(
            goal=f"Schedule the approved portfolio for {spec.title}; minimize makespan then tardiness.",
            work=Schedule(
                jobs=[Job(id=p.id, operations=p.operations, due=p.due) for p in projects], unit=spec.time_unit
            ),
            **shared,
        )
    if stage != "brief":
        raise ValueError("Unknown workflow stage")
    schedule = results["schedule"]
    return Mission(
        goal=(
            f"{spec.goal} Prepare an evidence brief for approved projects {', '.join(selected)}. "
            f"The verified schedule spans {schedule['makespan']} {spec.time_unit}; "
            f"total tardiness is {schedule['tardiness']} {spec.time_unit}. "
            "Distinguish supplied assumptions from established facts."
        )[:2000],
        work=Research(sources=[p.evidence for p in projects]),
        **shared,
    )


def check_stage(mission: Mission, result: dict[str, Any]) -> dict[str, Any]:
    """Check actual arithmetic and constraints, including claimed allocation optimality."""
    checked = work.verify_result(mission, result)
    if isinstance(mission.work, Allocation):
        allocation = mission.work
        cost = risk = baseline_value = 0
        for item in sorted(allocation.items, key=lambda item: (-item.value / item.cost, item.id)):
            if cost + item.cost <= allocation.budget and risk + item.risk <= allocation.max_risk:
                cost += item.cost
                risk += item.risk
                baseline_value += item.value
        if any(type(result.get(key)) is not int for key in ("baseline_value", "improvement")):
            raise ValueError("Allocation comparison metrics must be integers")
        if result["baseline_value"] != baseline_value or result["improvement"] != result["value"] - baseline_value:
            raise ValueError("Allocation baseline or improvement does not reproduce")
        optimum = 0
        for bits in itertools.product((False, True), repeat=len(allocation.items)):
            chosen = [item for item, enabled in zip(allocation.items, bits) if enabled]
            if sum(p.cost for p in chosen) <= allocation.budget and sum(p.risk for p in chosen) <= allocation.max_risk:
                optimum = max(optimum, sum(p.value for p in chosen))
        if type(result.get("optimality_proven")) is not bool:
            raise ValueError("Allocation optimality flag must be boolean")
        if result.get("optimal_value") is not None and result["optimal_value"] != optimum:
            raise ValueError("Reported allocation optimum does not reproduce")
        if result.get("optimality_proven") and result["value"] != optimum:
            raise ValueError("Claimed allocation optimum does not match enumeration")
        checked.update({"independent_optimum": optimum, "optimality_gap": optimum - result["value"]})
    if isinstance(mission.work, Schedule):
        baseline = work.build_schedule(mission.work, list(range(len(mission.work.jobs))))
        ids = [job.id for job in mission.work.jobs]
        order = result.get("order")
        if not isinstance(order, list) or sorted(order) != sorted(ids):
            raise ValueError("Schedule order must be a permutation of approved projects")
        rebuilt = work.build_schedule(mission.work, [ids.index(ident) for ident in order])
        if any(rebuilt[key] != result[key] for key in ("operations", "makespan", "tardiness")):
            raise ValueError("Schedule order does not reproduce the reported operations")
        if (
            result.get("baseline_makespan") != baseline["makespan"]
            or result.get("improvement") != baseline["makespan"] - result["makespan"]
        ):
            raise ValueError("Schedule baseline or improvement does not reproduce")
        checked["input_order_makespan"] = baseline["makespan"]
    if isinstance(mission.work, Research) and result.get("sources") != work.research(mission)["sources"]:
        raise ValueError("Evidence source fingerprints do not match the approved corpus")
    return checked


class Workbench:
    """Run one bounded stage at a time; never convert a computation into an approval."""

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.engine = Engine(journal)
        self.lock = threading.Lock()

    def list(self) -> list[dict[str, Any]]:
        """Return verified workflow summaries, without loading private key material."""
        self.journal.verify()
        with closing(sqlite3.connect(self.journal.path)) as cx:
            keys = [r[0] for r in cx.execute("SELECT DISTINCT mission FROM events WHERE mission LIKE '@sovereign:%'")]
        return [self.snapshot(key.split(":", 1)[1], verify=False) for key in keys]

    def create(self, spec: Mandate, ident: str) -> dict[str, Any]:
        """Create idempotently; reject a request ID reused for different inputs."""
        key = workflow_key(ident)
        self.journal.verify()
        with self.journal.transaction() as cx:
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("Agent is paused")
            try:
                old = self.journal.latest(key, cx)
                if old["mandate_hash"] != digest(spec.model_dump()):
                    raise Conflict("Workflow ID already belongs to another mandate")
            except KeyError:
                count = cx.execute(
                    "SELECT COUNT(DISTINCT mission) FROM events WHERE mission LIKE '@sovereign:%'"
                ).fetchone()[0]
                if count >= MAX_WORKFLOWS:
                    raise ValueError("This bounded workspace holds 100 mandates; create a new workspace")
                self.journal.append(
                    cx,
                    key,
                    {
                        "state": "active",
                        "mandate": spec.model_dump(),
                        "mandate_hash": digest(spec.model_dump()),
                        "jobs": {},
                    },
                )
        return self.snapshot(ident)

    def snapshot(self, ident: str, *, verify: bool = True) -> dict[str, Any]:
        """Expose dependency state and the exact artifacts available for review."""
        if verify:
            self.journal.verify()
        record = self.journal.latest(workflow_key(ident))
        spec = Mandate.model_validate(record["mandate"])
        jobs = {}
        results: dict[str, Any] = {}
        next_stage = None
        state = "completed"
        for stage in STAGES:
            job_id = record["jobs"].get(stage)
            if job_id is None:
                next_stage, state = stage, "ready"
                break
            job = self.journal.latest(job_id)
            expected = mission_for(spec, stage, results)
            if digest(job["request"]) != digest(expected.model_dump()):
                raise ValueError("Stored mission differs from approved workflow dependencies")
            jobs[stage] = job
            if job["state"] != "completed":
                next_stage, state = stage, job["state"]
                break
            if not job.get("review", {}).get("approved") or job["review"]["result_hash"] != digest(job["result"]):
                raise ValueError("Completed stage lacks an intact approval")
            check_stage(expected, job["result"])
            results[stage] = job["result"]
        return {
            "id": str(uuid.UUID(ident)),
            "mandate": record["mandate"],
            "mandate_hash": record["mandate_hash"],
            "state": state,
            "next_stage": next_stage,
            "jobs": jobs,
            "identity": self.journal.public,
            "control": self.journal.latest("@control")["state"],
            "scope": SCOPE,
        }

    def advance(self, ident: str) -> dict[str, Any]:
        """Execute the next job once, then stop at review; recover submission crashes idempotently."""
        if not self.lock.acquire(blocking=False):
            raise Conflict("A Sovereign action is already running")
        try:
            snapshot = self.snapshot(ident)
            stage = snapshot["next_stage"]
            if stage is None or snapshot["state"] not in {"ready", "queued"}:
                raise Conflict("Review the current result, or explicitly recover failed work, before advancing")
            if snapshot["control"] != "ready":
                raise Conflict("Agent is paused")
            results = {name: job["result"] for name, job in snapshot["jobs"].items() if job["state"] == "completed"}
            mission = mission_for(Mandate.model_validate(snapshot["mandate"]), stage, results)
            job_id = str(uuid.uuid5(uuid.UUID(ident), stage))
            self.journal.submit(mission, job_id)
            key = workflow_key(ident)
            with self.journal.transaction() as cx:
                record = self.journal.latest(key, cx)
                if stage not in record["jobs"]:
                    self.journal.append(
                        cx, key, {**self.journal.document(record), "jobs": {**record["jobs"], stage: job_id}}
                    )
            self.engine.execute(job_id)
            return self.snapshot(ident)
        finally:
            self.lock.release()

    def review(self, ident: str, revision: int, result_hash: str, approve: bool, note: str) -> dict[str, Any]:
        """Approve/reject only the active stage, bound to its exact revision and result."""
        snapshot = self.snapshot(ident)
        if snapshot["state"] != "review":
            raise Conflict("No result is awaiting review")
        job = snapshot["jobs"][snapshot["next_stage"]]
        check_stage(Mission.model_validate(job["request"]), job["result"])
        self.engine.review(job["id"], revision, result_hash, approve, note)
        return self.snapshot(ident)

    def recover(self, ident: str) -> dict[str, Any]:
        """Use the maintained lease-aware recovery path; never discard a failed result."""
        snapshot = self.snapshot(ident)
        if snapshot["state"] not in {"failed", "running"}:
            raise Conflict("Only failed or expired work can be recovered")
        self.engine.recover(snapshot["jobs"][snapshot["next_stage"]]["id"])
        return self.snapshot(ident)

    def export(self, ident: str) -> dict[str, Any]:
        """Sign a complete dependency-bound packet only after all three explicit approvals."""
        snapshot = self.snapshot(ident)
        if snapshot["state"] != "completed":
            raise Conflict("Approve all three stages before exporting a completed packet")
        body = {
            "schema": "sovereign-packet-v1",
            "workflow_id": snapshot["id"],
            "mandate": snapshot["mandate"],
            "scope": SCOPE,
            "receipts": {stage: self.engine.export(snapshot["jobs"][stage]["id"]) for stage in STAGES},
        }
        hashed = digest(body)
        return {
            "body": body,
            "public_key": self.journal.public,
            "sha256": hashed,
            "signature": base64.b64encode(self.journal.key.sign(bytes.fromhex(hashed))).decode(),
        }


def verify_packet(packet: dict[str, Any], trusted_public_key: str) -> dict[str, Any]:
    """Verify signatures, all dependency-derived inputs and numeric constraints against a pinned key."""
    if set(packet) != {"body", "public_key", "sha256", "signature"} or packet["public_key"] != trusted_public_key:
        raise ValueError("Packet or independently trusted public key mismatch")
    body = packet["body"]
    if (
        set(body) != {"schema", "workflow_id", "mandate", "scope", "receipts"}
        or body["schema"] != "sovereign-packet-v1"
    ):
        raise ValueError("Unsupported Sovereign packet")
    if packet["sha256"] != digest(body) or body["scope"] != SCOPE or set(body["receipts"]) != set(STAGES):
        raise ValueError("Packet content mismatch")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_public_key)).verify(
        base64.b64decode(packet["signature"], validate=True), bytes.fromhex(packet["sha256"])
    )
    spec = Mandate.model_validate(body["mandate"])
    ident = uuid.UUID(body["workflow_id"])
    results: dict[str, Any] = {}
    checks = {}
    for stage in STAGES:
        receipt = body["receipts"][stage]
        verify_export(receipt, trusted_public_key)
        signed = receipt["receipt"]["body"]
        if signed["mission"] != str(uuid.uuid5(ident, stage)):
            raise ValueError("Receipt belongs to a different workflow stage")
        document = signed["document"]
        mission = mission_for(spec, stage, results)
        if canonical(document["request"]) != canonical(mission.model_dump()):
            raise ValueError("Receipt input does not derive from the approved predecessors")
        checks[stage] = check_stage(mission, document["result"])
        results[stage] = document["result"]
    return {
        "verified": True,
        "public_key": trusted_public_key,
        "workflow_id": str(ident),
        "checks": checks,
        "scope": SCOPE,
    }
