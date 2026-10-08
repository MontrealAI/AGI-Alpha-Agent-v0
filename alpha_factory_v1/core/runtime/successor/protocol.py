# SPDX-License-Identifier: Apache-2.0
"""Versioned SUCCESSOR Ω records and deliberately narrow cross-runtime commitments.

Version one uses exact Unicode scalar strings without normalization, printable ASCII
object keys, safe JSON integers and no floating-point values. Physical measurements
use integer units; uncertain decimal quantities use explicit decimal strings. These
commitments are new domains and do not change any historical signed bytes.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

MAX_SAFE_INT = 2**53 - 1
MAX_JSON_BYTES = 2_000_000
MAX_JSON_DEPTH = 32
MAX_JSON_NODES = 100_000


def _timestamp(value: str) -> str:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z", value):
        raise ValueError("timestamp must be an explicit UTC RFC3339 value ending in Z")
    datetime.fromisoformat(value)
    return value


Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}$")]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, Field(min_length=1, max_length=4000)]
UTC = Annotated[
    str,
    Field(pattern=r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z$"),
    AfterValidator(_timestamp),
]
SafeInt = Annotated[int, Field(ge=-MAX_SAFE_INT, le=MAX_SAFE_INT)]
Count = Annotated[int, Field(ge=0, le=MAX_SAFE_INT)]
DecimalString = Annotated[str, Field(pattern=r"^-?(?:0|[1-9][0-9]{0,29})(?:\.[0-9]{1,18})?$")]
Scalar = str | int | bool | None
Outcome = Literal["pass", "fail", "tie", "insufficient_evidence", "retain_incumbent", "retain_alternative"]
Family = Literal["constitution", "evidence", "formation", "challenge", "verification", "admission", "renewal"]


def _validate_json(value: Any, *, max_depth: int = MAX_JSON_DEPTH) -> None:
    """Bound every node before serialization, including manually constructed values."""
    pending = [(value, 0)]
    count = 0
    while pending:
        item, depth = pending.pop()
        count += 1
        if count > MAX_JSON_NODES or depth > max_depth:
            raise ValueError("JSON structure exceeds node or depth limit")
        if isinstance(item, BaseModel):
            pending.append((item.model_dump(mode="python"), depth))
            continue
        elif item is None or type(item) is bool:
            continue
        if type(item) is int:
            if abs(item) > MAX_SAFE_INT:
                raise ValueError("integer exceeds exact JavaScript-safe range")
        elif type(item) is str:
            if any(0xD800 <= ord(char) <= 0xDFFF for char in item):
                raise ValueError("surrogate Unicode is not permitted")
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is dict:
            for key, child in item.items():
                if type(key) is not str or not key or any(ord(char) < 32 or ord(char) > 126 for char in key):
                    raise ValueError("object keys must be nonempty printable ASCII strings")
                pending.append((child, depth + 1))
        else:
            raise ValueError("commitments accept only JSON values; floating-point values are forbidden")


def canonical(value: Any) -> bytes:
    """Return sorted, compact UTF-8 JSON with no float or normalization ambiguity."""
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="python")
    _validate_json(value)
    encoded = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False, default=_dump_model
    ).encode("utf-8")
    if len(encoded) > MAX_JSON_BYTES:
        raise ValueError("canonical record exceeds byte limit")
    return encoded


def _dump_model(value: BaseModel) -> dict[str, Any]:
    return value.model_dump(mode="python")


def digest(domain: str, value: Any) -> str:
    """Hash a versioned, domain-separated record; domains contain no delimiters."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,127}", domain):
        raise ValueError("invalid commitment domain")
    return hashlib.sha256(b"successor-omega/v1:" + domain.encode("ascii") + b"\0" + canonical(value)).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _integer(value: str) -> int:
    if value == "-0":
        raise ValueError("negative zero is not a canonical integer")
    if len(value) > 17:
        raise ValueError("integer exceeds exact JavaScript-safe range")
    result = int(value)
    if abs(result) > MAX_SAFE_INT:
        raise ValueError("integer exceeds exact JavaScript-safe range")
    return result


def _no_float(value: str) -> Any:
    raise ValueError("floating-point JSON numbers and nonfinite constants are forbidden")


def safe_json_loads(data: str | bytes, *, max_bytes: int = MAX_JSON_BYTES, max_depth: int = MAX_JSON_DEPTH) -> Any:
    """Reject excessive nesting before parsing and reject duplicate keys at any level."""
    if isinstance(data, bytes):
        if len(data) > max_bytes:
            raise ValueError("JSON exceeds byte limit")
        data = data.decode("utf-8", errors="strict")
    elif not isinstance(data, str):
        raise TypeError("JSON input must be UTF-8 bytes or text")
    if len(data) > max_bytes or len(data.encode("utf-8", errors="strict")) > max_bytes:
        raise ValueError("JSON exceeds byte limit")
    depth, quoted, escaped = 0, False, False
    for char in data:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > max_depth:
                raise ValueError("JSON exceeds depth limit")
        elif char in "]}":
            depth -= 1
    result = json.loads(
        data, object_pairs_hook=_pairs, parse_int=_integer, parse_float=_no_float, parse_constant=_no_float
    )
    _validate_json(result, max_depth=max_depth)
    return result


class StrictModel(BaseModel):
    """All wire records reject coercion, unknown fields and unsupported versions."""

    model_config = ConfigDict(
        extra="forbid", strict=True, frozen=True, validate_default=True, revalidate_instances="always"
    )
    schema_version: Literal[1] = 1

    @model_validator(mode="before")
    @classmethod
    def check_wire_values(cls, values: Any) -> Any:
        if isinstance(values, dict):
            if "schema_version" in values and type(values["schema_version"]) is not int:
                raise ValueError("schema_version must be an integer")
            _validate_json(values)
        return values

    @model_validator(mode="after")
    def check_commitment_values(self) -> StrictModel:
        canonical(self.model_dump(mode="python"))
        return self


ModelT = TypeVar("ModelT", bound=StrictModel)


def load_record(model: type[ModelT], data: str | bytes) -> ModelT:
    """Parse untrusted bytes before strict schema validation."""
    return model.model_validate(safe_json_loads(data))


class RehearsalRequest(StrictModel):
    """One bounded, credential-free browser/native request."""

    kind: Literal["successor-rehearsal"] = "successor-rehearsal"
    request_id: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    mission: Literal["streaming-metrics-v1"] = "streaming-metrics-v1"
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    max_candidates: int = Field(default=4, ge=2, le=12)
    formation_trials: int = Field(default=2, ge=1, le=6)
    max_events: int = Field(default=1000, ge=64, le=20000)
    language: Literal["en", "fr"] = "en"


class Validity(StrictModel):
    """Explicit beginning and end; no implicit perpetual validity."""

    valid_from: UTC
    valid_until: UTC

    @model_validator(mode="after")
    def ordered(self) -> Validity:
        if datetime.fromisoformat(self.valid_until) <= datetime.fromisoformat(self.valid_from):
            raise ValueError("valid_until must follow valid_from")
        return self


class ResourceBudget(StrictModel):
    """Controllable ceilings and unmeasured costs are explicitly different."""

    limits: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)
    units: dict[Identifier, Text] = Field(default_factory=dict, max_length=32)
    enforceable: list[Identifier] = Field(default_factory=list, max_length=32)
    unknown_costs: list[Identifier] = Field(default_factory=list, max_length=32)
    stop_loss: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)

    @model_validator(mode="after")
    def resource_keys(self) -> ResourceBudget:
        if not set(self.enforceable) <= self.limits.keys() or not self.stop_loss.keys() <= self.limits.keys():
            raise ValueError("enforceable and stop-loss resources must have limits")
        return self


class OutcomeMeasure(StrictModel):
    """A named measurable objective with an explicit unit and hard-gate status."""

    name: Identifier
    unit: Text
    direction: Literal["minimize", "maximize", "exact"]
    threshold: DecimalString | None = None
    hard_gate: bool = False


class MissionConstitution(StrictModel):
    """Customer-controlled mission terms, evidence rights and authority ceiling."""

    mission_id: Identifier
    owner: Identifier
    objective: Text
    beneficiary: Identifier | None = None
    outcome_measures: list[OutcomeMeasure] = Field(default_factory=list, max_length=32)
    mission_distribution: Text = "bounded public synthetic streaming workloads"
    scope: Text = "offline local rehearsal"
    evidence_rights: list[Text] = Field(default_factory=list, max_length=32)
    constraints: list[Text] = Field(default_factory=list, max_length=64)
    prohibited_actions: list[Identifier] = Field(default_factory=list, max_length=64)
    incumbent: Identifier | None = None
    alternatives: list[Identifier] = Field(default_factory=list, max_length=32)
    utility_rule: Text = "hard correctness gates before measured cost and performance"
    accounting_rule: Text = "each measured cost deducted once; unknown costs remain unknown"
    budget: ResourceBudget = Field(default_factory=ResourceBudget)
    reviewer_budget_minutes: Count = 0
    proof_requirements: list[Identifier] = Field(default_factory=list, max_length=32)
    authority_ceiling: Literal["none", "sandbox", "production"] = "none"
    stop_conditions: list[Text] = Field(default_factory=list, max_length=32)
    validity: Validity | None = None


class Institution(StrictModel):
    """Identity persists while releases and authorization remain separate records."""

    id: Identifier
    constitution: MissionConstitution
    controller: Identifier
    serving_release_digest: Digest | None = None
    nominated_release_digest: Digest | None = None
    predecessor_id: Identifier | None = None
    discovery_locations: list[Text] = Field(default_factory=list, max_length=16)


class UnderwritingDecision(StrictModel):
    """An accountable bounded evidence programme, not an operational grant."""

    decision_id: Identifier
    institution_id: Identifier
    mission_id: Identifier
    principal: Identifier
    changed_assumption: Text
    considered_alternatives: list[Literal["retain", "repair", "rent", "build", "partner", "reserve", "stop"]] = Field(
        min_length=1, max_length=7
    )
    selected: Literal["retain", "repair", "rent", "build", "partner", "reserve", "stop"]
    decisive_evidence: list[Identifier] = Field(default_factory=list, max_length=64)
    proof_budget: ResourceBudget
    rationale: Text
    issued_at: UTC

    @model_validator(mode="after")
    def selection_considered(self) -> UnderwritingDecision:
        if self.selected not in self.considered_alternatives:
            raise ValueError("selected alternative was not considered")
        return self


class EvidenceRecord(StrictModel):
    """Content integrity, scope, custody, freshness and permission remain distinct."""

    evidence_id: Identifier
    source: Text
    acquired_at: UTC
    content_digest: Digest
    transformations: list[Text] = Field(default_factory=list, max_length=64)
    dependencies: list[Identifier] = Field(default_factory=list, max_length=128)
    permitted_uses: list[Identifier] = Field(default_factory=list, max_length=32)
    valid_until: UTC
    scope: Text
    uncertainty: Text
    restrictions: list[Text] = Field(default_factory=list, max_length=32)
    retention_until: UTC | None = None
    accepted_by: Identifier | None = None
    protected: bool = False
    revoked: bool = False


class TypedPort(StrictModel):
    """An inspectable typed observation, state or result."""

    name: Identifier
    type_name: Text
    constraints: list[Text] = Field(default_factory=list, max_length=32)


class Prediction(StrictModel):
    """A prediction committed before observation and retained when falsified."""

    prediction_id: Identifier
    metric: Identifier
    unit: Text
    predicted: DecimalString
    lower: DecimalString
    upper: DecimalString
    recorded_at: UTC
    experiment_id: Identifier
    observation: DecimalString | None = None
    falsified: bool | None = None
    decision_effect: Text


class WorldProgram(StrictModel):
    """Typed explanatory state and executable experiment-selection relationships."""

    world_id: Identifier
    artifact_digest: Digest
    inputs: list[TypedPort] = Field(default_factory=list, max_length=32)
    state: list[TypedPort] = Field(default_factory=list, max_length=32)
    transitions: list[Text] = Field(default_factory=list, max_length=64)
    predictions: list[Prediction] = Field(default_factory=list, max_length=128)
    invariants: list[Text] = Field(default_factory=list, max_length=64)
    outputs: list[TypedPort] = Field(default_factory=list, max_length=32)
    uncertainty: Text
    assumptions: list[Text] = Field(default_factory=list, max_length=64)
    evidence: list[Identifier] = Field(default_factory=list, max_length=128)
    falsifiers: list[Text] = Field(default_factory=list, max_length=64)
    revision_history: list[Digest] = Field(default_factory=list, max_length=128)


class PolicyProgram(StrictModel):
    """Proposed decisions are separate from actual action permission."""

    policy_id: Identifier
    artifact_digest: Digest
    objective: Text
    decision_rules: list[Text] = Field(min_length=1, max_length=64)
    admissible_actions: list[Identifier] = Field(default_factory=list, max_length=64)
    constraints: list[Text] = Field(default_factory=list, max_length=64)
    abstention: list[Text] = Field(default_factory=list, max_length=32)
    escalation: list[Text] = Field(default_factory=list, max_length=32)
    dependencies: list[Digest] = Field(default_factory=list, max_length=128)
    configuration: dict[Identifier, Scalar] = Field(default_factory=dict, max_length=64)


class JobContract(StrictModel):
    """Frozen richer work terms, independent of a legacy settlement specification."""

    job_id: Identifier
    family: Family
    worker: Identifier | None = None
    acceptance_owner: Identifier
    release_digest: Digest
    environment_digest: Digest
    inputs: dict[Identifier, Text] = Field(default_factory=dict, max_length=64)
    outputs: dict[Identifier, Text] = Field(default_factory=dict, max_length=64)
    critical_functions: list[Identifier] = Field(default_factory=list, max_length=64)
    resources: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)
    valid_until: UTC
    max_attempts: int = Field(default=1, ge=1, le=10)
    effects: list[Identifier] = Field(default_factory=list, max_length=32)
    institution_id: Identifier | None = None
    mission_id: Identifier | None = None
    goal: Text = "bounded evidence-bearing work"
    verifier: Identifier | None = None
    input_evidence: list[Identifier] = Field(default_factory=list, max_length=128)
    allowed_tools: list[Identifier] = Field(default_factory=list, max_length=32)
    prohibited_effects: list[Identifier] = Field(default_factory=list, max_length=32)
    rollback_target: Identifier | None = None
    acceptance_conditions: list[Text] = Field(default_factory=list, max_length=32)
    evidence_assumptions: list[Text] = Field(default_factory=list, max_length=32)
    repair_routes: list[Identifier] = Field(default_factory=list, max_length=16)
    lifecycle_obligations: list[Text] = Field(default_factory=list, max_length=32)


class JobDependency(StrictModel):
    """Typed dispatch obligations with explicit control ownership."""

    source: Identifier
    target: Identifier
    kind: Literal["evidence", "control", "challenge", "rollback"]
    principal: Identifier | None = None
    required_type: Text | None = None


class JobGraph(StrictModel):
    """A bounded graph; runtime compilation enforces coverage and dependency guards."""

    jobs: list[JobContract] = Field(min_length=1, max_length=256)
    edges: list[JobDependency] = Field(default_factory=list, max_length=1024)
    required_families: list[Family] = Field(default_factory=list, max_length=7)
    required_functions: list[Identifier] = Field(default_factory=list, max_length=64)


class ExecutionAuthorization(StrictModel):
    """Observed assignment binds immutable work terms to one actual execution."""

    authorization_id: Identifier
    acting_identity: Identifier
    job_terms_digest: Digest
    release_digest: Digest
    environment_digest: Digest
    capabilities: list[Identifier] = Field(default_factory=list, max_length=64)
    reservation_id: Identifier
    expires_at: UTC
    market_binding_digest: Digest | None = None


class BehaviorArtifact(StrictModel):
    """One complete behavior-affecting artifact, including configuration or memory."""

    name: Identifier
    role: Literal["source", "model", "prompt", "routing", "tool", "dependency", "memory", "world", "policy", "other"]
    digest: Digest
    location: Text | None = None


class ProviderManifest(StrictModel):
    """Remote requests identify configuration, without claiming immutable remote weights."""

    provider: Identifier
    model: Text
    endpoint: Text
    observed_at: UTC
    configuration: dict[Identifier, Scalar] = Field(default_factory=dict, max_length=64)
    behavioral_fingerprint: Digest | None = None
    pinning_limitations: Text
    implementation: Literal["deterministic", "remote-model", "local-model"]


class CandidateReleaseManifest(StrictModel):
    """Exact complete release composition, excluding protected verifier internals."""

    release_id: Identifier
    institution_id: Identifier
    mission_id: Identifier
    producer: Identifier
    environment_digest: Digest
    artifacts: list[BehaviorArtifact] = Field(default_factory=list, max_length=256)
    providers: list[ProviderManifest] = Field(default_factory=list, max_length=16)
    world_digest: Digest | None = None
    policy_digest: Digest | None = None
    memory_digests: list[Digest] = Field(default_factory=list, max_length=128)
    budget: ResourceBudget = Field(default_factory=ResourceBudget)
    development_evaluator_digest: Digest | None = None
    final_proof_interface_digest: Digest | None = None
    parent_release_digest: Digest | None = None
    configuration: dict[Identifier, Scalar] = Field(default_factory=dict, max_length=64)
    mutable_state_classes: list[Identifier] = Field(default_factory=list, max_length=32)
    immutable_trial: bool = True


class EnvironmentSpec(StrictModel):
    """Declared mission environment and partitions; labels do not establish custody."""

    environment_id: Identifier
    mission_families: list[Identifier] = Field(min_length=1, max_length=32)
    states: list[TypedPort] = Field(default_factory=list, max_length=32)
    allowed_observations: list[Identifier] = Field(default_factory=list, max_length=64)
    allowed_actions: list[Identifier] = Field(default_factory=list, max_length=64)
    transitions: list[Text] = Field(default_factory=list, max_length=64)
    reward_dimensions: list[OutcomeMeasure] = Field(default_factory=list, max_length=32)
    hard_constraints: list[Text] = Field(min_length=1, max_length=64)
    development_partition_digest: Digest
    proof_partition_commitment: Digest
    termination: list[Text] = Field(min_length=1, max_length=32)
    truncation: list[Text] = Field(default_factory=list, max_length=32)
    known_reality_gaps: list[Text] = Field(default_factory=list, max_length=32)


class Comparator(StrictModel):
    """A fixed deployable alternative, never a hindsight per-case oracle."""

    comparator_id: Identifier
    role: Literal["incumbent", "simple", "specialist", "general", "human", "hybrid"]
    release_digest: Digest | None = None
    configuration: dict[Identifier, Scalar] = Field(default_factory=dict, max_length=64)
    permitted_evidence: list[Identifier] = Field(default_factory=list, max_length=64)
    tools: list[Identifier] = Field(default_factory=list, max_length=32)
    observed_at: UTC
    resources: ResourceBudget = Field(default_factory=ResourceBudget)
    selection_rationale: Text
    status: Literal["measured", "unavailable"]
    unavailability_reason: Text | None = None

    @model_validator(mode="after")
    def availability(self) -> Comparator:
        if self.status == "measured" and self.release_digest is None:
            raise ValueError("measured comparator requires exact release digest")
        if self.status == "unavailable" and self.unavailability_reason is None:
            raise ValueError("unavailable comparator requires a reason")
        return self


class ComparatorManifest(StrictModel):
    """Frozen comparator set and common comparison conditions."""

    manifest_id: Identifier
    mission_id: Identifier
    comparators: list[Comparator] = Field(min_length=2, max_length=32)
    cost_rule_digest: Digest
    selection_rule: Text
    frozen_at: UTC


class ComparatorRequirement(StrictModel):
    """Applicability is explicit for every credible alternative family."""

    role: Literal["incumbent", "simple", "specialist", "general", "human", "hybrid"]
    required: bool
    rationale: Text


class SpecialistDesignationPolicy(StrictModel):
    """Versioned designation requirements; the software name grants no designation."""

    policy_id: Identifier
    mission_family: Identifier
    validity: Validity
    superiority_metric: Identifier
    superiority_threshold_bps: int = Field(ge=1, le=1000000)
    minimum_evaluation_units: int = Field(ge=1, le=MAX_SAFE_INT)
    required_independent_replications: int = Field(ge=1, le=1000)
    comparator_requirements: list[ComparatorRequirement] = Field(min_length=6, max_length=6)
    required_claim: Literal["alpha"] = "alpha"
    designation: Literal["specialist-asi"] = "specialist-asi"
    uncertainty_requirement: Text
    accountable_policy_owner: Identifier

    @model_validator(mode="after")
    def explicit_comparator_applicability(self) -> SpecialistDesignationPolicy:
        roles = {requirement.role for requirement in self.comparator_requirements}
        if roles != {"incumbent", "simple", "specialist", "general", "human", "hybrid"}:
            raise ValueError("all six comparator families require explicit unique applicability decisions")
        if not any(requirement.required for requirement in self.comparator_requirements):
            raise ValueError("designation requires at least one credible comparator")
        return self


class VerifierDisclosure(StrictModel):
    """Disclosure is evidence to check, not authority to appoint a trusted verifier."""

    verifier: Identifier
    organization: Text
    control_separation: Text
    custodian: Identifier
    funding_and_conflicts: Text
    protocol_controller: Identifier
    replication_status: Literal["not-replicated", "local-replay", "external-replication"]
    provenance: Literal["local", "independent"] = "local"


class ProofProtocol(StrictModel):
    """Preregistered examination binding scope, thresholds, units and uncertainty."""

    protocol_id: Identifier
    mission_id: Identifier
    candidate_release_digest: Digest
    comparator_manifest_digest: Digest
    environment_digest: Digest
    evidence_commitment: Digest
    verifier_disclosure: VerifierDisclosure
    evaluation_unit: Text
    thresholds: list[OutcomeMeasure] = Field(min_length=1, max_length=32)
    randomization: Text
    warmup_and_cache: Text
    timeout_ms: Count
    exclusions_policy: Text
    uncertainty_method: Text
    multiplicity_policy: Text
    cost_rule_digest: Digest
    validity: Validity
    frozen_at: UTC


class ProofReceipt(StrictModel):
    """An attributed result; trust and scientific claim qualification are checked separately."""

    proof_id: Identifier
    institution_id: Identifier
    mission_id: Identifier
    release_digest: Digest
    environment_digest: Digest
    verifier: Identifier
    valid_until: UTC
    outcome: Outcome
    claim: Literal["safety", "alpha", "correctness", "portability"]
    evidence_scope: Literal["local", "independent"] = "local"
    dependency_digests: list[Digest] = Field(default_factory=list, max_length=256)
    comparator_manifest_digest: Digest
    protocol_digest: Digest
    evidence_commitment: Digest
    disclosure: VerifierDisclosure | None = None
    evaluation_units: Count = 0
    measurements: dict[Identifier, DecimalString] = Field(default_factory=dict, max_length=128)
    uncertainty: Text = "not externally established"
    costs: ResourceBudget = Field(default_factory=ResourceBudget)
    failures: list[Text] = Field(default_factory=list, max_length=128)
    interventions: list[Text] = Field(default_factory=list, max_length=128)
    exclusions: list[Text] = Field(default_factory=list, max_length=128)
    issued_at: UTC | None = None


class AdmissionDecision(StrictModel):
    """A separate accountable decision does not itself authorize actions."""

    decision_id: Identifier
    institution_id: Identifier
    release_digest: Digest
    principal: Identifier
    outcome: Literal["admit", "refuse"]
    proof_ids: list[Identifier] = Field(default_factory=list, max_length=128)
    rationale: Text = "explicit local accountable decision"
    issued_at: UTC | None = None


class AuthorityEnvelope(StrictModel):
    """One indivisible permission; independent grants must never be combined."""

    grant_id: Identifier
    institution_id: Identifier
    mission_id: Identifier
    release_digest: Digest
    subject: Identifier
    issuer: Identifier
    actions: list[Identifier] = Field(min_length=1, max_length=64)
    tools: list[Identifier] = Field(min_length=1, max_length=64)
    targets: list[Text] = Field(min_length=1, max_length=64)
    resources: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)
    proof_ids: list[Identifier] = Field(default_factory=list, max_length=128)
    valid_until: UTC
    rollback_release_digest: Digest | None = None
    approval_required: bool = True
    context_digest: Digest
    scope: Literal["sandbox", "production"] = "sandbox"
    approval_conditions: list[Text] = Field(default_factory=list, max_length=32)
    monitoring: list[Text] = Field(default_factory=list, max_length=32)
    revocation_conditions: list[Text] = Field(default_factory=list, max_length=32)
    issued_at: UTC | None = None


class ChronicleEvent(StrictModel):
    """Attributable immutable historical event, distinct from current permission."""

    event_id: Identifier
    institution_id: Identifier
    principal: Identifier
    event_type: Identifier
    recorded_at: UTC
    subject_digest: Digest
    previous_event_digest: Digest | None = None
    dependencies: list[Digest] = Field(default_factory=list, max_length=128)
    details: dict[Identifier, Scalar] = Field(default_factory=dict, max_length=64)


class MemoryAdmission(StrictModel):
    """Permission to influence later work, distinct from retaining historical records."""

    admission_id: Identifier
    institution_id: Identifier
    principal: Identifier
    artifact_digest: Digest
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=128)
    permitted_uses: list[Identifier] = Field(min_length=1, max_length=32)
    scope: Text
    rights: list[Text] = Field(min_length=1, max_length=32)
    valid_until: UTC
    retention_until: UTC
    outcome: Literal["admit", "quarantine", "reject"]
    dependency_digests: list[Digest] = Field(default_factory=list, max_length=128)
    restrictions: list[Text] = Field(default_factory=list, max_length=32)


class SuccessorRecord(StrictModel):
    """Lineage carries permitted knowledge, never predecessor proof or grants."""

    successor_id: Identifier
    institution_id: Identifier
    predecessor_release_digest: Digest
    successor_release_digest: Digest
    inherited_memory: list[Identifier] = Field(default_factory=list, max_length=128)
    excluded_assets: list[Digest] = Field(default_factory=list, max_length=128)
    rejected_candidates: list[Digest] = Field(default_factory=list, max_length=128)
    failures_and_incidents: list[Identifier] = Field(default_factory=list, max_length=128)
    predecessor_disposition: Literal["serving", "retained-fallback", "retired", "impaired"]
    new_proof_ids: list[Identifier] = Field(default_factory=list, max_length=128)
    new_admission_id: Identifier | None = None
    new_grant_ids: list[Identifier] = Field(default_factory=list, max_length=128)
    recovery_release_digest: Digest | None = None


class ForecastRecord(StrictModel):
    """Modeled value is not accepted customer value or available capital."""

    forecast_id: Identifier
    institution_id: Identifier
    assumptions: list[Text] = Field(min_length=1, max_length=64)
    quantity: DecimalString
    unit: Text
    horizon: Text
    uncertainty: Text
    amortization_volume: Count
    evidence_ids: list[Identifier] = Field(default_factory=list, max_length=64)


class ExperimentalMeasurement(StrictModel):
    """Actual physical or monetary measurement, with unknown values represented explicitly."""

    measurement_id: Identifier
    institution_id: Identifier
    release_digest: Digest
    metric: Identifier
    value: DecimalString | None
    unit: Text
    status: Literal["measured", "unknown"]
    method: Text
    observed_at: UTC
    evidence_digest: Digest

    @model_validator(mode="after")
    def measurement_status(self) -> ExperimentalMeasurement:
        if (self.status == "unknown") != (self.value is None):
            raise ValueError("unknown measurements must be null; measured values must be explicit")
        return self


class AcceptedOutcome(StrictModel):
    """Realized value requires its own accountable acceptance and evidence."""

    outcome_id: Identifier
    institution_id: Identifier
    customer: Identifier
    accepted_by: Identifier
    quantity: DecimalString
    unit: Text
    evidence_ids: list[Identifier] = Field(min_length=1, max_length=128)
    acceptance_digest: Digest
    realized_at: UTC
    settlement_ids: list[Identifier] = Field(default_factory=list, max_length=64)


class SettlementReceipt(StrictModel):
    """Settlement attribution is distinct from superiority and customer value."""

    settlement_id: Identifier
    institution_id: Identifier
    job_id: Identifier
    execution_authorization_digest: Digest
    chain_id: Count
    market: Text
    market_job_id: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,77})$")
    transaction_hash: str = Field(pattern=r"^0x[0-9a-fA-F]{64}$")
    log_index: Count
    worker: Text
    asset: Text
    amount_atomic: str = Field(pattern=r"^(?:0|[1-9][0-9]{0,77})$")
    asset_decimals: int = Field(ge=0, le=255)
    status: Literal["paid", "refunded", "failed", "pending"]
    evidence_digest: Digest


class ResourceReservation(StrictModel):
    """Atomic resource hold with an explicit idempotency identity."""

    reservation_id: Identifier
    institution_id: Identifier
    idempotency_key: Identifier
    principal: Identifier
    resources: dict[Identifier, Count] = Field(min_length=1, max_length=32)
    status: Literal["reserved", "consumed", "released"]
    expires_at: UTC
    observed_usage: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)
    unknown_costs: list[Identifier] = Field(default_factory=list, max_length=32)


class AllocationDecision(StrictModel):
    """Authorized allocations account for obligations and reliability reserves."""

    allocation_id: Identifier
    institution_id: Identifier
    principal: Identifier
    resources: dict[Identifier, Count] = Field(min_length=1, max_length=32)
    available_before: dict[Identifier, Count] = Field(min_length=1, max_length=32)
    obligations: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)
    reliability_reserves: dict[Identifier, Count] = Field(default_factory=dict, max_length=32)
    rationale: Text
    issued_at: UTC

    @model_validator(mode="after")
    def available_resources(self) -> AllocationDecision:
        for name, amount in self.resources.items():
            available = self.available_before.get(name, 0)
            encumbered = self.obligations.get(name, 0) + self.reliability_reserves.get(name, 0)
            if amount + encumbered > available:
                raise ValueError("allocation exceeds available unencumbered resources")
        return self


class RehearsalSignature(BaseModel):
    """Locally supplied signature data never installs its own trusted key."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True, revalidate_instances="always")
    public_key: str = Field(min_length=1, max_length=256)
    signature: str = Field(min_length=1, max_length=256)


class RehearsalResult(StrictModel):
    """Bounded file handoff; evidence is checked recursively and by its originating models."""

    kind: Literal["successor-result"] = "successor-result"
    request_hash: Digest
    evidence: dict[str, Any] = Field(max_length=128)
    evidence_hash: Digest
    scope: Literal["local-native-rehearsal"] = "local-native-rehearsal"
    signature: RehearsalSignature | None = None

    @model_validator(mode="after")
    def evidence_integrity(self) -> RehearsalResult:
        if digest("evidence", self.evidence) != self.evidence_hash:
            raise ValueError("evidence commitment does not match")
        return self


PROTOCOL_MODELS: tuple[type[StrictModel], ...] = (
    RehearsalRequest,
    Institution,
    MissionConstitution,
    UnderwritingDecision,
    EvidenceRecord,
    WorldProgram,
    PolicyProgram,
    JobContract,
    JobGraph,
    ExecutionAuthorization,
    CandidateReleaseManifest,
    EnvironmentSpec,
    ComparatorManifest,
    SpecialistDesignationPolicy,
    ProofProtocol,
    ProofReceipt,
    AdmissionDecision,
    AuthorityEnvelope,
    ChronicleEvent,
    MemoryAdmission,
    SuccessorRecord,
    ForecastRecord,
    ExperimentalMeasurement,
    AcceptedOutcome,
    SettlementReceipt,
    ResourceReservation,
    AllocationDecision,
    RehearsalResult,
)


def schema_bundle() -> dict[str, Any]:
    """Return portable JSON schemas; schema support never substitutes for runtime guards."""
    return {
        "schema_version": 1,
        "kind": "successor-schema-bundle",
        "canonicalization": "sorted-printable-ASCII-keys/UTF8/no-normalization/safe-integers/no-floats/v1",
        "digest_prefix": "successor-omega/v1:{domain}\\u0000",
        "schemas": {model.__name__: model.model_json_schema() for model in PROTOCOL_MODELS},
    }


def canonical_vectors() -> list[dict[str, Any]]:
    """Cross-language vectors cover key ordering, Unicode and integer boundaries."""
    values = [
        ("request", RehearsalRequest(request_id="00000000-0000-4000-8000-000000000001").model_dump()),
        ("evidence", {"z": [False, True, None, -MAX_SAFE_INT, MAX_SAFE_INT], "a": "Ω · é · 😀"}),
        ("evidence", {"2": '\b\t\n\f\r\\"/', "10": "e\u0301", "1": "\u2028\u2029"}),
        (
            "job-terms",
            {
                "schema_version": 1,
                "job_id": "review-negative",
                "verdict": "fail",
                "amount_atomic": "1000000000000000000",
            },
        ),
    ]
    return [
        {
            "domain": domain,
            "value": value,
            "canonical": canonical(value).decode("utf-8"),
            "sha256": digest(domain, value),
        }
        for domain, value in values
    ]


def write_protocol_artifacts(directory: Path) -> None:
    """Regenerate deterministic schema and vector files for packaging and consumers."""
    directory.mkdir(parents=True, exist_ok=True)
    for name, value in (("schemas.json", schema_bundle()), ("canonical-vectors.json", canonical_vectors())):
        (directory / name).write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
