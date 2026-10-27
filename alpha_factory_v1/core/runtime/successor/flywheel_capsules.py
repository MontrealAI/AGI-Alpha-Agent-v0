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
from typing import Any, Literal, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag
from pydantic import Field, model_validator

from ..store import Conflict
from ..chain import address
from .flywheel_access import AccessRequest, ResourceAccess, direct_name
from .flywheel_costs import Charge, CostLedger, KEY as COST_KEY
from .flywheel_checkpoint import DurableCheckpoint
from .protocol import Digest, Identifier, StrictModel, Text, canonical, digest, safe_json_loads
from .transformation import IntentCharter, SelectionProgram, SourceDocument, execute_selection, assert_public_content
from .transformation_library import KEY, TransformationLibrary
from .trust import SignedEnvelope

BRANCH = "protected_network_v1"


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
    model_id: str = Field(min_length=1, max_length=200)
    reasoning_mode: str = Field(min_length=1, max_length=100)
    policy_digest: Digest
    matched_tools_digest: Digest
    resource_rules_digest: Digest
    recipient_capabilities_digest: Digest
    retention_cost_record: Identifier
    origin_input_digests: list[Digest] = Field(min_length=1, max_length=128)
    fresh_input_digests: list[Digest] = Field(min_length=2, max_length=128)
    planned_reuses: int = Field(ge=1, le=100_000)
    remaining_retention_micro_usd: int = Field(ge=0, le=10**15)
    prospective_basis: Text

    @model_validator(mode="after")
    def disjoint_inputs(self) -> EvaluationPlan:
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
    reasoning_mode: str = Field(min_length=1, max_length=100)
    tools_digest: Digest
    resource_rules_digest: Digest
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
        with self.journal.transaction() as cx:
            state = self.library.snapshot()
            if BRANCH not in state:
                state[BRANCH] = {
                    "entries": {},
                    "active": {},
                    "beta_digest": None,
                    "policy_digest": None,
                    "history": [],
                    "operations": {},
                    "invocations": {},
                }
                self._commit(cx, state)

    def _commit(self, cx: Any, state: dict[str, Any]) -> None:
        canonical(state)
        self.journal.append(cx, KEY, state)
        self.checkpoint.advance(self.journal, cx)

    def _state(self, cx: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        self.checkpoint.verify(self.journal, cx)
        state = self.journal.document(self.journal.latest(KEY, cx))
        return state, state[BRANCH]

    def _signed(self, signed: SignedEnvelope, action: str, role: str) -> dict[str, Any]:
        payload = self.trust.verify(signed, "flywheel-" + action, role)
        if (
            set(payload) != {"journal_identity", "operation_id", "record"}
            or payload["journal_identity"] != self.journal.identity
        ):
            raise ValueError("protected transition requires exact journal-bound signed terms")
        return payload

    def _begin(self, network: dict[str, Any], signed: SignedEnvelope) -> str:
        payload = signed.payload
        operation = payload["operation_id"]
        if not isinstance(operation, str) or not 1 <= len(operation) <= 128:
            raise ValueError("bounded protected operation identity required")
        if operation in network["operations"]:
            raise Conflict("protected transition already consumed; inspect current durable state")
        if len(network["operations"]) >= 4096:
            raise Conflict("protected library capacity reached")
        network["operations"][operation] = digest("flywheel-operation", signed.model_dump())
        network["history"].append({"signed": signed.model_dump(), "at": int(time.time())})
        return operation

    def configure(self, signed: SignedEnvelope) -> None:
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "configure", "controller")
        record = payload["record"]
        if (
            not isinstance(record, dict)
            or set(record) != {"beta_digest", "policy_digest"}
            or any(
                not isinstance(v, str) or len(v) != 64 or any(c not in "0123456789abcdef" for c in v)
                for v in record.values()
            )
        ):
            raise ValueError("current Beta and policy commitments required")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed)
            if record != {k: network[k] for k in record}:
                network.update(record)
                network["active"] = {}
                for entry in network["entries"].values():
                    if entry["state"] not in {"revoked", "rejected"}:
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
        nonce = secrets.token_bytes(12)
        aad = canonical(
            {"service": self.access.service.model_dump(), "journal": self.journal.identity, "manifest": ident}
        )
        ciphertext = AESGCM(self.keys[self.active_key]).encrypt(nonce, canonical(program), aad)
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed)
            if ident in network["entries"] or len(network["entries"]) >= 128:
                raise Conflict("duplicate candidate or capsule capacity reached")
            versions = [
                e["manifest"]["version"]
                for e in network["entries"].values()
                if e["manifest"]["skill_id"] == manifest.skill_id
            ]
            if manifest.version != max(versions, default=0) + 1:
                raise Conflict("capsule versions must advance without replacing history")
            origin = self.journal.latest(manifest.origin_mission, cx)
            if origin["digest"] != manifest.origin_record_digest or origin.get("state") != "accepted":
                raise ValueError("candidate must originate in this journal's exact accepted delivery")
            if not self.costs.report(manifest.origin_mission, cx)["complete"]:
                raise ValueError("originating delivery costs remain incomplete")
            wallet = self.journal.latest("@wallet", cx)
            if wallet["address"] != manifest.origin_wallet:
                raise ValueError("origin wallet must be proved through the existing runtime wallet binding")
            origin_authority = self.access.authority.verify(manifest.origin_agent, manifest.origin_wallet)
            network["entries"][ident] = {
                "manifest": manifest.model_dump(),
                "origin_authorization": origin_authority,
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
            self._begin(network, signed)
            entry = network["entries"][plan.candidate_digest]
            if (
                entry["state"] not in {"candidate", "requires-requalification"}
                or entry["state"] == "requires-requalification"
                and entry.get("revocation")
            ):
                raise Conflict("candidate cannot receive a new plan in this lifecycle state")
            self.library._distinct(signed.principal, "verifier", entry["producer"], "producer")
            origin = self.journal.latest(entry["manifest"]["origin_mission"], cx)
            if origin.get("request_hash") not in plan.origin_input_digests:
                raise ValueError("evaluation must exclude the originating delivery's actual input commitment")
            if plan.beta_digest != network["beta_digest"] or plan.policy_digest != network["policy_digest"]:
                raise ValueError("evaluation plan uses stale Beta or policy")
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
            self._begin(network, signed)
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
                    ):
                        raise ValueError("execution receipt differs from the matched frozen plan")
                    if run.candidate_digest != (ident if arm == 0 else None):
                        raise ValueError("execution receipt does not bind its actual candidate or Beta arm")
                    if run.model_id != plan.model_id or run.reasoning_mode != plan.reasoning_mode:
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
            if not cost_report["complete"]:
                raise ValueError("unknown incremental costs prevent a justified net Alpha claim")
            charges = self.costs.snapshot(cx)["charges"].values()
            retained_costs = [
                row for row in charges if row["bucket"] == "B" and row["mission_id"] == plan.retention_cost_record
            ]
            for receipt_digest, amount in required_costs:
                matching = [row for row in retained_costs if row["evidence_digest"] == receipt_digest]
                if len(matching) != 1 or matching[0]["accrued_micro_usd"] != amount:
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
            self._begin(network, signed)
            ident = record["candidate_digest"]
            entry = network["entries"][ident]
            if digest("flywheel-entry", entry) != record["previous_digest"]:
                raise Conflict("candidate changed since signed control decision")
            if entry["state"] == "revoked":
                raise Conflict("revocation is terminal; archive a new version")
            self.library._distinct(signed.principal, role, entry["producer"], "producer")
            if action == "revoke":
                entry.update(state="revoked", revocation=signed.model_dump())
                network["active"].pop(entry["manifest"]["skill_id"], None)
                changed = {ident}
                for _ in range(len(network["entries"])):
                    added = {
                        key
                        for key, child in network["entries"].items()
                        if key not in changed and set(child["manifest"]["dependency_digests"]) & changed
                    }
                    if not added:
                        break
                    for key in added:
                        child = network["entries"][key]
                        if child["state"] not in {"revoked", "rejected"}:
                            child["state"] = "requires-requalification"
                            network["active"].pop(child["manifest"]["skill_id"], None)
                    changed |= added
            else:
                if not int(time.time()) < record["expires_at"] <= int(time.time()) + 30 * 86400:
                    raise ValueError("finite current admission/validation expiry required")
                plan = EvaluationPlan.model_validate(entry["plan"]["payload"]["record"]) if entry["plan"] else None
                if (
                    plan is None
                    or plan.beta_digest != network["beta_digest"]
                    or plan.policy_digest != network["policy_digest"]
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

    def _dependencies(self, network: dict[str, Any], entry: dict[str, Any], seen: set[str] | None = None) -> None:
        seen = set() if seen is None else seen
        for ident in entry["manifest"]["dependency_digests"]:
            if ident in seen:
                raise ValueError("cyclic capsule dependencies are unsupported")
            self._eligible(network, ident)
            self._dependencies(network, network["entries"][ident], seen | {ident})

    def _eligible(self, network: dict[str, Any], ident: str) -> dict[str, Any]:
        entry = network["entries"][ident]
        if entry["state"] != "admitted" or network["active"].get(entry["manifest"]["skill_id"]) != ident:
            raise Conflict("capsule is not currently admitted and active")
        plan = entry["plan"]["payload"]["record"]
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
        with self.journal.transaction() as cx:
            _, network = self._state(cx)
            entry = self._eligible(network, ident)
            self._dependencies(network, entry)
            authorization = self.access.verify(
                proof, ident, "discover", digest("flywheel-discover", {"candidate_digest": ident}), cx
            )
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
        with self.journal.transaction() as cx:
            _, network = self._state(cx)
            authority = self.access.verify(
                proof, resource, "discover", digest("flywheel-catalog-request", {"resource": resource}), cx
            )
            manifests = []
            for ident in network["active"].values():
                try:
                    entry = self._eligible(network, ident)
                    self._dependencies(network, entry)
                except (KeyError, ValueError, Conflict):
                    continue
                manifests.append(
                    {"candidate_digest": ident, "manifest": copy.deepcopy(entry["manifest"]), "state": "admitted"}
                )
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
        request_hash = digest("flywheel-invocation", invocation)
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
            if source in {*plan["fresh_input_digests"], *plan["origin_input_digests"]}:
                raise ValueError("peer reuse requires fresh work outside development/evaluation")
            if invocation.mission_id in network["invocations"]:
                raise Conflict("mission invocation already attempted; inspect durable receipt")
            report = self.costs.report(cx=cx)
            if report["available_funds"] is None or report["available_funds"] < invocation.cost_cap_micro_usd:
                raise Conflict("finite available funds cannot cover this invocation's cost cap")
            if self.journal.latest("@control", cx)["state"] != "ready":
                raise Conflict("agent is stopped")
            authority = self.access.verify(proof, ident, "invoke", request_hash, cx)
            if (
                authority["name"] == entry["manifest"]["origin_agent"]
                or authority["wallet"] == entry["manifest"]["origin_wallet"]
            ):
                raise ValueError("peer reuse requires a different eligible originating agent")
            used, started = 0, time.monotonic_ns()

            def charge(units: int) -> None:
                nonlocal used
                used += units
                if used > invocation.logical_limit or time.monotonic_ns() - started > 2_000_000_000:
                    raise TimeoutError("bounded selector exhausted its logical or time allowance")

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
            except (ValueError, PermissionError, TimeoutError, KeyError, InvalidTag) as exc:
                error = type(exc).__name__
            receipt = {
                "candidate_digest": ident,
                "request_digest": request_hash,
                "input_digest": source,
                "beta_digest": invocation.beta_digest,
                "policy_digest": invocation.policy_digest,
                "authorization": authority,
                "logical_units": used,
                "elapsed_ns": time.monotonic_ns() - started,
                "result": result,
                "error": error,
                "status": "executed-awaiting-acceptance-and-complete-cost" if result is not None else "failed",
                "successful_reuse": False,
                "additional_value": None,
                "cost_cap_micro_usd": invocation.cost_cap_micro_usd,
                "execution": "installed-closed-selector; no frontier inference in this invocation",
            }
            activity = "reuse/" + invocation.mission_id
            costs = self.costs.snapshot(cx)
            if activity in costs["charges"]:
                raise Conflict("invocation cost activity already exists")
            pending = Charge(
                activity_id=activity,
                mission_id=invocation.mission_id,
                bucket="B",
                category="compute",
                accrued_micro_usd=None,
                paid_micro_usd=0,
                basis="unknown",
                evidence_digest=digest("flywheel-reuse-receipt", receipt),
                note="All attempted execution, including failures; complete compute, tools, acceptance and overhead reconciliation remains required",
            )
            costs["charges"][activity] = {**pending.model_dump(), "signed": None}
            network["invocations"][invocation.mission_id] = receipt
            self.journal.append(cx, COST_KEY, costs)
            self._commit(cx, state)
            return copy.deepcopy(receipt)

    def accept_reuse(self, signed: SignedEnvelope) -> dict[str, Any]:
        """Useful accepted reuse and attributable benefit require their own evidence."""
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "reuse-acceptance", "acceptance")
        record = ReuseAcceptance.model_validate(payload["record"])
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed)
            receipt = network["invocations"][record.mission_id]
            entry = self._eligible(network, receipt["candidate_digest"])
            self._dependencies(network, entry)
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
            plan = EvaluationPlan.model_validate(entry["plan"]["payload"]["record"])
            if (
                baseline.input_digest != receipt["input_digest"]
                or baseline.candidate_digest is not None
                or baseline.beta_digest != receipt["beta_digest"]
                or baseline.tools_digest != plan.matched_tools_digest
                or baseline.resource_rules_digest != plan.resource_rules_digest
                or baseline.model_id != plan.model_id
                or baseline.reasoning_mode != plan.reasoning_mode
            ):
                raise ValueError("fresh reuse baseline differs from the current matched scope")
            costs = self.costs.report(record.mission_id, cx)
            if not costs["complete"]:
                raise ValueError("complete reconciled reuse and failed-attempt costs are required")
            accepted = record.candidate_correct and record.beta_correct
            benefit = baseline.actual_cost_micro_usd - sum(costs["costs"].values())
            receipt.update(
                status="reused-accepted" if accepted else "reuse-rejected",
                successful_reuse=accepted,
                additional_value=benefit if accepted else None,
                acceptance=signed.model_dump(),
                baseline_output_digest=baseline.output_digest,
                cost_report=costs,
            )
            self._commit(cx, state)
            return copy.deepcopy(receipt)

    def rotate(self, signed: SignedEnvelope) -> None:
        """Reencrypt under a separately provisioned key; preserve historical key custody."""
        signed = SignedEnvelope.model_validate(copy.deepcopy(signed.model_dump()))
        payload = self._signed(signed, "rotate-key", "controller")
        if payload["record"] != {"target_key_id": self.active_key}:
            raise ValueError("rotation must bind the separately provisioned active key")
        with self.journal.transaction() as cx:
            state, network = self._state(cx)
            self._begin(network, signed)
            for ident, entry in network["entries"].items():
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
