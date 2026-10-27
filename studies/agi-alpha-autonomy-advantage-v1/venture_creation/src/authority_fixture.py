# SPDX-License-Identifier: Apache-2.0
"""Executable simulated eligible-agent authority/attestation gate.

Mirrors the existing native authorityStatus/fixture binding only. No live ENS,
private-key signature, settlement authority or correctness inference is supplied.
The venture's separate proof contract owns qualification and composition.
"""
import hashlib
import json
import re

FIXTURE_AUTHENTICATION = "SIMULATED_CONTROLLER_BINDING_ONLY"
DOMAIN = "AGIALPHA-HUMAN-MARKET-SIMULATION-V1\0"
DIRECT_AGENT = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.agent\.agi\.eth$")


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 2**53 - 1


def _text(value):
    return isinstance(value, str) and len(value) > 0


def evidence_hash(value):
    def inspect(item):
        if item is None or isinstance(item, (str, bool)):
            return
        if isinstance(item, int) and not isinstance(item, bool) and abs(item) <= 2**53 - 1:
            return
        if isinstance(item, list):
            for child in item:
                inspect(child)
            return
        if isinstance(item, dict) and all(isinstance(k, str) for k in item):
            for child in item.values():
                inspect(child)
            return
        raise ValueError("Fixture binding accepts finite integer JSON only; encode fractional time/cost in micros")
    inspect(value)
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256((DOMAIN + encoded).encode()).hexdigest()


def candidate_hash(candidate):
    return evidence_hash({key: value for key, value in candidate.items() if key != "attestations"})


def authority_status(fixture, week):
    reasons = []
    f = fixture or {}
    if not isinstance(f.get("name"), str) or not DIRECT_AGENT.fullmatch(f["name"]):
        reasons.append("DIRECT_AGENT_NAME_REQUIRED")
    if f.get("authenticationMode") != FIXTURE_AUTHENTICATION:
        reasons.append("EXPLICIT_SIMULATED_AUTHORITY_REQUIRED")
    if not _text(f.get("controller")):
        reasons.append("CONTROLLER_FIXTURE_REQUIRED")
    if f.get("eligible") is not True:
        reasons.append("INELIGIBLE_AGENT")
    if f.get("revoked") is True:
        reasons.append("AUTHORITY_REVOKED")
    if not _integer(week) or not _integer(f.get("validFromWeek")) or not _integer(f.get("expiresWeek")) or not f["validFromWeek"] <= week <= f["expiresWeek"]:
        reasons.append("AUTHORITY_NOT_CURRENT")
    return dict(eligible=not reasons, reasons=reasons, authenticationMode=FIXTURE_AUTHENTICATION, liveIdentityAuthenticated=False)


def make_fixture_attestation(candidate, authority, week, verdict="ADMIT_WITH_SCOPE"):
    payload = dict(authenticationMode=FIXTURE_AUTHENTICATION, signer=authority["name"], controller=authority["controller"],
                   candidateHash=candidate_hash(candidate), policyHash=candidate["policyHash"],
                   issuedWeek=week, expiresWeek=authority["expiresWeek"], verdict=verdict)
    return {**payload, "fixtureBinding": evidence_hash(payload)}


def make_fixture_attestations(candidate, fixtures, week, validator_names=None):
    creator = candidate["skill"]["creator"]
    selected = validator_names if validator_names is not None else [f["name"] for f in fixtures if f["name"] != creator]
    by_name = {f["name"]: f for f in fixtures}
    return [make_fixture_attestation(candidate, by_name[name], week) for name in selected]


def assess_fixture_attestations(candidate, fixtures, week, attestations, minimum_validators=2):
    """Authority and integrity only; a successful result never certifies skill truth."""
    reasons = []
    if not _integer(minimum_validators) or minimum_validators < 1:
        raise ValueError("At least one explicit distinct nonself validator is required")
    creator = candidate.get("skill", {}).get("creator")
    by_name = {f.get("name"): f for f in fixtures}
    if len(by_name) != len(fixtures):
        reasons.append("DUPLICATE_AUTHORITY_FIXTURE")
    if not authority_status(by_name.get(creator), week)["eligible"]:
        reasons.append("CREATOR_NOT_ELIGIBLE_DIRECT_AGENT_FIXTURE")
    if not _text(candidate.get("policyHash")):
        reasons.append("POLICY_BINDING_REQUIRED")
    bound = candidate_hash(candidate)
    counted = set()
    for a in attestations:
        payload = {key: value for key, value in a.items() if key != "fixtureBinding"}
        f = by_name.get(a.get("signer"))
        if a.get("fixtureBinding") != evidence_hash(payload) or a.get("candidateHash") != bound or a.get("policyHash") != candidate.get("policyHash"):
            reasons.append("ATTESTATION_BINDING_FAILED")
            continue
        if not authority_status(f, week)["eligible"] or a.get("authenticationMode") != FIXTURE_AUTHENTICATION or a.get("controller") != f.get("controller"):
            reasons.append("INELIGIBLE_OR_UNBOUND_VALIDATOR")
            continue
        if not _integer(a.get("issuedWeek")) or not _integer(a.get("expiresWeek")) or not a["issuedWeek"] <= week <= a["expiresWeek"]:
            reasons.append("ATTESTATION_NOT_CURRENT")
            continue
        if a.get("verdict") != "ADMIT_WITH_SCOPE":
            reasons.append("VALIDATOR_DID_NOT_ADMIT")
            continue
        if a["signer"] != creator:
            counted.add(a["signer"])
    if len(counted) < minimum_validators:
        reasons.append("INSUFFICIENT_DISTINCT_NONSELF_ELIGIBLE_ATTESTATIONS")
    return dict(allowed=not reasons, reasons=list(dict.fromkeys(reasons)), validatorNames=sorted(counted),
                candidateHash=bound, authenticationMode=FIXTURE_AUTHENTICATION, liveIdentityAuthenticated=False,
                liveSignatureVerified=False, correctnessEstablished=False,
                existingClubRoles="UNCHANGED", scope="Simulated authority/integrity only; separate venture proof contract required")
