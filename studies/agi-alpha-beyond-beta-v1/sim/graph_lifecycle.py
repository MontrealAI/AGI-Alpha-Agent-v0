# SPDX-License-Identifier: Apache-2.0
"""Research implementation of a versioned, access-controlled Alpha lifecycle.

Identity, payment receipts, economic observations and institutional authority are
SIMULATED INPUTS. AES-GCM operations and SHA-256 commitments, when requested,
execute locally on synthetic payloads. There is no ENS, chain, EIP-712 or ZK
verification, no custody, no production sandbox, and no AGI Jobs authority change.
The graph checks policy and provenance; admission never makes an output correct.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import re
import statistics
from collections import defaultdict
from typing import Any, Callable

SCHEMA = "beyond-beta-lifecycle/v1"
BASIS = "SIMULATED_IDENTITY_AUTHORITY_AND_ECONOMIC_ASSESSMENT"
DIRECT_AGENT = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
TERMINAL = frozenset({"REVOKED", "RETIRED", "SUPERSEDED"})
OPERATIONS = frozenset({"discover", "retrieve", "acquire", "execute", "export", "compose"})
SUNK_COSTS = ("sunk_construction", "sunk_assessment")
REMAINING_COSTS = ("remaining_acquisition", "remaining_integration", "remaining_maintenance",
                   "remaining_revalidation", "remaining_composition", "remaining_privacy", "remaining_risk")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def direct_agent(name: Any) -> bool:
    """Deliberately restricted ASCII direct-label profile; not ENS normalization."""
    return isinstance(name, str) and DIRECT_AGENT.fullmatch(name) is not None


def _finite(value: Any, nonnegative: bool = False) -> bool:
    return (type(value) in (int, float) and math.isfinite(value)
            and (not nonnegative or value >= 0))


def default_policy(**updates: Any) -> dict[str, Any]:
    policy = {"version": "beyond-beta-policy-1", "evidence_max_age": 6,
              "validator_quorum": 1, "minimum_paired_cases": 1,
              "prior_mean_gain": 0.0, "prior_effective_cases": 8.0,
              "member_operations": ["discover", "retrieve", "acquire", "execute", "compose"],
              "default_export_allowed": False, "separate_creator_validator": True,
              "quality_rule": "independent_original_scope_checks_pass",
              "admission_rule": "initial_full_cycle_positive_then_prospective_retention",
              "authority_basis": BASIS, "settlement_authority": "NONE"}
    policy.update(updates)
    return policy


def simulated_authorities(creator: str, members: list[str], prefix: str = "fixture"):
    """Explicit synthetic role fixtures, never claimed as real reviewers or ENS owners."""
    actors = {role: f"{prefix}-{role}.agent.agi.eth"
              for role in ("writer", "assessor", "validator", "admission", "governance")}
    actors["creator"] = creator
    registry = {name: {"authenticated_simulated": True, "roles": ["member"],
                      "write_for": [], "scopes": ["*"],
                      "member_operations": sorted(OPERATIONS - {"export"})}
                for name in set(members + [creator] + list(actors.values()))}
    registry[creator]["roles"].append("creator")
    for role, name in actors.items():
        if role != "creator":
            registry[name]["roles"].append(role)
    registry[actors["writer"]]["write_for"] = [creator]
    return registry, actors


def assess_alpha(observations: list[dict[str, Any]], costs: dict[str, float],
                 forecast: dict[str, Any], beta_version: str, policy: dict[str, Any],
                 context: str = "initial_admission") -> dict[str, Any]:
    """Paired paid evidence versus best observed competent Beta/equivalent.

Per-case net values include matched delivery/validation/recovery costs and use
the same prespecified value definition. Remaining costs must exclude those
already included per case. Forecasts and dollar-valued benefits remain modeled.
The zero-centred prior is an assumption, not extra performed tests. Correlated
group labels reduce the effective evidence count. The normal interval is a
descriptive diagnostic, not a calibrated posterior or a mandatory hurdle.
"""
    reasons: list[str] = []
    if not observations:
        reasons.append("no_paired_evidence")
    ids: set[str] = set()
    units: set[str] = set()
    value_bases: set[str] = set()
    groups: dict[str, list[float]] = defaultdict(list)
    gains: list[float] = []
    for obs in observations:
        case_id = obs.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in ids:
            reasons.append("duplicate_or_missing_case")
        ids.add(str(case_id))
        if obs.get("beta_version") != beta_version:
            reasons.append("observation_beta_mismatch")
        if obs.get("evidence_basis") not in {"SIMULATED_PAIRED_ASSESSMENT", "LOCAL_EXECUTED_TEST"}:
            reasons.append("unlabeled_evidence_basis")
        unit, value_basis = obs.get("acceptance_unit"), obs.get("project_value_basis")
        units.add(str(unit)); value_bases.add(str(value_basis))
        if unit == "component_test":
            if type(obs.get("component_test_passed")) is not bool or "candidate_accepted" in obs:
                reasons.append("component_test_must_not_claim_project_acceptance")
            if value_basis != "MODEL_EXTRAPOLATION_FROM_COMPONENT_TESTS":
                reasons.append("missing_component_to_project_extrapolation_label")
        elif unit == "complete_deployment":
            if type(obs.get("candidate_accepted")) is not bool:
                reasons.append("missing_complete_deployment_acceptance_observation")
            if value_basis not in {"SIMULATED_COMPLETE_DEPLOYMENT", "OBSERVED_COMPLETE_DEPLOYMENT"}:
                reasons.append("unlabeled_complete_deployment_value_basis")
        else:
            reasons.append("missing_assessment_unit")
        alternatives = obs.get("equivalent_net_values")
        values = [obs.get("candidate_net_value"), obs.get("beta_net_value")]
        if not isinstance(alternatives, list) or any(not _finite(x) for x in alternatives):
            reasons.append("missing_equivalent_comparison"); continue
        if any(not _finite(x) for x in values):
            reasons.append("invalid_paired_value"); continue
        gain = values[0] - max([values[1]] + alternatives)
        gains.append(gain)
        groups[str(obs.get("group_id", case_id))].append(gain)
    if len(gains) < policy["minimum_paired_cases"]:
        reasons.append("insufficient_paired_evidence")
    if len(units) > 1 or len(value_bases) > 1:
        reasons.append("mixed_assessment_units_or_value_bases")
    passed_components = sum(o.get("component_test_passed") is True for o in observations)
    accepted_deployments = sum(o.get("candidate_accepted") is True for o in observations)
    if not passed_components and not accepted_deployments:
        reasons.append("no_supported_assessment_observation")
    for key in SUNK_COSTS + REMAINING_COSTS:
        if key not in costs or not _finite(costs[key], True):
            reasons.append("missing_or_invalid_lifecycle_cost:" + key)
    expected_uses = forecast.get("expected_uses")
    missing = forecast.get("recipients_missing_equivalent")
    if not _finite(expected_uses, True) or expected_uses <= 0:
        reasons.append("no_eligible_reuse")
    if type(missing) is not int or missing <= 0:
        reasons.append("no_recipient_lacks_equivalent")
    if forecast.get("basis") not in {"ASSUMED_FROM_OBSERVED_STATE", "OBSERVED_ELIGIBLE_REQUESTS"}:
        reasons.append("unlabeled_reuse_forecast")
    if not isinstance(forecast.get("forecast_id"), str) or not forecast["forecast_id"]:
        reasons.append("missing_reuse_forecast_identity")
    n = len(gains)
    mean = statistics.mean(gains) if gains else 0.0
    grouped = [statistics.mean(g) for g in groups.values()]
    effective_n = len(grouped)
    se = statistics.stdev(grouped) / math.sqrt(effective_n) if effective_n > 1 else None
    prior_n, prior_mean = policy["prior_effective_cases"], policy["prior_mean_gain"]
    if not _finite(prior_n, True) or not _finite(prior_mean):
        raise ValueError("invalid prior policy")
    posterior = ((effective_n * mean + prior_n * prior_mean) / (effective_n + prior_n)
                 if effective_n + prior_n else 0.0)
    remaining = sum(costs.get(k, 0) for k in REMAINING_COSTS if _finite(costs.get(k), True))
    sunk = sum(costs.get(k, 0) for k in SUNK_COSTS if _finite(costs.get(k), True))
    reuse = expected_uses if _finite(expected_uses, True) else 0.0
    net = posterior * reuse - remaining
    if net <= 0:
        reasons.append("nonpositive_prospective_net_alpha")
    # An optimistic prior alone cannot promote a measured zero/redundant candidate.
    if mean <= 0:
        reasons.append("no_evidence_conditioned_incremental_advantage")
    if context not in {"initial_admission", "retention_reassessment"}:
        raise ValueError("unknown assessment context")
    gate_net = net - sunk if context == "initial_admission" else net
    if context == "initial_admission" and gate_net <= 0:
        reasons.append("nonpositive_initial_full_cycle_net_alpha")
    return {"eligible_for_validation": not reasons, "reasons": sorted(set(reasons)),
            "raw_paired_cases": n, "effective_evidence_groups": effective_n,
            "assessment_unit": next(iter(units)) if len(units) == 1 else None,
            "project_value_basis": next(iter(value_bases)) if len(value_bases) == 1 else None,
            "passed_component_tests": passed_components, "accepted_complete_deployments": accepted_deployments,
            "raw_mean_gain": mean, "cluster_mean_standard_error": se,
            "prior_mean_gain": prior_mean, "prior_effective_cases": prior_n,
            "posterior_expected_gain_per_use": posterior,
            "expected_eligible_uses": reuse, "expected_prospective_net_alpha": net,
            "full_cycle_expected_net_alpha": net - sunk, "sunk_costs": sunk,
            "gate_context": context, "expected_net_alpha_for_gate": gate_net,
            "remaining_costs": remaining,
            "descriptive_net_interval_95": ([net - 1.96 * se * reuse, net + 1.96 * se * reuse]
                                            if se is not None else None),
            "uncertainty_is_admission_hurdle": False,
            "beta_version": beta_version, "policy_hash": digest(policy),
            "observations_hash": digest(observations), "costs_hash": digest(costs),
            "forecast_hash": digest(forecast), "basis": BASIS}


class LifecycleGraph:
    """Current-state authority; event history and exported snapshots grant no rights."""
    def __init__(self, policy: dict[str, Any], authority_registry: dict[str, Any], beta_version: str):
        self._policy = copy.deepcopy(policy)
        if not policy.get("version") or policy.get("authority_basis") != BASIS:
            raise ValueError("explicit simulated policy required")
        if type(policy.get("evidence_max_age")) is not int or policy["evidence_max_age"] <= 0:
            raise ValueError("evidence_max_age must be positive integer")
        if type(policy.get("validator_quorum")) is not int or policy["validator_quorum"] < 1:
            raise ValueError("validator_quorum must be positive integer")
        if policy.get("settlement_authority") != "NONE":
            raise ValueError("graph has no settlement authority")
        if not set(policy.get("member_operations", [])) <= OPERATIONS:
            raise ValueError("unknown operation")
        self._policy_hash = digest(self._policy)
        self._registry = copy.deepcopy(authority_registry)
        self._beta_version = str(beta_version)
        self._records: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._canonical: dict[str, str] = {}
        self._clock = -1
        self._authority_revision = 0

    @property
    def policy(self):
        return copy.deepcopy(self._policy)

    @property
    def policy_hash(self):
        return self._policy_hash

    @property
    def registry(self):
        return copy.deepcopy(self._registry)

    @property
    def beta_version(self):
        return self._beta_version

    @property
    def events(self):
        return copy.deepcopy(self._events)

    @property
    def records(self):
        return copy.deepcopy(self._records)

    def snapshot(self, candidate_id: str):
        return copy.deepcopy(self._records[candidate_id])

    def _auth(self, actor: str, role: str, scope: str | None = None):
        if not direct_agent(actor):
            return ["not_exact_direct_agent"]
        authority = self._registry.get(actor, {})
        if authority.get("authenticated_simulated") is not True:
            return ["unauthenticated_simulated_identity"]
        if role not in authority.get("roles", []):
            return ["unauthorized_role:" + role]
        if scope is not None and scope not in authority.get("scopes", []) and "*" not in authority.get("scopes", []):
            return ["actor_scope_ineligible"]
        return []

    def _time(self, now: int):
        if type(now) is not int or now < self._clock:
            return ["time_rollback"]
        return []

    def _event(self, kind: str, cid: str | None, actor: str, before: str | None,
               allowed: bool, reasons: list[str], now: int, **extra):
        rec = self._records.get(cid, {})
        if allowed and type(now) is int:
            self._clock = max(self._clock, now)
        ev = {"sequence": len(self._events), "event": kind, "month": now,
              "candidate_id": cid, "actor": actor, "before": before,
              "after": rec.get("status"), "allowed": allowed, "reasons": sorted(set(reasons)),
              "policy_version": self._policy["version"], "policy_hash": self._policy_hash,
              "beta_version": self._beta_version, "evidence_hash": (rec.get("evidence") or {}).get("evidence_hash"),
              "auth_basis": BASIS, "scope": rec.get("scope", []),
              "authority_registry_revision": self._authority_revision,
              "dependencies": rec.get("dependencies", []), "valid_until": rec.get("valid_until"),
              "revoked": rec.get("status") == "REVOKED", "settlement_authority": "NONE",
              "previous_event_hash": self._events[-1]["event_hash"] if self._events else None,
              **extra}
        ev["event_hash"] = digest(ev)
        self._events.append(copy.deepcopy(ev))
        return copy.deepcopy(ev)

    def _write_auth(self, rec: dict[str, Any], actor: str):
        reasons = self._auth(actor, "writer")
        if rec.get("creator") not in self._registry.get(actor, {}).get("write_for", []):
            reasons.append("writer_not_authorized_for_creator")
        return reasons

    def _binding(self, rec: dict[str, Any]):
        return digest({"commitment": rec["commitment"], "policy_hash": self._policy_hash,
                       "beta_version": self._beta_version, "evidence": rec.get("evidence"),
                       "assessment": rec.get("assessment"), "generation": rec["generation"]})

    def propose(self, candidate: dict[str, Any], actor: str, now: int):
        c = copy.deepcopy(candidate); cid = c.get("id")
        reasons = self._time(now) + self._write_auth(c, actor) + self._auth(c.get("creator"), "creator")
        if not isinstance(cid, str) or not cid or cid in self._records:
            reasons.append("duplicate_or_missing_candidate_identity")
        if not isinstance(c.get("version"), str) or not c["version"]:
            reasons.append("missing_candidate_version")
        if not isinstance(c.get("scope"), list) or not c["scope"] or any(not isinstance(s, str) or not s for s in c["scope"]):
            reasons.append("missing_scope")
        if type(c.get("valid_until")) is not int or c["valid_until"] <= now:
            reasons.append("candidate_expired")
        if c.get("sanitized") is not True or c.get("contains_client_data", False) or c.get("restricted_third_party", False):
            reasons.append("unsanitized_or_restricted_payload")
        if type(c.get("shareable")) is not bool:
            reasons.append("missing_sharing_policy")
        if not isinstance(c.get("capsule_commitment"), str) or not SHA256.fullmatch(c["capsule_commitment"]):
            reasons.append("missing_capsule_commitment")
        if not isinstance(c.get("model_config"), dict) or not c["model_config"]:
            reasons.append("missing_model_configuration")
        if not isinstance(c.get("components"), list) or not c["components"]:
            reasons.append("missing_components")
        deps = c.get("dependencies")
        if not isinstance(deps, list):
            reasons.append("missing_dependency_manifest")
        elif any(not isinstance(d, dict) or not all(isinstance(d.get(k), str) and d[k] for k in ("id", "version", "commitment")) for d in deps):
            reasons.append("invalid_dependency_binding")
        if not reasons:
            c["schema"] = SCHEMA
            c["created_month"] = now
            c["commitment"] = digest(c)
            c.update(status="CANDIDATE", generation=0, policy_hash=self._policy_hash,
                     beta_version=self._beta_version, evidence=None, assessment=None, attestations=[],
                     ever_admitted=False)
            self._records[cid] = c
        return self._event("candidate_proposed", cid, actor, None, not reasons, reasons, now)

    def attach_evidence(self, cid: str, evidence: dict[str, Any], actor: str, now: int):
        rec = self._records.get(cid, {}); before = rec.get("status")
        reasons = self._time(now) + self._write_auth(rec, actor)
        if before not in {"CANDIDATE", "STALE", "REJECTED"}:
            reasons.append("evidence_transition_forbidden")
        e = copy.deepcopy(evidence)
        if e.get("beta_version") != self._beta_version or e.get("policy_hash") != self._policy_hash:
            reasons.append("evidence_policy_or_beta_mismatch")
        if e.get("candidate_commitment") != rec.get("commitment"):
            reasons.append("evidence_candidate_mismatch")
        if not isinstance(e.get("evidence_hash"), str) or not SHA256.fullmatch(e["evidence_hash"]):
            reasons.append("missing_evidence_hash")
        observed = e.get("observed_month")
        if type(observed) is not int or not observed <= now < observed + self._policy["evidence_max_age"]:
            reasons.append("stale_or_future_evidence")
        if not isinstance(e.get("paid_receipt_id"), str) or not e["paid_receipt_id"] or not _finite(e.get("paid_amount"), True) or e["paid_amount"] <= 0:
            reasons.append("missing_paid_assessment_receipt")
        if e.get("payment_basis") != "SIMULATED_LEDGER_RECEIPT":
            reasons.append("unlabeled_payment_receipt")
        if e.get("beta_qualified") is not True or e.get("equivalents_checked") is not True:
            reasons.append("competent_beta_or_equivalent_check_missing")
        if e.get("independent_checks_passed") is not True:
            reasons.append("independent_checks_failed")
        if e.get("evidence_basis") not in {"SIMULATED_PAIRED_ASSESSMENT", "LOCAL_EXECUTED_TEST"}:
            reasons.append("unlabeled_evidence_basis")
        joint = len(rec.get("components", [])) > 1 or bool(rec.get("dependencies"))
        if joint and (e.get("composition_checks_passed") is not True or not e.get("composition_receipt_id")):
            reasons.append("missing_paid_composition_validation")
        if joint and e.get("dependency_manifest_hash") != digest(rec.get("dependencies", [])):
            reasons.append("composition_dependency_binding_mismatch")
        if not reasons:
            rec.update(status="EVIDENCED", evidence=e, assessment=None, attestations=[],
                       beta_version=self._beta_version, policy_hash=self._policy_hash,
                       generation=rec["generation"] + 1)
        return self._event("evidence_attached", cid, actor, before, not reasons, reasons, now)

    def assess(self, cid: str, observations: list[dict[str, Any]], costs: dict[str, float],
               forecast: dict[str, Any], actor: str, now: int):
        rec = self._records.get(cid, {}); before = rec.get("status")
        reasons = self._time(now) + self._auth(actor, "assessor")
        if before != "EVIDENCED":
            reasons.append("assessment_before_evidence")
        evidence = rec.get("evidence") or {}
        if evidence.get("observations_hash") != digest(observations):
            reasons.append("observations_not_bound_to_evidence")
        if any(o.get("scope") not in rec.get("scope", []) for o in observations):
            reasons.append("observation_scope_mismatch")
        if _finite(costs.get("sunk_assessment"), True) and costs["sunk_assessment"] > evidence.get("paid_amount", 0) + 1e-8:
            reasons.append("assessment_receipt_underfunded")
        if not reasons:
            context = "retention_reassessment" if rec.get("ever_admitted") is True else "initial_admission"
            assessment = assess_alpha(observations, costs, forecast, self._beta_version, self._policy, context)
            rec["assessment"] = assessment
            rec["costs"] = copy.deepcopy(costs)
            rec["forecast"] = copy.deepcopy(forecast)
            reasons += assessment["reasons"]
            rec["status"] = "ALPHA_ASSESSED" if not reasons else "REJECTED"
        return self._event("alpha_assessed", cid, actor, before, not reasons, reasons, now,
                           assessment=rec.get("assessment"))

    def make_attestation(self, cid: str, actor: str, now: int, verdict: str = "supported"):
        rec = self._records[cid]
        return {"issuer": actor, "verdict": verdict, "authenticated_simulated": True,
                "binding_hash": self._binding(rec), "policy_hash": self._policy_hash,
                "beta_version": self._beta_version, "issued_month": now,
                "valid_until": min(rec["valid_until"], now + self._policy["evidence_max_age"]),
                "basis": BASIS}

    def validate(self, cid: str, attestations: list[dict[str, Any]], actor: str, now: int):
        rec = self._records.get(cid, {}); before = rec.get("status")
        reasons = self._time(now) + self._auth(actor, "validator")
        if before != "ALPHA_ASSESSED":
            reasons.append("validation_before_alpha_assessment")
        seen: set[str] = set()
        for att in attestations:
            issuer = att.get("issuer")
            for scope in rec.get("scope", []):
                reasons += self._auth(issuer, "validator", scope)
            if issuer in seen:
                reasons.append("duplicate_attester")
            seen.add(str(issuer))
            if self._policy["separate_creator_validator"] and issuer == rec.get("creator"):
                reasons.append("creator_cannot_self_validate")
            if att.get("authenticated_simulated") is not True or att.get("basis") != BASIS:
                reasons.append("unlabeled_attestation_authentication")
            if att.get("verdict") != "supported":
                reasons.append("validator_did_not_support")
            if att.get("policy_hash") != self._policy_hash or att.get("beta_version") != self._beta_version:
                reasons.append("attestation_policy_or_beta_mismatch")
            if rec and att.get("binding_hash") != self._binding(rec):
                reasons.append("attestation_binding_mismatch")
            issued, expiry = att.get("issued_month"), att.get("valid_until")
            if type(issued) is not int or type(expiry) is not int or not issued <= now < expiry:
                reasons.append("stale_or_future_attestation")
        if len(seen) < self._policy["validator_quorum"]:
            reasons.append("validator_quorum_missing")
        if not reasons:
            rec.update(status="VALIDATED", attestations=copy.deepcopy(attestations))
        return self._event("validation_completed", cid, actor, before, not reasons, reasons, now)

    def _current_reasons(self, cid: str, scope: str, now: int, seen: frozenset[str] = frozenset()):
        if type(now) is not int:
            return ["invalid_time"]
        rec = self._records.get(cid)
        if rec is None:
            return ["missing_record"]
        reasons = []
        if cid in seen:
            return ["dependency_cycle"]
        if rec.get("status") != "ADMITTED":
            reasons.append("record_not_currently_admitted:" + str(rec.get("status")))
        if rec.get("policy_hash") != self._policy_hash or rec.get("beta_version") != self._beta_version:
            reasons.append("record_policy_or_beta_stale")
        if scope not in rec.get("scope", []):
            reasons.append("scope_mismatch")
        if not rec.get("created_month", now + 1) <= now < rec.get("valid_until", -1):
            reasons.append("record_expired_or_future")
        evidence = rec.get("evidence") or {}
        observed = evidence.get("observed_month", -10**9)
        if not observed <= now < observed + self._policy["evidence_max_age"]:
            reasons.append("evidence_expired_or_future")
        if not (rec.get("assessment") or {}).get("eligible_for_validation"):
            reasons.append("missing_positive_alpha_assessment")
        attestations = rec.get("attestations", [])
        if len(attestations) < self._policy["validator_quorum"]:
            reasons.append("missing_current_validation")
        for att in attestations:
            if att.get("binding_hash") != self._binding(rec) or not att.get("issued_month", now+1) <= now < att.get("valid_until", -1):
                reasons.append("stale_validation_binding")
            for att_scope in rec["scope"]:
                if self._auth(att.get("issuer"), "validator", att_scope):
                    reasons.append("validator_no_longer_eligible")
        for dep in rec.get("dependencies", []):
            parent = self._records.get(dep["id"])
            if parent is None:
                reasons.append("missing_dependency"); continue
            if parent.get("version") != dep["version"] or parent.get("commitment") != dep["commitment"]:
                reasons.append("dependency_version_or_commitment_mismatch"); continue
            dep_scope = dep.get("scope", scope)
            if rec.get("shareable") and not parent.get("shareable"):
                reasons.append("shareable_record_has_private_dependency")
            if self._current_reasons(dep["id"], dep_scope, now, seen | {cid}):
                reasons.append("dependency_not_usable")
        return reasons

    def _dependency_access(self, cid: str, agent: str, scope: str, operation: str,
                           seen: frozenset[str] = frozenset()):
        if cid in seen:
            return ["dependency_access_cycle"]
        rec = self._records.get(cid, {})
        reasons = []
        for dep in rec.get("dependencies", []):
            parent = self._records.get(dep["id"], {})
            dep_scope = dep.get("scope", scope)
            dep_operation = "compose" if operation == "compose" else "execute"
            if self._auth(agent, "member", dep_scope):
                reasons.append("dependency_member_scope_denied")
            if dep_operation not in self._policy["member_operations"] or dep_operation not in self._registry.get(agent, {}).get("member_operations", []):
                reasons.append("dependency_operation_denied")
            if parent and not parent.get("shareable") and agent != parent.get("creator"):
                reasons.append("private_dependency_access_denied")
            reasons += self._dependency_access(dep["id"], agent, dep_scope, dep_operation, seen | {cid})
        return reasons

    def admit(self, cid: str, actor: str, now: int):
        rec = self._records.get(cid, {}); before = rec.get("status")
        reasons = self._time(now) + self._auth(actor, "admission")
        if before != "VALIDATED":
            reasons.append("admission_before_validation")
        # Check all reuse predicates without trusting a caller-provided status flag.
        if not reasons:
            rec["status"] = "ADMITTED"
            for scope in rec["scope"]:
                reasons += self._current_reasons(cid, scope, now)
            if reasons:
                rec["status"] = before
        if not reasons:
            rec["admitted_month"] = now
            rec["ever_admitted"] = True
        return self._event("admission_decided", cid, actor, before, not reasons, reasons, now)

    def inspect_use(self, cid: str, agent: str, scope: str, beta_version: str, now: int,
                    operation: str = "execute", recipient_state: dict[str, Any] | None = None):
        reasons = self._auth(agent, "member", scope)
        if type(now) is not int or now < self._clock:
            reasons.append("time_rollback")
        if beta_version != self._beta_version:
            reasons.append("request_beta_stale")
        if operation not in OPERATIONS:
            reasons.append("unknown_member_operation")
        allowed_ops = set(self._policy["member_operations"])
        if self._policy.get("default_export_allowed"):
            allowed_ops.add("export")
        if operation not in allowed_ops or operation not in self._registry.get(agent, {}).get("member_operations", []):
            reasons.append("operation_not_granted")
        rec = self._records.get(cid, {})
        if rec and not rec["shareable"] and agent != rec["creator"]:
            reasons.append("private_retention_creator_only")
        reasons += self._current_reasons(cid, scope, now)
        reasons += self._dependency_access(cid, agent, scope, operation)
        if recipient_state is not None:
            if recipient_state.get("compatible") is not True:
                reasons.append("recipient_incompatible")
            if operation == "acquire" and recipient_state.get("already_equivalent") is True:
                reasons.append("recipient_already_equivalent")
            if "model_config" in recipient_state and recipient_state["model_config"] != rec.get("model_config"):
                reasons.append("recipient_model_configuration_mismatch")
        return {"allowed": not reasons, "reasons": sorted(set(reasons)), "candidate_id": cid,
                "recipient": agent, "operation": operation, "policy_hash": self._policy_hash,
                "beta_version": self._beta_version, "current_status": rec.get("status"),
                "auth_basis": BASIS, "settlement_authority": "NONE",
                "action_authority": "Separate task authorization required; access grants no external action."}

    def use(self, cid: str, agent: str, scope: str, now: int, operation: str = "execute",
            recipient_state: dict[str, Any] | None = None):
        decision = self.inspect_use(cid, agent, scope, self._beta_version, now, operation, recipient_state)
        self._time(now)
        self._event("member_" + operation, cid, agent, self._records.get(cid, {}).get("status"),
                    decision["allowed"], decision["reasons"], now, recipient=agent, operation=operation)
        return decision

    def discover(self, agent: str, scope: str, now: int):
        return [self.snapshot(cid) for cid in self._records
                if self.inspect_use(cid, agent, scope, self._beta_version, now, "discover")["allowed"]]

    def promote_canonical(self, cid: str, actor: str, now: int):
        rec = self._records.get(cid, {}); before = rec.get("status")
        reasons = self._time(now) + self._auth(actor, "admission")
        for scope in rec.get("scope", [""]):
            reasons += self._current_reasons(cid, scope, now)
        if not reasons:
            for scope in rec["scope"]:
                self._canonical[scope] = cid
        return self._event("canonical_promotion", cid, actor, before, not reasons, reasons, now)

    def canonical_for(self, agent: str, scope: str, now: int):
        cid = self._canonical.get(scope)
        if cid and self.inspect_use(cid, agent, scope, self._beta_version, now, "discover")["allowed"]:
            return self.snapshot(cid)
        return None

    def revoke(self, cid: str, actor: str, now: int, reason: str, retire: bool = False):
        rec = self._records.get(cid, {}); before = rec.get("status")
        reasons = self._time(now)
        if self._auth(actor, "governance") and self._write_auth(rec, actor):
            reasons.append("no_revocation_authority")
        if not rec:
            reasons.append("missing_record")
        if not reason:
            reasons.append("missing_revocation_reason")
        if before in TERMINAL:
            reasons.append("terminal_record_cannot_transition")
        if not reasons:
            rec.update(status="RETIRED" if retire else "REVOKED", revocation_reason=reason,
                       retired_or_revoked_month=now)
        return self._event("retired" if retire else "revoked", cid, actor, before, not reasons, reasons, now)

    def supersede(self, old: str, new: str, actor: str, now: int):
        rec, replacement = self._records.get(old, {}), self._records.get(new, {})
        before = rec.get("status")
        reasons = self._time(now) + self._write_auth(rec, actor)
        if not rec or not replacement or old == new:
            reasons.append("missing_or_identical_supersession")
        if before in TERMINAL:
            reasons.append("terminal_record_cannot_transition")
        if rec.get("creator") != replacement.get("creator"):
            reasons.append("supersession_creator_mismatch")
        for scope in rec.get("scope", []):
            reasons += self._current_reasons(new, scope, now)
        if not reasons:
            rec.update(status="SUPERSEDED", superseded_by=new, superseded_month=now)
            for scope, cid in list(self._canonical.items()):
                if cid == old:
                    self._canonical[scope] = new
        return self._event("superseded", old, actor, before, not reasons, reasons, now, replacement=new)

    def beta_update(self, beta_version: str, actor: str, now: int):
        reasons = self._time(now) + self._auth(actor, "governance")
        if not beta_version or beta_version == self._beta_version:
            reasons.append("beta_version_not_new")
        if not reasons:
            old = self._beta_version
            self._beta_version = beta_version
            for cid, rec in self._records.items():
                if rec["status"] in {"ADMITTED", "VALIDATED", "ALPHA_ASSESSED", "EVIDENCED"}:
                    before = rec["status"]; rec["status"] = "STALE"
                    self._event("moving_beta_requires_reassessment", cid, actor, before, True, [], now,
                                previous_beta_version=old)
        return self._event("beta_updated", None, actor, None, not reasons, reasons, now)

    def update_policy(self, policy: dict[str, Any], actor: str, now: int):
        reasons = self._time(now) + self._auth(actor, "governance")
        if policy.get("version") == self._policy["version"]:
            reasons.append("policy_version_must_change")
        if not reasons:
            checked = LifecycleGraph(policy, self._registry, self._beta_version)
            self._policy, self._policy_hash = checked.policy, checked.policy_hash
            for cid, rec in self._records.items():
                if rec["status"] not in TERMINAL | {"CANDIDATE", "REJECTED"}:
                    before = rec["status"]; rec["status"] = "STALE"
                    self._event("policy_change_requires_reassessment", cid, actor, before, True, [], now)
        return self._event("policy_updated", None, actor, None, not reasons, reasons, now)

    def update_authority(self, identity: str, authority: dict[str, Any], actor: str, now: int):
        """Versioned change to the synthetic authority fixture; never an ENS/key change."""
        reasons = self._time(now) + self._auth(actor, "governance")
        if not direct_agent(identity):
            reasons.append("not_exact_direct_agent")
        roles = {"creator", "writer", "assessor", "validator", "admission", "governance", "member"}
        if (type(authority.get("authenticated_simulated")) is not bool
                or not isinstance(authority.get("roles"), list)
                or not set(authority.get("roles", [])) <= roles
                or not isinstance(authority.get("member_operations"), list)
                or not set(authority.get("member_operations", [])) <= OPERATIONS
                or not isinstance(authority.get("scopes"), list)
                or not isinstance(authority.get("write_for"), list)):
            reasons.append("invalid_authority_fixture")
        if not reasons:
            self._registry[identity] = copy.deepcopy(authority)
            self._authority_revision += 1
            for cid, rec in self._records.items():
                if rec["status"] in {"ADMITTED", "VALIDATED", "ALPHA_ASSESSED", "EVIDENCED"}:
                    before = rec["status"]; rec["status"] = "STALE"
                    self._event("authority_revision_requires_reassessment", cid, actor, before, True, [], now)
        return self._event("authority_fixture_updated", None, actor, None, not reasons, reasons, now,
                           changed_identity=identity, authority_hash=digest(authority))


def create_assessed_record(graph: LifecycleGraph, candidate: dict[str, Any], evidence: dict[str, Any],
                           observations: list[dict[str, Any]], costs: dict[str, float],
                           forecast: dict[str, Any], actors: dict[str, str], now: int):
    """Convenience path, never a bypass: each stage calls the checked public method."""
    cid = candidate["id"]
    stages = []
    stages.append(graph.propose(candidate, actors["writer"], now))
    if not stages[-1]["allowed"]:
        return {"admitted": False, "stages": stages, "record": None}
    e = copy.deepcopy(evidence)
    e.update(candidate_commitment=graph.snapshot(cid)["commitment"],
             observations_hash=digest(observations), policy_hash=graph.policy_hash,
             beta_version=graph.beta_version)
    stages.append(graph.attach_evidence(cid, e, actors["writer"], now))
    if stages[-1]["allowed"]:
        stages.append(graph.assess(cid, observations, costs, forecast, actors["assessor"], now))
    if stages[-1]["allowed"]:
        att = graph.make_attestation(cid, actors["validator"], now)
        stages.append(graph.validate(cid, [att], actors["validator"], now))
    if stages[-1]["allowed"]:
        stages.append(graph.admit(cid, actors["admission"], now))
    return {"admitted": graph.snapshot(cid)["status"] == "ADMITTED",
            "stages": stages, "record": graph.snapshot(cid)}


def reassess_record(graph: LifecycleGraph, cid: str, evidence: dict[str, Any],
                    observations: list[dict[str, Any]], costs: dict[str, float],
                    forecast: dict[str, Any], actors: dict[str, str], now: int):
    """Paid fresh assessment of a nonterminal record; terminal history stays terminal.

Refreshing an admitted record first withdraws its current influence. The immutable
payload id/version and content commitment stay unchanged; evidence generation,
policy and Beta binding change. A changed payload must use a new id and supersede.
"""
    before = graph._records.get(cid, {}).get("status")
    reasons = graph._time(now) + graph._write_auth(graph._records.get(cid, {}), actors["writer"])
    if before in TERMINAL or before is None:
        reasons.append("terminal_or_missing_record_cannot_reassess")
    if reasons:
        ev = graph._event("reassessment_requested", cid, actors["writer"], before, False, reasons, now)
        return {"admitted": False, "stages": [ev], "record": graph.records.get(cid)}
    graph._records[cid]["status"] = "STALE"
    graph._event("reassessment_requested", cid, actors["writer"], before, True, [], now)
    e = copy.deepcopy(evidence)
    e.update(candidate_commitment=graph.snapshot(cid)["commitment"], observations_hash=digest(observations),
             policy_hash=graph.policy_hash, beta_version=graph.beta_version)
    stages = [graph.attach_evidence(cid, e, actors["writer"], now)]
    if stages[-1]["allowed"]:
        stages.append(graph.assess(cid, observations, costs, forecast, actors["assessor"], now))
    if stages[-1]["allowed"]:
        att = graph.make_attestation(cid, actors["validator"], now)
        stages.append(graph.validate(cid, [att], actors["validator"], now))
    if stages[-1]["allowed"]:
        stages.append(graph.admit(cid, actors["admission"], now))
    return {"admitted": graph.snapshot(cid)["status"] == "ADMITTED", "stages": stages,
            "record": graph.snapshot(cid)}


def seal_capsule(payload: bytes, context: dict[str, Any], key: bytes | None = None):
    """Real local AES-256-GCM; generated keys are synthetic, never network credentials."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    key = key or AESGCM.generate_key(bit_length=256)
    if len(key) != 32:
        raise ValueError("256-bit synthetic key required")
    salt, nonce = os.urandom(32), os.urandom(12)
    content_commitment = hashlib.sha256(salt + payload).hexdigest()
    envelope = canonical({"salt": base64.b64encode(salt).decode(),
                          "payload": base64.b64encode(payload).decode()})
    aad = canonical(context)
    ciphertext = AESGCM(key).encrypt(nonce, envelope, aad)
    return {"algorithm": "AES-256-GCM", "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ciphertext).decode(),
            "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
            "content_commitment": content_commitment, "context_sha256": hashlib.sha256(aad).hexdigest(),
            "crypto_basis": "ACTUAL_LOCAL_CRYPTOGRAPHY_SYNTHETIC_PAYLOAD_AND_KEY"}, key


def open_capsule(capsule: dict[str, Any], key: bytes, context: dict[str, Any]):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    if capsule.get("algorithm") != "AES-256-GCM":
        raise ValueError("unsupported capsule cipher")
    aad = canonical(context)
    ciphertext = base64.b64decode(capsule["ciphertext"], validate=True)
    if hashlib.sha256(aad).hexdigest() != capsule["context_sha256"] or hashlib.sha256(ciphertext).hexdigest() != capsule["ciphertext_sha256"]:
        raise ValueError("capsule commitment mismatch")
    plain = AESGCM(key).decrypt(base64.b64decode(capsule["nonce"], validate=True), ciphertext, aad)
    envelope = json.loads(plain)
    salt, payload = base64.b64decode(envelope["salt"]), base64.b64decode(envelope["payload"])
    if hashlib.sha256(salt + payload).hexdigest() != capsule["content_commitment"]:
        raise ValueError("content commitment mismatch")
    return payload


class CapsuleVault:
    """Local fixture vault. Process memory and callbacks are NOT a production sandbox."""
    def __init__(self, trusted_executors: dict[str, Callable[[bytes], Any]] | None = None):
        self._items: dict[str, tuple[dict[str, Any], bytes, dict[str, Any]]] = {}
        self._executors = dict(trusted_executors or {})
        if any(not isinstance(k, str) or not k or not callable(v) for k, v in self._executors.items()):
            raise ValueError("trusted executors require named callable entries")

    def put(self, cid: str, payload: bytes, context: dict[str, Any]):
        if cid in self._items:
            raise ValueError("capsule identities are immutable")
        capsule, key = seal_capsule(payload, context)
        self._items[cid] = (capsule, key, copy.deepcopy(context))
        return copy.deepcopy(capsule)

    def _check(self, graph: LifecycleGraph, cid: str, actor: str, scope: str, now: int, operation: str):
        decision = graph.use(cid, actor, scope, now, operation)
        if not decision["allowed"]:
            raise PermissionError(",".join(decision["reasons"]))
        capsule, key, context = self._items[cid]
        if graph.snapshot(cid)["capsule_commitment"] != capsule["content_commitment"]:
            raise ValueError("record does not commit to this capsule")
        return capsule, key, context

    def retrieve(self, graph: LifecycleGraph, cid: str, actor: str, scope: str, now: int):
        capsule, _, _ = self._check(graph, cid, actor, scope, now, "retrieve")
        return copy.deepcopy(capsule)  # Ciphertext/manifest only; decryption key is not returned.

    def execute(self, graph: LifecycleGraph, cid: str, actor: str, scope: str, now: int,
                executor_id: str, action_authorized: bool = False):
        if not isinstance(executor_id, str) or executor_id not in self._executors:
            raise PermissionError("unregistered_executor")
        if action_authorized is not True:
            raise PermissionError("capability_access_does_not_authorize_action")
        capsule, key, context = self._check(graph, cid, actor, scope, now, "execute")
        return self._executors[executor_id](open_capsule(capsule, key, context))

    def export(self, graph: LifecycleGraph, cid: str, actor: str, scope: str, now: int):
        capsule, key, context = self._check(graph, cid, actor, scope, now, "export")
        return open_capsule(capsule, key, context)
