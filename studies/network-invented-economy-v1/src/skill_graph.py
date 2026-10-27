# SPDX-License-Identifier: Apache-2.0
"""Research-only, in-memory capability lifecycle; all identity keys are public fixtures.

AES-GCM and Ed25519 operations are real. ENS resolution, identity authentication,
validator judgments, authority assignments and clock inputs are simulated. No key
in this module is a secret or a production credential. No skill code is executed.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
import threading
from dataclasses import asdict, dataclass, field, replace
from typing import Any

from cryptography.exceptions import InvalidSignature, InvalidTag
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

if __package__:
    from .alpha_assessment import AlphaAssessment, AlphaCosts, BetaBaseline, evaluate_alpha
else:
    from alpha_assessment import AlphaAssessment, AlphaCosts, BetaBaseline, evaluate_alpha

SCHEMA = "beyond-beta.skill-graph.v3"
TREE_POLICY = "sha256-typed-sorted-pair-duplicate-last-v1"
TERMINAL = frozenset({"revoked", "retired", "superseded"})
FIXTURE_AES_KEY = hashlib.sha256(b"PUBLIC-TEST-FIXTURE-NOT-A-SECRET:v1").digest()
DIRECT_NAME = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth\Z")
HEX_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


class GraphError(ValueError):
    """A lifecycle, authority, evidence or applicability check refused an operation."""


def canonical(value: Any) -> bytes:
    """Return documented Python JSON canonical bytes, not an RFC 8785 claim."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def digest(domain: str, value: Any) -> str:
    """Hash one schema-bound typed object with unambiguous length framing."""
    return hashlib.sha256(canonical([SCHEMA, domain, value])).hexdigest()


def direct_agent(name: str) -> bool:
    """Recognize canonical direct-child ASCII fixtures, without conferring ownership."""
    return isinstance(name, str) and DIRECT_NAME.fullmatch(name) is not None


def _parent(left: str, right: str) -> str:
    return digest("merkle-node", sorted((left, right)))


def merkle_root(leaves: list[str]) -> str:
    """Commit sorted leaves; the last leaf is duplicated at odd-width levels."""
    nodes = sorted(leaves)
    if not nodes:
        return digest("merkle-empty", TREE_POLICY)
    while len(nodes) > 1:
        nodes = [_parent(nodes[i], nodes[min(i + 1, len(nodes) - 1)]) for i in range(0, len(nodes), 2)]
    return nodes[0]


def merkle_proof(leaves: list[str], leaf: str) -> tuple[str, ...]:
    """Build a sorted-pair inclusion path for an exact existing leaf."""
    nodes = sorted(leaves)
    if leaf not in nodes:
        raise GraphError("leaf is absent")
    index, proof = nodes.index(leaf), []
    while len(nodes) > 1:
        proof.append(nodes[index ^ 1] if (index ^ 1) < len(nodes) else nodes[index])
        nodes = [_parent(nodes[i], nodes[min(i + 1, len(nodes) - 1)]) for i in range(0, len(nodes), 2)]
        index //= 2
    return tuple(proof)


def verify_inclusion(leaf: str, proof: tuple[str, ...], root: str) -> bool:
    """Verify commitment inclusion only; this never grants reuse authority."""
    for sibling in proof:
        leaf = _parent(leaf, sibling)
    return leaf == root


@dataclass(frozen=True)
class Principal:
    """A trusted test-harness assignment, not an ENS ownership observation."""

    name: str
    fixture_wallet: str
    permissions: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Session:
    """An identity-checked object issued by a particular fixture directory."""

    name: str
    fixture_wallet: str
    issued_at: int


class FixtureDirectory:
    """Simulate owner resolution and authentication with explicit fixture values."""

    def __init__(self, principals: tuple[Principal, ...]) -> None:
        if len({p.name for p in principals}) != len(principals):
            raise GraphError("duplicate principal")
        if not all(direct_agent(p.name) for p in principals):
            raise GraphError("only direct-label agent fixtures may hold authority")
        self._principals = {p.name: p for p in principals}
        self._sessions: dict[int, Session] = {}
        self._disabled: set[str] = set()

    def open_session(self, name: str, fixture_wallet: str, now: int = 0) -> Session:
        """Require the fixture's exact owner, not just a matching name suffix."""
        principal = self._principals.get(name)
        if principal is None or name in self._disabled or principal.fixture_wallet != fixture_wallet:
            raise GraphError("simulated identity/owner check failed")
        session = Session(name, fixture_wallet, now)
        self._sessions[id(session)] = session
        return session

    def require(self, session: Session, permission: str | None = None) -> Principal:
        """Recheck session issuance, current membership and the requested role."""
        if self._sessions.get(id(session)) is not session or session.name in self._disabled:
            raise GraphError("unknown or disabled authentication session")
        principal = self._principals[session.name]
        if permission is not None and permission not in principal.permissions:
            raise GraphError("role permission absent: " + permission)
        return principal

    def disable_fixture(self, name: str) -> None:
        """Simulate loss of current membership from the trusted test harness."""
        if name not in self._principals:
            raise GraphError("unknown principal")
        self._disabled.add(name)

    def eligible(self, name: str, permission: str) -> bool:
        """Check current eligibility for a stored attestor identity."""
        principal = self._principals.get(name)
        return principal is not None and name not in self._disabled and permission in principal.permissions

    @staticmethod
    def fixture_key(name: str) -> Ed25519PrivateKey:
        """Derive a PUBLIC fixture signing key; it conveys no real identity trust."""
        return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(("PUBLIC-FIXTURE:" + name).encode()).digest())


@dataclass(frozen=True)
class Policy:
    """Versioned admission requirements; no numerical UI score is evidence."""

    version: str = "research-admission-v1"
    quorum: int = 2
    min_cases: int = 8
    max_evidence_age: int = 12
    max_attestation_age: int = 8
    require_positive_benefit: bool = True

    def __post_init__(self) -> None:
        if not self.version or self.quorum < 1 or self.min_cases < 1:
            raise GraphError("invalid policy")
        if self.max_evidence_age < 1 or self.max_attestation_age < 1:
            raise GraphError("invalid policy freshness window")

    @property
    def hash(self) -> str:
        return digest("policy", asdict(self))


@dataclass(frozen=True)
class Dependency:
    """Pin an exact retained manifest, rather than a mutable capability label."""

    skill_id: str
    manifest_hash: str


@dataclass(frozen=True)
class Manifest:
    """Immutable, authorized-network-readable scope and capsule commitment."""

    skill_id: str
    version: int
    creator: str
    record_writer: str
    family: str
    scopes: tuple[str, ...]
    prerequisites: tuple[str, ...]
    required_actions: tuple[str, ...]
    dependencies: tuple[Dependency, ...]
    payload_hash: str
    sanitized: bool
    reuse_rights: str
    rollback: str
    limits: str
    components: tuple[Dependency, ...] = ()
    protected_evaluation_material: bool = False

    @property
    def hash(self) -> str:
        return digest("manifest", asdict(self))


@dataclass(frozen=True)
class Evidence:
    """A bounded claim, replay identity and observations; truth is not inferred from hashes."""

    manifest_hash: str
    policy_hash: str
    observed_at: int
    expires_at: int
    cases: int
    failed_cases: int
    benefit: float
    replay_hash: str
    observation_hash: str
    scope: tuple[str, ...]
    source_kind: str
    rights_check: bool

    def __post_init__(self) -> None:
        for value in (self.observed_at, self.expires_at, self.cases, self.failed_cases):
            if type(value) is not int or value < 0:
                raise GraphError("evidence counts and times must be nonnegative integers")
        if self.expires_at <= self.observed_at or self.failed_cases > self.cases:
            raise GraphError("evidence interval or case counts are inconsistent")
        if not isinstance(self.benefit, (float, int)) or not math.isfinite(self.benefit):
            raise GraphError("benefit must be finite")
        for value in (self.manifest_hash, self.policy_hash, self.replay_hash, self.observation_hash):
            if not isinstance(value, str) or HEX_DIGEST.fullmatch(value) is None:
                raise GraphError("evidence identities must be exact SHA256 digests")

    @property
    def hash(self) -> str:
        return digest("evidence", asdict(self))


@dataclass(frozen=True)
class Attestation:
    """Exact signed validation statement, distinct from an informal reviewer label."""

    skill_id: str
    manifest_hash: str
    evidence_hash: str
    policy_hash: str
    alpha_hash: str
    validator: str
    verdict: str
    issued_at: int
    expires_at: int
    signature: str = ""

    def statement(self) -> dict[str, Any]:
        """Return the exact typed payload covered by the Ed25519 fixture signature."""
        value = asdict(self)
        del value["signature"]
        return {"domain": SCHEMA + ".attestation", **value}


@dataclass(frozen=True)
class ReusePermit:
    """A one-use local authorization checked again immediately before consumption."""

    skill_id: str
    actor: str
    manifest_hash: str
    policy_hash: str
    evidence_hash: str
    alpha_hash: str
    beta_id: str
    epoch_root: str
    scope: str
    tools: tuple[str, ...]


@dataclass(frozen=True)
class FailureMemory:
    """A sanitized failure report, never a positive skill or admission record.

    The report's hash establishes its identity, not its truth. Model, tool and
    environment context are bound through the exact Beta configuration hash.
    Protected evaluator cases and scorer internals must stay outside this store.
    """

    failure_id: str
    creator: str
    record_writer: str
    observed_at: int
    scopes: tuple[str, ...]
    failure_kind: str
    summary: str
    evidence_hash: str
    beta_id: str
    beta_hash: str
    policy_hash: str
    source_kind: str
    sanitized: bool
    rights_check: bool
    protected_evaluation_material: bool = False

    @property
    def hash(self) -> str:
        return digest("failure-memory", asdict(self))


@dataclass
class _Record:
    manifest: Manifest
    nonce: bytes
    ciphertext: bytes
    status: str = "candidate"
    canonical: bool = False
    evidence: Evidence | None = None
    alpha: AlphaAssessment | None = None
    alpha_context_hash: str | None = None
    comparator_snapshot: tuple[str, ...] = ()
    component_evidence: dict[str, str] = field(default_factory=dict)
    attestations: dict[str, Attestation] = field(default_factory=dict)
    admission: dict[str, Any] | None = None


class ResearchGraph:
    """Enforce the research lifecycle without providing a production service."""

    def __init__(
        self, directory: FixtureDirectory, policy: Policy | None = None, beta: BetaBaseline | None = None,
    ) -> None:
        self.directory = directory
        self._policy = policy or Policy()
        self._policy_versions = {self._policy.version}
        self._beta = beta or fixture_beta()
        self._beta_versions = {self._beta.beta_id}
        self._now = 0
        self._records: dict[str, _Record] = {}
        self._failures: dict[str, FailureMemory] = {}
        self._withdrawn_failures: set[str] = set()
        self._events: list[dict[str, Any]] = []
        self._epochs: list[dict[str, Any]] = []
        self._assessment_history: list[dict[str, Any]] = []
        self._permits: dict[int, ReusePermit] = {}
        self._lock = threading.RLock()
        self._commit("initialize", "fixture-harness", "", 0)

    @property
    def policy(self) -> Policy:
        """Expose the immutable current policy without a writable public slot."""
        return self._policy

    @property
    def beta(self) -> BetaBaseline:
        """Expose the immutable current competent-comparator specification."""
        return self._beta

    def _observe_time(self, now: int) -> None:
        if type(now) is not int or now < self._now:
            raise GraphError("the research clock cannot move backward")
        self._now = now

    def _record(self, skill_id: str) -> _Record:
        if skill_id not in self._records:
            raise GraphError("unknown skill")
        return self._records[skill_id]

    def _owner(self, actor: Session, record: _Record) -> None:
        self.directory.require(actor, "record.write")
        if record.manifest.record_writer != actor.name:
            raise GraphError("record belongs to a different direct-agent owner")

    def _live_version(self, record: _Record) -> None:
        if record.status in TERMINAL:
            raise GraphError("terminal skill versions cannot re-enter the lifecycle")

    def _state_leaf(self, skill_id: str, record: _Record) -> str:
        return digest("skill-state", {
            "skill_id": skill_id, "manifest": record.manifest.hash,
            "capsule": hashlib.sha256(record.ciphertext).hexdigest(), "status": record.status,
            "canonical": record.canonical, "evidence": record.evidence.hash if record.evidence else None,
            "alpha": record.alpha_context_hash,
            "attestations": sorted(digest("attestation", asdict(a)) for a in record.attestations.values()),
            "admission": record.admission,
        })

    def _commit(self, action: str, actor: str, skill_id: str, now: int) -> None:
        event = {"sequence": len(self._events), "action": action, "actor": actor,
                 "skill_id": skill_id, "time": now, "policy_hash": self.policy.hash,
                 "beta_id": self.beta.beta_id, "beta_hash": self.beta.hash}
        self._events.append(event)
        roots = {
            "skills": merkle_root([self._state_leaf(k, r) for k, r in self._records.items()]),
            "events": merkle_root([digest("event", e) for e in self._events]),
            "policy": merkle_root([self.policy.hash]),
            "beta": merkle_root([self.beta.hash]),
            "failure_memory": merkle_root([
                digest("failure-memory-state", {"record": record.hash, "withdrawn": key in self._withdrawn_failures})
                for key, record in self._failures.items()
            ]),
        }
        epoch = {"schema": SCHEMA, "tree_policy": TREE_POLICY, "epoch": len(self._epochs),
                 "previous_root": self._epochs[-1]["root"] if self._epochs else None,
                 "roots": roots, "policy_hash": self.policy.hash, "beta_hash": self.beta.hash,
                 "enforcement": "simulated-local"}
        epoch["root"] = digest("graph-epoch", epoch)
        self._epochs.append(epoch)

    def create_candidate(
        self, actor: Session, skill_id: str, payload: bytes, family: str, scopes: tuple[str, ...],
        *, prerequisites: tuple[str, ...] = (), required_actions: tuple[str, ...] = ("execute.synthetic",),
        dependencies: tuple[Dependency, ...] = (), sanitized: bool = True,
        components: tuple[Dependency, ...] = (),
        protected_evaluation_material: bool = False,
        reuse_rights: str = "all-authenticated-direct-agents", rollback: str = "abstain and reconstruct",
        limits: str = "public or synthetic finite-domain research only", version: int = 1, now: int = 0,
    ) -> Manifest:
        """Create one immutable owned candidate; creation grants no reuse authority."""
        with self._lock:
            self.directory.require(actor, "record.write")
            self._observe_time(now)
            if (skill_id in self._records or skill_id in self._failures or not skill_id or version < 1
                    or not payload or not family or not scopes):
                raise GraphError("invalid or duplicate candidate identity")
            if type(protected_evaluation_material) is not bool or protected_evaluation_material:
                raise GraphError("protected evaluation testcases/scorer internals cannot enter shared capsules")
            pins = tuple(dependencies) + tuple(components)
            if len({d.skill_id for d in pins}) != len(pins) or any(d.skill_id == skill_id for d in pins):
                raise GraphError("invalid dependencies")
            for dependency in pins:
                if self._record(dependency.skill_id).manifest.hash != dependency.manifest_hash:
                    raise GraphError("dependency pin mismatch")
            if any(self._record(c.skill_id).manifest.components for c in components):
                raise GraphError("nested candidate-only bundles must first be admitted as dependencies")
            manifest = Manifest(skill_id, version, actor.name, actor.name, family, tuple(scopes),
                                tuple(prerequisites), tuple(required_actions), tuple(dependencies),
                                hashlib.sha256(payload).hexdigest(), sanitized, reuse_rights, rollback, limits,
                                tuple(components), protected_evaluation_material)
            nonce = hashlib.sha256(canonical(["FIXTURE-NONCE", manifest.hash])).digest()[:12]
            ciphertext = AESGCM(FIXTURE_AES_KEY).encrypt(nonce, payload, manifest.hash.encode())
            self._records[skill_id] = _Record(manifest, nonce, ciphertext)
            self._commit("candidate", actor.name, skill_id, now)
            return manifest

    def record_failure(
        self, actor: Session, failure_id: str, scopes: tuple[str, ...], failure_kind: str,
        summary: str, evidence_hash: str, now: int, *, source_kind: str = "simulation-fixture",
        sanitized: bool = True, rights_check: bool = True, protected_evaluation_material: bool = False,
    ) -> FailureMemory:
        """Retain a shareable negative report without entering the positive skill graph.

        Sanitization/rights/protected-material flags are enforced declarations,
        not automatic semantic inspection or proof of lawful disclosure.
        """
        with self._lock:
            self.directory.require(actor, "record.write")
            self._observe_time(now)
            if not failure_id or failure_id in self._failures or failure_id in self._records:
                raise GraphError("failure identities must be unique and disjoint from skills")
            if (not isinstance(scopes, tuple) or not scopes or not all(isinstance(s, str) and s for s in scopes)
                    or not isinstance(failure_kind, str) or not failure_kind
                    or not isinstance(summary, str) or not summary):
                raise GraphError("failure scope, category and sanitized summary are required")
            if (not isinstance(evidence_hash, str) or HEX_DIGEST.fullmatch(evidence_hash) is None
                    or source_kind not in {"actual-local-experiment", "simulation-fixture"}):
                raise GraphError("failure evidence identity and honest provenance are required")
            if (sanitized is not True or rights_check is not True
                    or protected_evaluation_material is not False):
                raise GraphError("failure memory excludes restricted or protected evaluation contents")
            memory = FailureMemory(failure_id, actor.name, actor.name, now, scopes, failure_kind, summary,
                                   evidence_hash, self.beta.beta_id, self.beta.hash, self.policy.hash,
                                   source_kind, sanitized, rights_check, protected_evaluation_material)
            self._failures[failure_id] = memory
            self._commit("failure-recorded", actor.name, failure_id, now)
            return memory

    def read_failures(self, actor: Session, now: int, scope: str | None = None) -> tuple[dict[str, Any], ...]:
        """Expose separate current/historical negative memory to every member.

        Reading a past failure grants no capability, execution permit, positive
        Alpha status, canonical promotion or automatic exclusion of a mission.
        """
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            return tuple(copy.deepcopy({
                **asdict(memory), "record_hash": memory.hash, "kind": "failure-memory",
                "positive_alpha": False, "eligible_for_skill_selection": False,
                "context_current": memory.beta_hash == self.beta.hash and memory.policy_hash == self.policy.hash,
            }) for key, memory in self._failures.items()
                if key not in self._withdrawn_failures and (scope is None or scope in memory.scopes))

    def withdraw_failure(self, actor: Session, failure_id: str, reason: str, now: int) -> None:
        """Withdraw a report from future reading while preserving its committed history."""
        with self._lock:
            self.directory.require(actor, "record.write")
            self._observe_time(now)
            memory = self._failures.get(failure_id)
            if memory is None or memory.record_writer != actor.name or not reason:
                raise GraphError("only the failure record owner can withdraw a described report")
            if failure_id in self._withdrawn_failures:
                raise GraphError("failure record already withdrawn")
            self._withdrawn_failures.add(failure_id)
            self._commit("failure-withdrawn:" + reason, actor.name, failure_id, now)

    def submit_evidence(self, actor: Session, skill_id: str, evidence: Evidence, now: int) -> None:
        """Begin or restart validation, clearing every earlier admission and attestation."""
        with self._lock:
            record = self._record(skill_id)
            self._owner(actor, record)
            self._observe_time(now)
            self._live_version(record)
            if evidence.manifest_hash != record.manifest.hash or evidence.policy_hash != self.policy.hash:
                raise GraphError("evidence is bound to another manifest or policy")
            if evidence.observed_at > now or evidence.expires_at <= evidence.observed_at:
                raise GraphError("invalid evidence times")
            if evidence.source_kind not in {"actual-local-experiment", "simulation-fixture"}:
                raise GraphError("unsupported provenance category")
            canonical(asdict(evidence))
            record.evidence = evidence
            record.status, record.canonical, record.admission = "evidenced", False, None
            record.alpha, record.alpha_context_hash = None, None
            record.comparator_snapshot, record.component_evidence = (), {}
            record.attestations.clear()
            self._commit("evidence", actor.name, skill_id, now)

    def _comparator_snapshot(self, excluded_skill: str, now: int) -> tuple[str, ...]:
        available = []
        for skill_id, record in self._records.items():
            if skill_id == excluded_skill:
                continue
            try:
                self._current(record, now)
            except GraphError:
                continue
            available.append(record.manifest.hash)
        return tuple(sorted(available))

    def _comparator_hash(self, snapshot: tuple[str, ...]) -> str:
        return digest("competent-beta-plus-available-capabilities", {"beta": self.beta.hash, "available": snapshot})

    def comparator_hash(self, actor: Session, skill_id: str, now: int) -> str:
        """Pin competent Beta plus every currently admitted available capability.

        This is an assessment-time snapshot. Admission checks it again; later
        admissions do not retroactively erase all other skills. A changed Beta
        version explicitly invalidates prior assessments throughout the graph.
        """
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            self._record(skill_id)
            return self._comparator_hash(self._comparator_snapshot(skill_id, now))

    def _alpha_binding(self, record: _Record) -> str:
        return digest("alpha-context", {
            "assessment": record.alpha.hash if record.alpha else None,
            "beta": self.beta.hash, "manifest": record.manifest.hash,
            "comparator_snapshot": record.comparator_snapshot, "component_evidence": record.component_evidence,
        })

    def assess_alpha(self, actor: Session, skill_id: str, assessment: AlphaAssessment, now: int) -> dict[str, Any]:
        """Record scoped net advantage before validation; rejected claims stay unavailable."""
        with self._lock:
            record = self._record(skill_id)
            self._owner(actor, record)
            self._observe_time(now)
            self._live_version(record)
            if record.status not in {"evidenced", "needs-alpha-reassessment", "alpha-rejected"}:
                raise GraphError("a current evidence revision must precede Alpha assessment")
            if record.evidence is None or assessment.evidence_hash != record.evidence.hash:
                raise GraphError("Alpha assessment must bind the exact evidence revision")
            if assessment.beta_id != self.beta.beta_id:
                raise GraphError("Alpha assessment uses a superseded Beta baseline")
            if set(assessment.scope) != set(record.manifest.scopes):
                raise GraphError("Alpha and manifest scope must match exactly")
            expected = sorted(d.manifest_hash for d in record.manifest.dependencies + record.manifest.components)
            if sorted(assessment.dependency_hashes) != expected:
                raise GraphError("Alpha assessment does not bind the complete bundle")
            snapshot = self._comparator_snapshot(skill_id, now)
            if assessment.comparator_capability_set_hash != self._comparator_hash(snapshot):
                raise GraphError("Alpha comparator omits or changes currently available capabilities")
            components = {}
            for pin in record.manifest.components:
                child = self._record(pin.skill_id)
                if child.manifest.hash != pin.manifest_hash or child.evidence is None or child.status in TERMINAL:
                    raise GraphError("bundle component requires current pinned evidence")
                components[pin.skill_id] = child.evidence.hash
            decision = evaluate_alpha(assessment)
            duplicates = any(
                other.manifest.hash in snapshot and other.manifest.payload_hash == record.manifest.payload_hash
                and set(record.manifest.scopes) <= set(other.manifest.scopes)
                for other in self._records.values()
            )
            accepted = decision.accepted and not duplicates
            record.alpha = assessment
            record.comparator_snapshot, record.component_evidence = snapshot, components
            record.alpha_context_hash = self._alpha_binding(record)
            record.status = "alpha-assessed" if accepted else "alpha-rejected"
            record.canonical, record.admission = False, None
            record.attestations.clear()
            result = {**asdict(decision), "accepted": accepted,
                      "reason": "duplicate-current-capsule" if duplicates else decision.reason,
                      "skill_id": skill_id, "time": now, "alpha_context_hash": record.alpha_context_hash,
                      "assessment": asdict(assessment)}
            self._assessment_history.append(copy.deepcopy(result))
            self._commit("alpha-assessed" if accepted else "alpha-rejected", actor.name, skill_id, now)
            return copy.deepcopy(result)

    def _alpha_gate(self, record: _Record, now: int, *, fresh_comparator: bool = False) -> None:
        assessment = record.alpha
        if assessment is None or assessment.beta_id != self.beta.beta_id:
            raise GraphError("current versioned Beta Alpha assessment required")
        if record.evidence is None or assessment.evidence_hash != record.evidence.hash:
            raise GraphError("Alpha evidence binding changed")
        if record.alpha_context_hash != self._alpha_binding(record) or not evaluate_alpha(assessment).accepted:
            raise GraphError("Alpha context changed or net advantage is not positive")
        if fresh_comparator and assessment.comparator_capability_set_hash != self._comparator_hash(
            self._comparator_snapshot(record.manifest.skill_id, now),
        ):
            raise GraphError("available comparator capabilities changed before admission")

    def sign_attestation(
        self, actor: Session, skill_id: str, verdict: str, now: int, expires_at: int,
    ) -> Attestation:
        """Sign an exact statement using a publicly known validator fixture key."""
        with self._lock:
            self.directory.require(actor, "graph.validate")
            self._observe_time(now)
            record = self._record(skill_id)
            self._live_version(record)
            if record.status not in {"alpha-assessed", "validated"} or actor.name == record.manifest.creator:
                raise GraphError("positive Alpha assessment required and self-validation excluded")
            self._alpha_gate(record, now, fresh_comparator=True)
            if verdict not in {"supported", "blocked", "needs-evidence"} or expires_at <= now:
                raise GraphError("invalid attestation")
            unsigned = Attestation(skill_id, record.manifest.hash, record.evidence.hash, self.policy.hash,
                                   record.alpha_context_hash,
                                   actor.name, verdict, now, expires_at)
            signature = self.directory.fixture_key(actor.name).sign(canonical(unsigned.statement())).hex()
            return Attestation(**{**asdict(unsigned), "signature": signature})

    def _verify_attestation(self, record: _Record, attestation: Attestation, now: int) -> None:
        evidence = record.evidence
        if evidence is None:
            raise GraphError("no evidence")
        if not self.directory.eligible(attestation.validator, "graph.validate"):
            raise GraphError("validator no longer eligible")
        if attestation.validator == record.manifest.creator:
            raise GraphError("creator cannot validate own skill")
        if (attestation.skill_id != record.manifest.skill_id or attestation.manifest_hash != record.manifest.hash
                or attestation.evidence_hash != evidence.hash or attestation.policy_hash != self.policy.hash
                or attestation.alpha_hash != record.alpha_context_hash):
            raise GraphError("attestation binding mismatch")
        if not (attestation.issued_at <= now < attestation.expires_at):
            raise GraphError("attestation not current")
        if now - attestation.issued_at > self.policy.max_attestation_age:
            raise GraphError("attestation exceeds policy age")
        try:
            self.directory.fixture_key(attestation.validator).public_key().verify(
                bytes.fromhex(attestation.signature), canonical(attestation.statement()),
            )
        except (InvalidSignature, ValueError) as error:
            raise GraphError("invalid attestation signature") from error

    def attach_attestation(self, actor: Session, attestation: Attestation, now: int) -> None:
        """Only the authenticated signer may submit its current signed statement."""
        with self._lock:
            self.directory.require(actor, "graph.validate")
            self._observe_time(now)
            if attestation.validator != actor.name:
                raise GraphError("attestation submitter differs from signer")
            record = self._record(attestation.skill_id)
            self._live_version(record)
            if record.status not in {"alpha-assessed", "validated"}:
                raise GraphError("positive Alpha revision must be open for validation")
            self._verify_attestation(record, attestation, now)
            record.attestations[actor.name] = attestation
            record.status = "alpha-assessed"
            self._commit("attestation", actor.name, attestation.skill_id, now)

    def _evidence_content_gate(self, record: _Record, now: int, *, require_benefit: bool = True) -> None:
        evidence, manifest = record.evidence, record.manifest
        if evidence is None or evidence.policy_hash != self.policy.hash or evidence.manifest_hash != manifest.hash:
            raise GraphError("current policy-bound evidence required")
        if not (evidence.observed_at <= now < evidence.expires_at):
            raise GraphError("evidence expired or not yet valid")
        if now - evidence.observed_at > self.policy.max_evidence_age:
            raise GraphError("evidence stale under current policy")
        if evidence.cases < self.policy.min_cases or evidence.failed_cases != 0:
            raise GraphError("executable evidence requirements failed")
        if require_benefit and self.policy.require_positive_benefit and not evidence.benefit > 0:
            raise GraphError("no bounded positive recipient benefit recorded")
        if not (evidence.replay_hash and evidence.observation_hash and set(manifest.scopes) <= set(evidence.scope)):
            raise GraphError("missing replay or scope evidence")
        if not (manifest.sanitized and evidence.rights_check and manifest.rollback and manifest.limits):
            raise GraphError("sanitization, rights, limits or rollback absent")
        if manifest.protected_evaluation_material:
            raise GraphError("protected evaluation contents cannot be validated for network sharing")
        if manifest.reuse_rights != "all-authenticated-direct-agents":
            raise GraphError("shareable skills must be available across the entire authenticated network")

    def _evidence_gate(self, record: _Record, now: int) -> None:
        self._evidence_content_gate(record, now)
        self._alpha_gate(record, now)
        for attestation in record.attestations.values():
            self._verify_attestation(record, attestation, now)
            if attestation.verdict != "supported":
                raise GraphError("unresolved adverse attestation")
        if len(record.attestations) < self.policy.quorum:
            raise GraphError("eligible signed validator quorum absent")

    def _dependency_gate(self, record: _Record, now: int, visiting: set[str]) -> None:
        for dependency in record.manifest.dependencies:
            child = self._record(dependency.skill_id)
            if child.manifest.hash != dependency.manifest_hash:
                raise GraphError("dependency version changed")
            self._current(child, now, visiting)
        for component in record.manifest.components:
            child = self._record(component.skill_id)
            if child.manifest.hash != component.manifest_hash or child.status in TERMINAL:
                raise GraphError("bundle component retired, revoked or changed")
            if child.evidence is None or record.component_evidence.get(component.skill_id) != child.evidence.hash:
                raise GraphError("bundle component evidence changed; reassess the bundle")
            self._capsule(child)
            self._evidence_content_gate(child, now, require_benefit=False)
            self._dependency_gate(child, now, visiting | {component.skill_id})

    def _capsule(self, record: _Record) -> bytes:
        try:
            payload = AESGCM(FIXTURE_AES_KEY).decrypt(record.nonce, record.ciphertext, record.manifest.hash.encode())
        except InvalidTag as error:
            raise GraphError("capsule authentication failed") from error
        if hashlib.sha256(payload).hexdigest() != record.manifest.payload_hash:
            raise GraphError("capsule content hash mismatch")
        return payload

    def _current(self, record: _Record, now: int, visiting: set[str] | None = None) -> None:
        visiting = set() if visiting is None else set(visiting)
        skill_id = record.manifest.skill_id
        if skill_id in visiting:
            raise GraphError("cyclic dependency")
        visiting.add(skill_id)
        if record.status != "admitted" or record.admission is None:
            raise GraphError("skill has no current admission")
        if record.admission["policy_hash"] != self.policy.hash:
            raise GraphError("policy changed; revalidation required")
        if record.evidence is None or record.admission["evidence_hash"] != record.evidence.hash:
            raise GraphError("admission evidence changed")
        if record.admission["manifest_hash"] != record.manifest.hash:
            raise GraphError("admitted manifest changed")
        if (record.admission["alpha_hash"] != record.alpha_context_hash
                or record.admission["beta_id"] != self.beta.beta_id):
            raise GraphError("admitted Alpha assessment or Beta baseline changed")
        self._capsule(record)
        self._evidence_gate(record, now)
        self._dependency_gate(record, now, visiting)

    def validate(self, actor: Session, skill_id: str, now: int) -> None:
        """Evaluate the mechanical gate; validator agreement is not independent truth."""
        with self._lock:
            self.directory.require(actor, "graph.validate")
            self._observe_time(now)
            record = self._record(skill_id)
            self._live_version(record)
            if record.status != "alpha-assessed":
                raise GraphError("only a positive Alpha-assessed revision may validate")
            self._alpha_gate(record, now, fresh_comparator=True)
            self._evidence_gate(record, now)
            self._dependency_gate(record, now, {skill_id})
            record.status = "validated"
            self._commit("validated", actor.name, skill_id, now)

    def admit(self, actor: Session, skill_id: str, now: int) -> None:
        """Grant scoped network availability only after a distinct validated state."""
        with self._lock:
            self.directory.require(actor, "graph.admit")
            self._observe_time(now)
            record = self._record(skill_id)
            self._live_version(record)
            if record.status != "validated":
                raise GraphError("admission cannot bypass validation")
            if actor.name in {record.manifest.creator, record.manifest.record_writer} or actor.name in record.attestations:
                raise GraphError("the producer, evidence attestors and admission actor must be distinct")
            self._alpha_gate(record, now, fresh_comparator=True)
            self._evidence_gate(record, now)
            self._dependency_gate(record, now, {skill_id})
            record.admission = {"actor": actor.name, "policy_hash": self.policy.hash,
                                "manifest_hash": record.manifest.hash, "evidence_hash": record.evidence.hash,
                                "alpha_hash": record.alpha_context_hash, "beta_id": self.beta.beta_id,
                                "admitted_at": now, "judgment_source": "simulation-fixture-policy"}
            record.status = "admitted"
            self._commit("admitted", actor.name, skill_id, now)

    def promote_canonical(self, actor: Session, skill_id: str, now: int) -> None:
        """Canonical presentation cannot create or bypass capability admission."""
        with self._lock:
            self.directory.require(actor, "graph.admit")
            self._observe_time(now)
            record = self._record(skill_id)
            self._current(record, now)
            if any(r.canonical and r.status == "admitted" and r.manifest.payload_hash == record.manifest.payload_hash
                   for k, r in self._records.items() if k != skill_id):
                raise GraphError("duplicate canonical payload")
            record.canonical = True
            self._commit("canonical", actor.name, skill_id, now)

    def discover(self, actor: Session, now: int) -> tuple[dict[str, Any], ...]:
        """Every current member sees every currently usable admitted capability."""
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            found = []
            for record in self._records.values():
                try:
                    self._current(record, now)
                except GraphError:
                    continue
                found.append({**asdict(record.manifest), "manifest_hash": record.manifest.hash,
                              "status": record.status, "canonical": record.canonical,
                              "policy_hash": self.policy.hash, "evidence_hash": record.evidence.hash,
                              "alpha_hash": record.alpha_context_hash, "beta_id": self.beta.beta_id,
                              "alpha_assessment": asdict(record.alpha),
                              "alpha_decision": asdict(evaluate_alpha(record.alpha))})
            return tuple(copy.deepcopy(found))

    def retrieve(self, actor: Session, skill_id: str, now: int) -> bytes:
        """Authorize full-network capsule inspection/export independently of action permission."""
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            record = self._record(skill_id)
            self._current(record, now)
            return self._capsule(record)

    def retrieve_component(self, actor: Session, bundle_id: str, component_id: str, now: int) -> bytes:
        """All members may inspect bundle-only components under the admitted bundle.

        The component remains unavailable as an independently reusable Alpha skill;
        it has no separate standalone economic-advantage claim or admission.
        """
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            bundle = self._record(bundle_id)
            self._current(bundle, now)
            if component_id not in {component.skill_id for component in bundle.manifest.components}:
                raise GraphError("component is not part of this admitted bundle")
            return self._capsule(self._record(component_id))

    @staticmethod
    def _scope_tools(record: _Record, scope: str, tools: tuple[str, ...]) -> None:
        if scope not in record.manifest.scopes or not set(record.manifest.prerequisites) <= set(tools):
            raise GraphError("scope or prerequisites not satisfied")

    def _applicable(self, record: _Record, scope: str, tools: tuple[str, ...], now: int) -> None:
        self._current(record, now)
        self._scope_tools(record, scope, tools)
        for dependency in record.manifest.dependencies:
            child = self._record(dependency.skill_id)
            if not set(child.manifest.prerequisites) <= set(tools):
                raise GraphError("dependency prerequisites not satisfied")
            self._applicable(child, scope, tools, now)
        for component in record.manifest.components:
            child = self._record(component.skill_id)
            self._scope_tools(child, scope, tools)
            for dependency in child.manifest.dependencies:
                self._applicable(self._record(dependency.skill_id), scope, tools, now)

    def select(self, actor: Session, family: str, scope: str, tools: tuple[str, ...], now: int) -> tuple[str, ...]:
        """Select applicable active records without assuming use is mandatory."""
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            selected = []
            for skill_id, record in self._records.items():
                if record.manifest.family != family:
                    continue
                try:
                    self._applicable(record, scope, tools, now)
                except GraphError:
                    continue
                selected.append(skill_id)
            return tuple(selected)

    def authorize_reuse(
        self, actor: Session, skill_id: str, scope: str, tools: tuple[str, ...], now: int,
    ) -> ReusePermit:
        """Check current scope/dependencies/status plus separate operational permissions."""
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            record = self._record(skill_id)
            self._applicable(record, scope, tools, now)
            pending = [record]
            while pending:
                child = pending.pop()
                for action in child.manifest.required_actions:
                    self.directory.require(actor, action)
                pending.extend(self._record(d.skill_id) for d in child.manifest.dependencies + child.manifest.components)
            permit = ReusePermit(skill_id, actor.name, record.manifest.hash, self.policy.hash,
                                 record.evidence.hash, record.alpha_context_hash, self.beta.beta_id,
                                 self._epochs[-1]["root"], scope, tuple(tools))
            self._permits[id(permit)] = permit
            return permit

    def consume_reuse(self, actor: Session, permit: ReusePermit, now: int) -> dict[str, Any]:
        """Recheck immediately and consume once; return a receipt without executing code."""
        with self._lock:
            self.directory.require(actor)
            self._observe_time(now)
            if self._permits.get(id(permit)) is not permit or actor.name != permit.actor:
                raise GraphError("unknown, consumed or foreign reuse permit")
            if permit.epoch_root != self._epochs[-1]["root"] or permit.policy_hash != self.policy.hash:
                raise GraphError("graph changed after authorization")
            self._applicable(self._record(permit.skill_id), permit.scope, permit.tools, now)
            fresh = self.authorize_reuse(actor, permit.skill_id, permit.scope, permit.tools, now)
            self._permits.pop(id(fresh))
            self._permits.pop(id(permit))
            receipt = {"skill_id": permit.skill_id, "actor": actor.name, "policy_hash": permit.policy_hash,
                       "manifest_hash": permit.manifest_hash, "evidence_hash": permit.evidence_hash,
                       "alpha_hash": permit.alpha_hash, "beta_id": permit.beta_id,
                       "checked_epoch_root": permit.epoch_root, "time": now,
                       "operation": "simulated-authorized-reuse", "code_executed": False}
            self._commit("reuse-authorized", actor.name, permit.skill_id, now)
            return receipt

    def terminate(self, actor: Session, skill_id: str, status: str, reason: str, now: int) -> None:
        """Retire or revoke an owned version permanently without deleting its history."""
        with self._lock:
            record = self._record(skill_id)
            self._owner(actor, record)
            self._observe_time(now)
            self._live_version(record)
            if status not in {"retired", "revoked"} or not reason:
                raise GraphError("invalid termination")
            record.status, record.canonical, record.admission = status, False, None
            self._commit(status + ":" + reason, actor.name, skill_id, now)

    def supersede(self, actor: Session, old_skill_id: str, new_skill_id: str, now: int) -> None:
        """Require a separately admitted replacement; never relabel an old version."""
        with self._lock:
            old, new = self._record(old_skill_id), self._record(new_skill_id)
            self._owner(actor, old)
            self._owner(actor, new)
            self._observe_time(now)
            self._live_version(old)
            self._current(new, now)
            if old_skill_id == new_skill_id or new.manifest.version <= old.manifest.version:
                raise GraphError("replacement must have a new identity and later version")
            if new.manifest.family != old.manifest.family:
                raise GraphError("replacement family differs")
            pending = list(new.manifest.dependencies + new.manifest.components)
            while pending:
                dependency = pending.pop()
                if dependency.skill_id == old_skill_id:
                    raise GraphError("replacement still depends on the version being superseded")
                child = self._record(dependency.skill_id).manifest
                pending.extend(child.dependencies + child.components)
            old.status, old.canonical, old.admission = "superseded", False, None
            self._commit("superseded-by:" + new_skill_id, actor.name, old_skill_id, now)

    def set_policy(self, actor: Session, policy: Policy, now: int) -> None:
        """Versioned policy changes invalidate previous reuse until fresh validation."""
        with self._lock:
            self.directory.require(actor, "graph.policy")
            self._observe_time(now)
            if policy.version in self._policy_versions or policy.hash == self.policy.hash:
                raise GraphError("policy updates require a distinct version and content")
            self._policy = policy
            self._policy_versions.add(policy.version)
            self._commit("policy-changed", actor.name, "", now)

    def set_beta_baseline(self, actor: Session, beta: BetaBaseline, now: int) -> None:
        """Invalidate earlier Alpha assessments when competent Beta changes.

        Historical assessments remain inspectable but cannot grant selection,
        validation, canonical status or reuse. Fresh assessment and eligible
        attestations are mandatory; an owner may instead retire the skill.
        """
        with self._lock:
            self.directory.require(actor, "graph.policy")
            self._observe_time(now)
            if beta.beta_id in self._beta_versions or beta.hash == self.beta.hash:
                raise GraphError("Beta updates require a distinct version and content")
            self._beta, self._beta_versions = beta, self._beta_versions | {beta.beta_id}
            for record in self._records.values():
                if record.status in TERMINAL or record.alpha is None:
                    continue
                record.status, record.canonical, record.admission = "needs-alpha-reassessment", False, None
                record.attestations.clear()
            self._commit("beta-baseline-changed", actor.name, "", now)

    def assessment_history(self, actor: Session) -> tuple[dict[str, Any], ...]:
        """Retain old assessment evidence without letting it influence selection."""
        with self._lock:
            self.directory.require(actor)
            return tuple(copy.deepcopy(self._assessment_history))

    def public_commitment(self) -> dict[str, Any]:
        """Expose only typed roots and schema metadata, never a private capsule."""
        with self._lock:
            return copy.deepcopy(self._epochs[-1])

    def inclusion(self, actor: Session, skill_id: str) -> dict[str, Any]:
        """Provide a member an exact state inclusion path; it is not an admission token."""
        with self._lock:
            self.directory.require(actor)
            leaf = self._state_leaf(skill_id, self._record(skill_id))
            leaves = [self._state_leaf(k, r) for k, r in self._records.items()]
            return {"leaf": leaf, "proof": merkle_proof(leaves, leaf),
                    "root": self._epochs[-1]["roots"]["skills"], "epoch_root": self._epochs[-1]["root"]}

    def history(self, actor: Session) -> tuple[dict[str, Any], ...]:
        """Expose an immutable copy of provenance to authenticated members."""
        self.directory.require(actor)
        return tuple(copy.deepcopy(self._events))


def fixture_beta(version: str = "competent-beta-fixture-v1") -> BetaBaseline:
    """Declare synthetic competent-comparator inputs without claiming live model use."""
    return BetaBaseline(
        version, digest("fixture-beta-configuration", {
            "version": version, "models": "synthetic-frontier-role-config-v1",
            "tools": ("python-3.12", "finite-checkers-v1"), "environment": "local-research-fixture-v1",
            "prior": "frontier-tools-and-experience",
        }),
        "PUBLIC fixture: bound models, tools, environment, adequate context and prior capabilities; no live model trial",
        "simulation-fixture",
    )


def fixture_graph() -> tuple[ResearchGraph, dict[str, Session]]:
    """Construct explicit research identities with different operational permissions."""
    roles = {
        "inventor": {"record.write", "execute.synthetic"},
        "validator-a": {"graph.validate", "execute.synthetic"},
        "validator-b": {"graph.validate", "execute.synthetic"},
        "admitter": {"graph.admit", "graph.policy"},
        "recipient-a": {"execute.synthetic"},
        "recipient-b": set(),
    }
    principals = tuple(Principal(name + ".agent.agi.eth", "fixture-wallet:" + name, frozenset(perms))
                       for name, perms in roles.items())
    directory = FixtureDirectory(principals)
    sessions = {p.name.split(".")[0]: directory.open_session(p.name, p.fixture_wallet) for p in principals}
    return ResearchGraph(directory), sessions


def fixture_evidence(manifest: Manifest, policy: Policy, now: int = 1) -> Evidence:
    """Return synthetic gate inputs, never empirical capability measurements."""
    return Evidence(manifest.hash, policy.hash, now, now + 12, 16, 0, 1.0,
                    digest("fixture-replay", manifest.skill_id), digest("fixture-observation", manifest.skill_id),
                    manifest.scopes, "simulation-fixture", True)


def fixture_alpha(graph: ResearchGraph, actor: Session, manifest: Manifest, now: int = 1) -> AlphaAssessment:
    """Return explicit synthetic paired-gain/cost inputs for lifecycle tests only."""
    evidence = graph._record(manifest.skill_id).evidence
    if evidence is None:
        raise GraphError("fixture evidence must precede fixture Alpha assessment")
    return AlphaAssessment(
        beta_id=graph.beta.beta_id, comparator_capability_set_hash=graph.comparator_hash(actor, manifest.skill_id, now),
        scope=manifest.scopes, paired_gains=(90.0, 110.0), planned_reuse=10,
        costs=AlphaCosts(acquisition=25, construction=100, validation=25, integration=20,
                         operating=10, risk=10, maintenance=10, migration=10, distribution=10),
        uncertainty_margin_per_use=20, source_kind="simulation-fixture", protocol_id="synthetic-paired-fixture-v1",
        evidence_hash=evidence.hash,
        dependency_hashes=tuple(sorted(d.manifest_hash for d in manifest.dependencies + manifest.components)),
    )


def run_graph_demo() -> dict[str, Any]:
    """Exercise admission, full-network availability, action separation and revocation."""
    graph, actors = fixture_graph()
    manifest = graph.create_candidate(actors["inventor"], "deviation-witness-v1", b"synthetic deviation-check capsule",
                                      "coordination-mechanisms", ("finite-quasilinear-types",),
                                      prerequisites=("python-3.12",))
    blocked = []
    try:
        graph.promote_canonical(actors["admitter"], manifest.skill_id, 0)
    except GraphError:
        blocked.append("canonical-before-admission")
    graph.submit_evidence(actors["inventor"], manifest.skill_id, fixture_evidence(manifest, graph.policy), 1)
    alpha_result = graph.assess_alpha(actors["inventor"], manifest.skill_id,
                                     fixture_alpha(graph, actors["inventor"], manifest, 1), 1)
    for validator in ("validator-a", "validator-b"):
        attestation = graph.sign_attestation(actors[validator], manifest.skill_id, "supported", 1, 9)
        graph.attach_attestation(actors[validator], attestation, 1)
    graph.validate(actors["validator-a"], manifest.skill_id, 1)
    graph.admit(actors["admitter"], manifest.skill_id, 1)
    graph.promote_canonical(actors["admitter"], manifest.skill_id, 1)
    availability = {name: [r["skill_id"] for r in graph.discover(actor, 2)] for name, actor in actors.items()}
    exported = graph.retrieve(actors["recipient-b"], manifest.skill_id, 2)
    try:
        graph.authorize_reuse(actors["recipient-b"], manifest.skill_id, "finite-quasilinear-types", ("python-3.12",), 2)
    except GraphError:
        blocked.append("execution-without-operational-permission")
    costly = graph.create_candidate(actors["inventor"], "costly-novel-candidate", b"different synthetic invention",
                                   "coordination-mechanisms", manifest.scopes, now=2)
    graph.submit_evidence(actors["inventor"], costly.skill_id, fixture_evidence(costly, graph.policy, 2), 2)
    negative = replace(fixture_alpha(graph, actors["inventor"], costly, 2), costs=AlphaCosts(construction=2000))
    rejected_alpha = graph.assess_alpha(actors["inventor"], costly.skill_id, negative, 2)
    failure = graph.record_failure(
        actors["inventor"], "failure-costly-novel-candidate", manifest.scopes, "alpha-rejection",
        "Declared lifecycle costs exceed modeled benefit; revise costs, evidence or scope before a new attempt.",
        rejected_alpha["assessment_hash"], 2,
    )
    failure_readers = {name: [row["failure_id"] for row in graph.read_failures(actor, 2)]
                       for name, actor in actors.items()}
    try:
        graph.create_candidate(actors["inventor"], "protected-evaluation-candidate", b"synthetic test placeholder",
                               "coordination-mechanisms", manifest.scopes,
                               protected_evaluation_material=True, now=2)
    except GraphError:
        blocked.append("protected-evaluation-material-sharing")
    proof = graph.inclusion(actors["recipient-a"], manifest.skill_id)
    permit = graph.authorize_reuse(
        actors["recipient-a"], manifest.skill_id, "finite-quasilinear-types", ("python-3.12",), 2,
    )
    receipt = graph.consume_reuse(actors["recipient-a"], permit, 2)
    held = graph.authorize_reuse(
        actors["recipient-a"], manifest.skill_id, "finite-quasilinear-types", ("python-3.12",), 2,
    )
    old_beta = graph.beta.beta_id
    graph.set_beta_baseline(actors["admitter"], fixture_beta("competent-beta-fixture-v2"), 3)
    unavailable_after_beta = graph.select(actors["recipient-a"], "coordination-mechanisms",
                                          "finite-quasilinear-types", ("python-3.12",), 3)
    try:
        graph.consume_reuse(actors["recipient-a"], held, 3)
    except GraphError:
        blocked.append("held-reuse-after-beta-update")
    graph.submit_evidence(actors["inventor"], manifest.skill_id, fixture_evidence(manifest, graph.policy, 3), 3)
    fresh_alpha = graph.assess_alpha(actors["inventor"], manifest.skill_id,
                                    fixture_alpha(graph, actors["inventor"], manifest, 3), 3)
    for validator in ("validator-a", "validator-b"):
        attestation = graph.sign_attestation(actors[validator], manifest.skill_id, "supported", 3, 11)
        graph.attach_attestation(actors[validator], attestation, 3)
    graph.validate(actors["validator-a"], manifest.skill_id, 3)
    graph.admit(actors["admitter"], manifest.skill_id, 3)
    held = graph.authorize_reuse(
        actors["recipient-a"], manifest.skill_id, "finite-quasilinear-types", ("python-3.12",), 3,
    )
    graph.terminate(actors["inventor"], manifest.skill_id, "revoked", "scope counterexample", 4)
    try:
        graph.consume_reuse(actors["recipient-a"], held, 4)
    except GraphError:
        blocked.append("held-reuse-after-revocation")
    try:
        graph.submit_evidence(actors["inventor"], manifest.skill_id, fixture_evidence(manifest, graph.policy, 4), 4)
    except GraphError:
        blocked.append("revoked-version-readmission")
    return {
        "schema": SCHEMA, "authentication": "simulated-fixture-directory-no-live-ENS",
        "cryptography": "actual-AES-GCM-Ed25519-SHA256-with-public-fixture-keys",
        "production_confidentiality": False, "zk_proofs": False, "onchain_transactions": 0,
        "capability_validation": "simulation-fixture-no-empirical-quality-claim",
        "alpha_assessment": alpha_result, "rejected_alpha_assessment": rejected_alpha,
        "failure_memory": {"record": asdict(failure), "available_to_members": failure_readers,
                           "after_beta_change": graph.read_failures(actors["recipient-a"], 4),
                           "eligible_for_positive_selection": False},
        "protected_evaluation_policy": {
            "testcases_and_scorer_internals_allowed": False,
            "semantic_sanitization_proved": False,
            "mechanism": "explicit declarations and rights checks; no automatic semantic classifier",
        },
        "beta_reassessment": {"old_beta_id": old_beta, "new_beta_id": graph.beta.beta_id,
                              "selected_after_update": unavailable_after_beta,
                              "old_assessments_retained": len(graph.assessment_history(actors["recipient-a"])),
                              "fresh_assessment": fresh_alpha},
        "network_availability_before_revocation": availability,
        "export_without_execution_permission_bytes": len(exported),
        "authorized_recipient_copying_prevented": False,
        "inclusion_verified": verify_inclusion(proof["leaf"], proof["proof"], proof["root"]),
        "reuse_receipt": receipt, "refused_operations": blocked,
        "selected_after_revocation": graph.select(actors["recipient-a"], "coordination-mechanisms",
                                                 "finite-quasilinear-types", ("python-3.12",), 4),
        "public_commitment": graph.public_commitment(), "history": graph.history(actors["recipient-a"]),
    }


if __name__ == "__main__":
    print(json.dumps(run_graph_demo(), indent=2, sort_keys=True))
