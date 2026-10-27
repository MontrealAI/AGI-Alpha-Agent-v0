# SPDX-License-Identifier: Apache-2.0
"""BeyondBeta research lifecycle: supplied evidence, fixture authority, real crypto.

This is an offline graph/admission adapter, not a new agent executor. Identity and
permissions are explicit fixtures. AES-GCM encryption and Ed25519 verification
execute, but no ENS resolution, EIP-712, ZK proof, chain or live credential exists.
"""
from __future__ import annotations
import base64
from copy import deepcopy
from decimal import Decimal, localcontext, ROUND_CEILING
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import uuid

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

# Reuse only the unchanged, parity-tested direct-agent eligibility primitive.
_native_path = Path(__file__).resolve().parents[2] / "venture_creation/src/authority_fixture.py"
_spec = importlib.util.spec_from_file_location("beyond_beta_native_authority", _native_path)
_native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_native)
FIXTURE_MODE = _native.FIXTURE_AUTHENTICATION
COST_CATEGORIES = ("production", "verification", "correction", "tooling_compute", "integration",
                   "support", "maintenance", "adaptation", "revalidation", "construction",
                   "failed_research", "search")
TERMINAL = {"REVOKED", "RETIRED", "SUPERSEDED"}


class Refusal(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Refusal(reason)


def integer(x, minimum=0):
    return isinstance(x, int) and not isinstance(x, bool) and minimum <= x <= 2**53 - 1


def canonical(value):
    def visit(x):
        if x is None or isinstance(x, (str, bool)):
            return
        if isinstance(x, int) and not isinstance(x, bool) and abs(x) <= 2**53 - 1:
            return
        if isinstance(x, list):
            for y in x:
                visit(y)
            return
        if isinstance(x, dict) and all(isinstance(k, str) for k in x):
            for y in x.values():
                visit(y)
            return
        raise Refusal("ONLY_FINITE_INTEGER_JSON; use explicit monetary/time units")
    visit(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def digest(kind, value):
    raw = value if isinstance(value, bytes) else canonical(value)
    return hashlib.sha256(b"BEYOND-BETA-V1\0" + kind.encode() + b"\0" + raw).hexdigest()


def costs(**values):
    """Explicit zeros are known zeros. Omitted/unknown categories in evidence fail."""
    require(set(values) <= set(COST_CATEGORIES), "UNKNOWN_COST_CATEGORY")
    result = {k: values.get(k, 0) for k in COST_CATEGORIES}
    require(all(integer(x) for x in result.values()), "NONNEGATIVE_INTEGER_COSTS_REQUIRED")
    return result


def total_cost(value):
    require(isinstance(value, dict) and set(value) == set(COST_CATEGORIES), "INCOMPLETE_COST_CATEGORIES")
    require(all(integer(x) for x in value.values()), "UNKNOWN_OR_NEGATIVE_COST")
    return sum(value.values())


class OfflinePrincipal:
    """Ephemeral fixture key, generated in memory; never a live ENS credential."""
    def __init__(self, name):
        self.name = name
        self._key = Ed25519PrivateKey.generate()

    @property
    def public_key(self):
        return self._key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

    def sign(self, payload):
        return base64.b64encode(self._key.sign(canonical(payload))).decode()


def authority_fixture(principal, roles, valid_until=10_000):
    return dict(name=principal.name, controller="OFFLINE-EPHEMERAL-FIXTURE", eligible=True,
                validFromWeek=0, expiresWeek=valid_until, revoked=False,
                authenticationMode=FIXTURE_MODE, publicKey=principal.public_key, roles=list(roles))


class CapsuleVault:
    """Authenticated encryption at rest; all keys are ephemeral process memory."""
    def __init__(self):
        self._keys = {}

    def seal(self, artifact, descriptor):
        key, nonce = AESGCM.generate_key(bit_length=256), os.urandom(12)
        aad = canonical(descriptor)
        encrypted = AESGCM(key).encrypt(nonce, canonical(artifact), aad)
        envelope = dict(schema="beyond-beta-capsule/v1", algorithm="AES-256-GCM", nonce=nonce.hex(),
                        ciphertext=base64.b64encode(encrypted).decode(), aadHash=digest("AAD", aad))
        commitment = digest("CAPSULE", envelope)
        self._keys[commitment] = key
        return commitment, envelope

    def open(self, commitment, envelope, descriptor):
        require(digest("CAPSULE", envelope) == commitment, "CAPSULE_COMMITMENT_CHANGED")
        aad = canonical(descriptor)
        require(envelope["aadHash"] == digest("AAD", aad), "CAPSULE_CONTEXT_CHANGED")
        try:
            plain = AESGCM(self._keys[commitment]).decrypt(bytes.fromhex(envelope["nonce"]), base64.b64decode(envelope["ciphertext"], validate=True), aad)
        except Exception as exc:
            raise Refusal("CAPSULE_AUTHENTICATION_FAILED") from exc
        artifact = json.loads(plain)
        require(digest("ARTIFACT", artifact) == descriptor["artifactHash"], "ARTIFACT_IDENTITY_CHANGED")
        return artifact


class BeyondBetaGraph:
    def __init__(self, policy, beta, inventory, authority_fixtures):
        self.policy, self.beta = deepcopy(policy), deepcopy(beta)
        canonical(self.policy); canonical(self.beta)
        for name in ("minCases", "minValidators", "maxEvidenceAge", "permitLife", "maxAllocationUses", "minCompositionCases"):
            require(integer(policy.get(name), 1), "INVALID_POLICY_" + name)
        require(integer(policy.get("minAcceptanceBps")) and policy["minAcceptanceBps"] <= 10000, "INVALID_QUALITY_POLICY")
        require(integer(policy.get("uncertaintyMultiplierMilli")) and integer(policy.get("minimumNetAlphaMicros")), "INVALID_ALPHA_POLICY")
        require(policy.get("functions") and len(set(policy["functions"])) == len(policy["functions"]), "FUNCTION_ENVELOPE_REQUIRED")
        require(beta.get("competent") is True and beta.get("competenceEvidenceHash") and beta.get("version"), "COMPETENT_BETA_EVIDENCE_REQUIRED")
        self.policy_hash, self.beta_hash = digest("POLICY", policy), digest("BETA", beta)
        self.inventory = deepcopy(inventory)
        self.authorities = {f["name"]: deepcopy(f) for f in authority_fixtures}
        require(len(self.authorities) == len(authority_fixtures), "DUPLICATE_IDENTITY")
        self._records, self._canonical, self._log = {}, {}, []
        self._cost_owners, self._charge_ids, self._failure_memory = {}, {}, []
        self._comparison_epoch = {f: 0 for f in policy["functions"]}
        self._vault, self._clock = CapsuleVault(), 0
        self._permit_signer = OfflinePrincipal("offline-permit.agent.agi.eth")

    def _time(self, epoch):
        require(integer(epoch) and epoch >= self._clock, "HISTORICAL_CLOCK_BYPASS_REFUSED")
        self._clock = epoch

    def _auth(self, principal, epoch, role=None):
        require(integer(epoch) and epoch >= self._clock, "HISTORICAL_CLOCK_BYPASS_REFUSED")
        require(digest("POLICY", self.policy) == self.policy_hash and digest("BETA", self.beta) == self.beta_hash, "MUTATED_UNCOMMITTED_POLICY_OR_BETA")
        fixture = self.authorities.get(principal.name)
        require(_native.authority_status(fixture, epoch)["eligible"], "AUTHORITY_NOT_ELIGIBLE")
        require(principal.public_key == fixture["publicKey"], "WRONG_FIXTURE_CONTROLLER_KEY")
        challenge = dict(domain="BEYOND-BETA-FIXTURE-AUTH", nonce=os.urandom(16).hex(), epoch=epoch)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(fixture["publicKey"])).verify(base64.b64decode(principal.sign(challenge)), canonical(challenge))
        if role:
            require(role in fixture["roles"], "ROLE_NOT_AUTHORIZED:" + role)
        self._clock = epoch
        return fixture

    def _event(self, kind, key, epoch, binding):
        event = dict(index=len(self._log), kind=kind, key=key, epoch=epoch, binding=binding,
                     previous=self._log[-1]["hash"] if self._log else digest("GENESIS", {}))
        self._log.append({**event, "hash": digest("EVENT", event)})

    def log_root(self):
        nodes = [digest("MERKLE-LEAF", e) for e in self._log]
        if not nodes:
            return digest("MERKLE-EMPTY", {})
        while len(nodes) > 1:
            if len(nodes) % 2:
                nodes.append(nodes[-1])
            nodes = [digest("MERKLE-NODE", {"left": nodes[i], "right": nodes[i+1]}) for i in range(0, len(nodes), 2)]
        return nodes[0]

    def _artifact(self, artifact):
        require(isinstance(artifact, dict) and set(artifact) == {"schema", "function", "nodes", "publicSourceIds"}, "UNAPPROVED_ARTIFACT_FIELDS_CLIENT_CONTENT_REFUSED")
        require(artifact["schema"] == "beyond-beta-shareable-ir/v1" and artifact["function"] in self.policy["functions"], "UNAPPROVED_FUNCTION")
        require(set(artifact["publicSourceIds"]) <= set(self.policy["publicSourceIds"]), "UNAPPROVED_OR_CLIENT_PROVENANCE")
        require(isinstance(artifact["nodes"], list) and 1 <= len(artifact["nodes"]) <= 128, "BOUNDED_IR_REQUIRED")
        for i, node in enumerate(artifact["nodes"]):
            require(set(node) == {"op", "inputs", "parameterKeys"}, "FREE_TEXT_OR_CLIENT_DATA_REFUSED")
            require(node["op"] in self.policy["operators"], "UNAPPROVED_OPERATOR")
            require(len(node["inputs"]) == self.policy["operators"][node["op"]], "OPERATOR_ARITY")
            require(all(isinstance(x, int) and not isinstance(x, bool) and -self.policy["inputArity"] <= x < i for x in node["inputs"]), "CYCLIC_OR_UNBOUND_IR_INPUT")
            require(set(node["parameterKeys"]) <= set(self.policy["publicParameters"]), "UNAPPROVED_CONSTANT_OR_CLIENT_DATA")
        canonical(artifact)

    def _compose_permissions(self, creator, key, shared_bundle, visited=None):
        visited=set() if visited is None else set(visited)
        require(key not in visited,"CYCLIC_COMPOSITION_PERMISSION")
        visited.add(key);d=self._records[key]["descriptor"]
        if not d["shareable"]:
            require(not shared_bundle,"PRIVATE_COMPONENT_CANNOT_BE_EXPORTED_THROUGH_SHARED_BUNDLE")
            require(d["creator"]==creator,"FOREIGN_PRIVATE_COMPONENT_COMPOSE_PERMISSION_REQUIRED")
        if d["supportOnly"]:
            require(d["creator"]==creator,"UNADMITTED_SUPPORT_COMPONENT_OWNER_CONSENT_REQUIRED")
        for dep in d["dependencies"]:
            self._compose_permissions(creator,dep["key"],shared_bundle,visited)

    def dependency_keys(self, dependencies):
        """Exact transitive closure for cost/freshness checks; never use authority."""
        seen=set();pending=list(dependencies)
        while pending:
            dep=pending.pop();key=dep["key"]
            if key in seen:continue
            seen.add(key);d=self._records[key]["descriptor"]
            pending.extend(d["dependencies"])
        return sorted(seen)

    def support_costs(self, dependencies):
        """Deduplicated transitive support cost; metadata only, never use authority."""
        return {key:self._records[key]["descriptor"]["supportConstructionMicros"]
                for key in self.dependency_keys(dependencies) if self._records[key]["descriptor"]["supportOnly"]}

    def create(self, creator, writer, artifact, dependencies=None, shareable=True, epoch=0, skill_id=None, version=1, supersedes=None, support_only=False, support_construction_micros=None):
        self._auth(creator, epoch, "creator"); self._auth(writer, epoch, "writer")
        self._artifact(artifact)
        require(isinstance(shareable, bool) and integer(version, 1), "INVALID_CANDIDATE_IDENTITY")
        require(shareable or self.policy.get("privateAblation", False), "PRIVATE_STORAGE_REQUIRES_EXPLICIT_ABLATION_POLICY")
        skill_id = skill_id or "skill-" + uuid.uuid4().hex
        require(re.fullmatch(r"[a-z][a-z0-9-]{0,63}", skill_id), "INVALID_SKILL_ID")
        key = skill_id + "@" + str(version)
        require(key not in self._records, "IMMUTABLE_VERSION_ALREADY_EXISTS")
        deps = deepcopy(dependencies or [])
        if deps:
            self._auth(creator, epoch, "compose")
        require(isinstance(support_only, bool), "EXPLICIT_SUPPORT_CLASS_REQUIRED")
        if support_only:
            require(integer(support_construction_micros), "COMPLETE_SUPPORT_CONSTRUCTION_COST_REQUIRED")
        else:
            require(support_construction_micros is None, "SUPPORT_COST_ON_CANONICAL_CANDIDATE")
        require(len({d["key"] for d in deps}) == len(deps), "DUPLICATE_DEPENDENCY")
        for dep in deps:
            require(set(dep) == {"key", "artifactHash"} and dep["key"] in self._records, "EXPLICIT_DEPENDENCY_VERSION_REQUIRED")
            require(dep["artifactHash"] == self._records[dep["key"]]["descriptor"]["artifactHash"], "DEPENDENCY_ARTIFACT_MISMATCH")
            require(not shareable or self._records[dep["key"]]["descriptor"]["shareable"], "PRIVATE_COMPONENT_CANNOT_BE_EXPORTED_THROUGH_SHARED_BUNDLE")
            self._compose_permissions(creator.name,dep["key"],shareable)
        if supersedes:
            old = self._records[supersedes]["descriptor"]
            require(old["creator"] == creator.name and old["skillId"] == skill_id and old["version"] < version, "INVALID_SUPERSESSION_LINEAGE")
        descriptor = dict(schema="beyond-beta-candidate/v1", key=key, skillId=skill_id, version=version,
            function=artifact["function"], creator=creator.name, writer=writer.name, artifactHash=digest("ARTIFACT", artifact),
            dependencies=deps, shareable=shareable, policyHash=self.policy_hash, betaHash=self.beta_hash,
            createdEpoch=epoch, supersedes=supersedes, supportOnly=support_only, supportConstructionMicros=support_construction_micros)
        capsule_hash, capsule = self._vault.seal(artifact, descriptor)
        self._records[key] = dict(descriptor=descriptor, candidateHash=digest("CANDIDATE", descriptor), capsuleHash=capsule_hash,
            capsule=capsule, stage="CANDIDATE", evidence=None, assessment=None, validators=[], admission=None, history=[], usedCaseIds=[], historicalConstructionMicros=0, initialCostFloor=costs(), failedQualificationExecutionMicros=0, failedEvidenceHashes=[])
        self._event("CANDIDATE", key, epoch, self._records[key]["candidateHash"])
        return key

    register = create

    def comparison_context(self, key):
        record = self._records[key]; function = record["descriptor"]["function"]
        catalog = []
        for item in self.inventory:
            if item["function"] == function and item.get("available", True):
                catalog.append({"arm": "inventory:" + item["id"] + "@" + str(item["version"]), "commitment": digest("INVENTORY", item)})
        for other in self._canonical.values():
            r = self._records[other]
            if other != key and r["stage"] == "ADMITTED" and r["descriptor"]["function"] == function:
                # Availability is a present-tense capability, not a historical
                # admission label. This predicate does not call comparison_context.
                try:
                    self._usable(other, self._clock, set())
                except Refusal:
                    continue
                if not r["descriptor"]["shareable"] and r["descriptor"]["creator"] != record["descriptor"]["creator"]:
                    continue
                catalog.append({"arm": "inventory:" + other, "commitment": r["candidateHash"]})
        catalog.sort(key=lambda x: x["arm"])
        require(len({x["arm"] for x in catalog}) == len(catalog), "DUPLICATE_COMPARATOR_ID")
        return dict(policyHash=self.policy_hash, betaHash=self.beta_hash,
                    inventoryHash=digest("INVENTORY-SNAPSHOT", catalog), comparators=catalog,
                    comparisonEpoch=self._comparison_epoch[function], requiredArms=["candidate", "beta"] + [x["arm"] for x in catalog])

    def _writer(self, principal, record, epoch):
        self._auth(principal, epoch, "writer")
        require(principal.name == record["descriptor"]["writer"], "WRITER_NOT_DELEGATED_FOR_THIS_SKILL")

    def _cost_ownership(self, evidence):
        """A is provenance only; B/C own the incremental fixed admission costs."""
        ownership=evidence["costOwnership"]
        require(isinstance(ownership,dict) and set(ownership)=={"schema","originJobCosts","retentionEntries","researchEntries"},"EXPLICIT_A_B_C_COST_OWNERSHIP_REQUIRED")
        require(ownership["schema"]=="beyond-beta-cost-ownership/v1","WRONG_COST_OWNERSHIP_SCHEMA")
        known={};charge_ids={};fixed=costs();a_total=0;b_total=0;c_total=0
        for entry in ownership["originJobCosts"]:
            require(set(entry)=={"jobId","ledgerCommitment","costMicros","ownership"},"INVALID_ORIGIN_JOB_COST_PROVENANCE")
            require(entry["ownership"]=="DELIVERY_A_ALREADY_CHARGED" and isinstance(entry["jobId"],str) and entry["jobId"] and integer(entry["costMicros"]),"ORIGIN_JOB_COST_MUST_BE_ALREADY_CHARGED_A")
            commitment=entry["ledgerCommitment"]
            require(isinstance(commitment,str) and re.fullmatch(r"[0-9a-f]{64}",commitment),"SOURCE_LEDGER_COMMITMENT_REQUIRED")
            require(commitment not in known,"DUPLICATE_ORIGIN_OR_RETENTION_LEDGER_CHARGE")
            known[commitment]={"ownership":entry["ownership"],"recordHash":digest("COST-PROVENANCE",entry)}
            a_total+=entry["costMicros"]
        for field,expected in (("retentionEntries","INCREMENTAL_RETENTION_B"),("researchEntries","OPTIONAL_RESEARCH_C")):
            for entry in ownership[field]:
                require(set(entry)=={"chargeId","ledgerCommitment","costs","ownership"},"INVALID_INCREMENTAL_COST_ENTRY")
                require(entry["ownership"]==expected and isinstance(entry["chargeId"],str) and entry["chargeId"],"EXPLICIT_INCREMENTAL_COST_OWNER_REQUIRED")
                amount=total_cost(entry["costs"]);commitment=entry["ledgerCommitment"]
                require(isinstance(commitment,str) and re.fullmatch(r"[0-9a-f]{64}",commitment),"SOURCE_LEDGER_COMMITMENT_REQUIRED")
                require(commitment not in known and entry["chargeId"] not in charge_ids,"DUPLICATE_ORIGIN_OR_RETENTION_LEDGER_CHARGE")
                known[commitment]={"ownership":expected,"recordHash":digest("COST-PROVENANCE",entry)}
                charge_ids[entry["chargeId"]]=commitment
                for category in COST_CATEGORIES:fixed[category]+=entry["costs"][category]
                if field=="retentionEntries":b_total+=amount
                else:c_total+=amount
        require(fixed==evidence["arms"]["candidate"]["lifecycleCosts"],"LIFECYCLE_MUST_EQUAL_INCREMENTAL_B_PLUS_C_NOT_ORIGIN_A")
        for commitment,record in known.items():
            require(commitment not in self._cost_owners or self._cost_owners[commitment]==record,"PAID_COST_OWNERSHIP_OR_AMOUNT_CANNOT_BE_RECLASSIFIED")
        for charge_id,commitment in charge_ids.items():
            require(charge_id not in self._charge_ids or self._charge_ids[charge_id]==commitment,"CHARGE_ID_REBOUND_TO_DIFFERENT_LEDGER_RECORD")
        summary=dict(originDeliveryCostMicros=a_total,incrementalRetentionCostMicros=b_total,optionalResearchCostMicros=c_total,
                     alphaLifecycleCostMicros=b_total+c_total,originDeliveryIncludedInAlpha=False,
                     enterpriseOriginCostRecord="RETAINED_IN_EXTERNAL_ENTERPRISE_LEDGER; provenance only in this gate",
                     ledgerCommitments=sorted(known))
        return summary,known,charge_ids

    def _remember_failure(self,key,epoch,reason_codes):
        r=self._records[key]
        if not r["assessment"]:return
        payload=dict(candidateHash=r["candidateHash"],artifactHash=r["descriptor"]["artifactHash"],function=r["descriptor"]["function"],
                     policyHash=r["assessment"]["policyHash"],betaHash=r["assessment"]["betaHash"],
                     evidenceHash=r["assessment"]["evidenceHash"],assessmentHash=digest("ASSESSMENT",r["assessment"]),
                     reasonCodes=sorted(reason_codes),dataBasis=r["evidence"]["dataBasis"])
        failure_id=digest("FAILURE-MEMORY",payload)
        if any(x["id"]==failure_id for x in self._failure_memory):return
        row=dict(id=failure_id,**payload,recordedEpoch=epoch,productionAuthority=False,executable=False,
                 positiveGraphAdmission=False,scope="RESEARCH_HINT_ONLY; fresh full assessment and admission required for productive reuse")
        self._failure_memory.append(row)
        self._event("FAILURE_MEMORY_RECORDED",key,epoch,failure_id)

    def register_evidence(self, writer, key, evidence, epoch):
        record = self._records[key]; self._writer(writer, record, epoch)
        require(record["stage"] not in TERMINAL, "TERMINAL_RECORD_CANNOT_BE_REACTIVATED")
        require(isinstance(evidence, dict) and set(evidence) == {"schema", "candidateHash", "policyHash", "betaHash", "inventoryHash", "capturedEpoch", "caseSetId", "cases", "arms", "phase", "composition", "dataBasis","costOwnership"}, "UNKNOWN_OR_INCOMPLETE_EVIDENCE_FIELDS")
        require(evidence["schema"] == "beyond-beta-matched-evidence/v1", "WRONG_EVIDENCE_SCHEMA")
        require(evidence["candidateHash"] == record["candidateHash"], "WRONG_CANDIDATE_EVIDENCE")
        require(evidence["dataBasis"] in {"EXECUTED_MEASUREMENTS", "SIMULATED_FIXTURE"}, "EVIDENCE_BASIS_REQUIRED")
        require(integer(evidence["capturedEpoch"]) and evidence["capturedEpoch"] <= epoch, "FUTURE_EVIDENCE")
        _,owners,charge_ids=self._cost_ownership(evidence)
        prior = record["evidence"]
        if record["admission"]:
            require(evidence["phase"] == "revalidation", "PROSPECTIVE_REVALIDATION_PHASE_REQUIRED")
            require(evidence["arms"]["candidate"]["historicalConstructionMicros"] == record["historicalConstructionMicros"], "HISTORICAL_CONSTRUCTION_RECOVERY_NOT_PRESERVED")
        else:
            require(evidence["phase"] == "initial", "INITIAL_EVIDENCE_REQUIRED")
            fixed=evidence["arms"]["candidate"]["lifecycleCosts"]
            total_cost(fixed)
            for category in COST_CATEGORIES:
                require(fixed[category] >= record["initialCostFloor"][category], "UNRECOVERED_INITIAL_PROGRAM_COST_ERASURE")
                record["initialCostFloor"][category] = fixed[category]
            record["historicalConstructionMicros"] = fixed["construction"]
        if prior:
            require(not set(record["usedCaseIds"]).intersection(c["id"] for c in evidence["cases"]), "REVALIDATION_REUSES_OLD_CASES")
        canonical(evidence)
        if prior:
            record["history"].append({"evidenceHash": digest("EVIDENCE", prior), "assessment": record["assessment"], "admission": record["admission"]})
        record.update(evidence=deepcopy(evidence), assessment=None, validators=[], stage="EVIDENCE")
        self._cost_owners.update(owners);self._charge_ids.update(charge_ids)
        record["usedCaseIds"].extend(c["id"] for c in evidence["cases"])
        self._event("EVIDENCE", key, epoch, digest("EVIDENCE", evidence))

    revalidate = register_evidence

    def _bindings(self, key, epoch, promotion=False):
        r = self._records[key]; e = r["evidence"]; c = self.comparison_context(key)
        require(r["candidateHash"] == digest("CANDIDATE", r["descriptor"]), "CANDIDATE_DESCRIPTOR_CHANGED")
        require(e is not None, "NO_EVIDENCE")
        require(e["policyHash"] == c["policyHash"] and e["betaHash"] == c["betaHash"], "STALE_BETA_OR_POLICY")
        require(e["inventoryHash"] == c["inventoryHash"], "STALE_INVENTORY_SNAPSHOT")
        require(epoch - e["capturedEpoch"] <= self.policy["maxEvidenceAge"], "STALE_EVIDENCE")
        require(set(e["arms"]) == set(c["requiredArms"]), "OMITTED_OR_UNDECLARED_RELEVANT_COMPARATOR")
        for dep in r["descriptor"]["dependencies"]:
            self._component(dep["key"], epoch, set())
            require(self._records[dep["key"]]["descriptor"]["artifactHash"] == dep["artifactHash"], "DEPENDENCY_VERSION_CHANGED")
        if promotion:
            require(r["assessment"] and r["assessment"]["qualified"], "NET_ALPHA_GATE_NOT_PASSED")
            require(r["assessment"]["evidenceHash"] == digest("EVIDENCE", e), "ASSESSMENT_EVIDENCE_CHANGED")
        return c

    def assess(self, assessor, key, epoch):
        self._auth(assessor, epoch, "assessor")
        r = self._records[key]
        require(assessor.name not in {r["descriptor"]["creator"], r["descriptor"]["writer"]}, "ASSESSOR_MUST_BE_INDEPENDENT")
        require(r["stage"] in {"EVIDENCE", "ASSESSED"}, "EVIDENCE_STAGE_REQUIRED")
        context = self._bindings(key, epoch); e = r["evidence"]
        cost_ownership,_,_=self._cost_ownership(e)
        cases = e["cases"]
        require(len(cases) >= self.policy["minCases"] and len({x["id"] for x in cases}) == len(cases), "INSUFFICIENT_DISTINCT_MATCHED_CASES")
        require(all(set(x) == {"id", "valueMicros"} and isinstance(x["id"], str) and integer(x["valueMicros"]) for x in cases), "INVALID_COMMON_CASE_VALUES")
        ids = [x["id"] for x in cases]; n = len(ids)
        arms, means, details = {}, {}, {}
        with localcontext() as ctx:
            ctx.prec = 50
            for name, arm in e["arms"].items():
                require(set(arm) == {"records", "lifecycleCosts", "allocationUses", "historicalConstructionMicros"}, "INCOMPLETE_ARM_COST_OR_ALLOCATION")
                require(integer(arm["allocationUses"], 1) and arm["allocationUses"] <= self.policy["maxAllocationUses"], "UNBOUNDED_COST_AMORTIZATION")
                require(integer(arm["historicalConstructionMicros"]), "HISTORICAL_RECOVERY_RECORD_REQUIRED")
                fixed = total_cost(arm["lifecycleCosts"])
                if e["phase"] == "revalidation":
                    require(arm["lifecycleCosts"]["construction"] == 0, "DOUBLE_CHARGED_HISTORICAL_CONSTRUCTION")
                rows = arm["records"]
                require(len(rows) == n and [x["caseId"] for x in rows] == ids, "UNMATCHED_OR_REORDERED_CASES")
                values, accepted, critical, variable_cost = [], 0, 0, 0
                for case, row in zip(cases, rows):
                    require(set(row) == {"caseId", "accepted", "criticalFailure", "costs"}, "INVALID_OUTCOME_RECORD")
                    require(type(row["accepted"]) is bool and type(row["criticalFailure"]) is bool, "EXPLICIT_ACCEPTANCE_REQUIRED")
                    c = total_cost(row["costs"]); variable_cost += c
                    accepted += row["accepted"]; critical += row["criticalFailure"]
                    values.append(Decimal(case["valueMicros"] if row["accepted"] else 0) - c - Decimal(fixed) / arm["allocationUses"])
                arms[name] = values; means[name] = sum(values) / n
                details[name] = dict(accepted=accepted, criticalFailures=critical, totalExecutionCostMicros=variable_cost,
                    lifecycleCostMicros=fixed, allocationUses=arm["allocationUses"], historicalConstructionMicros=arm["historicalConstructionMicros"],
                    meanNetValueMicros=str(means[name]), completeCostPerAcceptedMicros=str((Decimal(variable_cost) + Decimal(n)*fixed/arm["allocationUses"])/accepted) if accepted else None)
            comparisons = []
            for name in context["requiredArms"]:
                if name == "candidate":
                    continue
                deltas = [a-b for a,b in zip(arms["candidate"], arms[name])]
                mean = sum(deltas) / n
                se = (sum((x-mean)**2 for x in deltas) / (n-1) / n).sqrt() if n > 1 else Decimal(0)
                allowance = (se * self.policy["uncertaintyMultiplierMilli"] / 1000).to_integral_value(rounding=ROUND_CEILING)
                lower = mean - allowance
                comparisons.append(dict(comparator=name, meanNetAlphaMicros=str(mean), standardErrorMicros=str(se),
                    policyUncertaintyAllowanceMicros=str(allowance), lowerNetAlphaMicros=str(lower),
                    positive=lower > self.policy["minimumNetAlphaMicros"]))
        candidate = details["candidate"]
        quality = candidate["accepted"] * 10000 >= n*self.policy["minAcceptanceBps"] and candidate["criticalFailures"] == 0
        deps = r["descriptor"]["dependencies"]
        if deps:
            composition = e["composition"]
            support = self.support_costs(deps)
            expected_fields={"dependencyHash", "independentCaseIds"} | ({"supportConstructionMicros"} if support else set())
            require(isinstance(composition, dict) and set(composition) == expected_fields, "INDEPENDENT_COMPOSITION_EVIDENCE_REQUIRED")
            require(composition["dependencyHash"] == digest("DEPENDENCIES", deps), "COMPOSITION_DEPENDENCY_SUBSTITUTION")
            if support:
                require(composition["supportConstructionMicros"] == support, "SUPPORT_COMPONENT_COST_BINDING")
                if e["phase"] == "initial":
                    require(e["arms"]["candidate"]["lifecycleCosts"]["construction"] >= sum(support.values()), "SUPPORT_BUILD_COST_OMITTED_FROM_BUNDLE")
            ci = composition["independentCaseIds"]
            require(len(set(ci)) == len(ci) and len(ci) >= self.policy["minCompositionCases"] and set(ci) <= set(ids), "INSUFFICIENT_COMPOSITION_CASES")
            component_cases = {case_id for key in self.dependency_keys(deps) for case_id in self._records[key]["usedCaseIds"]}
            require(not set(ci).intersection(component_cases), "COMPOSITION_REUSES_COMPONENT_CASES")
        else:
            require(e["composition"] is None, "UNDECLARED_COMPOSITION")
        assessment = dict(schema="beyond-beta-net-alpha/v1", candidateHash=r["candidateHash"], evidenceHash=digest("EVIDENCE", e),
            policyHash=self.policy_hash, betaHash=self.beta_hash, inventoryHash=context["inventoryHash"],
            comparisonEpoch=context["comparisonEpoch"], assessedEpoch=epoch, assessor=assessor.name,
            arms=details, comparisons=comparisons, acceptanceGate=quality,
            qualified=quality and all(c["positive"] for c in comparisons),
            basis=e["dataBasis"], uncertaintyRule="PAIRED_MEAN_MINUS_PREDECLARED_MULTIPLE_OF_STANDARD_ERROR",
            costOwnership=cost_ownership,
            statisticalClaim="A gate on supplied finite evidence; no distribution-free or actual commercial guarantee",
            prospectiveRevalidation=e["phase"] == "revalidation")
        if not assessment["qualified"] and e["phase"]=="initial" and assessment["evidenceHash"] not in r["failedEvidenceHashes"]:
            # A failed qualification is paid research, not a free alternate view
            # of the same experiment. Carry every matched arm's execution cost.
            failed_execution=sum(a["totalExecutionCostMicros"] for a in details.values())
            r["failedQualificationExecutionMicros"]+=failed_execution
            r["initialCostFloor"]["failed_research"]+=failed_execution
            r["failedEvidenceHashes"].append(assessment["evidenceHash"])
        r.update(assessment=assessment, validators=[], stage="ASSESSED")
        self._event("NET_ALPHA_ASSESSED", key, epoch, digest("ASSESSMENT", assessment))
        if not assessment["qualified"]:
            reasons=(["ACCEPTANCE_GATE_FAILED"] if not quality else [])+["NONPOSITIVE_NET_ALPHA:"+c["comparator"] for c in comparisons if not c["positive"]]
            self._remember_failure(key,epoch,reasons)
        return deepcopy(assessment)

    def validate(self, validator, key, epoch, verdict="ACCEPT"):
        self._auth(validator, epoch, "validator"); r = self._records[key]
        require(r["stage"] in {"ASSESSED", "VALIDATED"} and r["assessment"], "ASSESSMENT_REQUIRED")
        require(validator.name not in {r["descriptor"]["creator"], r["descriptor"]["writer"], r["assessment"]["assessor"]}, "NONINDEPENDENT_VALIDATOR")
        require(verdict in {"ACCEPT", "REPAIR", "REJECT"}, "INVALID_VALIDATOR_VERDICT")
        self._bindings(key, epoch)
        receipt = dict(type="BEYOND_BETA_VALIDATION_V1", signer=validator.name, candidateHash=r["candidateHash"],
            evidenceHash=digest("EVIDENCE", r["evidence"]), assessmentHash=digest("ASSESSMENT", r["assessment"]),
            policyHash=self.policy_hash, betaHash=self.beta_hash, capsuleHash=r["capsuleHash"],
            logRoot=self.log_root(), epoch=epoch, expiry=epoch+self.policy["maxEvidenceAge"], verdict=verdict)
        r["validators"] = [x for x in r["validators"] if x["payload"]["signer"] != validator.name]
        r["validators"].append(dict(payload=receipt, signature=validator.sign(receipt)))
        r["stage"] = "VALIDATED"
        self._event("VALIDATED", key, epoch, digest("VALIDATION", r["validators"][-1]))
        if verdict!="ACCEPT":self._remember_failure(key,epoch,["VALIDATOR_"+verdict])
        return deepcopy(r["validators"][-1])

    def _validator_gate(self, r, epoch):
        counted = set()
        for v in r["validators"]:
            p = v["payload"]; f = self.authorities.get(p["signer"])
            require(_native.authority_status(f, epoch)["eligible"] and "validator" in f["roles"], "VALIDATOR_AUTHORITY_EXPIRED_OR_REVOKED")
            require(p["expiry"] >= epoch and p["verdict"] == "ACCEPT", "VALIDATION_EXPIRED_OR_NOT_ACCEPTED")
            require(p["candidateHash"] == r["candidateHash"] and p["evidenceHash"] == digest("EVIDENCE", r["evidence"]) and p["assessmentHash"] == digest("ASSESSMENT", r["assessment"]), "VALIDATION_BINDING_CHANGED")
            try:
                Ed25519PublicKey.from_public_bytes(bytes.fromhex(f["publicKey"])).verify(base64.b64decode(v["signature"], validate=True), canonical(p))
            except Exception as exc:
                raise Refusal("INVALID_FIXTURE_VALIDATOR_SIGNATURE") from exc
            counted.add(p["signer"])
        require(len(counted) >= self.policy["minValidators"], "INSUFFICIENT_INDEPENDENT_VALIDATORS")

    def admit(self, admitter, key, epoch):
        self._auth(admitter, epoch, "admission"); r = self._records[key]
        require(admitter.name not in {r["descriptor"]["creator"], r["descriptor"]["writer"]}, "ADMISSION_ROLE_SEPARATION")
        require(r["stage"] == "VALIDATED", "MANDATORY_CANONICAL_PROMOTION_GATE")
        require(not r["descriptor"]["supportOnly"], "SUPPORT_ARTIFACT_HAS_NO_STANDALONE_PROMOTION")
        self._bindings(key, epoch, True); self._validator_gate(r, epoch)
        require(admitter.name not in {v["payload"]["signer"] for v in r["validators"]}, "VERIFIER_AND_ADMITTER_MUST_DIFFER")
        artifact = self._vault.open(r["capsuleHash"], r["capsule"], r["descriptor"]); self._artifact(artifact)
        d = r["descriptor"]; old = self._canonical.get(d["skillId"])
        require(old is None or old == key or d["supersedes"] == old, "EXPLICIT_SUPERSESSION_REQUIRED")
        if old and old != key:
            self._records[old]["stage"] = "SUPERSEDED"
            self._event("SUPERSEDED", old, epoch, r["candidateHash"])
        # A fresh revalidation also returns a comparator to availability. It must
        # invalidate older standalone receipts that did not compare that restored
        # option. Duplicate calls cannot reach this point: VALIDATED plus fresh
        # evidence is mandatory, and admission changes the stage to ADMITTED.
        self._comparison_epoch[d["function"]] += 1
        receipt = dict(type="BEYOND_BETA_ADMISSION_V1", key=key, signer=admitter.name, candidateHash=r["candidateHash"],
            policyHash=self.policy_hash, betaHash=self.beta_hash, evidenceHash=digest("EVIDENCE", r["evidence"]),
            assessmentHash=digest("ASSESSMENT", r["assessment"]), dependencyHash=digest("DEPENDENCIES", d["dependencies"]),
            validationRoot=digest("VALIDATIONS", r["validators"]), logRoot=self.log_root(), admittedEpoch=epoch,
            comparisonEpoch=self._comparison_epoch[d["function"]], validUntil=r["evidence"]["capturedEpoch"]+self.policy["maxEvidenceAge"], shareable=d["shareable"])
        r.update(admission=dict(payload=receipt, signature=admitter.sign(receipt)), stage="ADMITTED")
        self._canonical[d["skillId"]] = key
        self._event("CANONICAL_ADMISSION", key, epoch, digest("ADMISSION", r["admission"]))
        return deepcopy(r["admission"])

    def _component(self, key, epoch, visited):
        require(key in self._records and key not in visited, "MISSING_OR_CYCLIC_DEPENDENCY")
        r=self._records[key]; d=r["descriptor"]
        if not d["supportOnly"]:
            # The new bundle's independent evidence establishes the value of using
            # this exact component internally; it does not restore standalone Alpha.
            return self._usable(key, epoch, visited, as_component=True)
        require(r["stage"] not in TERMINAL and d["createdEpoch"] <= epoch, "RETIRED_OR_REVOKED_SUPPORT_COMPONENT")
        require(r["candidateHash"] == digest("CANDIDATE",d), "SUPPORT_COMPONENT_DESCRIPTOR_CHANGED")
        for actor,role in ((d["creator"],"creator"),(d["writer"],"writer")):
            f=self.authorities.get(actor)
            require(_native.authority_status(f,epoch)["eligible"] and role in f["roles"], "SUPPORT_AUTHORITY_NOT_CURRENT")
        self._artifact(self._vault.open(r["capsuleHash"],r["capsule"],d))
        for child in d["dependencies"]:
            self._component(child["key"],epoch,set(visited)|{key})
        return r

    def _usable(self, key, epoch, visited, as_component=False):
        require(key in self._records and key not in visited, "MISSING_OR_CYCLIC_DEPENDENCY")
        visited = set(visited) | {key}; r = self._records[key]; d = r["descriptor"]
        require(r["candidateHash"] == digest("CANDIDATE", d), "CANDIDATE_DESCRIPTOR_CHANGED")
        require(r["stage"] == "ADMITTED" and self._canonical.get(d["skillId"]) == key, "NOT_CURRENT_CANONICAL_ADMISSION")
        p = r["admission"]["payload"]
        require(p["policyHash"] == self.policy_hash and p["betaHash"] == self.beta_hash, "STALE_BETA_OR_POLICY")
        if not as_component:
            require(p["comparisonEpoch"] == self._comparison_epoch[d["function"]], "NEW_RELEVANT_INVENTORY_REQUIRES_REVALIDATION")
        require(epoch <= p["validUntil"], "STALE_PROOF_REVALIDATION_REQUIRED")
        self._validator_gate(r, epoch)
        f = self.authorities.get(p["signer"])
        require(_native.authority_status(f, epoch)["eligible"] and "admission" in f["roles"], "ADMISSION_AUTHORITY_NO_LONGER_ELIGIBLE")
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(f["publicKey"])).verify(base64.b64decode(r["admission"]["signature"], validate=True), canonical(p))
        except Exception as exc:
            raise Refusal("ADMISSION_RECEIPT_SIGNATURE_FAILED") from exc
        require(p["candidateHash"] == r["candidateHash"] and p["assessmentHash"] == digest("ASSESSMENT", r["assessment"]), "ADMISSION_BINDING_CHANGED")
        for dep in d["dependencies"]:
            child = self._component(dep["key"], epoch, visited)
            require(child["descriptor"]["artifactHash"] == dep["artifactHash"], "DEPENDENCY_VERSION_SUBSTITUTED")
        return r

    def discover(self, agent, epoch, function=None):
        self._auth(agent, epoch)
        result = []
        for key in sorted(self._canonical.values()):
            try:
                r = self._usable(key, epoch, set())
            except Refusal:
                continue
            d = r["descriptor"]
            if (d["shareable"] or agent.name == d["creator"]) and (function is None or function == d["function"]):
                result.append(dict(key=key, function=d["function"], artifactHash=d["artifactHash"], capsuleHash=r["capsuleHash"],
                                   admissionHash=digest("ADMISSION", r["admission"]), availableToEligibleNetwork=d["shareable"], mandatoryUse=False))
        return result

    def authorize_reuse(self, executor, key, mission, epoch):
        self._auth(executor, epoch, "execution"); r = self._usable(key, epoch, set()); d = r["descriptor"]
        require(d["shareable"] or executor.name == d["creator"], "PRIVATE_ABLATION_NOT_SHARED")
        require(set(mission) == {"id", "function", "policyHash", "permittedOperators"}, "EXPLICIT_EXECUTION_MISSION_REQUIRED")
        require(mission["function"] == d["function"] and mission["policyHash"] == self.policy_hash, "MISSION_SCOPE_OR_POLICY_MISMATCH")
        artifact = self._vault.open(r["capsuleHash"], r["capsule"], d)
        required_ops={n["op"] for n in artifact["nodes"]}
        pending=list(d["dependencies"]);seen=set()
        while pending:
            dep=pending.pop()
            if dep["key"] in seen:continue
            seen.add(dep["key"]);child=self._component(dep["key"],epoch,set())
            content=self._vault.open(child["capsuleHash"],child["capsule"],child["descriptor"])
            required_ops.update(n["op"] for n in content["nodes"]);pending.extend(child["descriptor"]["dependencies"])
        require(required_ops <= set(mission["permittedOperators"]), "EXECUTION_PERMISSION_INSUFFICIENT")
        p = dict(type="BEYOND_BETA_REUSE_PERMIT_V1", key=key, actor=executor.name, missionHash=digest("MISSION", mission),
                 admissionHash=digest("ADMISSION", r["admission"]), policyHash=self.policy_hash, betaHash=self.beta_hash,
                 comparisonEpoch=self._comparison_epoch[d["function"]], issuedEpoch=epoch, expiry=min(epoch+self.policy["permitLife"], r["admission"]["payload"]["validUntil"]))
        return dict(payload=p, signature=self._permit_signer.sign(p))

    def resolve_reuse(self, executor, permit, epoch):
        self._auth(executor, epoch, "execution"); self._auth(executor,epoch,"retrieve"); p = permit["payload"]
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self._permit_signer.public_key)).verify(base64.b64decode(permit["signature"], validate=True), canonical(p))
        except Exception as exc:
            raise Refusal("INVALID_REUSE_PERMIT") from exc
        require(p["actor"] == executor.name and p["issuedEpoch"] <= epoch <= p["expiry"], "WRONG_ACTOR_OR_EXPIRED_PERMIT")
        r = self._usable(p["key"], epoch, set())
        require(p["admissionHash"] == digest("ADMISSION", r["admission"]), "PERMIT_PREDATES_REVALIDATION_OR_REVOCATION")
        components={};pending=list(r["descriptor"]["dependencies"])
        while pending:
            dep=pending.pop()
            if dep["key"] in components:continue
            child=self._component(dep["key"],epoch,set())
            components[dep["key"]]=self._vault.open(child["capsuleHash"],child["capsule"],child["descriptor"])
            pending.extend(child["descriptor"]["dependencies"])
        return dict(artifact=self._vault.open(r["capsuleHash"], r["capsule"], r["descriptor"]),
                    confinedComponentArtifacts=components,
                    invocationBinding=deepcopy(p), evidenceBasis=r["evidence"]["dataBasis"],
                    release="PLAINTEXT_IR_TO_EXPLICITLY_AUTHORIZED_RETRIEVING_EXECUTOR; not execute-only confidentiality",
                    execution="AUTHORIZED_DESCRIPTOR_ONLY; existing runtime must enforce this gate at dispatch")

    reuse = authorize_reuse

    def retrieve(self, agent, key, epoch):
        self._auth(agent,epoch,"retrieve");r=self._usable(key,epoch,set())
        require(r["descriptor"]["shareable"] or agent.name==r["descriptor"]["creator"],"PRIVATE_ABLATION_NOT_SHARED")
        return {"artifact":self._vault.open(r["capsuleHash"],r["capsule"],r["descriptor"]),"release":"PLAINTEXT_IR","executionAuthorized":False}

    def export_capsule(self, agent, key, epoch):
        self._auth(agent,epoch,"export");r=self._usable(key,epoch,set())
        require(r["descriptor"]["shareable"] or agent.name==r["descriptor"]["creator"],"PRIVATE_ABLATION_NOT_SHARED")
        return deepcopy({"capsule":r["capsule"],"descriptor":r["descriptor"],"capsuleHash":r["capsuleHash"],"decryptionKeyIncluded":False})

    def advance_beta(self, admitter, new_beta, epoch):
        self._auth(admitter, epoch, "admission")
        require(new_beta.get("competent") is True and new_beta.get("competenceEvidenceHash") and new_beta["version"] != self.beta["version"], "EXPLICIT_NEW_COMPETENT_BETA_VERSION_REQUIRED")
        canonical(new_beta); self.beta = deepcopy(new_beta); self.beta_hash = digest("BETA", new_beta)
        for function in self._comparison_epoch:
            self._comparison_epoch[function] += 1
        self._event("BETA_ADVANCED", "beta", epoch, self.beta_hash)

    def advance_inventory(self, admitter, inventory, epoch):
        self._auth(admitter, epoch, "admission")
        for function in self._comparison_epoch:
            old = [x for x in self.inventory if x["function"] == function]
            new = [x for x in inventory if x["function"] == function]
            if digest("INVENTORY", old) != digest("INVENTORY", new):
                self._comparison_epoch[function] += 1
        canonical(inventory); self.inventory = deepcopy(inventory)
        self._event("INVENTORY_ADVANCED", "inventory", epoch, digest("INVENTORY", inventory))

    def advance_policy(self, admitter, policy, epoch):
        self._auth(admitter, epoch, "admission")
        require(policy.get("version") != self.policy.get("version") and set(policy["functions"]) == set(self.policy["functions"]), "EXPLICIT_POLICY_VERSION_WITH_SAME_DECLARED_FUNCTIONS_REQUIRED")
        # Reuse constructor validation without carrying over any canonical records.
        BeyondBetaGraph(policy, self.beta, self.inventory, list(self.authorities.values()))
        self.policy = deepcopy(policy); self.policy_hash = digest("POLICY", policy)
        for function in self._comparison_epoch:
            self._comparison_epoch[function] += 1
        self._event("POLICY_ADVANCED", "policy", epoch, self.policy_hash)

    def retire(self, writer, key, epoch, revoke=False):
        r = self._records[key]; self._writer(writer, r, epoch)
        require(r["stage"] not in TERMINAL, "TERMINAL_STATE_IS_IRREVERSIBLE")
        r["stage"] = "REVOKED" if revoke else "RETIRED"
        self._event(r["stage"], key, epoch, r["candidateHash"])

    def revoke(self, writer, key, epoch):
        return self.retire(writer, key, epoch, revoke=True)

    def record(self, key):
        r = self._records[key]
        return deepcopy({k: v for k,v in r.items() if k != "capsule"})

    def failure_memory(self,agent,epoch,function=None):
        self._auth(agent,epoch)
        return deepcopy([x for x in self._failure_memory if function is None or x["function"]==function])

    def audit_log(self):
        return dict(events=deepcopy(self._log), root=self.log_root(), hash="SHA-256",
                    canonicalization="UTF-8 sorted-key finite integer JSON", leafDomain="MERKLE-LEAF", nodeDomain="MERKLE-NODE", oddLeaf="DUPLICATE_LAST",
                    liveIdentity=False, livePermissions=False, encryption="EXECUTED_AES_256_GCM_EPHEMERAL_KEYS",
                    signatures="EXECUTED_ED25519_OFFLINE_FIXTURE_KEYS", existingClubRoles="UNCHANGED",
                    limitation="Revocation blocks future guarded influence; it cannot erase previously disclosed plaintext.")
