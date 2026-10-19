# SPDX-License-Identifier: Apache-2.0
"""Versioned structural methods, configured review and inert local reuse routing.

Signatures bind configured principals to explicit scope. Local role separation is
not independent organizational evidence, and selection grants no execution right.
"""

from __future__ import annotations

import copy
from typing import Any, Literal, cast

from pydantic import Field, model_validator

from ..store import Conflict, Journal
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest
from .transformation import validate_envelope
from .trust import SignedEnvelope, TrustRegistry

KEY = "@transformation-library:v1"
SCOPE: Literal["local-structural-only"] = "local-structural-only"
MAX_ENTRIES = 128


def portable_behavior_digest(envelope: dict[str, Any]) -> str:
    """Bind reviewed executable behavior separately from campaign and development inputs."""
    checked = validate_envelope(copy.deepcopy(envelope))
    return digest(
        "ti-library-behavior",
        {key: checked["bindings"][key] for key in ("engine_sha256", "operators", "instrument", "provider")},
    )


class ReuseCosts(StrictModel):
    """Declared comparable logical units, without currency or savings inference."""

    setup_units: int = Field(ge=0, le=1_000_000_000)
    per_use_units: int = Field(ge=0, le=1_000_000_000)
    scope: Literal["declared-logical-units"] = "declared-logical-units"


class ReuseConditions(StrictModel):
    """A narrow supported population and explicit prerequisites and failure tags."""

    method_id: Identifier
    version: int = Field(ge=1, le=MAX_ENTRIES)
    producer: Identifier
    supported_scope: list[Identifier] = Field(min_length=1, max_length=32)
    prerequisites: list[Identifier] = Field(max_length=32)
    failure_conditions: list[Identifier] = Field(min_length=1, max_length=32)
    retirement_triggers: list[Text] = Field(min_length=1, max_length=32)
    costs: ReuseCosts
    evidence_digests: list[Digest] = Field(min_length=1, max_length=32)
    evidence_scope: Literal["local-structural-only"] = SCOPE

    @model_validator(mode="after")
    def unique_conditions(self) -> ReuseConditions:
        for values in (self.supported_scope, self.prerequisites, self.failure_conditions, self.evidence_digests):
            if len(set(values)) != len(values):
                raise ValueError("reuse conditions cannot contain duplicate identities")
        return self


class RouterContext(StrictModel):
    """The caller supplies current trusted context; no import extends permissions."""

    publicOnly: Literal[True]
    task_scope: Identifier
    prerequisites: list[Identifier] = Field(max_length=64)
    observed_failures: list[Identifier] = Field(max_length=64)
    current_behavior_digest: Digest
    target_charter_digest: Digest
    reuse_horizon: int = Field(ge=1, le=1_000_000)
    max_total_units: int = Field(ge=0, le=1_000_000_000_000_000)
    incumbent_per_use_units: int = Field(ge=0, le=1_000_000_000)
    evidence_scope: Literal["local-structural-only"] = SCOPE

    @model_validator(mode="before")
    @classmethod
    def explicit_public_context(cls, value: Any) -> Any:
        if type(value) is not dict or value.get("publicOnly") is not True:
            raise ValueError("routing requires an explicit exact-boolean public-only context")
        return value


class TransformationLibrary:
    """Keep every archive, review, promotion, retirement and rollback in one journal."""

    def __init__(self, journal: Journal, trust: TrustRegistry, *, producer: str = "local-producer") -> None:
        self.journal, self.trust, self.producer = journal, trust, producer
        trust.anchor(producer, "producer")
        journal.verify()
        with journal.transaction() as cx:
            try:
                journal.latest(KEY, cx)
            except KeyError:
                journal.append(
                    cx,
                    KEY,
                    {
                        "schema": "transformation-library/v1",
                        "entries": [],
                        "active": {},
                        "history": [],
                        "operations": {},
                    },
                )

    def snapshot(self) -> dict[str, Any]:
        """Return a detached record; changing the caller's copy cannot alter history."""
        return self.journal.document(self.journal.latest(KEY))

    @staticmethod
    def _entry(state: dict[str, Any], archive_digest: str) -> dict[str, Any]:
        for entry in state["entries"]:
            if entry["archive_digest"] == archive_digest:
                if (
                    digest(
                        "ti-library-archive",
                        {
                            "envelope": entry["envelope"],
                            "conditions": entry["conditions"],
                            "behavior_digest": entry["behavior_digest"],
                        },
                    )
                    != archive_digest
                ):
                    raise ValueError("archived method or declared evidence scope changed")
                return cast(dict[str, Any], entry)
        raise KeyError("unknown archived method")

    @staticmethod
    def _operation(state: dict[str, Any], operation_id: str, payload: Any) -> bool:
        if type(operation_id) is not str or not operation_id or len(operation_id) > 128:
            raise ValueError("a bounded operation identity is required")
        fingerprint = digest("ti-library-command", payload)
        previous = state["operations"].get(operation_id)
        if previous is not None and previous != fingerprint:
            raise Conflict("operation identity already has different library terms")
        if previous is None and len(state["operations"]) >= 4096:
            raise Conflict("library operation capacity reached; preserve and export its history")
        state["operations"][operation_id] = fingerprint
        return previous is not None

    def _signed(self, envelope: SignedEnvelope, domain: str, role: str) -> tuple[SignedEnvelope, dict[str, Any]]:
        stable = SignedEnvelope.model_validate(copy.deepcopy(envelope.model_dump()))
        payload = self.trust.verify(stable, domain, role)
        canonical(payload)
        if payload.get("journal_identity") != self.journal.identity:
            raise ValueError("library approval belongs to another journal")
        return stable, payload

    def _distinct(self, first: str, first_role: str, second: str, second_role: str) -> None:
        if (
            first == second
            or self.trust.anchor(first, first_role).public_key == self.trust.anchor(second, second_role).public_key
        ):
            raise ValueError("review, producer and controller require distinct configured principals and keys")

    def archive(self, envelope: dict[str, Any], conditions: ReuseConditions, *, operation_id: str) -> dict[str, Any]:
        """Retain a full native package as pending evidence without approving reuse."""
        envelope = validate_envelope(copy.deepcopy(envelope))
        conditions = ReuseConditions.model_validate(copy.deepcopy(conditions.model_dump()))
        if conditions.producer != self.producer:
            raise ValueError("archive producer must match the independently configured runtime producer")
        self.trust.anchor(conditions.producer, "producer")
        record = {
            "envelope": envelope,
            "conditions": conditions.model_dump(),
            "behavior_digest": portable_behavior_digest(envelope),
        }
        archive_digest = digest("ti-library-archive", record)
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            replay = self._operation(state, operation_id, record)
            if replay:
                return copy.deepcopy(self._entry(state, archive_digest))
            if any(e["archive_digest"] == archive_digest for e in state["entries"]):
                self.journal.append(cx, KEY, state)
                return copy.deepcopy(self._entry(state, archive_digest))
            if len(state["entries"]) >= MAX_ENTRIES:
                raise Conflict("library capacity reached; existing evidence cannot be pruned automatically")
            versions = [
                e["conditions"]["version"]
                for e in state["entries"]
                if e["conditions"]["method_id"] == conditions.method_id
            ]
            if conditions.version != max(versions, default=0) + 1:
                raise Conflict("method version must advance exactly once without replacing historical evidence")
            entry = {
                **record,
                "archive_digest": archive_digest,
                "state": "pending-review",
                "review": None,
                "activation": None,
                "retirement": None,
                "authority_granted": False,
            }
            state["entries"].append(entry)
            state["history"].append(
                {"action": "archive", "archive_digest": archive_digest, "operation_id": operation_id}
            )
            self.journal.append(cx, KEY, state)
            return copy.deepcopy(entry)

    def review(self, archive_digest: str, envelope: SignedEnvelope, *, operation_id: str) -> dict[str, Any]:
        """Require a distinct configured verifier to attest the exact supported scope."""
        signed, payload = self._signed(envelope, "ti-library-review", "verifier")
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            replay = self._operation(state, operation_id, [archive_digest, signed.model_dump()])
            entry = self._entry(state, archive_digest)
            if replay:
                return copy.deepcopy(entry)
            conditions = entry["conditions"]
            self._distinct(signed.principal, "verifier", conditions["producer"], "producer")
            expected = {
                "journal_identity": self.journal.identity,
                "archive_digest": archive_digest,
                "supported_scope": conditions["supported_scope"],
                "bindings_digest": entry["envelope"]["bindings_digest"],
                "behavior_digest": entry["behavior_digest"],
                "evidence_digests": conditions["evidence_digests"],
                "evidence_scope": SCOPE,
                "outcome_claim": "structural-coverage-only",
                "operation_id": operation_id,
            }
            if set(payload) != {*expected, "verdict", "limitations"} or any(
                payload[k] != v for k, v in expected.items()
            ):
                raise ValueError("review must bind the exact archive, evidence, scope and frozen behavior")
            if (
                payload["verdict"] not in {"supported", "rejected"}
                or type(payload["limitations"]) is not str
                or not payload["limitations"].strip()
                or len(payload["limitations"]) > 4000
            ):
                raise ValueError("review requires an explicit bounded verdict and retained limitations")
            if entry["state"] != "pending-review":
                raise Conflict("reviewed or retired methods require a new version, not replacement review")
            if payload["verdict"] == "supported":
                native = entry["envelope"]
                if native["phase"] != "completed" or native["freeze"] is None or native["result"] is None:
                    raise Conflict("unfinished exploration cannot receive a supported reuse review")
                evidence = {native["freeze"]["digest"], digest("ti-library-result", native["result"])}
                if not evidence <= set(conditions["evidence_digests"]):
                    raise ValueError("review evidence must include the actual frozen comparison and retained result")
            entry["review"] = signed.model_dump()
            entry["state"] = payload["verdict"]
            state["history"].append(
                {"action": "review", "archive_digest": archive_digest, "operation_id": operation_id}
            )
            self.journal.append(cx, KEY, state)
            return copy.deepcopy(entry)

    def control(
        self,
        archive_digest: str,
        envelope: SignedEnvelope,
        *,
        expected_behavior_digest: str,
        operation_id: str,
    ) -> dict[str, Any]:
        """Explicit promotion, rollback or retirement changes a local routing pointer only."""
        signed, payload = self._signed(envelope, "ti-library-control", "controller")
        with self.journal.transaction() as cx:
            state = self.journal.document(self.journal.latest(KEY, cx))
            replay = self._operation(
                state, operation_id, [archive_digest, signed.model_dump(), expected_behavior_digest]
            )
            entry = self._entry(state, archive_digest)
            if replay:
                return copy.deepcopy(entry)
            method_id = entry["conditions"]["method_id"]
            active = state["active"].get(method_id)
            expected = {
                "journal_identity": self.journal.identity,
                "archive_digest": archive_digest,
                "previous_active": active,
                "bindings_digest": entry["envelope"]["bindings_digest"],
                "behavior_digest": expected_behavior_digest,
                "stage": "local-reuse-only",
                "authority_expansion": False,
                "operation_id": operation_id,
            }
            if set(payload) != {*expected, "action", "reason"} or any(payload[k] != v for k, v in expected.items()):
                raise ValueError("control must bind the current active method and exact local-only terms")
            if payload["authority_expansion"] is not False:
                raise ValueError("control cannot coerce authority expansion declarations")
            if type(payload["reason"]) is not str or not payload["reason"].strip() or len(payload["reason"]) > 4000:
                raise ValueError("control requires a bounded explanation")
            if entry["behavior_digest"] != expected_behavior_digest:
                raise Conflict("frozen behavior changed; fresh review and authorization are required")
            self._distinct(signed.principal, "controller", entry["conditions"]["producer"], "producer")
            if payload["action"] == "retire":
                if entry["state"] == "retired":
                    raise Conflict("retirement is final; archive a new version for changed evidence")
                entry["state"], entry["retirement"] = "retired", signed.model_dump()
                if active == archive_digest:
                    del state["active"][method_id]
            elif payload["action"] in {"promote", "rollback"}:
                if entry["state"] != "supported" or entry["review"] is None:
                    raise Conflict("local reuse requires a separately supported, nonretired method")
                review = SignedEnvelope.model_validate(entry["review"])
                self._signed(review, "ti-library-review", "verifier")
                self._distinct(signed.principal, "controller", review.principal, "verifier")
                if entry["envelope"]["phase"] != "completed" or entry["envelope"]["freeze"] is None:
                    raise Conflict("unfinished exploration cannot become a locally reusable method")
                if self.journal.latest("@control", cx)["state"] != "ready":
                    raise Conflict("agent is stopped")
                if payload["action"] == "rollback" and not any(
                    h.get("archive_digest") == archive_digest and h["action"] == "promote" for h in state["history"]
                ):
                    raise Conflict("rollback requires a previously explicitly promoted method")
                state["active"][method_id] = archive_digest
                entry["activation"] = signed.model_dump()
            else:
                raise ValueError("unsupported library control action")
            state["history"].append(
                {
                    "action": payload["action"],
                    "archive_digest": archive_digest,
                    "previous_active": active,
                    "approval": signed.model_dump(),
                    "operation_id": operation_id,
                }
            )
            self.journal.append(cx, KEY, state)
            return copy.deepcopy(entry)

    def route(self, context: RouterContext) -> dict[str, Any]:
        """Select an eligible active method after full declared setup and reuse costs."""
        context = RouterContext.model_validate(copy.deepcopy(context.model_dump()))
        state = self.snapshot()
        candidates: list[tuple[int, str, dict[str, Any]]] = []
        if self.journal.latest("@control")["state"] == "ready":
            for archive_digest in state["active"].values():
                entry = self._entry(state, archive_digest)
                conditions = entry["conditions"]
                if entry["state"] != "supported" or entry["review"] is None:
                    continue
                try:
                    review, reviewed = self._signed(
                        SignedEnvelope.model_validate(entry["review"]), "ti-library-review", "verifier"
                    )
                    activation, approved = self._signed(
                        SignedEnvelope.model_validate(entry["activation"]), "ti-library-control", "controller"
                    )
                    self._distinct(review.principal, "verifier", conditions["producer"], "producer")
                    self._distinct(activation.principal, "controller", conditions["producer"], "producer")
                    self._distinct(activation.principal, "controller", review.principal, "verifier")
                except ValueError:
                    continue
                if (
                    reviewed.get("archive_digest") != archive_digest
                    or reviewed.get("verdict") != "supported"
                    or reviewed.get("supported_scope") != conditions["supported_scope"]
                    or reviewed.get("bindings_digest") != entry["envelope"]["bindings_digest"]
                    or reviewed.get("behavior_digest") != entry["behavior_digest"]
                    or reviewed.get("evidence_scope") != SCOPE
                    or reviewed.get("outcome_claim") != "structural-coverage-only"
                    or reviewed.get("evidence_digests") != conditions["evidence_digests"]
                    or approved.get("archive_digest") != archive_digest
                    or approved.get("action") not in {"promote", "rollback"}
                    or approved.get("stage") != "local-reuse-only"
                    or approved.get("authority_expansion") is not False
                    or approved.get("bindings_digest") != entry["envelope"]["bindings_digest"]
                    or approved.get("behavior_digest") != entry["behavior_digest"]
                ):
                    continue
                if (
                    context.task_scope not in conditions["supported_scope"]
                    or not set(conditions["prerequisites"]) <= set(context.prerequisites)
                    or set(conditions["failure_conditions"]) & set(context.observed_failures)
                    or entry["behavior_digest"] != context.current_behavior_digest
                    or conditions["evidence_scope"] != context.evidence_scope
                ):
                    continue
                cost = conditions["costs"]["setup_units"] + conditions["costs"]["per_use_units"] * context.reuse_horizon
                if cost <= context.max_total_units and cost < context.incumbent_per_use_units * context.reuse_horizon:
                    candidates.append((cost, archive_digest, entry))
        base = {
            "authority_granted": False,
            "execution_approved": False,
            "spending_approved": False,
            "evidence_scope": SCOPE,
            "independent_organizational_review": False,
            "reuse_horizon": context.reuse_horizon,
            "target_charter_digest": context.target_charter_digest,
        }
        if not candidates:
            return {**base, "decision": "retain-incumbent", "archive_digest": None}
        cost, selected_digest, selected = min(candidates, key=lambda row: (row[0], row[1]))
        return {
            **base,
            "decision": "select-local-method",
            "archive_digest": selected_digest,
            "method_id": selected["conditions"]["method_id"],
            "version": selected["conditions"]["version"],
            "declared_total_units": cost,
        }
