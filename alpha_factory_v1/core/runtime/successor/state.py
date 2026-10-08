# SPDX-License-Identifier: Apache-2.0
"""Signed institution state, conservative resource accounting and action gateway."""

from __future__ import annotations

import base64
from collections.abc import Callable
from datetime import UTC, datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..store import Conflict, Journal
from .protocol import (
    AdmissionDecision,
    AuthorityEnvelope,
    CandidateReleaseManifest,
    ComparatorManifest,
    EvidenceRecord,
    Institution,
    MemoryAdmission,
    ProofReceipt,
    SpecialistDesignationPolicy,
    StrictModel,
    canonical,
    digest,
    safe_json_loads,
)
from .trust import JournalCheckpoint, SignedEnvelope, TrustRegistry

MAX_UNITS = 2**53 - 1


def utc_now() -> str:
    """Use an explicit UTC timestamp, shared across one atomic decision."""
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def current(until: str, now: str) -> bool:
    """Check expiry without relying on different textual timestamp precision."""
    return datetime.fromisoformat(until) > datetime.fromisoformat(now)


def checked_resources(resources: dict[str, int]) -> None:
    """Reject booleans, negative quantities and quantities unsafe in browsers."""
    if len(resources) > 32 or any(
        not key or len(key) > 80 or type(value) is not int or not 0 <= value <= MAX_UNITS
        for key, value in resources.items()
    ):
        raise ValueError("resources require bounded nonnegative integer units")


class PortableMethodEntry(BaseModel):
    """One bounded public method artifact; imported content is never executed here."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)
    domain: str
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    content: dict[str, Any]

    @model_validator(mode="after")
    def committed(self) -> PortableMethodEntry:
        if digest(self.domain, self.content) != self.digest:
            raise ValueError("portable method artifact content commitment mismatch")
        return self


class PortableMethodBundle(StrictModel):
    """Public complete methods survive export without inheriting permission to influence."""

    kind: Literal["successor-method-bundle"] = "successor-method-bundle"
    institution_id: str
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    entries: dict[str, PortableMethodEntry]

    @model_validator(mode="after")
    def complete_bundle(self) -> PortableMethodBundle:
        domains = {
            "candidate": "release",
            "descendant": "release",
            "world": "world-program",
            "policy": "policy-program",
            "knowledge": "memory",
            "request": "request",
            "current": "current-comparator",
        }
        if set(self.entries) != set(domains) or any(
            self.entries[key].domain != domain for key, domain in domains.items()
        ):
            raise ValueError(
                "portable methods require exact candidate, descendant, WORLD, POLICY, "
                "knowledge, request and Current artifacts"
            )
        if self.request_hash != self.entries["request"].digest:
            raise ValueError("portable methods refer to another request commitment")
        if self.entries["candidate"].content.get("request_hash") != self.request_hash:
            raise ValueError("portable candidate was frozen for another request")
        return self


class EvidenceSubmission(StrictModel):
    """An accountable evidence decision explicitly binds its institution."""

    institution_id: str
    evidence: EvidenceRecord


class ActionRequest(StrictModel):
    """Complete immutable context for a single capability boundary crossing."""

    action_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,96}$")
    subject: str
    release_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    environment_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    action: str = Field(min_length=1, max_length=80)
    tool: str = Field(min_length=1, max_length=80)
    target: str = Field(min_length=1, max_length=512)
    context_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    resources: dict[str, int]
    scope: Literal["sandbox", "production"] = "sandbox"
    approval: SignedEnvelope | None = None
    job_id: str | None = None


class ResourceLedger(StrictModel):
    """Reservation and expenditure are distinct, never rewritten to a target."""

    limits: dict[str, int]
    reserved: dict[str, int] = Field(default_factory=dict)
    spent: dict[str, int] = Field(default_factory=dict)
    unknown: list[str] = Field(default_factory=list)
    overruns: list[str] = Field(default_factory=list)


class AuthenticatedRecord(StrictModel):
    """Keep original signatures and permanent impairment attribution."""

    envelope: SignedEnvelope
    status: Literal["active", "revoked", "impaired", "historical"] = "active"
    reason: str = ""


class ActionRecord(StrictModel):
    """An uncertain action cannot be replayed to duplicate an external effect."""

    request: ActionRequest
    grant_id: str
    state: Literal["reserved", "executing", "completed", "failed", "uncertain", "cancelled"] = "reserved"
    result_digest: str | None = None
    actual_resources: dict[str, int] | None = None
    error: str = ""
    measurement_scope: Literal["operator-reported"] = "operator-reported"


class SuccessorState(StrictModel):
    """One atomic institution snapshot inside the existing signed journal."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=False, validate_default=True)
    schema_version: Literal[1] = 1
    institution: Institution
    releases: dict[str, CandidateReleaseManifest] = Field(default_factory=dict)
    proofs: dict[str, AuthenticatedRecord] = Field(default_factory=dict)
    evidence: dict[str, AuthenticatedRecord] = Field(default_factory=dict)
    memory: dict[str, AuthenticatedRecord] = Field(default_factory=dict)
    admissions: dict[str, AuthenticatedRecord] = Field(default_factory=dict)
    grants: dict[str, AuthenticatedRecord] = Field(default_factory=dict)
    resources: ResourceLedger
    actions: dict[str, ActionRecord] = Field(default_factory=dict)
    serving_release: str | None = None
    nominated_release: str | None = None
    stopped: bool = False
    historical_records: dict[str, list[AuthenticatedRecord]] = Field(default_factory=dict)
    historical_settlements: list[str] = Field(default_factory=list, max_length=1024)
    artifact_bundle_json: str | None = None
    lineage: list[dict[str, str]] = Field(default_factory=list)
    operations: dict[str, str] = Field(default_factory=dict)
    denials: list[dict[str, str]] = Field(default_factory=list)


class ActionGateway:
    """Only operator-installed handlers are callable; no generated host code."""

    def __init__(self, handlers: dict[tuple[str, str], Callable[[ActionRequest], Any]]) -> None:
        self._handlers = dict(handlers)

    def execute(self, request: ActionRequest) -> Any:
        """Dispatch a fixed tool/action pair with its complete validated context."""
        handler = self._handlers.get((request.tool, request.action))
        if handler is None:
            raise ValueError("no enforced execution boundary is installed for this tool/action")
        return handler(request)


class SuccessorStore:
    """Enforce state transitions under the legacy journal's BEGIN IMMEDIATE lock."""

    def __init__(self, journal: Journal, trust: TrustRegistry, checkpoint: JournalCheckpoint | None = None) -> None:
        self.journal = journal
        self.trust = trust
        journal.verify()
        if checkpoint is not None:
            checkpoint.verify(journal)

    @staticmethod
    def _key(institution_id: str) -> str:
        if not institution_id or len(institution_id) > 160 or institution_id.startswith("@"):
            raise ValueError("invalid institution identity")
        return "@successor:" + institution_id

    def read(self, institution_id: str) -> dict[str, Any]:
        """Return an authenticated snapshot with journal revision and digest."""
        record = self.journal.latest(self._key(institution_id))
        SuccessorState.model_validate(self.journal.document(record))
        return record

    def create_institution(self, institution: Institution, budgets: dict[str, int]) -> dict[str, Any]:
        """Create persistent identity; this operation conveys no operating grant."""
        checked_resources(budgets)
        self.trust.anchor(institution.controller, "controller")
        state = SuccessorState(institution=institution, resources=ResourceLedger(limits=budgets))
        key = self._key(institution.id)
        with self.journal.transaction() as cx:
            try:
                existing = self.journal.latest(key, cx)
            except KeyError:
                return self.journal.append(cx, key, state.model_dump(mode="json"))
            if (
                existing["institution"] != institution.model_dump(mode="json")
                or existing["resources"]["limits"] != budgets
            ):
                raise Conflict("institution identity already belongs to different terms")
            return existing

    def _change(
        self,
        institution_id: str,
        operation: str,
        request_id: str,
        payload: Any,
        mutate: Callable[[SuccessorState, str], None],
        *,
        expected_revision: int | None = None,
        require_ready: bool = True,
    ) -> dict[str, Any]:
        if not request_id or len(request_id) > 160:
            raise ValueError("a bounded idempotency key is required")
        fingerprint = digest("command", {"operation": operation, "payload": payload})
        key = self._key(institution_id)
        with self.journal.transaction() as cx:
            old = self.journal.latest(key, cx)
            state = SuccessorState.model_validate(self.journal.document(old))
            if request_id in state.operations:
                if state.operations[request_id] != fingerprint:
                    raise Conflict("idempotency key belongs to different command terms")
                return old
            if expected_revision is not None and old["revision"] != expected_revision:
                raise Conflict("institution revision changed; review before retry")
            if len(state.operations) >= 10000:
                raise Conflict("institution operation limit reached; archive and renew explicitly")
            if require_ready and (self.journal.latest("@control", cx)["state"] != "ready" or state.stopped):
                raise Conflict("institution or agent is stopped")
            mutate(state, utc_now())
            state.operations[request_id] = fingerprint
            return self.journal.append(cx, key, state.model_dump(mode="json"))

    def _release(self, state: SuccessorState, release_digest: str) -> CandidateReleaseManifest:
        release = state.releases.get(release_digest)
        if release is None or digest("release", release) != release_digest:
            raise ValueError("exact frozen release is missing or changed")
        for memory_digest in release.memory_digests:
            self._memory(state, memory_digest, utc_now())
        return release

    def register_release(
        self, institution_id: str, release: CandidateReleaseManifest, *, request_id: str
    ) -> dict[str, Any]:
        """Freeze complete behavior without changing the currently serving release."""

        def mutate(state: SuccessorState, now: str) -> None:
            if (
                release.institution_id != institution_id
                or release.mission_id != state.institution.constitution.mission_id
            ):
                raise ValueError("release belongs to another institution or mission")
            self.trust.anchor(release.producer, "producer")
            for memory_digest in release.memory_digests:
                self._memory(state, memory_digest, now, use="formation")
            key = digest("release", release)
            state.releases[key] = release
            state.nominated_release = key

        return self._change(institution_id, "freeze", request_id, release, mutate, require_ready=False)

    def _proof(self, state: SuccessorState, proof_id: str, release_digest: str, now: str) -> ProofReceipt:
        record = state.proofs.get(proof_id)
        if record is None or record.status != "active":
            raise ValueError("required proof is missing, revoked or impaired")
        payload = self.trust.verify(record.envelope, "proof", "verifier")
        proof = ProofReceipt.model_validate(payload)
        release = self._release(state, release_digest)
        if (
            proof.release_digest != release_digest
            or proof.environment_digest != release.environment_digest
            or proof.institution_id != state.institution.id
            or proof.mission_id != release.mission_id
            or proof.verifier != record.envelope.principal
            or proof.outcome != "pass"
            or proof.issued_at is None
            or current(proof.issued_at, now)
            or proof.disclosure is None
            or proof.disclosure.verifier != proof.verifier
            or proof.evaluation_units < 1
            or not current(proof.valid_until, now)
        ):
            raise ValueError("proof does not establish a current claim for this exact execution")
        if proof.claim == "alpha" and (
            proof.costs.unknown_costs
            or state.institution.constitution.budget.unknown_costs
            or state.resources.unknown
            or state.resources.overruns
        ):
            raise ValueError("economic Alpha prerequisites contain unknown costs or resource overruns")
        for dependency_digest in proof.dependency_digests:
            matches = [
                evidence_id
                for evidence_id, entry in state.evidence.items()
                if EvidenceSubmission.model_validate(entry.envelope.payload).evidence.content_digest
                == dependency_digest
            ]
            if not matches:
                raise ValueError("proof evidence dependency is missing")
            for evidence_id in matches:
                evidence = self._evidence(state, evidence_id, now)
                if "proof" not in evidence.permitted_uses or evidence.scope != proof.mission_id:
                    raise ValueError("evidence rights or scope do not permit proof for this mission")
        anchor = self.trust.anchor(proof.verifier, "verifier")
        if proof.evidence_scope == "independent" and (
            anchor.provenance != "independent"
            or proof.disclosure is None
            or proof.disclosure.provenance != "independent"
        ):
            raise ValueError("local verification cannot become independent by relabelling")
        return proof

    def record_proof(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Retain all verdicts; only current positive receipts can satisfy a guard."""
        payload = self.trust.verify(envelope, "proof", "verifier")
        proof = ProofReceipt.model_validate(payload)

        def mutate(state: SuccessorState, now: str) -> None:
            release = self._release(state, proof.release_digest)
            if (
                proof.institution_id != institution_id
                or proof.mission_id != release.mission_id
                or proof.environment_digest != release.environment_digest
                or proof.verifier != envelope.principal
                or proof.verifier == release.producer
            ):
                raise ValueError("proof identity, release, environment or role binding is invalid")
            anchor = self.trust.anchor(proof.verifier, "verifier")
            if proof.evidence_scope == "independent" and (
                anchor.provenance != "independent"
                or proof.disclosure is None
                or proof.disclosure.provenance != "independent"
            ):
                raise ValueError("local verification cannot assert external independence")
            if proof.proof_id in state.proofs:
                raise Conflict("proof ID already exists; examination receipts are immutable")
            state.proofs[proof.proof_id] = AuthenticatedRecord(envelope=envelope)

        return self._change(institution_id, "proof", request_id, envelope, mutate, require_ready=False)

    def admit(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Record an accountable admission separately from a scientific verdict."""
        decision = AdmissionDecision.model_validate(self.trust.verify(envelope, "admission", "admission"))

        def mutate(state: SuccessorState, now: str) -> None:
            release = self._release(state, decision.release_digest)
            if (
                decision.institution_id != institution_id
                or decision.principal != envelope.principal
                or decision.principal == release.producer
                or decision.principal != state.institution.controller
            ):
                raise ValueError("producer cannot admit itself or another institution")
            if decision.outcome == "admit":
                if not decision.proof_ids:
                    raise ValueError("admission requires an explicit positive proof prerequisite")
                claims = {
                    self._proof(state, proof_id, decision.release_digest, now).claim for proof_id in decision.proof_ids
                }
                if not set(state.institution.constitution.proof_requirements) <= claims:
                    raise ValueError("admission omits a constitution-required proof claim")
            if decision.decision_id in state.admissions:
                raise Conflict("admission decision ID already exists")
            for prior_id, prior in state.admissions.items():
                previous = AdmissionDecision.model_validate(prior.envelope.payload)
                if previous.release_digest == decision.release_digest and prior.status == "active":
                    state.admissions[prior_id] = prior.model_copy(
                        update={"status": "historical", "reason": "superseded by an accountable decision"}
                    )
            state.admissions[decision.decision_id] = AuthenticatedRecord(envelope=envelope)
            if decision.outcome == "refuse":
                for grant_id, entry in state.grants.items():
                    previous_grant = AuthorityEnvelope.model_validate(entry.envelope.payload)
                    if previous_grant.release_digest == decision.release_digest and entry.status == "active":
                        state.grants[grant_id] = entry.model_copy(
                            update={"status": "impaired", "reason": "current admission decision refuses operation"}
                        )

        return self._change(institution_id, "admission", request_id, envelope, mutate, require_ready=False)

    def _admitted(self, state: SuccessorState, release_digest: str, now: str) -> None:
        for entry in state.admissions.values():
            if entry.status != "active":
                continue
            try:
                decision = AdmissionDecision.model_validate(self.trust.verify(entry.envelope, "admission", "admission"))
                if decision.release_digest != release_digest or decision.outcome != "admit" or not decision.proof_ids:
                    continue
                claims = {self._proof(state, proof_id, release_digest, now).claim for proof_id in decision.proof_ids}
                if not set(state.institution.constitution.proof_requirements) <= claims:
                    continue
                if decision.principal != state.institution.controller:
                    continue
                return
            except ValueError:
                continue
        raise ValueError("release lacks a currently valid accountable admission")

    def grant(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Install one complete authority envelope, never an aggregate of fragments."""
        grant = AuthorityEnvelope.model_validate(self.trust.verify(envelope, "authority", "authority"))
        checked_resources(grant.resources)
        if not grant.resources or any(amount < 1 for amount in grant.resources.values()):
            raise ValueError("authority requires explicit positive controllable resource ceilings")

        def mutate(state: SuccessorState, now: str) -> None:
            release = self._release(state, grant.release_digest)
            if (
                grant.institution_id != institution_id
                or grant.mission_id != release.mission_id
                or grant.issuer != envelope.principal
                or grant.issuer == release.producer
                or grant.issuer != state.institution.controller
                or not current(grant.valid_until, now)
            ):
                raise ValueError("grant identity, release, role or validity is invalid")
            ceiling = state.institution.constitution.authority_ceiling
            if ceiling == "none" or (grant.scope == "production" and ceiling != "production"):
                raise ValueError("grant exceeds the mission authority ceiling")
            if set(grant.actions).intersection(state.institution.constitution.prohibited_actions):
                raise ValueError("grant includes a prohibited action")
            if grant.scope == "production" and (
                not grant.rollback_release_digest or state.resources.unknown or state.resources.overruns
            ):
                raise ValueError("production authority requires valid rollback and measured resources")
            self._admitted(state, grant.release_digest, now)
            if not grant.proof_ids:
                raise ValueError("authority requires explicit proof prerequisites")
            for proof_id in grant.proof_ids:
                proof = self._proof(state, proof_id, grant.release_digest, now)
                if grant.scope == "production" and proof.evidence_scope != "independent":
                    raise ValueError("local receipts support sandbox rehearsal authority only")
            if grant.rollback_release_digest:
                self._release(state, grant.rollback_release_digest)
                self._admitted(state, grant.rollback_release_digest, now)
            if grant.grant_id in state.grants:
                raise Conflict("grant ID already exists; issue a new authority decision")
            state.grants[grant.grant_id] = AuthenticatedRecord(envelope=envelope)

        return self._change(institution_id, "grant", request_id, envelope, mutate, require_ready=False)

    def _authorized(self, state: SuccessorState, action: ActionRequest, now: str) -> str:
        checked_resources(action.resources)
        if not action.resources or any(amount < 1 for amount in action.resources.values()):
            raise ValueError("action requires positive bounded resource reservations")
        self.trust.anchor(action.subject, "worker")
        constitution = state.institution.constitution
        if action.action in constitution.prohibited_actions:
            raise ValueError("mission constitution prohibits this action")
        if constitution.validity and (
            current(constitution.validity.valid_from, now) or not current(constitution.validity.valid_until, now)
        ):
            raise ValueError("mission constitution is outside its validity window")
        release = self._release(state, action.release_digest)
        if action.environment_digest != release.environment_digest:
            raise ValueError("executing environment differs from frozen release")
        if state.serving_release != action.release_digest:
            raise ValueError("only the atomically installed serving release may act")
        self._admitted(state, action.release_digest, now)
        for grant_id, entry in state.grants.items():
            if entry.status != "active":
                continue
            try:
                grant = AuthorityEnvelope.model_validate(self.trust.verify(entry.envelope, "authority", "authority"))
                if (
                    grant.subject != action.subject
                    or grant.release_digest != action.release_digest
                    or grant.scope != action.scope
                    or action.action not in grant.actions
                    or action.tool not in grant.tools
                    or action.target not in grant.targets
                    or set(grant.resources) != set(action.resources)
                    or grant.context_digest != action.context_digest
                    or not current(grant.valid_until, now)
                    or any(amount > grant.resources.get(unit, -1) for unit, amount in action.resources.items())
                ):
                    continue
                usage = {
                    unit: sum(
                        previous.request.resources.get(unit, 0)
                        for previous in state.actions.values()
                        if previous.grant_id == grant_id
                        and previous.request.action_id != action.action_id
                        and previous.state != "cancelled"
                    )
                    for unit in action.resources
                }
                if any(
                    amount + usage[unit] > grant.resources.get(unit, -1) for unit, amount in action.resources.items()
                ):
                    continue
                if not grant.proof_ids:
                    continue
                for proof_id in grant.proof_ids:
                    proof = self._proof(state, proof_id, action.release_digest, now)
                    if action.scope == "production" and proof.evidence_scope != "independent":
                        raise ValueError("production proof is unavailable")
                if grant.rollback_release_digest:
                    self._admitted(state, grant.rollback_release_digest, now)
                if grant.approval_required:
                    if action.approval is None or action.approval.principal != state.institution.controller:
                        continue
                    approval = self.trust.verify(action.approval, "action-approval", "controller")
                    expected = digest("action", action.model_dump(mode="json", exclude={"approval"}))
                    if approval != {"action_digest": expected}:
                        continue
                return grant_id
            except ValueError:
                continue
        raise ValueError("no single current grant authorizes the complete action context")

    def _deny(self, institution_id: str, action_id: str, reason: str) -> None:
        with self.journal.transaction() as cx:
            old = self.journal.latest(self._key(institution_id), cx)
            state = SuccessorState.model_validate(self.journal.document(old))
            state.denials.append({"action_id": action_id, "time": utc_now(), "reason": reason[:500]})
            if len(state.denials) > 1000:
                del state.denials[: len(state.denials) - 1000]
            self.journal.append(cx, self._key(institution_id), state.model_dump(mode="json"))

    def dispatch_action(self, institution_id: str, action: ActionRequest) -> dict[str, Any]:
        """Atomically reserve shared ceilings; retry cannot reserve a second time."""

        def mutate(state: SuccessorState, now: str) -> None:
            grant_id = self._authorized(state, action, now)
            if action.action_id in state.actions:
                raise Conflict("action identity already exists")
            for unit, amount in action.resources.items():
                ledger = state.resources
                available = ledger.limits.get(unit, -1) - ledger.reserved.get(unit, 0) - ledger.spent.get(unit, 0)
                if amount > available:
                    raise ValueError("shared controllable resource ceiling is exhausted or unavailable")
            for unit, amount in action.resources.items():
                state.resources.reserved[unit] = state.resources.reserved.get(unit, 0) + amount
            state.actions[action.action_id] = ActionRecord(request=action, grant_id=grant_id)

        try:
            return self._change(institution_id, "dispatch", "action:" + action.action_id, action, mutate)
        except (ValueError, Conflict) as exc:
            self._deny(institution_id, action.action_id, str(exc))
            raise

    @staticmethod
    def _charge(state: SuccessorState, action: ActionRecord, actual: dict[str, int] | None) -> None:
        if actual is not None:
            checked_resources(actual)
            if set(actual) != set(action.request.resources):
                raise ValueError("actual measurement must cover exactly the reserved resource units")
        for unit, bound in action.request.resources.items():
            state.resources.reserved[unit] -= bound
            measured = bound if actual is None else actual[unit]
            state.resources.spent[unit] = state.resources.spent.get(unit, 0) + max(bound, measured)
            if measured > bound:
                state.resources.overruns.append(action.request.action_id + ":" + unit)
                state.stopped = True
        if actual is None:
            state.resources.unknown.append(action.request.action_id)

    def execute_action(
        self,
        institution_id: str,
        action_id: str,
        gateway: ActionGateway,
        *,
        actual_resources: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """Revalidate immediately at the boundary; uncertain external effects never auto-retry.

        The journal lock serializes revocation and bounded handler execution. Handlers
        must provide their own hard isolation/time limit; this API never evaluates
        arbitrary code. An interrupted transaction retains its reservation for recovery.
        """
        try:
            with self.journal.transaction() as cx:
                old = self.journal.latest(self._key(institution_id), cx)
                state = SuccessorState.model_validate(self.journal.document(old))
                action = state.actions.get(action_id)
                if action is None:
                    raise Conflict("action does not exist")
                if action.state in {"completed", "failed"}:
                    if action.actual_resources != actual_resources:
                        raise Conflict("retry measurement differs from completed action")
                    return old
                if action.state != "reserved":
                    raise Conflict("action already started; signed recovery is required, never replay its effect")
                if state.stopped or self.journal.latest("@control", cx)["state"] != "ready":
                    raise Conflict("institution or agent is stopped")
                self._authorized(state, action.request, utc_now())
                state.actions[action_id] = action.model_copy(update={"state": "executing"})
                self.journal.append(cx, self._key(institution_id), state.model_dump(mode="json"))
        except (ValueError, Conflict) as exc:
            self._deny(institution_id, action_id, str(exc))
            raise
        failure: list[Exception] = []

        def mutate(state: SuccessorState, now: str) -> None:
            action = state.actions.get(action_id)
            if action is None or action.state != "executing":
                raise Conflict("action is missing or no longer dispatchable")
            self._authorized(state, action.request, now)
            if actual_resources is not None:
                checked_resources(actual_resources)
                if set(actual_resources) != set(action.request.resources):
                    raise ValueError("complete actual resource measurements are required")
            try:
                result = gateway.execute(action.request)
                result_digest = digest("action-result", result)
                updated = action.model_copy(update={"state": "completed", "result_digest": result_digest})
            except Exception as exc:  # noqa: BLE001 - persist boundary failures before re-raising
                failure.append(exc)
                updated = action.model_copy(update={"state": "failed", "error": type(exc).__name__})
            self._charge(state, action, actual_resources)
            state.actions[action_id] = updated.model_copy(update={"actual_resources": actual_resources})

        try:
            result = self._change(
                institution_id,
                "execute",
                "execute:" + action_id,
                {"action_id": action_id, "actual_resources": actual_resources},
                mutate,
            )
        except (ValueError, Conflict) as exc:
            self._deny(institution_id, action_id, str(exc))
            raise
        if failure:
            raise ValueError("bounded action failed; failure receipt retained") from failure[0]
        return result

    def revoke(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Apply a signed revocation even while stopped; retain the old grant."""
        payload = self.trust.verify(envelope, "revocation", "authority")
        if set(payload) != {"grant_id", "reason"} or not all(isinstance(x, str) for x in payload.values()):
            raise ValueError("revocation requires only grant_id and reason strings")

        def mutate(state: SuccessorState, now: str) -> None:
            entry = state.grants.get(payload["grant_id"])
            if entry is None:
                raise ValueError("grant does not exist")
            grant = AuthorityEnvelope.model_validate(entry.envelope.payload)
            if envelope.principal not in {grant.issuer, state.institution.controller}:
                raise ValueError("principal cannot revoke this authority")
            state.grants[payload["grant_id"]] = entry.model_copy(
                update={"status": "revoked", "reason": payload["reason"]}
            )

        return self._change(institution_id, "revoke", request_id, envelope, mutate, require_ready=False)

    def impair(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Contract only affected claims; economic Alpha loss need not revoke safety."""
        payload = self.trust.verify(envelope, "impairment", "controller")
        if set(payload) != {"release_digest", "claims", "reason"}:
            raise ValueError("impairment requires release_digest, claims and reason")
        if not isinstance(payload["claims"], list) or not all(isinstance(v, str) for v in payload["claims"]):
            raise ValueError("impairment claims must be a list of strings")

        def mutate(state: SuccessorState, now: str) -> None:
            self._release(state, payload["release_digest"])
            if envelope.principal != state.institution.controller:
                raise ValueError("only the institution controller can record impairment")
            affected = set()
            for ident, entry in state.proofs.items():
                proof = ProofReceipt.model_validate(entry.envelope.payload)
                if proof.release_digest == payload["release_digest"] and (
                    not payload["claims"] or proof.claim in payload["claims"]
                ):
                    affected.add(ident)
                    state.proofs[ident] = entry.model_copy(update={"status": "impaired", "reason": payload["reason"]})
            for ident, entry in state.grants.items():
                grant = AuthorityEnvelope.model_validate(entry.envelope.payload)
                if affected.intersection(grant.proof_ids):
                    state.grants[ident] = entry.model_copy(update={"status": "impaired", "reason": payload["reason"]})

        return self._change(institution_id, "impair", request_id, envelope, mutate, require_ready=False)

    def cutover(
        self,
        institution_id: str,
        envelope: SignedEnvelope,
        *,
        request_id: str,
        expected_revision: int,
    ) -> dict[str, Any]:
        """Atomically replace the sole serving release after accountable authorization."""
        payload = self.trust.verify(envelope, "cutover", "controller")
        if set(payload) != {"release_digest"}:
            raise ValueError("cutover must bind exactly one frozen release")

        def mutate(state: SuccessorState, now: str) -> None:
            release = self._release(state, payload["release_digest"])
            if envelope.principal != state.institution.controller or envelope.principal == release.producer:
                raise ValueError("producer cannot install its own successor")
            self._admitted(state, payload["release_digest"], now)
            if any(action.state in {"reserved", "executing"} for action in state.actions.values()):
                raise Conflict("drain or recover in-flight actions before serving cutover")
            has_grant = False
            for entry in state.grants.values():
                if entry.status != "active":
                    continue
                grant = AuthorityEnvelope.model_validate(self.trust.verify(entry.envelope, "authority", "authority"))
                if grant.release_digest == payload["release_digest"] and current(grant.valid_until, now):
                    for proof_id in grant.proof_ids:
                        self._proof(state, proof_id, grant.release_digest, now)
                    has_grant = bool(grant.proof_ids)
                    if has_grant:
                        break
            if not has_grant:
                raise ValueError("cutover requires a current complete authority envelope")
            state.lineage.append({"from": state.serving_release or "", "to": payload["release_digest"], "time": now})
            state.serving_release = payload["release_digest"]
            state.stopped = False

        return self._change(
            institution_id,
            "cutover",
            request_id,
            envelope,
            mutate,
            expected_revision=expected_revision,
            require_ready=False,
        )

    def recover(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Conservatively consume uncertain reservations and require a new decision."""
        payload = self.trust.verify(envelope, "recovery", "controller")
        if payload != {"institution_id": institution_id}:
            raise ValueError("recovery must bind the institution")

        def mutate(state: SuccessorState, now: str) -> None:
            if envelope.principal != state.institution.controller:
                raise ValueError("recovery requires the institution controller")
            affected_releases = set()
            for action_id, action in state.actions.items():
                if action.state in {"reserved", "executing"}:
                    self._charge(state, action, None)
                    affected_releases.add(action.request.release_digest)
                    state.actions[action_id] = action.model_copy(update={"state": "uncertain"})
            for records in (state.proofs, state.admissions, state.grants):
                for record_id, entry in records.items():
                    if entry.envelope.payload.get("release_digest") in affected_releases and entry.status == "active":
                        records[record_id] = entry.model_copy(
                            update={
                                "status": "impaired",
                                "reason": "uncertain action requires fresh recovery evidence and accountable admission",
                            }
                        )
            state.stopped = True

        return self._change(institution_id, "recover", request_id, envelope, mutate, require_ready=False)

    def descendant(self, institution_id: str, release: CandidateReleaseManifest, *, request_id: str) -> dict[str, Any]:
        """Create a shadow successor whose exact identity has no inherited receipts."""
        existing = self.read(institution_id)
        if digest("release", release) in existing["releases"] and request_id not in existing["operations"]:
            raise Conflict("descendant must have a new release identity")
        return self.register_release(institution_id, release, request_id=request_id)

    def record_evidence(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Accept evidence metadata and commitments without interpreting evidence as instructions."""
        submission = EvidenceSubmission.model_validate(self.trust.verify(envelope, "evidence", "acceptance"))

        def mutate(state: SuccessorState, now: str) -> None:
            evidence = submission.evidence
            if submission.institution_id != institution_id or envelope.principal != state.institution.controller:
                raise ValueError("evidence admission requires the institution controller")
            if evidence.accepted_by != envelope.principal or evidence.revoked or not current(evidence.valid_until, now):
                raise ValueError("evidence acceptance, rights or freshness is invalid")
            if current(evidence.acquired_at, now) or not evidence.permitted_uses:
                raise ValueError("evidence acquisition must be past and rights explicit")
            if evidence.evidence_id in state.evidence:
                raise Conflict("evidence identity is immutable")
            for dependency in evidence.dependencies:
                parent = self._evidence(state, dependency, now)
                if not set(evidence.permitted_uses) <= set(parent.permitted_uses):
                    raise ValueError("derived evidence cannot widen dependency rights")
                if not set(parent.restrictions) <= set(evidence.restrictions) or evidence.scope != parent.scope:
                    raise ValueError("derived evidence must preserve dependency restrictions and scope")
            state.evidence[evidence.evidence_id] = AuthenticatedRecord(envelope=envelope)

        return self._change(institution_id, "evidence", request_id, envelope, mutate, require_ready=False)

    def _evidence(
        self, state: SuccessorState, evidence_id: str, now: str, seen: set[str] | None = None
    ) -> EvidenceRecord:
        seen = set() if seen is None else seen
        if evidence_id in seen:
            raise ValueError("cyclic evidence dependencies are invalid")
        seen.add(evidence_id)
        entry = state.evidence.get(evidence_id)
        if entry is None or entry.status != "active":
            raise ValueError("required evidence is missing, revoked or quarantined")
        submission = EvidenceSubmission.model_validate(self.trust.verify(entry.envelope, "evidence", "acceptance"))
        evidence = submission.evidence
        if (
            submission.institution_id != state.institution.id
            or evidence.revoked
            or not current(evidence.valid_until, now)
            or (evidence.retention_until and not current(evidence.retention_until, now))
        ):
            raise ValueError("evidence freshness or retention rights expired")
        for dependency in evidence.dependencies:
            parent = self._evidence(state, dependency, now, set(seen))
            if not set(evidence.permitted_uses) <= set(parent.permitted_uses):
                raise ValueError("evidence dependency rights have contracted")
            if not set(parent.restrictions) <= set(evidence.restrictions) or parent.scope != evidence.scope:
                raise ValueError("evidence dependency scope or restrictions changed")
        return evidence

    def _memory(
        self, state: SuccessorState, artifact_digest: str, now: str, *, use: str | None = None
    ) -> MemoryAdmission:
        for entry in state.memory.values():
            if entry.status != "active":
                continue
            memory = MemoryAdmission.model_validate(self.trust.verify(entry.envelope, "memory-admission", "admission"))
            if memory.artifact_digest != artifact_digest or memory.outcome != "admit":
                continue
            if memory.scope != state.institution.constitution.mission_id:
                raise ValueError("memory scope does not match this exact mission")
            if not current(memory.valid_until, now) or not current(memory.retention_until, now):
                raise ValueError("memory permission expired")
            if use is not None and use not in memory.permitted_uses:
                raise ValueError("memory rights exclude this use")
            for evidence_id in memory.evidence_ids:
                evidence = self._evidence(state, evidence_id, now)
                if evidence.scope != memory.scope:
                    raise ValueError("memory and evidence scope differ")
                if not set(memory.permitted_uses) <= set(evidence.permitted_uses):
                    raise ValueError("memory permission exceeds source evidence rights")
                if not set(evidence.restrictions) <= set(memory.restrictions):
                    raise ValueError("memory omits inherited evidence restrictions")
            return memory
        raise ValueError("artifact has no current memory admission")

    def admit_memory(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Admit influence only under current integrity, scope, evidence and retention rights."""
        memory = MemoryAdmission.model_validate(self.trust.verify(envelope, "memory-admission", "admission"))

        def mutate(state: SuccessorState, now: str) -> None:
            if memory.institution_id != institution_id or memory.principal != envelope.principal:
                raise ValueError("memory decision is bound to another principal or institution")
            if memory.principal != state.institution.controller:
                raise ValueError("memory admission requires the institution controller")
            if memory.admission_id in state.memory:
                raise Conflict("memory admission identity already exists")
            state.memory[memory.admission_id] = AuthenticatedRecord(envelope=envelope)
            if memory.outcome == "admit":
                self._memory(state, memory.artifact_digest, now)

        return self._change(institution_id, "memory-admission", request_id, envelope, mutate, require_ready=False)

    def revoke_evidence(self, institution_id: str, envelope: SignedEnvelope, *, request_id: str) -> dict[str, Any]:
        """Revoked rights immediately block all dependent memory and release proof use."""
        payload = self.trust.verify(envelope, "evidence-revocation", "controller")
        if set(payload) != {"evidence_id", "reason"} or not all(isinstance(value, str) for value in payload.values()):
            raise ValueError("evidence revocation requires evidence_id and reason")

        def mutate(state: SuccessorState, now: str) -> None:
            if envelope.principal != state.institution.controller:
                raise ValueError("evidence revocation requires the institution controller")
            entry = state.evidence.get(payload["evidence_id"])
            if entry is None:
                raise ValueError("evidence does not exist")
            state.evidence[payload["evidence_id"]] = entry.model_copy(
                update={"status": "revoked", "reason": payload["reason"]}
            )

        return self._change(institution_id, "evidence-revocation", request_id, envelope, mutate, require_ready=False)

    def assess_designation(
        self,
        institution_id: str,
        policy_envelope: SignedEnvelope,
        comparator_manifest: ComparatorManifest,
        proof_ids: list[str],
    ) -> dict[str, Any]:
        """Assess a signed designation policy without manufacturing independent qualification."""
        policy = SpecialistDesignationPolicy.model_validate(
            self.trust.verify(policy_envelope, "designation-policy", "controller")
        )
        state = SuccessorState.model_validate(self.journal.document(self.read(institution_id)))
        now = utc_now()
        reasons = []
        if (
            policy.accountable_policy_owner != state.institution.controller
            or policy_envelope.principal != state.institution.controller
        ):
            raise ValueError("designation policy requires the institution controller")
        if policy.mission_family != state.institution.constitution.mission_id:
            reasons.append("designation policy belongs to another mission family")
        if current(policy.validity.valid_from, now) or not current(policy.validity.valid_until, now):
            reasons.append("designation policy is outside its validity window")
        if state.resources.unknown or state.resources.overruns or state.institution.constitution.budget.unknown_costs:
            reasons.append("economic or resource measurements are unknown or overrun")
        measured = {entry.role for entry in comparator_manifest.comparators if entry.status == "measured"}
        required = {entry.role for entry in policy.comparator_requirements if entry.required}
        if not required <= measured:
            reasons.append("credible required comparator families remain unmeasured")
        qualifying = []
        organizations: set[str] = set()
        attestations: set[str] = set()
        release_digest = None
        for proof_id in dict.fromkeys(proof_ids):
            entry = state.proofs.get(proof_id)
            if entry is None:
                continue
            try:
                candidate = ProofReceipt.model_validate(entry.envelope.payload)
                proof = self._proof(state, proof_id, candidate.release_digest, now)
                anchor = self.trust.anchor(proof.verifier, "verifier")
                if (
                    proof.claim != policy.required_claim
                    or proof.evidence_scope != "independent"
                    or anchor.provenance != "independent"
                    or proof.disclosure is None
                    or proof.disclosure.replication_status != "external-replication"
                    or proof.comparator_manifest_digest != digest("comparator-manifest", comparator_manifest)
                    or proof.evaluation_units < policy.minimum_evaluation_units
                    or proof.uncertainty != policy.uncertainty_requirement
                    or proof.costs.unknown_costs
                ):
                    continue
                value = proof.measurements.get(policy.superiority_metric)
                if value is None or Decimal(value) < policy.superiority_threshold_bps:
                    continue
                if release_digest is not None and release_digest != proof.release_digest:
                    continue
                if proof.disclosure.organization in organizations or anchor.independence_attestation in attestations:
                    continue
                release_digest = proof.release_digest
                organizations.add(proof.disclosure.organization)
                attestations.add(anchor.independence_attestation)
                qualifying.append(proof_id)
            except ValueError:
                continue
        if len(qualifying) < policy.required_independent_replications:
            reasons.append("current independently replicated Alpha evidence does not meet the signed policy")
        return {
            "status": "HOLD" if reasons else "designated",
            "designation": policy.designation if not reasons else None,
            "policy_digest": digest("designation-policy", policy),
            "release_digest": release_digest,
            "qualifying_proof_ids": qualifying,
            "reasons": reasons,
            "production_authority": False,
        }

    @staticmethod
    def _method_bundle(
        institution_id: str, releases: dict[str, CandidateReleaseManifest], value: Any, memory_commitments: set[str]
    ) -> dict[str, Any]:
        bundle = PortableMethodBundle.model_validate(value)
        if bundle.institution_id != institution_id:
            raise ValueError("portable method bundle belongs to another institution")
        committed = {
            artifact.digest
            for release in releases.values()
            for artifact in release.artifacts
            if artifact.role == "other" and artifact.name == "complete-composition"
        }
        for name in ("candidate", "descendant"):
            if digest("composition", bundle.entries[name].content) not in committed:
                raise ValueError("portable method composition is absent from the institution's frozen releases")
        current = bundle.entries["current"]
        if digest("composition", {"manifest": current.content, "subject_digest": current.digest}) not in committed:
            raise ValueError("portable Current artifact is absent from the institution's frozen releases")
        if bundle.entries["knowledge"].digest not in memory_commitments:
            raise ValueError("portable knowledge is absent from retained memory admission history")
        candidate, descendant = bundle.entries["candidate"].content, bundle.entries["descendant"].content
        if candidate.get("policy") != bundle.entries["policy"].content:
            raise ValueError("portable policy differs from the frozen candidate")
        if candidate.get("world", {}).get("prediction_commitment") != bundle.entries["world"].content.get(
            "prediction_commitment"
        ):
            raise ValueError("portable WORLD prediction commitment differs from the frozen candidate")
        if descendant.get("memory", {}).get("digest") != bundle.entries["knowledge"].digest:
            raise ValueError("portable successor memory differs from admitted knowledge")
        return bundle.model_dump(mode="json")

    def export_portable(self, institution_id: str, *, artifact_bundle: dict[str, Any] | None = None) -> dict[str, Any]:
        """Export knowledge and commitments, excluding all secret state and permissions."""
        with self.journal.transaction() as cx:
            raw = self.journal.latest(self._key(institution_id), cx)
            state = SuccessorState.model_validate(self.journal.document(raw))
            if artifact_bundle is not None:
                memory_commitments = {
                    MemoryAdmission.model_validate(entry.envelope.payload).artifact_digest
                    for entry in list(state.memory.values()) + state.historical_records.get("memory", [])
                }
                bundle = self._method_bundle(institution_id, state.releases, artifact_bundle, memory_commitments)
                serialized = canonical(bundle).decode("utf-8")
                if state.artifact_bundle_json != serialized:
                    state.artifact_bundle_json = serialized
                    raw = self.journal.append(cx, self._key(institution_id), state.model_dump(mode="json"))
            payload = {
                "schema_version": 1,
                "kind": "successor-portable",
                "artifact_bundle": safe_json_loads(state.artifact_bundle_json) if state.artifact_bundle_json else None,
                "institution": state.institution.model_dump(mode="json"),
                "releases": {key: value.model_dump(mode="json") for key, value in state.releases.items()},
                "historical_proofs": {key: value.model_dump(mode="json") for key, value in state.proofs.items()},
                "historical_evidence": {key: value.model_dump(mode="json") for key, value in state.evidence.items()},
                "historical_memory": {key: value.model_dump(mode="json") for key, value in state.memory.items()},
                "historical_records": {
                    key: [entry.model_dump(mode="json") for entry in entries]
                    for key, entries in state.historical_records.items()
                },
                "lineage": state.lineage,
                "source_identity": self.journal.identity,
                "source_revision": raw["revision"],
                "source_digest": raw["digest"],
                "checkpoint": {
                    "identity": self.journal.identity,
                    "sequence": cx.execute("SELECT MAX(seq) FROM events").fetchone()[0],
                    "head": cx.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()[0],
                },
                "active_proofs": [],
                "active_grants": [],
                "restoration": "Supply independent trust anchors; re-examine, admit and grant before cutover.",
            }
            from .ascension import list_settlements, validate_historical_settlement

            settlements = [validate_historical_settlement(safe_json_loads(raw)) for raw in state.historical_settlements]
            settlements.extend(list_settlements(self.journal, institution_id, cx=cx))
            payload["settlements"] = list(
                {digest("historical-settlement", record): record for record in settlements}.values()
            )
            commitment = digest("portable", payload)
            signature = base64.b64encode(self.journal.key.sign(bytes.fromhex(commitment))).decode("ascii")
            return {"payload": payload, "digest": commitment, "signature": signature}

    def restore_portable(
        self,
        package: dict[str, Any],
        budgets: dict[str, int],
        *,
        source_public_key: str,
        checkpoint: JournalCheckpoint,
    ) -> dict[str, Any]:
        """Import only validated public knowledge; predecessor authority stays empty."""
        if (
            set(package) != {"payload", "digest", "signature"}
            or digest("portable", package["payload"]) != package["digest"]
        ):
            raise ValueError("portable commitment mismatch")
        payload = package["payload"]
        if payload.get("source_identity") != "urn:agialpha:ed25519:" + source_public_key:
            raise ValueError("portable source differs from independently supplied source key")
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(source_public_key)).verify(
                base64.b64decode(package["signature"], validate=True), bytes.fromhex(package["digest"])
            )
        except (InvalidSignature, ValueError) as exc:
            raise ValueError("portable source signature is invalid") from exc
        expected_checkpoint = {
            "identity": checkpoint.identity,
            "sequence": checkpoint.sequence,
            "head": checkpoint.head,
        }
        if payload.get("checkpoint") != expected_checkpoint or checkpoint.identity != payload["source_identity"]:
            raise ValueError("portable history differs from the independently retained checkpoint")
        if type(payload.get("source_revision")) is not int or not 1 <= payload["source_revision"] <= MAX_UNITS:
            raise ValueError("portable source revision must be a bounded positive integer")
        if payload["source_revision"] > checkpoint.sequence:
            raise ValueError("portable state is newer than its declared checkpoint")
        allowed = {
            "schema_version",
            "kind",
            "institution",
            "releases",
            "historical_proofs",
            "historical_evidence",
            "historical_memory",
            "historical_records",
            "settlements",
            "artifact_bundle",
            "lineage",
            "source_identity",
            "source_revision",
            "source_digest",
            "checkpoint",
            "active_proofs",
            "active_grants",
            "restoration",
        }
        if (
            set(payload) != allowed
            or type(payload["schema_version"]) is not int
            or payload["schema_version"] != 1
            or payload["kind"] != "successor-portable"
        ):
            raise ValueError("unsupported portable schema or fields")
        if payload["active_proofs"] or payload["active_grants"]:
            raise ValueError("portable imports cannot restore active proof or grants")
        institution = Institution.model_validate(payload["institution"])
        releases = {key: CandidateReleaseManifest.model_validate(value) for key, value in payload["releases"].items()}
        for key, value in releases.items():
            if digest("release", value) != key or value.institution_id != institution.id:
                raise ValueError("portable release binding is invalid")
        restored_bundle = None
        if payload["artifact_bundle"] is not None:
            memory_commitments = {
                MemoryAdmission.model_validate(
                    AuthenticatedRecord.model_validate(entry).envelope.payload
                ).artifact_digest
                for entry in list(payload["historical_memory"].values())
                + payload["historical_records"].get("memory", [])
            }
            restored_bundle = canonical(
                self._method_bundle(institution.id, releases, payload["artifact_bundle"], memory_commitments)
            ).decode("utf-8")
        for entry in payload["historical_proofs"].values():
            historical = AuthenticatedRecord.model_validate(entry)
            ProofReceipt.model_validate(historical.envelope.payload)
        for entry in payload["historical_evidence"].values():
            EvidenceSubmission.model_validate(AuthenticatedRecord.model_validate(entry).envelope.payload)
        for entry in payload["historical_memory"].values():
            MemoryAdmission.model_validate(AuthenticatedRecord.model_validate(entry).envelope.payload)
        from .ascension import validate_historical_settlement

        historical_settlements = [
            canonical(validate_historical_settlement(record)).decode("utf-8") for record in payload["settlements"]
        ]
        checked_resources(budgets)
        self.trust.anchor(institution.controller, "controller")
        state = SuccessorState(
            institution=institution,
            releases=releases,
            historical_settlements=historical_settlements,
            artifact_bundle_json=restored_bundle,
            resources=ResourceLedger(limits=budgets),
            historical_records={
                namespace: list(
                    {
                        digest(
                            "historical-record", AuthenticatedRecord.model_validate(entry).envelope
                        ): AuthenticatedRecord.model_validate(entry).model_copy(update={"status": "historical"})
                        for entry in (
                            payload["historical_records"].get(namespace, [])
                            + list(payload.get("historical_" + namespace, {}).values())
                        )
                    }.values()
                )
                for namespace in set(payload["historical_records"]) | {"proofs", "evidence", "memory"}
            },
            stopped=True,
            lineage=payload["lineage"] + [{"restored_from": payload["source_digest"], "time": utc_now()}],
        )
        with self.journal.transaction() as cx:
            key = self._key(institution.id)
            if cx.execute("SELECT 1 FROM events WHERE mission=?", (key,)).fetchone():
                raise Conflict("portable restore requires a clean institution destination")
            return self.journal.append(cx, key, state.model_dump(mode="json"))
