# SPDX-License-Identifier: Apache-2.0
"""Adversarial wire-format, commitment and substantive schema contract checks."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from alpha_factory_v1.core.runtime.successor import protocol
from alpha_factory_v1.core.runtime.successor.protocol import (
    MAX_SAFE_INT,
    AllocationDecision,
    AuthorityEnvelope,
    Comparator,
    ExperimentalMeasurement,
    Institution,
    JobContract,
    MissionConstitution,
    ProofReceipt,
    RehearsalRequest,
    RehearsalResult,
    ResourceBudget,
    SpecialistDesignationPolicy,
    UnderwritingDecision,
    Validity,
    canonical,
    canonical_vectors,
    digest,
    load_record,
    safe_json_loads,
    schema_bundle,
)

REQUEST_ID = "00000000-0000-4000-8000-000000000001"
FUTURE = "2030-01-01T00:00:00Z"


def test_request_is_strict_bounded_and_normalized() -> None:
    request = load_record(RehearsalRequest, json.dumps({"request_id": REQUEST_ID}))
    assert request.max_candidates == 4 and request.language == "en"
    assert load_record(RehearsalRequest, canonical(request)) == request
    for changes in (
        {"schema_version": 2},
        {"schema_version": True},
        {"seed": True},
        {"seed": "1"},
        {"max_candidates": 13},
        {"formation_trials": 0},
        {"max_events": 20001},
        {"language": "de"},
        {"mission": "unrestricted"},
        {"command": "shell"},
        {"request_id": "00000000-0000-0000-0000-000000000000"},
    ):
        with pytest.raises(ValidationError):
            RehearsalRequest.model_validate({"request_id": REQUEST_ID, **changes})


@pytest.mark.parametrize(
    "bad",
    [
        b'{"x":1,"x":2}',
        b'{"x":{"y":1,"y":2}}',
        b'{"x":1.0}',
        b'{"x":-0}',
        b'{"x":1e2}',
        b'{"x":NaN}',
        b'{"x":Infinity}',
        b'{"x":9007199254740992}',
        b'{"x":-9007199254740992}',
        b'{"x":"\\ud800"}',
        '{"Ω":1}',
        b'{"":1}',
        b'{"x":"\xff"}',
    ],
)
def test_hostile_json_is_rejected(bad: str | bytes) -> None:
    with pytest.raises(ValueError):
        safe_json_loads(bad)


def test_import_is_bounded_before_json_parser(monkeypatch: pytest.MonkeyPatch) -> None:
    def parser_must_not_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("parser reached before preflight")

    monkeypatch.setattr(json, "loads", parser_must_not_run)
    with pytest.raises(ValueError, match="depth"):
        safe_json_loads("[" * 33 + "0" + "]" * 33)
    with pytest.raises(ValueError, match="byte"):
        safe_json_loads(b" " * 101, max_bytes=100)


def test_depth_scan_understands_escaped_strings() -> None:
    value = {"description": "[" * 100 + '\\"' + "]" * 100}
    assert safe_json_loads(json.dumps(value), max_depth=2) == value


@pytest.mark.parametrize("bad", [1.0, float("inf"), {"x": 2**53}, {"x": "\udfff"}, {"é": 1}, {1: 1}, (1, 2)])
def test_manual_objects_cannot_bypass_commitment_validation(bad: object) -> None:
    with pytest.raises(ValueError):
        canonical(bad)


def test_recursive_python_object_is_bounded() -> None:
    recursive: list[object] = []
    recursive.append(recursive)
    with pytest.raises(ValueError, match="depth"):
        canonical(recursive)


def test_commitment_bytes_domains_and_unicode_semantics() -> None:
    value = {"z": False, "a": "Ωé😀", "n": MAX_SAFE_INT}
    expected = '{"a":"Ωé😀","n":9007199254740991,"z":false}'.encode()
    assert canonical(value) == expected
    assert digest("request", value) == hashlib.sha256(b"successor-omega/v1:request\0" + expected).hexdigest()
    assert digest("request", value) != digest("evidence", value)
    assert digest("evidence", {"text": "é"}) != digest("evidence", {"text": "e\u0301"})
    for bad in ("", "Ω", "request\0evidence", "request\n"):
        with pytest.raises(ValueError):
            digest(bad, value)


def test_forged_model_copies_are_revalidated() -> None:
    request = RehearsalRequest(request_id=REQUEST_ID)
    forged = request.model_copy(update={"max_candidates": 100000})
    with pytest.raises(ValidationError):
        RehearsalRequest.model_validate(forged)


def test_nested_models_validate_without_coercion() -> None:
    constitution = MissionConstitution(mission_id="metrics", owner="owner", objective="exact aggregation")
    institution = Institution(id="institution", constitution=constitution, controller="owner")
    assert canonical({"payload": institution}) == canonical({"payload": institution.model_dump()})
    assert Institution.model_validate(institution.model_dump()) == institution
    bad = institution.model_dump()
    bad["constitution"]["budget"]["limits"] = {"calls": 2.0}
    with pytest.raises(ValidationError):
        Institution.model_validate(bad)


def test_sealed_terms_explicitly_support_unassigned_worker() -> None:
    job = JobContract(
        job_id="job",
        family="verification",
        acceptance_owner="reviewer",
        release_digest="a" * 64,
        environment_digest="b" * 64,
        valid_until=FUTURE,
    )
    assert job.worker is None
    assigned = job.model_copy(update={"worker": "worker"})
    assert digest("job-terms", job) != digest("job-terms", assigned)
    assert "market_job_id" not in job.model_dump()


def test_proof_cannot_omit_exact_comparison_and_evidence_bindings() -> None:
    minimum = {
        "proof_id": "proof",
        "institution_id": "i",
        "mission_id": "m",
        "release_digest": "a" * 64,
        "environment_digest": "b" * 64,
        "verifier": "verifier",
        "valid_until": FUTURE,
        "outcome": "pass",
        "claim": "correctness",
    }
    with pytest.raises(ValidationError):
        ProofReceipt.model_validate(minimum)
    proof = ProofReceipt.model_validate(
        {
            **minimum,
            "comparator_manifest_digest": "c" * 64,
            "protocol_digest": "d" * 64,
            "evidence_commitment": "e" * 64,
        }
    )
    assert proof.evidence_scope == "local"


def test_authority_defaults_and_unknown_scope_are_conservative() -> None:
    values = {
        "grant_id": "grant",
        "institution_id": "i",
        "mission_id": "m",
        "release_digest": "a" * 64,
        "subject": "worker",
        "issuer": "owner",
        "actions": ["aggregate"],
        "tools": ["bounded-engine"],
        "targets": ["local-case"],
        "valid_until": FUTURE,
        "context_digest": "b" * 64,
    }
    grant = AuthorityEnvelope.model_validate(values)
    assert grant.scope == "sandbox" and grant.approval_required is True
    with pytest.raises(ValidationError):
        AuthorityEnvelope.model_validate({**values, "authorityStatus": "approved"})


def test_validity_checks_calendar_and_order() -> None:
    for beginning, ending in (
        (FUTURE, FUTURE),
        ("2030-02-30T00:00:00Z", FUTURE),
        ("2029-01-01T00:00:00+00:00", FUTURE),
        (FUTURE, "2029-01-01T00:00:00Z"),
    ):
        with pytest.raises(ValidationError):
            Validity(valid_from=beginning, valid_until=ending)


def test_unknown_measurement_never_becomes_zero() -> None:
    values = {
        "measurement_id": "m",
        "institution_id": "i",
        "release_digest": "a" * 64,
        "metric": "review-cost",
        "unit": "USD",
        "status": "unknown",
        "method": "not observed",
        "observed_at": FUTURE,
        "evidence_digest": "b" * 64,
    }
    assert ExperimentalMeasurement.model_validate({**values, "value": None}).value is None
    with pytest.raises(ValidationError):
        ExperimentalMeasurement.model_validate({**values, "value": "0"})


def test_economic_allocations_account_for_reserves() -> None:
    values = {
        "allocation_id": "a",
        "institution_id": "i",
        "principal": "owner",
        "resources": {"calls": 5},
        "available_before": {"calls": 10},
        "obligations": {"calls": 3},
        "reliability_reserves": {"calls": 2},
        "rationale": "bounded evidence programme",
        "issued_at": FUTURE,
    }
    assert AllocationDecision.model_validate(values).resources == {"calls": 5}
    with pytest.raises(ValidationError):
        AllocationDecision.model_validate({**values, "resources": {"calls": 6}})
    with pytest.raises(ValidationError):
        ResourceBudget(limits={"calls": 2}, enforceable=["unobserved-human-time"])


def test_unavailable_comparator_requires_honest_reason() -> None:
    with pytest.raises(ValidationError):
        Comparator(
            comparator_id="frontier",
            role="general",
            observed_at=FUTURE,
            selection_rationale="credible available option",
            status="unavailable",
        )
    with pytest.raises(ValidationError):
        UnderwritingDecision(
            decision_id="d",
            institution_id="i",
            mission_id="m",
            principal="owner",
            changed_assumption="workload",
            considered_alternatives=["retain"],
            selected="build",
            proof_budget=ResourceBudget(),
            rationale="no examined build alternative",
            issued_at=FUTURE,
        )


def test_result_verifies_integrity_but_does_not_install_signing_authority() -> None:
    evidence = {"verdict": "HOLD", "measurements": {"elapsed_ns": 100}}
    values = {"request_hash": "a" * 64, "evidence": evidence, "evidence_hash": digest("evidence", evidence)}
    result = RehearsalResult.model_validate(values)
    assert result.scope == "local-native-rehearsal" and result.signature is None
    with pytest.raises(ValidationError):
        RehearsalResult.model_validate({**values, "evidence": {"verdict": "PASS"}})
    with pytest.raises(ValidationError):
        RehearsalResult.model_validate({**values, "trusted_keys": ["attacker"]})


def test_generated_schemas_and_vectors_match_packaged_contracts() -> None:
    directory = Path(protocol.__file__).parent
    assert json.loads((directory / "schemas.json").read_text(encoding="utf-8")) == schema_bundle()
    assert json.loads((directory / "canonical-vectors.json").read_text(encoding="utf-8")) == canonical_vectors()
    assert len(schema_bundle()["schemas"]) == 28
    for schema in schema_bundle()["schemas"].values():
        assert schema["additionalProperties"] is False
        assert schema["properties"]["schema_version"]["const"] == 1
    for vector in canonical_vectors():
        assert safe_json_loads(vector["canonical"]) == vector["value"]


def test_designation_policy_requires_every_comparator_applicability_decision() -> None:
    values: dict[str, Any] = {
        "policy_id": "metrics-designation-v1",
        "mission_family": "streaming-metrics-v1",
        "validity": {"valid_from": "2026-01-01T00:00:00Z", "valid_until": FUTURE},
        "superiority_metric": "utility_margin_bps",
        "superiority_threshold_bps": 500,
        "minimum_evaluation_units": 100,
        "required_independent_replications": 2,
        "uncertainty_requirement": "preregistered lower bound exceeds threshold",
        "accountable_policy_owner": "controller",
        "comparator_requirements": [
            {"role": role, "required": role != "human", "rationale": "documented mission applicability"}
            for role in ("incumbent", "simple", "specialist", "general", "human", "hybrid")
        ],
    }
    assert SpecialistDesignationPolicy.model_validate(values).designation == "specialist-asi"
    with pytest.raises(ValidationError):
        SpecialistDesignationPolicy.model_validate({**values, "required_independent_replications": 0})
    with pytest.raises(ValidationError):
        SpecialistDesignationPolicy.model_validate(
            {**values, "comparator_requirements": values["comparator_requirements"][:5]}
        )
