# SPDX-License-Identifier: Apache-2.0
"""Development-only adversarial tests for the independent static verifier."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

from alpha_factory_v1.core.runtime.invention_verification.qualify_verify import (
    LOSS_DRIVER,
    UNCERTAINTY,
    prove_program,
    read_json,
    sha,
    verify_bundle,
    verify_source_freeze,
)

F = TypeVar("F", bound=Callable[..., Any])


def parameterize(name: str, values: list[Any]) -> Callable[[F], F]:
    """Keep pytest's decorator typed under this repository's skipped imports."""
    return cast(Callable[[F], F], pytest.mark.parametrize(name, values))


def example() -> tuple[dict[str, Any], dict[str, Any]]:
    """Supply a tiny literal fixture; this is not public-domain evidence."""
    baseline = {
        "op": "sequence",
        "steps": [{"op": "observe", "field": "voltage"}, {"op": "emit", "status": "CONSISTENT"}],
    }
    proposal = {
        "op": "sequence",
        "steps": [
            {"op": "observe", "field": "voltage"},
            {
                "op": "if",
                "test": {"op": "dimension-is", "field": "voltage", "dimension": "voltage"},
                "then": {"op": "emit", "status": "CONSISTENT"},
                "else": {"op": "emit", "status": "ABSTAIN"},
            },
        ],
    }
    excerpt = "Synthetic fixture: voltage requirement 34.5 kVA. The intended correction is unknown."
    source_hash = hashlib.sha256(excerpt.encode()).hexdigest()
    request: dict[str, Any] = {
        "schema": "agialpha/specification-synthesis-request/v1",
        "problem": {
            "id": "synthetic",
            "activity": "literal dimensional consistency only",
            "scope": "specification-consistency-only",
        },
        "records": [{"id": "literal", "source_id": "fixture", "fields": {"voltage": {"value": "69/2", "unit": "kVA"}}}],
        "sources": [
            {
                "id": "fixture",
                "url": "https://example.org/synthetic-fixture",
                "sha256": source_hash,
                "excerpt": excerpt,
            }
        ],
        "requirements": {"voltage": "voltage"},
        "baseline": baseline,
        "proposal": proposal,
        "author": {
            "kind": "host-model",
            "model": "fixture model label",
            "prompt": "fixture context",
            "usage": "UNKNOWN",
        },
        "budget": {"max_nodes": 32, "max_depth": 8, "max_candidates": 1},
    }
    witness: dict[str, Any] = {
        "record_id": "literal",
        "field": "voltage",
        "observed_unit": "kVA",
        "required_dimension": "voltage",
        "source_id": "fixture",
        "source_hash": source_hash,
        "loss_driver": LOSS_DRIVER,
        "uncertainty": UNCERTAINTY,
    }
    bundle: dict[str, Any] = {
        "schema": "agialpha/specification-synthesis-bundle/v1",
        "request_hash": sha(request),
        "baseline_hash": sha(baseline),
        "proposal_hash": sha(proposal),
        "criticism": witness,
        "constraint": {
            "kind": "require-dimension",
            "field": "voltage",
            "dimension": "voltage",
            "record_id": "literal",
            "source_id": "fixture",
            "record_hash": sha(request["records"][0]),
            "baseline_hash": sha(baseline),
            "witness_hash": sha(witness),
            "validated": True,
        },
        "program": proposal,
        "static": {"valid": True, "scope": "static dominance proof only"},
        "sandbox": {"status": "BLOCKED", "reason": "No qualified Docker boundary in fixture", "executed": False},
        "economics": {
            "status": "UNKNOWN",
            "operating_cohort_admitted": False,
            "earned_surplus": "0",
            "actual_external_cash_paid": "0",
        },
        "confirmation": False,
    }
    return request, bundle


def rebound(request: dict[str, Any], bundle: dict[str, Any]) -> None:
    bundle["request_hash"] = sha(request)
    bundle["baseline_hash"] = sha(request["baseline"])
    bundle["proposal_hash"] = sha(request["proposal"])
    bundle["program"] = request["proposal"]
    bundle["constraint"]["baseline_hash"] = bundle["baseline_hash"]
    bundle["constraint"]["record_hash"] = sha(request["records"][0])
    bundle["constraint"]["witness_hash"] = sha(bundle["criticism"])


def test_valid_static_proof_is_not_execution_or_business() -> None:
    request, bundle = example()
    receipt = verify_bundle(request, bundle)
    assert receipt["accepted_static"] is True
    assert (
        receipt["candidate_executed"] is receipt["technical_activity_accepted"] is receipt["business_accepted"] is False
    )
    assert receipt["all_cohort_ids"] == ["literal"]
    assert receipt["intended_source_correction"] == "UNKNOWN"


@parameterize("op", ["eval", "shell", "network", "open", "import", "hardware", "pay"])
def test_no_generated_capability_can_be_smuggled(op: str) -> None:
    request, bundle = example()
    request["proposal"]["steps"].insert(0, {"op": op})
    rebound(request, bundle)
    with pytest.raises(ValueError, match="uninstalled AST"):
        verify_bundle(request, bundle)


def test_predicate_before_observation_rejected() -> None:
    request, bundle = example()
    request["proposal"]["steps"].reverse()
    rebound(request, bundle)
    with pytest.raises(ValueError, match="observation must dominate"):
        verify_bundle(request, bundle)


def test_unguarded_other_branch_is_checked() -> None:
    request, bundle = example()
    request["proposal"]["steps"][1]["else"]["status"] = "CONSISTENT"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="dimensional dominance"):
        verify_bundle(request, bundle)


def test_wrong_dimension_guard_rejected() -> None:
    request, bundle = example()
    request["proposal"]["steps"][1]["test"]["dimension"] = "apparent_power"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="unregistered predicate type"):
        verify_bundle(request, bundle)


def test_duplicate_terminal_and_hidden_tail_rejected() -> None:
    request, bundle = example()
    request["proposal"]["steps"].append({"op": "emit", "status": "CONSISTENT"})
    rebound(request, bundle)
    with pytest.raises(ValueError, match="nonterminal tail"):
        verify_bundle(request, bundle)


def test_open_branch_without_terminal_rejected() -> None:
    request, bundle = example()
    request["proposal"]["steps"].pop()
    rebound(request, bundle)
    with pytest.raises(ValueError, match="every branch"):
        verify_bundle(request, bundle)


def test_irrelevant_criticism_cannot_become_constraint() -> None:
    request, bundle = example()
    request["records"][0]["fields"]["voltage"]["unit"] = "kV"
    bundle["criticism"]["observed_unit"] = "kV"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="irrelevant dimensional"):
        verify_bundle(request, bundle)


def test_already_safe_baseline_refutes_criticism() -> None:
    request, bundle = example()
    request["baseline"] = deepcopy(request["proposal"])
    request["proposal"] = {"op": "sequence", "steps": [request["proposal"]]}
    rebound(request, bundle)
    with pytest.raises(ValueError, match="baseline defect"):
        verify_bundle(request, bundle)


@parameterize("bad_field", ["source_hash", "source_id", "record_id"])
def test_critic_identity_or_source_tampering_rejected(bad_field: str) -> None:
    request, bundle = example()
    bundle["criticism"][bad_field] = "wrong"
    rebound(request, bundle)
    with pytest.raises(ValueError):
        verify_bundle(request, bundle)


def test_source_bytes_must_match_hash() -> None:
    request, bundle = example()
    request["sources"][0]["excerpt"] += " changed"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="source excerpt hash"):
        verify_bundle(request, bundle)


def test_literal_quantity_not_assertion_must_match_source() -> None:
    request, bundle = example()
    request["records"][0]["fields"]["voltage"]["value"] = "100"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="absent from literal"):
        verify_bundle(request, bundle)


def test_same_cohort_cannot_drop_or_duplicate_record() -> None:
    request, bundle = example()
    request["records"].append(deepcopy(request["records"][0]))
    rebound(request, bundle)
    with pytest.raises(ValueError, match="record/source identity"):
        verify_bundle(request, bundle)


def test_missing_record_field_is_not_silently_removed_from_requirements() -> None:
    request, bundle = example()
    request["requirements"]["frequency"] = "frequency"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="dimensional dominance"):
        verify_bundle(request, bundle)


def test_constraint_requires_reproduced_exact_bindings() -> None:
    request, bundle = example()
    bundle["constraint"]["record_hash"] = "forged"
    with pytest.raises(ValueError, match="constraint"):
        verify_bundle(request, bundle)


@parameterize("change", ["execution", "profit", "earned", "confirmation"])
def test_static_evidence_cannot_promote_other_claims(change: str) -> None:
    request, bundle = example()
    if change == "execution":
        bundle["sandbox"]["executed"] = True
    elif change == "profit":
        bundle["economics"]["status"] = "GO"
    elif change == "earned":
        bundle["economics"]["earned_surplus"] = "1"
    else:
        bundle["confirmation"] = True
    with pytest.raises(ValueError):
        verify_bundle(request, bundle)


@parameterize("value", [0, True, 1.0, "-1", "1/0", "NaN"])
def test_quantity_types_and_positive_bounds(value: Any) -> None:
    request, bundle = example()
    request["records"][0]["fields"]["voltage"]["value"] = value
    rebound(request, bundle)
    with pytest.raises(ValueError):
        verify_bundle(request, bundle)


def test_all_fields_must_dominate_consistency() -> None:
    requirements = {"voltage": "voltage", "frequency": "frequency"}
    request, _ = example()
    with pytest.raises(ValueError, match="dimensional dominance"):
        prove_program(request["proposal"], requirements, request["budget"], dominance=True)


def test_small_budget_does_not_reset_after_failure() -> None:
    request, bundle = example()
    request["budget"]["max_nodes"] = 1
    rebound(request, bundle)
    with pytest.raises(ValueError, match="program budget"):
        verify_bundle(request, bundle)


def test_unknown_fields_and_extra_private_keys_rejected() -> None:
    request, bundle = example()
    request["proposal"]["steps"][0]["answer"] = "hidden"
    rebound(request, bundle)
    with pytest.raises(ValueError, match="record keys"):
        verify_bundle(request, bundle)


def test_duplicate_json_key_refused(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"confirmation":false,"confirmation":true}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        read_json(path)


def test_verifier_must_be_in_freeze(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="verifier source"):
        verify_source_freeze(tmp_path, {"other.py": "x"})


def test_source_pin_mismatch_rejected(tmp_path: Path) -> None:
    relative = "alpha_factory_v1/core/runtime/invention_verification/qualify_verify.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("fixture")
    helper_files = [
        "alpha_factory_v1/core/runtime/invention_verification/__init__.py",
        "alpha_factory_v1/core/runtime/invention_verification/readonly.py",
    ]
    pins = {relative: "wrong"}
    for name in helper_files:
        helper = tmp_path / name
        helper.write_text("helper fixture")
        pins[name] = hashlib.sha256(helper.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="source freeze mismatch"):
        verify_source_freeze(tmp_path, pins)


def test_vacuous_abstention_does_not_establish_useful_screen() -> None:
    request, bundle = example()
    request["proposal"] = {"op": "emit", "status": "ABSTAIN"}
    rebound(request, bundle)
    with pytest.raises(ValueError, match="nonvacuous"):
        verify_bundle(request, bundle)


def test_contradictory_retest_does_not_make_positive_path() -> None:
    request, bundle = example()
    branch = request["proposal"]["steps"][1]
    branch["then"] = {"op": "emit", "status": "ABSTAIN"}
    branch["else"] = deepcopy(branch)
    branch["else"]["then"] = {"op": "emit", "status": "CONSISTENT"}
    rebound(request, bundle)
    with pytest.raises(ValueError, match="repeated dimensional"):
        verify_bundle(request, bundle)


def with_construction(request: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Add explicit generated-attempt accounting to a development fixture."""
    checked = prove_program(request["proposal"], request["requirements"], request["budget"], dominance=True)
    proof = {"valid": True, "scope": "static dominance proof only"}
    proof.update({name: checked[name] for name in ["nodes", "depth", "consistent_paths"]})
    bundle["static"] = proof
    bundle["construction"] = {
        "program": request["proposal"],
        "origin": "host-model",
        "attempts": [
            {
                "program": request["proposal"],
                "origin": "host-model",
                "hash": sha(request["proposal"]),
                "status": "STATIC_VALID",
                "proof": proof,
            }
        ],
        "candidate_count": 1,
        "constraint_used": sha(bundle["constraint"]),
        "static": proof,
        "runtime_status": "NOT_EXECUTED",
    }
    bundle["resources"] = {
        "self_cpu_ns": 1,
        "wall_ns": 1,
        "child_cpu_seconds": "0.0",
        "model_tokens": "UNKNOWN",
        "prior_campaign_consumption": "UNKNOWN; not zero",
        "deterministic_candidate_count": 0,
    }
    return bundle


def test_criticism_can_be_validated_before_proposal_proof() -> None:
    from alpha_factory_v1.core.runtime.invention_verification.qualify_verify import verify_criticism

    request, bundle = example()
    request["proposal"] = {"op": "shell"}
    receipt = verify_criticism(request, bundle["criticism"])
    assert receipt["critic_validated"] is True
    assert receipt["candidate_executed"] is False
    with pytest.raises(ValueError):
        verify_bundle(request, bundle)


def test_complete_construction_attempt_accounting() -> None:
    request, bundle = example()
    receipt = verify_bundle(request, with_construction(request, bundle))
    assert receipt["accepted_static"] is True


@parameterize("key", ["candidate_count", "constraint_used", "runtime_status"])
def test_construction_counter_identity_and_execution_tampering(key: str) -> None:
    request, bundle = example()
    with_construction(request, bundle)
    bundle["construction"][key] = "forged"
    with pytest.raises(ValueError):
        verify_bundle(request, bundle)


def test_failed_adaptation_cannot_be_renamed_a_pass() -> None:
    request, bundle = example()
    with_construction(request, bundle)
    failed = bundle["construction"]["attempts"][0]
    failed["program"] = request["baseline"]
    failed["hash"] = sha(request["baseline"])
    with pytest.raises(ValueError, match="failed adaptation"):
        verify_bundle(request, bundle)


def test_failed_adaptation_kept_with_full_structure() -> None:
    request, bundle = example()
    request["budget"]["max_candidates"] = 2
    rebound(request, bundle)
    with_construction(request, bundle)
    bundle["construction"]["attempts"].append(
        {
            "program": request["baseline"],
            "hash": sha(request["baseline"]),
            "origin": "deterministic-constraint-compiler",
            "status": "REJECTED",
            "failure": "missing dimensional dominance",
        }
    )
    bundle["construction"]["candidate_count"] = 2
    bundle["resources"]["deterministic_candidate_count"] = 1
    assert verify_bundle(request, bundle)["accepted_static"] is True


def test_known_usage_does_not_replace_unknown_usage() -> None:
    request, bundle = example()
    with_construction(request, bundle)
    bundle["resources"]["model_tokens"] = "0"
    with pytest.raises(ValueError, match="unknown usage"):
        verify_bundle(request, bundle)


def test_conventional_reference_cannot_drop_bad_record() -> None:
    from alpha_factory_v1.core.runtime.invention_verification.qualify_verify import conventional_reference

    request, bundle = example()
    bundle["conventional_reference"] = conventional_reference(request)
    assert verify_bundle(request, bundle)["accepted_static"] is True
    bundle["conventional_reference"] = []
    with pytest.raises(ValueError, match="all-cohort"):
        verify_bundle(request, bundle)


def test_conventional_reference_cannot_claim_wrong_dimension_is_consistent() -> None:
    from alpha_factory_v1.core.runtime.invention_verification.qualify_verify import conventional_reference

    request, bundle = example()
    bundle["conventional_reference"] = conventional_reference(request)
    bundle["conventional_reference"][0] = {"id": "literal", "status": "CONSISTENT", "failures": []}
    with pytest.raises(ValueError, match="all-cohort"):
        verify_bundle(request, bundle)


def test_nonnegative_quantity_does_not_claim_voltage_suitability() -> None:
    from alpha_factory_v1.core.runtime.invention_verification.qualify_verify import (
        conventional_reference,
        verify_request,
    )

    request, _ = example()
    request["records"][0]["fields"]["voltage"] = {"value": "0", "unit": "kV"}
    verify_request(request)
    assert conventional_reference(request)[0]["status"] == "CONSISTENT"


def test_boolean_cannot_impersonate_static_count() -> None:
    request, bundle = example()
    with_construction(request, bundle)
    bundle["static"]["consistent_paths"] = True
    with pytest.raises(ValueError, match="accounting mismatch"):
        verify_bundle(request, bundle)
