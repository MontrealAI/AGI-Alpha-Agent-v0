# SPDX-License-Identifier: Apache-2.0
"""Protected closed-program capsules inside the existing transformation library.

This adds a protected branch to its authoritative journal record, not a second
registry. Local structural promotion cannot admit a protected capability. All
external evidence remains an attributed configured-signer attestation.
"""

from __future__ import annotations

import base64
import copy
import secrets
import time
import hashlib
import platform
import unicodedata
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlsplit

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import Field, model_validator

from ..store import Conflict, _private_recovery_bytes, digest as runtime_digest
from ..chain import address
from .flywheel_access import AccessRequest, ResourceAccess, direct_name
from .flywheel_costs import Charge, CostLedger, accepted_native_delivery
from .flywheel_checkpoint import DurableCheckpoint
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest, safe_json_loads
from .transformation import (
    IntentCharter,
    SelectionProgram,
    SourceDocument,
    SourceClaim,
    execute_selection,
    assert_public_content,
    _checked_source_bytes,
)
from .transformation_library import KEY, PROTECTED_BRANCH, TransformationLibrary
from .trust import SignedEnvelope

BRANCH = PROTECTED_BRANCH
MAX_INVOCATION_INPUT_BYTES = 250_000
MAX_INVOCATION_RECORD_BYTES = 1_000_000
REVOCATION_RESERVE_BYTES = 25_000


def source_fingerprints(document: SourceDocument) -> set[str]:
    """Exclude reused source identity or text despite superficial document rewrapping."""
    uri = urlsplit(document.source_url)
    source_uri = uri._replace(scheme=uri.scheme.lower(), netloc=uri.netloc.lower(), query="", fragment="").geturl()
    text = " ".join(unicodedata.normalize("NFKC", " ".join(c.text for c in document.claims)).casefold().split())
    return {digest("flywheel-source-uri", source_uri), digest("flywheel-source-text", text)}


def origin_source_documents(origin: dict[str, Any]) -> list[SourceDocument]:
    """Canonical source-document projection of each accepted native Research input.

    This is a provenance projection, not an inferred summary or evaluation case.
    Whole-mission identity remains separate from these ti-source commitments.
    """
    documents = []
    for source_index, source in enumerate(origin["request"]["work"]["sources"]):
        chunks = [source["text"][index : index + 1500] for index in range(0, len(source["text"]), 1500)]
        for offset in range(0, len(chunks), 12):
            documents.append(
                SourceDocument(
                    title=source["title"] + f" / native source part {offset // 12 + 1}",
                    source_url=source["url"],
                    claims=[
                        SourceClaim(
                            id=f"origin-{source_index}-{offset + index}",
                            text=text,
                            weight=1,
                            depends_on=[],
                            provenance=f"Native mission {origin['id']}; source {source['id']}; record {origin['digest']}",
                        )
                        for index, text in enumerate(chunks[offset : offset + 12])
                    ],
                )
            )
    return documents


class CapsuleManifest(StrictModel):
    skill_id: Identifier
    version: int = Field(ge=1, le=1_000_000)
    origin_mission: Identifier
    origin_record_digest: Digest
    origin_agent: str = Field(max_length=100)
    origin_wallet: str = Field(pattern=r"^0x[0-9a-f]{40}$")
    content_digest: Digest
    supported_scope: Literal["bounded-public-source-selection/v1"]
    prerequisites: list[Digest] = Field(max_length=16)
    limitations: Text
    rights: Literal["cleared-for-authenticated-network"]
    rights_evidence: Digest
    dependency_digests: list[Digest] = Field(max_length=16)
    export_policy: Literal["controlled-invocation-only"] = "controlled-invocation-only"

    @model_validator(mode="after")
    def bounded_manifest(self) -> CapsuleManifest:
        direct_name(self.origin_agent)
        address(self.origin_wallet)
        if len(set(self.dependency_digests)) != len(self.dependency_digests):
            raise ValueError("dependencies cannot repeat")
        assert_public_content(self.model_dump())
        return self


class EvaluationPlan(StrictModel):
    candidate_digest: Digest
    beta_digest: Digest
    execution_digest: Digest
    model_id: str = Field(min_length=1, max_length=200)
    reasoning_mode: Literal["standard", "pro"]
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"]
    policy_digest: Digest
    matched_tools_digest: Digest
    resource_rules_digest: Digest
    recipient_capabilities_digest: Digest
    retention_cost_record: Identifier
    origin_input_digests: list[Digest] = Field(min_length=1, max_length=128)
    fresh_input_digests: list[Digest] = Field(min_length=2, max_length=128)
    fresh_inputs: list[SourceDocument] = Field(min_length=2, max_length=128)
    planned_reuses: int = Field(ge=1, le=100_000)
    remaining_retention_micro_usd: int = Field(ge=0, le=10**15)
    prospective_basis: Text

    @model_validator(mode="after")
    def disjoint_inputs(self) -> EvaluationPlan:
        if self.fresh_input_digests != [digest("ti-source", document) for document in self.fresh_inputs]:
            raise ValueError("fresh source documents must match their exact ti-source commitments")
        if set(self.origin_input_digests) & set(self.fresh_input_digests) or len(set(self.fresh_input_digests)) != len(
            self.fresh_input_digests
        ):
            raise ValueError("evaluation requires distinct fresh cases excluded from originating delivery")
        return self


class FrontierRun(StrictModel):
    """An execution custodian's exact receipt; no self-asserted heuristic model IDs."""

    input_digest: Digest
    candidate_digest: Digest | None
    output_digest: Digest
    beta_digest: Digest
    model_id: str = Field(min_length=1, max_length=200)
    reasoning_mode: Literal["standard", "pro"]
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"]
    tools_digest: Digest
    resource_rules_digest: Digest
    recipient_capabilities_digest: Digest
    provider_response_digest: Digest
    billing_evidence_digest: Digest
    actual_cost_micro_usd: int = Field(ge=0, le=10**15)
    usage: dict[str, int]
    started_at: int = Field(ge=1)
    finished_at: int = Field(ge=1)
    evidence_basis: Literal["configured-executor-attestation"]

    @model_validator(mode="after")
    def complete_receipt(self) -> FrontierRun:
        if (
            self.finished_at < self.started_at
            or not self.usage
            or len(self.usage) > 32
            or any(type(v) is not int or not 0 <= v <= 10**12 for v in self.usage.values())
            or any(not 1 <= len(key) <= 80 for key in self.usage)
        ):
            raise ValueError("complete bounded usage and execution interval required")
        return self


class AlphaEvidence(StrictModel):
    plan_digest: Digest
    candidate_runs: list[SignedEnvelope] = Field(min_length=2, max_length=128)
    beta_runs: list[SignedEnvelope] = Field(min_length=2, max_length=128)
    acceptance: list[SignedEnvelope] = Field(min_length=2, max_length=128)
    lower_net_saving_per_use_micro_usd: int = Field(ge=-(10**15), le=10**15)
    uncertainty_basis: Text
    false_passes: int = Field(ge=0, le=1_000_000)
    false_rejections: int = Field(ge=0, le=1_000_000)
    abstentions: int = Field(ge=0, le=1_000_000)
    correlated_failure_analysis: Text


class Invocation(StrictModel):
    mission_id: Identifier
    document: SourceDocument
    charter: IntentCharter
    beta_digest: Digest
    policy_digest: Digest
    recipient_capabilities_digest: Digest
    prerequisite_digests: list[Digest] = Field(max_length=32)
    logical_limit: int = Field(ge=1, le=100_000)
    cost_cap_micro_usd: int = Field(ge=0, le=10**12)


class ProtectedLibrary:
    """Compose installed trust, existing library, costs and resource authentication."""

    def __init__(
        self,
        library: TransformationLibrary,
        costs: CostLedger,
        access: ResourceAccess,
        keys: dict[str, bytes],
        active_key: str,
        checkpoint: DurableCheckpoint,
        *,
        custody_files: dict[str, str] | None = None,
    ) -> None:
        if library.journal is not costs.journal or library.journal is not access.journal:
            raise ValueError("one authoritative transactional journal is required")
        if (
            not keys
            or active_key not in keys
            or any(not key or len(key) > 80 or len(value) != 32 for key, value in keys.items())
        ):
            raise ValueError("explicit operator-provisioned AES-256 key inventory required")
        self.library, self.journal, self.trust, self.costs, self.access = (
            library,
            library.journal,
            library.trust,
            costs,
            access,
        )
        self.keys, self.active_key, self.checkpoint = dict(keys), active_key, checkpoint
        self._custody_files = dict(custody_files or {})
        if len(self._custody_files) > 18:
            raise ValueError("bounded deployment, trust and key custody inventory required")
        self.costs.checkpoint = checkpoint
        self.costs.custody_check = self._check_custody_files
        self._boot_execution_digest = self._execution_binding()
        with self.journal.transaction() as cx:
            state = self.library.snapshot()
            if BRANCH not in state:
                state[BRANCH] = {
                    "storage_schema": 2,
                    "entries": {},
                    "active": {},
                    "beta_digest": None,
                    "policy_digest": None,
                    "history": [],
                    "operations": {},
                    "invocations": {},
                }
                self._commit(cx, state)

    def _check_custody_files(self) -> None:
        for name, expected in self._custody_files.items():
            try:
                raw = _private_recovery_bytes(Path(name), limit=131_072)
            except (OSError, ValueError):
                raise Conflict("configured custody is unavailable; service restart required") from None
            if hashlib.sha256(raw).hexdigest() != expected:
                raise Conflict("configured trust or key custody changed; service restart and requalification required")

    def _execution_binding(self) -> str:
        import cryptography
        import httpx
        import pydantic
        from ..models import RuntimeConfig

        self._check_custody_files()
        actual_config = RuntimeConfig.model_validate_json(
            _private_recovery_bytes(self.journal.root / "config.json", limit=131_072)
        ).model_dump()
        if actual_config != self.journal.config.model_dump():
            raise Conflict("runtime configuration changed in another process; restart and requalify")

        here = Path(__file__).parent
        paths = [
            *here.glob("flywheel_*.py"),
            here / "transformation.py",
            here / "trust.py",
            here / "protocol.py",
            here / "signatures.py",
            here / "transformation_library.py",
            *[
                here.parent / name
                for name in ("chain.py", "engine.py", "models.py", "provider.py", "store.py", "work.py")
            ],
        ]
        sources = {}
        for path in sorted(paths):
            if path.is_symlink() or not path.is_file() or path.stat().st_size > 256_000:
                raise ValueError("installed protected runtime requires bounded regular source files")
            raw = _checked_source_bytes(path, path.read_bytes(), source_loader=globals().get("__loader__"))
            sources[path.relative_to(here.parent).as_posix()] = hashlib.sha256(raw).hexdigest()
        readers = [
            {
                "implementation": type(reader).__module__ + "." + type(reader).__qualname__,
                "configuration": reader.config.model_dump() if hasattr(reader, "config") else None,
            }
            for reader in self.access.authority.readers
        ]
        from importlib.metadata import version

        dependency_versions = {name: version(name) for name in ("eth-account", "eth-utils", "eth-hash")}
        return digest(
            "flywheel-execution-environment",
            {
                "sources": sources,
                "python": platform.python_version(),
                "cryptography": cryptography.__version__,
                "pydantic": pydantic.__version__,
                "httpx": httpx.__version__,
                "runtime_configuration": actual_config,
                "custody_configuration": self._custody_files,
                "service": self.access.service.model_dump(),
                "ens_pins": self.access.authority.pins.model_dump(),
                "readers": readers,
                "chain_dependencies": dependency_versions,
            },
        )

    @property
    def execution_digest(self) -> str:
        return self._boot_execution_digest

    def _commit(self, cx: Any, state: dict[str, Any]) -> None:
        network = state[BRANCH]
        revocable = sum(
            not entry.get("archive") and entry["state"] != "revoked" for entry in network["entries"].values()
        )
        pending = sum(row["status"] == "executing-or-uncertain" for row in network["invocations"].values())
        network["reserved_capacity_bytes"] = 32_768 + REVOCATION_RESERVE_BYTES * revocable + 128 * pending
        network["reserved_capacity_nodes"] = 2048 + 64 * revocable + 8 * pending
        self.library._persist(cx, state)
        self.checkpoint.advance(self.journal, cx)

    def _state(self, cx: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        if self._execution_binding() != self._boot_execution_digest:
            raise Conflict("installed runtime changed; restart and requalify affected claims")
        if self.journal.latest("@control", cx)["config_hash"] != runtime_digest(self.journal.config.model_dump()):
            raise Conflict("runtime configuration changed; restart and requalify")
        self.checkpoint.verify(self.journal, cx)
        state = self.journal.document(self.journal.latest(KEY, cx))
        if state[BRANCH].get("storage_schema") != 2:
            raise Conflict("unqualified pre-release storage requires explicit signed migration while stopped")
        return state, state[BRANCH]

    @staticmethod
    def _invocation_key(mission_id: str) -> str:
        return "@flywheel-invocation:" + mission_id

    def inspect_invocation(self, mission_id: str) -> dict[str, Any]:
        """Operator-only durable request/receipt history, including evicted cache rows."""
        with self.journal.transaction() as cx:
            self._state(cx)
            return self.journal.document(self.journal.latest(self._invocation_key(mission_id), cx))

    def _cache_invocation(self, network: dict[str, Any], mission_id: str, receipt: dict[str, Any]) -> None:
        index = network["invocations"]
        index[mission_id] = {
            "status": receipt["status"],
            "receipt_digest": digest("flywheel-reuse-receipt", receipt),
            "journal_key": self._invocation_key(mission_id),
            "updated_at_ms": time.time_ns() // 1_000_000,
        }
        completed = sorted(
            (key for key in index if index[key]["status"] != "executing-or-uncertain"),
            key=lambda key: index[key]["updated_at_ms"],
        )
        for key in completed[:-32]:
            del index[key]

    def _signed(self, signed: SignedEnvelope, action: str, role: str) -> dict[str, Any]:
        payload = self.trust.verify(signed, "flywheel-" + action, role)
        if (
            set(payload) != {"journal_identity", "operation_id", "record"}
            or payload["journal_identity"] != self.journal.identity
        ):
            raise ValueError("protected transition requires exact journal-bound signed terms")
        return payload

    def _begin(self, network: dict[str, Any], signed: SignedEnvelope, cx: Any) -> str:
        payload = signed.payload
        operation = payload["operation_id"]
        if not isinstance(operation, str) or not 1 <= len(operation) <= 128:
            raise ValueError("bounded protected operation identity required")
        try:
            self.journal.latest("@flywheel-operation:" + operation, cx)
        except KeyError:
            pass
        else:
            raise Conflict("protected transition already consumed; inspect current durable state")
        if operation in network["operations"]:
            raise Conflict("protected transition already consumed; inspect current durable state")
        network["operations"][operation] = digest("flywheel-operation", signed.model_dump())
        while len(network["operations"]) > 128:
            del network["operations"][next(iter(network["operations"]))]
        self.journal.append(
            cx, "@flywheel-operation:" + operation, {"signed": signed.model_dump(), "at": int(time.time())}
        )
        network["history"] = [
            *network["history"][-63:],
            {
                "operation_id": operation,
                "digest": digest("flywheel-operation", signed.model_dump()),
                "at": int(time.time()),
            },
        ]
        return operation

    def configure(self, signed: SignedEnvelope) -> None:
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "configure", "controller")
        record = payload["record"]
        if (
            not isinstance(record, dict)
            or set(record) != {"beta_digest", "policy_digest", "execution_digest"}
            or any(
                not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v)
                for v in record.values()
            )
        ):
            raise ValueError("current Beta and policy commitments required")
        if record["execution_digest"] != self.execution_digest:
            raise ValueError("configuration must bind the actual installed execution environment")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            if record != {k: network.get(k) for k in record}:
                network.update(record)
                network["active"] = {}
                for entry in network["entries"].values():
                    if not entry.get("archive") and entry["state"] not in {"revoked", "rejected"}:
                        entry["state"] = "requires-requalification"
            self._commit(cx, state)

    def retain(self, manifest: CapsuleManifest, program: SelectionProgram, signed: SignedEnvelope) -> str:
        manifest = CapsuleManifest.model_validate(manifest.model_dump())
        program = SelectionProgram.model_validate(program.model_dump())
        ident = digest("flywheel-manifest", manifest)
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "candidate", "producer")
        if payload["record"] != {"manifest_digest": ident} or signed.principal != self.library.producer:
            raise ValueError("producer signature must bind the exact frozen manifest")
        if digest("flywheel-program", program) != manifest.content_digest:
            raise ValueError("candidate implementation digest mismatch")
        origin_authority = self.access.authority.verify(manifest.origin_agent, manifest.origin_wallet)
        origin_deadline = time.monotonic_ns() + 2_000_000_000
        nonce = secrets.token_bytes(12)
        aad = canonical(
            {"service": self.access.service.model_dump(), "journal": self.journal.identity, "manifest": ident}
        )
        ciphertext = AESGCM(self.keys[self.active_key]).encrypt(nonce, canonical(program), aad)
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            if ident in network["entries"] or len(network["entries"]) >= 128:
                raise Conflict("duplicate candidate or capsule capacity reached")
            versions = [
                e["manifest"]["version"]
                for e in network["entries"].values()
                if e["manifest"]["skill_id"] == manifest.skill_id
            ]
            if manifest.version != max(versions, default=0) + 1:
                raise Conflict("capsule versions must advance without replacing history")
            origin = accepted_native_delivery(self.journal, manifest.origin_mission, cx)
            if origin["digest"] != manifest.origin_record_digest:
                raise ValueError("candidate must originate in this journal's exact accepted delivery")
            if not self.costs.report(manifest.origin_mission, cx)["bucket_complete"]["A"]:
                raise ValueError("originating delivery costs remain incomplete")
            wallet = self.journal.latest("@wallet", cx)
            if wallet["address"] != manifest.origin_wallet:
                raise ValueError("origin wallet must be proved through the existing runtime wallet binding")
            if time.monotonic_ns() >= origin_deadline:
                raise Conflict("origin authority evidence became stale before retention")
            origin_documents = origin_source_documents(origin)
            network["entries"][ident] = {
                "manifest": manifest.model_dump(),
                "origin_authorization": origin_authority,
                "origin_input_digests": [
                    origin["request_hash"],
                    *[digest("ti-source", document) for document in origin_documents],
                ],
                "origin_source_fingerprints": sorted(
                    {stamp for document in origin_documents for stamp in source_fingerprints(document)}
                ),
                "state": "candidate",
                "producer": signed.principal,
                "key_id": self.active_key,
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ciphertext).decode(),
                "plan": None,
                "evidence": None,
                "decision": None,
                "validation": None,
                "admission": None,
            }
            self._commit(cx, state)
        return ident

    def freeze(self, signed: SignedEnvelope) -> None:
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "plan", "verifier")
        plan = EvaluationPlan.model_validate(payload["record"])
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            entry = network["entries"][plan.candidate_digest]
            if (
                entry["state"] not in {"candidate", "requires-requalification"}
                or entry["state"] == "requires-requalification"
                and entry.get("revocation")
            ):
                raise Conflict("candidate cannot receive a new plan in this lifecycle state")
            self.library._distinct(signed.principal, "verifier", entry["producer"], "producer")
            origin = self.journal.latest(entry["manifest"]["origin_mission"], cx)
            if origin["digest"] != entry["manifest"]["origin_record_digest"]:
                raise ValueError("originating delivery changed since candidate retention")
            if not set(entry["origin_input_digests"]) <= set(plan.origin_input_digests):
                raise ValueError(
                    "evaluation must exclude the actual originating source ti-source commitments and mission identity"
                )
            if plan.beta_digest != network["beta_digest"] or plan.policy_digest != network["policy_digest"]:
                raise ValueError("evaluation plan uses stale Beta or policy")
            if (
                plan.execution_digest != self.execution_digest
                or network.get("execution_digest") != self.execution_digest
            ):
                raise ValueError("evaluation plan uses an unqualified execution environment")
            exposures = network.setdefault("evaluation_inputs", {})
            source_exposures = network.setdefault("evaluation_sources", {})
            if set(plan.fresh_input_digests) & set(exposures):
                raise ValueError("fresh evaluation cannot reuse a previously exposed input commitment")
            for document in plan.fresh_inputs:
                stamps = source_fingerprints(document)
                if stamps & set(entry["origin_source_fingerprints"]):
                    raise ValueError("fresh evaluation cannot reuse originating source material or identity")
                if stamps & set(source_exposures):
                    raise ValueError("fresh evaluation cannot reuse a previously exposed source identity or text")
                for stamp in stamps:
                    source_exposures[stamp] = plan.candidate_digest
            for input_digest in plan.fresh_input_digests:
                exposures[input_digest] = plan.candidate_digest
            entry.update(
                state="frozen",
                frozen_at=int(time.time()),
                plan=signed.model_dump(),
                evidence=None,
                decision=None,
                validation=None,
                admission=None,
            )
            self._commit(cx, state)

    def evaluate(self, signed: SignedEnvelope) -> str:
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "evidence", "verifier")
        evidence = AlphaEvidence.model_validate(payload["record"])
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            matches = [
                (ident, entry)
                for ident, entry in network["entries"].items()
                if entry["plan"] and digest("flywheel-plan", entry["plan"]) == evidence.plan_digest
            ]
            if len(matches) != 1:
                raise ValueError("evidence does not identify one precommitted evaluation plan")
            ident, entry = matches[0]
            if entry["state"] != "frozen":
                raise Conflict("fresh evidence requires a frozen unassessed candidate")
            plan = EvaluationPlan.model_validate(entry["plan"]["payload"]["record"])
            if (
                signed.principal != entry["plan"]["principal"]
                or plan.beta_digest != network["beta_digest"]
                or plan.policy_digest != network["policy_digest"]
                or plan.execution_digest != self.execution_digest
                or network.get("execution_digest") != self.execution_digest
            ):
                raise ValueError("evidence evaluator, Beta or policy changed")
            if (
                not len(evidence.candidate_runs)
                == len(evidence.beta_runs)
                == len(evidence.acceptance)
                == len(plan.fresh_input_digests)
            ):
                raise ValueError("every fresh case needs both arms and independent acceptance")
            verified = []
            required_costs: list[tuple[str, int]] = []
            all_correct = True
            for expected_input, candidate, beta, acceptance in zip(
                plan.fresh_input_digests, evidence.candidate_runs, evidence.beta_runs, evidence.acceptance
            ):
                runs = []
                for arm, receipt in enumerate((candidate, beta)):
                    raw = self.trust.verify(receipt, "flywheel-frontier-run", "execution")
                    run = FrontierRun.model_validate(raw)
                    self.library._distinct(receipt.principal, "execution", entry["producer"], "producer")
                    self.library._distinct(receipt.principal, "execution", signed.principal, "verifier")
                    if (
                        run.input_digest != expected_input
                        or run.beta_digest != plan.beta_digest
                        or run.tools_digest != plan.matched_tools_digest
                        or run.resource_rules_digest != plan.resource_rules_digest
                        or run.recipient_capabilities_digest != plan.recipient_capabilities_digest
                    ):
                        raise ValueError("execution receipt differs from the matched frozen plan")
                    if run.candidate_digest != (ident if arm == 0 else None):
                        raise ValueError("execution receipt does not bind its actual candidate or Beta arm")
                    if (
                        run.model_id != plan.model_id
                        or run.reasoning_mode != plan.reasoning_mode
                        or run.reasoning_effort != plan.reasoning_effort
                    ):
                        raise ValueError("paired arms require the same precommitted frontier model and reasoning mode")
                    if run.started_at < entry["frozen_at"] or run.finished_at > int(time.time()):
                        raise ValueError("execution preceded candidate freeze")
                    runs.append(run)
                    required_costs.append(
                        (digest("flywheel-frontier-run-record", receipt.model_dump()), run.actual_cost_micro_usd)
                    )
                accepted = self.trust.verify(acceptance, "flywheel-pair-acceptance", "acceptance")
                self.library._distinct(acceptance.principal, "acceptance", signed.principal, "verifier")
                self.library._distinct(acceptance.principal, "acceptance", entry["producer"], "producer")
                for receipt in (candidate, beta):
                    self.library._distinct(acceptance.principal, "acceptance", receipt.principal, "execution")
                expected = {
                    "plan_digest": evidence.plan_digest,
                    "input_digest": expected_input,
                    "candidate_output": runs[0].output_digest,
                    "beta_output": runs[1].output_digest,
                    "candidate_digest": ident,
                }
                if (
                    set(accepted) != {*expected, "candidate_correct", "beta_correct", "evidence_digest"}
                    or any(accepted[k] != v for k, v in expected.items())
                    or any(type(accepted[k]) is not bool for k in ("candidate_correct", "beta_correct"))
                ):
                    raise ValueError("acceptance must bind the exact paired outcomes and frozen candidate")
                all_correct = all_correct and accepted["candidate_correct"] and accepted["beta_correct"]
                verified.append(runs[1].actual_cost_micro_usd - runs[0].actual_cost_micro_usd)
            if evidence.lower_net_saving_per_use_micro_usd > min(verified):
                raise ValueError("conservative saving bound exceeds an observed paired net saving")
            cost_report = self.costs.report(plan.retention_cost_record, cx)
            if not cost_report["bucket_complete"]["B"]:
                raise ValueError("unknown incremental costs prevent a justified net Alpha claim")
            charges = list(self.costs.snapshot(cx)["charges"].values())
            for receipt_digest, amount in required_costs:
                matching = [row for row in charges if row["evidence_digest"] == receipt_digest]
                if (
                    len(matching) != 1
                    or matching[0]["accrued_micro_usd"] != amount
                    or matching[0]["bucket"] != "B"
                    or matching[0]["mission_id"] != plan.retention_cost_record
                ):
                    raise ValueError(
                        "every matched evaluation invocation must be charged exactly once in incremental retention"
                    )
            b_cost = cost_report["costs"]["B"]
            benefit = evidence.lower_net_saving_per_use_micro_usd * plan.planned_reuses
            justified = (
                all_correct
                and not evidence.false_passes
                and not evidence.abstentions
                and benefit > b_cost + plan.remaining_retention_micro_usd
            )
            entry.update(
                state="assessed" if justified else "rejected",
                evidence=signed.model_dump(),
                decision={
                    "justified": justified,
                    "net_lower_micro_usd": benefit - b_cost - plan.remaining_retention_micro_usd,
                    "retention_cost_micro_usd": b_cost,
                    "originating_delivery_A_charged_again": False,
                    "basis": "configured executor, acceptance and evaluator attestations; prospective reuse count is an assumption",
                },
            )
            self._commit(cx, state)
            return str(entry["state"])

    def control(self, signed: SignedEnvelope, action: Literal["validate", "admit", "revoke"]) -> None:
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        role = "verifier" if action == "validate" else "controller"
        payload = self._signed(signed, action, role)
        record = payload["record"]
        if (
            not isinstance(record, dict)
            or set(record) != {"candidate_digest", "previous_digest", "reason", "expires_at"}
            or not isinstance(record["reason"], str)
            or not 1 <= len(record["reason"]) <= 4000
            or type(record["expires_at"]) is not int
        ):
            raise ValueError("control must bind current state, reason and expiry")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            ident = record["candidate_digest"]
            entry = network["entries"][ident]
            if entry.get("archive"):
                raise Conflict("archived lifecycle is terminal; retain a new version")
            if digest("flywheel-entry", entry) != record["previous_digest"]:
                raise Conflict("candidate changed since signed control decision")
            if entry["state"] == "revoked":
                raise Conflict("revocation is terminal; archive a new version")
            self.library._distinct(signed.principal, role, entry["producer"], "producer")
            if action == "revoke":
                entry.update(state="revoked", revocation=signed.model_dump())
                if network["active"].get(entry["manifest"]["skill_id"]) == ident:
                    network["active"].pop(entry["manifest"]["skill_id"])
                changed = {ident}
                for _ in range(len(network["entries"])):
                    added = {
                        key
                        for key, child in network["entries"].items()
                        if key not in changed and set(child["manifest"].get("dependency_digests", [])) & changed
                    }
                    if not added:
                        break
                    for key in added:
                        child = network["entries"][key]
                        if child["state"] not in {"revoked", "rejected"}:
                            child["state"] = "requires-requalification"
                            if network["active"].get(child["manifest"]["skill_id"]) == key:
                                network["active"].pop(child["manifest"]["skill_id"])
                    changed |= added
            else:
                if not int(time.time()) < record["expires_at"] <= int(time.time()) + 30 * 86400:
                    raise ValueError("finite current admission/validation expiry required")
                plan = EvaluationPlan.model_validate(entry["plan"]["payload"]["record"]) if entry["plan"] else None
                if (
                    plan is None
                    or plan.beta_digest != network["beta_digest"]
                    or plan.policy_digest != network["policy_digest"]
                    or plan.execution_digest != self.execution_digest
                    or network.get("execution_digest") != self.execution_digest
                ):
                    raise ValueError("control uses stale evaluation bindings")
                if action == "validate":
                    if entry["state"] != "assessed":
                        raise Conflict("validation cannot bypass justified Alpha assessment")
                    self.library._distinct(signed.principal, role, entry["evidence"]["principal"], "verifier")
                    entry.update(state="validated", validation=signed.model_dump())
                else:
                    if entry["state"] != "validated":
                        raise Conflict("admission cannot bypass separate validation")
                    self.library._distinct(signed.principal, role, entry["validation"]["principal"], "verifier")
                    self.library._distinct(signed.principal, role, entry["evidence"]["principal"], "verifier")
                    if entry["validation"]["payload"]["record"]["expires_at"] <= int(time.time()):
                        raise ValueError("validation expired")
                    self._dependencies(network, entry)
                    entry.update(state="admitted", admission=signed.model_dump())
                    network["active"][entry["manifest"]["skill_id"]] = ident
            self._commit(cx, state)

    def _dependencies(
        self,
        network: dict[str, Any],
        entry: dict[str, Any],
        *,
        checked: set[str] | None = None,
        deadline_ns: int | None = None,
    ) -> None:
        checked = set() if checked is None else checked
        deadline_ns = time.monotonic_ns() + 1_000_000_000 if deadline_ns is None else deadline_ns
        visiting: set[str] = set()
        stack = [(ident, False) for ident in reversed(entry["manifest"]["dependency_digests"])]
        while stack:
            if time.monotonic_ns() >= deadline_ns:
                raise Conflict("dependency verification budget exhausted; no partial authorization")
            ident, finished = stack.pop()
            if finished:
                visiting.remove(ident)
                checked.add(ident)
                continue
            if ident in visiting:
                raise ValueError("cyclic capsule dependencies are unsupported")
            if ident in checked:
                continue
            child = self._eligible(network, ident)
            visiting.add(ident)
            stack.append((ident, True))
            stack.extend((dep, False) for dep in reversed(child["manifest"]["dependency_digests"]))

    def _eligible(self, network: dict[str, Any], ident: str) -> dict[str, Any]:
        entry = network["entries"][ident]
        if entry["state"] != "admitted" or network["active"].get(entry["manifest"]["skill_id"]) != ident:
            raise Conflict("capsule is not currently admitted and active")
        plan = entry["plan"]["payload"]["record"]
        if (
            plan.get("execution_digest") != self.execution_digest
            or network.get("execution_digest") != self.execution_digest
        ):
            raise Conflict("capsule requires requalification in this execution environment")
        if plan["beta_digest"] != network["beta_digest"] or plan["policy_digest"] != network["policy_digest"]:
            raise Conflict("capsule requires fresh Beta/policy requalification")
        self.trust.anchor(entry["producer"], "producer")
        for field, role, domain in (
            ("evidence", "verifier", "evidence"),
            ("validation", "verifier", "validate"),
            ("admission", "controller", "admit"),
        ):
            self._signed(SignedEnvelope.model_validate(entry[field]), domain, role)
        evidence = AlphaEvidence.model_validate(entry["evidence"]["payload"]["record"])
        for receipt in [*evidence.candidate_runs, *evidence.beta_runs]:
            self.trust.verify(receipt, "flywheel-frontier-run", "execution")
        for receipt in evidence.acceptance:
            self.trust.verify(receipt, "flywheel-pair-acceptance", "acceptance")
        if min(entry[field]["payload"]["record"]["expires_at"] for field in ("validation", "admission")) <= int(
            time.time()
        ):
            raise Conflict("capsule validation or admission expired")
        return cast(dict[str, Any], entry)

    def manifest(self, ident: str, proof: AccessRequest) -> dict[str, Any]:
        prepared = self.access.prepare(
            proof, ident, "discover", digest("flywheel-discover", {"candidate_digest": ident})
        )
        with self.journal.transaction() as cx:
            _, network = self._state(cx)
            entry = self._eligible(network, ident)
            self._dependencies(network, entry)
            authorization = self.access.consume(prepared, cx)
            self.checkpoint.advance(self.journal, cx)
            return {
                "manifest": copy.deepcopy(entry["manifest"]),
                "state": entry["state"],
                "authorization": authorization,
                "export": "controlled-invocation-only",
            }

    def catalog_resource(self) -> str:
        """One deterministic public identifier names the protected discovery resource."""
        return digest("flywheel-catalog-resource", self.access.service.model_dump())

    def catalog(self, proof: AccessRequest) -> dict[str, Any]:
        """Every eligible agent may discover current available manifests after fresh proof."""
        resource = self.catalog_resource()
        prepared = self.access.prepare(
            proof, resource, "discover", digest("flywheel-catalog-request", {"resource": resource})
        )
        with self.journal.transaction() as cx:
            _, network = self._state(cx)
            authority = self.access.consume(prepared, cx)
            manifests = []
            checked: set[str] = set()
            deadline = time.monotonic_ns() + 1_000_000_000
            for ident in network["active"].values():
                if time.monotonic_ns() >= deadline:
                    raise Conflict("catalog verification budget exhausted; no partial disclosure")
                try:
                    entry = network["entries"][ident] if ident in checked else self._eligible(network, ident)
                    self._dependencies(network, entry, checked=checked, deadline_ns=deadline)
                    checked.add(ident)
                except (KeyError, ValueError, Conflict):
                    continue
                manifests.append(
                    {"candidate_digest": ident, "manifest": copy.deepcopy(entry["manifest"]), "state": "admitted"}
                )
            if time.monotonic_ns() >= deadline:
                raise Conflict("catalog verification budget exhausted; no partial disclosure")
            self.checkpoint.advance(self.journal, cx)
            return {
                "manifests": manifests,
                "authorization": authority,
                "policy_digest": network["policy_digest"],
                "beta_digest": network["beta_digest"],
                "export": "controlled-invocation-only",
            }

    def invoke(self, ident: str, invocation: Invocation, proof: AccessRequest) -> dict[str, Any]:
        invocation = Invocation.model_validate(invocation.model_dump())
        if len(canonical(invocation)) > MAX_INVOCATION_INPUT_BYTES:
            raise ValueError("invocation input exceeds the durable record budget")
        request_hash = digest("flywheel-invocation", invocation)
        prepared = self.access.prepare(proof, ident, "invoke", request_hash)
        activity = "reuse/" + invocation.mission_id
        attempt_digest = digest(
            "flywheel-invocation-attempt",
            {"candidate_digest": ident, "mission_id": invocation.mission_id, "request_digest": request_hash},
        )
        pending = Charge(
            activity_id=activity,
            mission_id=invocation.mission_id,
            bucket="B",
            category="compute",
            accrued_micro_usd=None,
            paid_micro_usd=0,
            basis="unknown",
            evidence_digest=attempt_digest,
            note="Durably reserved before bounded execution, including crashes; all-resource reconciliation remains required",
        )
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            entry = self._eligible(network, ident)
            self._dependencies(network, entry)
            if (
                invocation.beta_digest != network["beta_digest"]
                or invocation.policy_digest != network["policy_digest"]
                or not set(entry["manifest"]["prerequisites"]) <= set(invocation.prerequisite_digests)
            ):
                raise ValueError("invocation has stale context or missing prerequisites")
            source = digest("ti-source", invocation.document)
            plan = entry["plan"]["payload"]["record"]
            if source in {*plan["fresh_input_digests"], *plan["origin_input_digests"]} or source in network.get(
                "evaluation_inputs", {}
            ):
                raise ValueError("reuse requires fresh work outside all historical development/evaluation exposure")
            stamps = source_fingerprints(invocation.document)
            if stamps & (set(entry["origin_source_fingerprints"]) | set(network.get("evaluation_sources", {}))):
                raise ValueError(
                    "reuse requires fresh source material outside origin and historical evaluation exposure"
                )
            try:
                self.journal.latest(self._invocation_key(invocation.mission_id), cx)
            except KeyError:
                pass
            else:
                raise Conflict("mission invocation already attempted; inspect durable receipt")
            costs = self.costs.snapshot(cx)
            self.costs.require_open(costs, invocation.mission_id, "B")
            if activity in costs["charges"]:
                raise Conflict("invocation cost activity already exists")
            report = self.costs.report(cx=cx)
            if report["available_funds"] is None or report["available_funds"] < invocation.cost_cap_micro_usd:
                raise Conflict("finite available funds cannot cover this invocation's cost cap")
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("agent is stopped")
            authority = self.access.consume(prepared, cx)
            peer_identity = (
                authority["name"] != entry["manifest"]["origin_agent"]
                and authority["wallet"] != entry["manifest"]["origin_wallet"]
            )
            receipt = {
                "candidate_digest": ident,
                "request_digest": request_hash,
                "attempt_digest": attempt_digest,
                "input_digest": source,
                "beta_digest": invocation.beta_digest,
                "policy_digest": invocation.policy_digest,
                "recipient_capabilities_digest": invocation.recipient_capabilities_digest,
                "authorization": authority,
                "logical_units": 0,
                "elapsed_ns": None,
                "started_at": int(time.time()),
                "finished_at": None,
                "result": None,
                "error": None,
                "status": "executing-or-uncertain",
                "successful_reuse": False,
                "peer_identity": peer_identity,
                "successful_peer_reuse": False,
                "additional_value": None,
                "cost_cap_micro_usd": invocation.cost_cap_micro_usd,
                "execution": "installed-closed-selector; no frontier inference in this invocation",
                "execution_digest": self.execution_digest,
                "qualification_digest": digest("flywheel-plan", entry["plan"]),
            }
            costs["charges"][activity] = {**pending.model_dump(), "signed": None}
            self.journal.append(
                cx,
                self._invocation_key(invocation.mission_id),
                {"request": invocation.model_dump(), "receipt": receipt},
            )
            self._cache_invocation(network, invocation.mission_id, receipt)
            self.costs._persist(cx, costs)
            self._commit(cx, state)
            # This committed reservation survives process interruption. No paid or
            # local computation precedes accounting eligibility and consumption.
        used, started = 0, time.monotonic_ns()

        def charge(units: int) -> None:
            nonlocal used
            used += units
            if used > invocation.logical_limit or time.monotonic_ns() - started > 2_000_000_000:
                raise TimeoutError("bounded selector exhausted its logical or time allowance")
            if self.journal.latest("@control")["state"] != "ready":
                raise PermissionError("agent stopped during bounded execution")

        result, error = None, None
        try:
            aad = canonical(
                {"service": self.access.service.model_dump(), "journal": self.journal.identity, "manifest": ident}
            )
            program = SelectionProgram.model_validate(
                safe_json_loads(
                    AESGCM(self.keys[entry["key_id"]]).decrypt(
                        base64.b64decode(entry["nonce"], validate=True),
                        base64.b64decode(entry["ciphertext"], validate=True),
                        aad,
                    )
                )
            )
            if digest("flywheel-program", program) != entry["manifest"]["content_digest"]:
                raise ValueError("private implementation digest mismatch")
            result = execute_selection(invocation.document, program, invocation.charter, charge)
        except Exception as exc:
            error = type(exc).__name__
        receipt.update(
            logical_units=used,
            elapsed_ns=time.monotonic_ns() - started,
            finished_at=int(time.time()),
            result=result,
            error=error,
            status="executed-awaiting-acceptance-and-complete-cost" if result is not None else "failed",
        )
        try:
            if len(canonical({"request": invocation, "receipt": receipt})) > MAX_INVOCATION_RECORD_BYTES:
                raise ValueError("result exceeds durable record budget")
        except (TypeError, ValueError):
            receipt.update(result=None, status="failed", error="OutputStorageBudgetExceeded")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            stored = self.journal.document(self.journal.latest(self._invocation_key(invocation.mission_id), cx))
            current = stored["receipt"]
            if current["status"] != "executing-or-uncertain" or current["attempt_digest"] != attempt_digest:
                raise Conflict("invocation changed; preserve its durable uncertain attempt")
            self.journal.append(cx, self._invocation_key(invocation.mission_id), {**stored, "receipt": receipt})
            self._cache_invocation(network, invocation.mission_id, receipt)
            self._commit(cx, state)
        return copy.deepcopy(receipt)

    def accept_reuse(self, signed: SignedEnvelope) -> dict[str, Any]:
        """Useful accepted reuse and attributable benefit require their own evidence."""
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "reuse-acceptance", "acceptance")
        record = ReuseAcceptance.model_validate(payload["record"])
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            stored = self.journal.document(self.journal.latest(self._invocation_key(record.mission_id), cx))
            if stored.get("legacy_unqualified"):
                raise Conflict("legacy unqualified receipt cannot become qualified reuse")
            receipt = stored["receipt"]
            entry = self._eligible(network, receipt["candidate_digest"])
            self._dependencies(network, entry)
            current_plan = entry["plan"]["payload"]["record"]
            if (
                receipt["beta_digest"] != current_plan["beta_digest"]
                or receipt["policy_digest"] != current_plan["policy_digest"]
                or receipt["execution_digest"] != self.execution_digest
                or receipt["qualification_digest"] != digest("flywheel-plan", entry["plan"])
            ):
                raise ValueError("reuse receipt uses a superseded qualification context")
            if (
                receipt["status"] != "executed-awaiting-acceptance-and-complete-cost"
                or digest("flywheel-reuse-receipt", receipt) != record.receipt_digest
            ):
                raise Conflict("reuse acceptance must identify one actual unfinished execution receipt")
            baseline = FrontierRun.model_validate(
                self.trust.verify(record.beta_run, "flywheel-frontier-run", "execution")
            )
            self.library._distinct(signed.principal, "acceptance", record.beta_run.principal, "execution")
            self.library._distinct(signed.principal, "acceptance", entry["producer"], "producer")
            self.library._distinct(record.beta_run.principal, "execution", entry["producer"], "producer")
            self.library._distinct(record.beta_run.principal, "execution", entry["evidence"]["principal"], "verifier")
            plan = EvaluationPlan.model_validate(entry["plan"]["payload"]["record"])
            if (
                baseline.input_digest != receipt["input_digest"]
                or baseline.candidate_digest is not None
                or baseline.beta_digest != receipt["beta_digest"]
                or baseline.tools_digest != plan.matched_tools_digest
                or baseline.resource_rules_digest != plan.resource_rules_digest
                or baseline.model_id != plan.model_id
                or baseline.reasoning_mode != plan.reasoning_mode
                or baseline.reasoning_effort != plan.reasoning_effort
                or baseline.recipient_capabilities_digest != receipt["recipient_capabilities_digest"]
            ):
                raise ValueError("fresh reuse baseline differs from the current matched scope")
            if baseline.started_at < receipt["authorization"]["request_committed_at"] or baseline.finished_at > int(
                time.time()
            ):
                raise ValueError("reuse baseline must execute inside the fresh request window")
            costs = self.costs.report(record.mission_id, cx)
            if not costs["complete"] or not costs["bucket_complete"]["B"]:
                raise ValueError("complete reconciled reuse and failed-attempt costs are required")
            baseline_digest = digest("flywheel-frontier-run-record", record.beta_run.model_dump())
            baseline_charges = [
                row for row in self.costs.snapshot(cx)["charges"].values() if row["evidence_digest"] == baseline_digest
            ]
            if (
                len(baseline_charges) != 1
                or baseline_charges[0]["mission_id"] != record.mission_id
                or baseline_charges[0]["bucket"] != "B"
                or baseline_charges[0]["accrued_micro_usd"] != baseline.actual_cost_micro_usd
            ):
                raise ValueError("actual reuse comparison must be charged exactly once in incremental costs")
            accepted = record.candidate_correct and record.beta_correct
            peer_identity = (
                receipt["authorization"]["name"] != entry["manifest"]["origin_agent"]
                and receipt["authorization"]["wallet"] != entry["manifest"]["origin_wallet"]
            )
            benefit = baseline.actual_cost_micro_usd - sum(costs["costs"].values())
            receipt.update(
                status="reused-accepted" if accepted else "reuse-rejected",
                successful_reuse=accepted,
                peer_identity=peer_identity,
                successful_peer_reuse=accepted and peer_identity,
                additional_value=benefit if accepted else None,
                comparison_cost_micro_usd=baseline.actual_cost_micro_usd,
                operating_saving_before_comparison_micro_usd=benefit + baseline.actual_cost_micro_usd
                if accepted
                else None,
                acceptance=signed.model_dump(),
                baseline_output_digest=baseline.output_digest,
                cost_report=costs,
            )
            if len(canonical({**stored, "receipt": receipt})) > MAX_INVOCATION_RECORD_BYTES:
                raise ValueError("acceptance evidence exceeds the durable record budget")
            self.journal.append(cx, self._invocation_key(record.mission_id), {**stored, "receipt": receipt})
            self._cache_invocation(network, record.mission_id, receipt)
            self._commit(cx, state)
            return copy.deepcopy(receipt)

    def _archive_entry(self, cx: Any, ident: str, entry: dict[str, Any], provenance: str) -> dict[str, Any]:
        key = "@flywheel-capsule-archive:" + ident
        binding = digest("flywheel-entry", entry)
        self.journal.append(cx, key, {"entry": entry, "entry_digest": binding, "provenance": provenance})
        return {
            "manifest": {name: entry["manifest"][name] for name in ("skill_id", "version")},
            "state": entry["state"],
            "producer": entry["producer"],
            "plan": None,
            "evidence": None,
            "archive": {"journal_key": key, "entry_digest": binding},
        }

    def archive(self, signed: SignedEnvelope) -> dict[str, Any]:
        """Compact only terminal entries; immutable encrypted history stays in this Journal."""
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "archive", "controller")
        record = payload["record"]
        if (
            not isinstance(record, dict)
            or set(record) != {"candidate_digest", "previous_digest", "reason"}
            or not isinstance(record["reason"], str)
            or not 1 <= len(record["reason"]) <= 4000
        ):
            raise ValueError("archive requires exact current entry and reason")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            ident = record["candidate_digest"]
            entry = network["entries"][ident]
            if entry.get("archive") or entry["state"] not in {"revoked", "rejected"}:
                raise Conflict("only terminal inactive entries can be archived")
            if digest("flywheel-entry", entry) != record["previous_digest"]:
                raise Conflict("entry changed since archive decision")
            self.library._distinct(signed.principal, "controller", entry["producer"], "producer")
            terminal = self._archive_entry(cx, ident, entry, "signed-terminal-archive/v1")
            network["entries"][ident] = terminal
            self._commit(cx, state)
            return copy.deepcopy(terminal["archive"])

    def migrate(self, signed: SignedEnvelope) -> None:
        """Explicitly retire unqualified pre-release storage, preserving every original record."""
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "migrate", "controller")
        record = payload["record"]
        if (
            not isinstance(record, dict)
            or set(record) != {"previous_digest", "reason"}
            or not isinstance(record["reason"], str)
            or not 1 <= len(record["reason"]) <= 4000
        ):
            raise ValueError("migration requires exact pre-release state and retirement reason")
        self._check_custody_files()
        with self.journal.transaction() as cx:
            self.checkpoint.verify(self.journal, cx)
            if self.journal.latest("@control", cx)["state"] != "paused":
                raise Conflict("stop the runtime before retiring unqualified pre-release state")
            state = self.journal.document(self.journal.latest(KEY, cx))
            old = state[BRANCH]
            if old.get("storage_schema") not in {None, 1}:
                raise Conflict("pre-release migration does not reinterpret current or future storage")
            binding = digest("flywheel-pre-release-state", old)
            if binding != record["previous_digest"]:
                raise Conflict("pre-release state changed since migration approval")
            self.journal.append(
                cx,
                "@flywheel-pre-release:" + binding,
                {"network": old, "signed": signed.model_dump(), "qualification": "unqualified-pre-release"},
            )
            network = {
                **old,
                "storage_schema": 2,
                "entries": {},
                "active": {},
                "operations": {},
                "history": [],
                "invocations": {},
                "beta_digest": None,
                "policy_digest": None,
                "execution_digest": None,
            }
            for ident, entry in old["entries"].items():
                terminal = self._archive_entry(cx, ident, entry, "unqualified-pre-release-retirement/v1")
                terminal["state"] = "revoked"
                network["entries"][ident] = terminal
            for operation, fingerprint in old.get("operations", {}).items():
                key = "@flywheel-operation:" + operation
                try:
                    self.journal.latest(key, cx)
                except KeyError:
                    self.journal.append(cx, key, {"legacy_operation_digest": fingerprint})
            for mission, receipt in old.get("invocations", {}).items():
                if "request_digest" not in receipt:
                    continue
                self.journal.append(
                    cx,
                    self._invocation_key(mission),
                    {
                        "request": None,
                        "receipt": receipt,
                        "legacy_unqualified": True,
                        "request_recovery": "original request was not retained by the pre-release format",
                    },
                )
                self._cache_invocation(network, mission, {**receipt, "status": "legacy-unqualified"})
            state[BRANCH] = network
            self._begin(network, signed, cx)
            self._commit(cx, state)

    def rotate(self, signed: SignedEnvelope) -> None:
        """Reencrypt under a separately provisioned key; preserve historical key custody."""
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "rotate-key", "controller")
        if payload["record"] != {"target_key_id": self.active_key}:
            raise ValueError("rotation must bind the separately provisioned active key")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed, cx)
            for ident, entry in network["entries"].items():
                if entry.get("archive"):
                    continue
                if entry["key_id"] == self.active_key:
                    continue
                aad = canonical(
                    {"service": self.access.service.model_dump(), "journal": self.journal.identity, "manifest": ident}
                )
                plaintext = AESGCM(self.keys[entry["key_id"]]).decrypt(
                    base64.b64decode(entry["nonce"], validate=True),
                    base64.b64decode(entry["ciphertext"], validate=True),
                    aad,
                )
                nonce = secrets.token_bytes(12)
                ciphertext = AESGCM(self.keys[self.active_key]).encrypt(nonce, plaintext, aad)
                entry.update(
                    key_id=self.active_key,
                    nonce=base64.b64encode(nonce).decode(),
                    ciphertext=base64.b64encode(ciphertext).decode(),
                )
            self._commit(cx, state)


class ReuseAcceptance(StrictModel):
    mission_id: Identifier
    receipt_digest: Digest
    beta_run: SignedEnvelope
    candidate_correct: bool
    beta_correct: bool
    independent_tests_digest: Digest
    residual_interventions_digest: Digest
    limitations: Text
