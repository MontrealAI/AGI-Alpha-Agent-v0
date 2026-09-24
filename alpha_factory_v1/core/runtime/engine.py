# SPDX-License-Identifier: Apache-2.0
"""Connect the original seven roles to durable, reviewed mission execution."""

from __future__ import annotations

import threading
import time
from typing import Any

from .models import Allocation, Forecast, Mission, Research, Schedule, Coding
from .provider import synthesize, generate_code
from .store import Conflict, Journal, digest, public_error
from . import work


def verify_export(artifact: dict[str, Any], trusted_public_key: str) -> dict[str, Any]:
    """Verify a portable receipt against an independently trusted agent key."""
    import base64
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    if artifact.get("schema") != 1 or artifact.get("public_key") != trusted_public_key:
        raise ValueError("export schema or trusted identity mismatch")
    receipt = artifact["receipt"]
    body = receipt["body"]
    if digest(body) != receipt["hash"] or body["identity"] != f"urn:agialpha:ed25519:{trusted_public_key}":
        raise ValueError("export content or identity mismatch")
    Ed25519PublicKey.from_public_bytes(bytes.fromhex(trusted_public_key)).verify(
        base64.b64decode(receipt["signature"], validate=True), bytes.fromhex(receipt["hash"])
    )
    document = body["document"]
    if document["state"] != "completed" or document["review"]["result_hash"] != digest(document["result"]):
        raise ValueError("export is not an approved intact result")
    return {"valid": True, "identity": body["identity"], "mission": body["mission"], "hash": receipt["hash"]}


class Engine:
    """Execute bounded work with explicit policy and independently checked results."""

    def __init__(self, journal: Journal) -> None:
        self.journal = journal
        self.journal.verify()
        self.lock = threading.Lock()

    def _memory(self, mission: Mission) -> dict[str, Any] | None:
        candidates = []
        for old in self.journal.missions():
            if old["state"] != "completed" or old["request"]["work"]["kind"] != mission.work.kind:
                continue
            if isinstance(mission.work, (Allocation, Schedule)):
                key = "items" if isinstance(mission.work, Allocation) else "jobs"
                old_ids = sorted(item["id"] for item in old["request"]["work"][key])
                new_ids = sorted(item.id for item in getattr(mission.work, key))
                if old_ids != new_ids:
                    continue
                candidates.append(old)
        return max(candidates, key=lambda item: item["revision"]) if candidates else None

    def execute(self, ident: str) -> dict[str, Any]:
        """Run one mission and stop at operator review; failures remain visible."""
        if not self.lock.acquire(blocking=False):
            raise Conflict("an execution is already active in this process")
        try:
            self.journal.verify()
            cfg = self.journal.config.model_copy(deep=True)
            config_hash = digest(cfg.model_dump())
            initial = self.journal.latest(ident)
            mission = Mission.model_validate(initial["request"])
            record = self.journal.transition(
                ident,
                initial["revision"],
                {"queued"},
                "running",
                expected_config_hash=config_hash,
                fields={
                    "lease_expires_ns": time.time_ns() + 660 * 10**9,
                    "stages": [],
                    "error": None,
                    "execution_config_hash": config_hash,
                },
            )
            started = time.monotonic()
            last_check = 0.0

            def checkpoint(force: bool = False) -> None:
                nonlocal last_check
                now = time.monotonic()
                if now - started > 600:
                    raise TimeoutError("mission exceeded its 600 second wall-clock budget")
                if force or now - last_check >= 0.05:
                    control = self.journal.latest("@control")
                    if control["state"] != "ready":
                        raise Conflict("operator paused execution")
                    if control["config_hash"] != config_hash:
                        raise Conflict("configuration changed during execution; restart and recover")
                    last_check = now

            def stage(role: str, detail: dict[str, Any]) -> None:
                nonlocal record
                checkpoint(True)
                stages = [*record["stages"], {"role": role, "detail": detail}]
                record = self.journal.transition(
                    ident,
                    record["revision"],
                    {"running"},
                    "running",
                    fields={"stages": stages},
                    expected_config_hash=config_hash,
                )

            result: dict[str, Any] | None = None
            try:
                stage(
                    "planning",
                    {
                        "goal": mission.goal,
                        "kind": mission.work.kind,
                        "input_hash": initial["request_hash"],
                        "config_hash": config_hash,
                        "evaluation_limit": cfg.max_evaluations,
                        "wall_seconds_limit": 600,
                    },
                )
                memory = self._memory(mission)
                stage(
                    "research",
                    {
                        "input_provenance": "operator-supplied",
                        "parent": memory["id"] if memory else None,
                        "parent_digest": memory["digest"] if memory else None,
                    },
                )
                inference = None
                if isinstance(mission.work, Research):
                    result = work.research(mission)
                    if cfg.llm_url:
                        checkpoint(True)
                        findings, inference = synthesize(mission, cfg)
                        result.update(findings)
                        result["method"] = "model synthesis with exact quotation verification"
                elif isinstance(mission.work, Allocation):
                    remembered = memory["result"]["selected"] if memory else None
                    result = work.allocation(mission, checkpoint, cfg.max_evaluations, remembered)
                elif isinstance(mission.work, Schedule):
                    remembered = memory["result"]["order"] if memory else None
                    result = work.schedule(mission, checkpoint, cfg.max_evaluations, remembered)
                elif isinstance(mission.work, Coding):
                    if not cfg.allow_code_execution:
                        raise ValueError("code execution requires explicit operator configuration")
                    code = mission.work.candidate
                    if not code:
                        checkpoint(True)
                        code, inference = generate_code(mission, cfg)
                    checkpoint(True)
                    result = work.coding(mission, code)
                elif isinstance(mission.work, Forecast):
                    result = work.forecast(mission)
                else:  # pragma: no cover - discriminated schema rejects unknown kinds
                    raise ValueError("unsupported mission kind")
                stage("strategy", {"method": result["method"], "inference": inference})
                stage(
                    "market",
                    {
                        "objective_improvement": result.get("improvement"),
                        "realized_revenue": None,
                        "unit": result.get("unit"),
                        "token_settlement": "not_recorded",
                    },
                )
                stage(
                    "codegen",
                    {
                        "artifact_type": "application/json",
                        "result_hash": digest(result),
                        "execution": (
                            "isolated Python benchmark"
                            if isinstance(mission.work, Coding)
                            else "built-in analytical tools; no model-generated code executed"
                        ),
                    },
                )
                verification = work.verify_result(mission, result)
                stage("safety", verification)
                stage("memory", {"archive": "signed mission journal", "learning_eligible_after_approval": True})
                return self.journal.transition(
                    ident,
                    record["revision"],
                    {"running"},
                    "review",
                    expected_config_hash=config_hash,
                    fields={
                        "result": result,
                        "verification": verification,
                        "inference": inference,
                        "elapsed_seconds": round(time.monotonic() - started, 6),
                    },
                )
            except Exception as exc:
                # Do not journal provider messages: they can include credentials,
                # source excerpts or upstream response bodies. CLI logs show type.
                current = self.journal.latest(ident)
                if current["state"] == "running":
                    self.journal.transition(
                        ident,
                        current["revision"],
                        {"running"},
                        "failed",
                        require_ready=False,
                        fields={
                            "error": type(exc).__name__,
                            "message": public_error(exc),
                            "failure_stage": len(current.get("stages", [])),
                            "failed_result": result,
                        },
                    )
                raise
        finally:
            self.lock.release()

    def review(self, ident: str, revision: int, result_hash: str, approve: bool, note: str) -> dict[str, Any]:
        """Approve exactly the artifact reviewed, or retain it as rejected."""
        self.journal.verify()
        config_hash = digest(self.journal.config.model_dump())
        current = self.journal.latest(ident)
        if self.journal.latest("@control")["state"] != "ready":
            raise Conflict("agent is paused")
        if current["state"] != "review" or current["revision"] != revision:
            raise Conflict("mission changed; fetch and review the current result")
        if result_hash != digest(current["result"]):
            raise Conflict("reviewed artifact hash does not match")
        if not note.strip() or len(note) > 2000:
            raise ValueError("review requires a note of 1–2000 characters")
        verification = work.verify_result(Mission.model_validate(current["request"]), current["result"])
        return self.journal.transition(
            ident,
            revision,
            {"review"},
            "completed" if approve else "rejected",
            expected_config_hash=config_hash,
            fields={
                "review": {
                    "approved": approve,
                    "note": note,
                    "result_hash": result_hash,
                    "verification": verification,
                    "actor": "operator",
                }
            },
        )

    def recover(self, ident: str) -> dict[str, Any]:
        """Requeue failed work or an expired worker lease without changing inputs."""
        self.journal.verify()
        record = self.journal.latest(ident)
        if record["state"] == "running" and time.time_ns() < record["lease_expires_ns"]:
            raise Conflict("worker lease is still active; pause it or wait for expiry")
        return self.journal.transition(
            ident, record["revision"], {"failed", "running"}, "queued", fields={"recovered_from": record["digest"]}
        )

    def export(self, ident: str) -> dict[str, Any]:
        """Return a portable result and signed journal receipt, without secrets."""
        self.journal.verify()
        record = self.journal.latest(ident)
        if record["state"] != "completed":
            raise Conflict("only approved, completed artifacts can be exported")
        with self.journal.transaction() as cx:
            row = cx.execute("SELECT body,hash,signature FROM events WHERE seq=?", (record["revision"],)).fetchone()
        import json

        return {
            "schema": 1,
            "public_key": self.journal.public,
            "receipt": {"body": json.loads(row[0]), "hash": row[1], "signature": row[2]},
        }
