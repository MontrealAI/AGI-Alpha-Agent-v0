# SPDX-License-Identifier: Apache-2.0
"""Additive regressions for evidence binding and structural transfer boundaries."""

from __future__ import annotations

import copy
import base64
import argparse
from fractions import Fraction
import hashlib
from pathlib import Path
from types import SimpleNamespace
import tempfile
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.structural_transfer import contracts, engine, operator


def capacity_source() -> dict[str, Any]:
    """Provide an executed development source without external-demand claims."""
    return {
        "schema": contracts.SOURCE_SCHEMA,
        "id": "capacity-development",
        "kind": "capacity-ledger",
        "task": {
            "capacity": "100",
            "demands": [{"id": "first", "amount": "40"}, {"id": "too-large", "amount": "70"}],
            "dimension": "currency",
            "unit": "microUSD",
        },
        "context": "Development arithmetic; no external customer or cash attestation.",
    }


def capacity_target_spec() -> dict[str, Any]:
    """Declare a structurally compatible target without a real adapter operation."""
    roles = {"max_load": "capacity", "used_load": "reserved", "free_load": "remaining"}
    return {
        "family": "linear-capacity",
        "variables": [{"name": name, "dimension": "mass", "unit": "kg", "role": role} for name, role in roles.items()],
        "relations": [{"kind": "conservation", "inputs": ["used_load", "free_load"], "output": "max_load"}],
        "assumptions": ["All weights use the same stated scale."],
    }


def capacity_mapping() -> dict[str, Any]:
    return {
        "variables": {"capacity": "max_load", "reserved": "used_load", "remaining": "free_load"},
        "bindings": [
            {
                "source_dimension": "currency",
                "source_unit": "microUSD",
                "target_dimension": "mass",
                "target_unit": "kg",
                "mode": "structural-instantiation",
            }
        ],
    }


def rehash_capture(capture: dict[str, Any]) -> None:
    """Refresh a caller-controlled hash so replay, rather than hashing alone, must reject a forgery."""
    capture["capture_hash"] = contracts.digest({key: value for key, value in capture.items() if key != "capture_hash"})


def fixture_adapter_spec(adapter_id: str) -> dict[str, Any]:
    """A test-only arithmetic adapter; it supplies no external evaluation evidence."""
    if adapter_id != "test-capacity":
        raise ValueError("not a whitelisted test adapter")
    return {
        "family": "linear-capacity",
        "variables": [
            {"name": name, "dimension": "items", "unit": "item", "role": name}
            for name in ["capacity", "reserved", "remaining"]
        ],
        "relations": [{"kind": "conservation", "inputs": ["reserved", "remaining"], "output": "capacity"}],
        "assumptions": [],
    }


def fixture_construct(
    adapter_id: str, *, principle: dict[str, Any], target: dict[str, Any], mapping: dict[str, Any]
) -> dict[str, Any]:
    fixture_adapter_spec(adapter_id)
    return {
        "operation": "capacity-first-fit",
        "target_hash": contracts.digest(target),
        "mapping_hash": contracts.digest(mapping),
    }


def fixture_execute(adapter_id: str, constructed: dict[str, Any], target: dict[str, Any]) -> dict[str, Any]:
    fixture_adapter_spec(adapter_id)
    if constructed.get("operation") != "capacity-first-fit" or constructed.get("target_hash") != contracts.digest(
        target
    ):
        raise ValueError("constructed operation does not bind the target")
    return {"task_id": target["id"], **engine.execute_source("capacity-ledger", target["inputs"])}


def fixture_check(
    adapter_id: str, *, target: dict[str, Any], artifact: dict[str, Any], constructed: dict[str, Any]
) -> dict[str, Any]:
    fixture_adapter_spec(adapter_id)
    if artifact["task_id"] != target["id"]:
        raise ValueError("task identity mismatch")
    output = {key: value for key, value in artifact.items() if key != "task_id"}
    verdict = engine.check_source("capacity-ledger", target["inputs"], output)
    return {"accepted": verdict["accepted"], "task_id": target["id"], "artifact_hash": contracts.digest(artifact)}


def install_fixture_adapter(monkeypatch: pytest.MonkeyPatch, check: Any = fixture_check) -> None:
    adapters = SimpleNamespace(
        adapter_spec=fixture_adapter_spec, construct=fixture_construct, execute=fixture_execute, check=check
    )
    monkeypatch.setattr(engine, "_adapters", lambda: adapters)


def primary_request() -> dict[str, Any]:
    """Execute a test beneficiary operation before extracting a source principle."""
    source_target = {
        "id": "source-operation",
        "adapter_id": "test-capacity",
        "need": "Allocate a development batch without exceeding its stated capacity.",
        "assumptions": [],
        "inputs": {
            "capacity": "12",
            "demands": [{"id": "source-a", "amount": "8"}, {"id": "source-b", "amount": "7"}],
            "dimension": "items",
            "unit": "item",
        },
    }
    source = {
        "schema": contracts.SOURCE_SCHEMA,
        "id": "accepted-test-source",
        "kind": "adapter-work",
        "task": {
            "adapter_id": "test-capacity",
            "target": source_target,
            "constructed": {"operation": "capacity-first-fit", "target_hash": contracts.digest(source_target)},
        },
        "context": "Test-only executed operation; not a customer-demand or generalized-transfer claim.",
        "cost_ids": ["source-work"],
    }
    with tempfile.NamedTemporaryFile(suffix="-source-task.json") as evidence:
        raw_source = contracts.canonical(source_target)
        evidence.write(raw_source)
        evidence.flush()
        source["evidence"] = [{"path": evidence.name, "sha256": hashlib.sha256(raw_source).hexdigest(), "role": "task"}]
        capture = engine.extract(source)
    target = copy.deepcopy(source_target)
    target["id"] = "target-use"
    target["need"] = "Allocate a second distinct development batch."
    target["inputs"]["capacity"] = "10"
    target["inputs"]["demands"] = [{"id": "target-a", "amount": "4"}, {"id": "target-b", "amount": "5"}]
    names = ["capacity", "reserved", "remaining"]
    return {
        "schema": contracts.REQUEST_SCHEMA,
        "id": "development-primary-pipeline",
        "captures": [capture],
        "target": target,
        "mapping": {
            "variables": {name: name for name in names},
            "bindings": [
                {
                    "source_dimension": "items",
                    "source_unit": "item",
                    "target_dimension": "items",
                    "target_unit": "item",
                    "mode": "structural-instantiation",
                }
            ],
        },
        "costs": [estimated_cost("source-work", "source"), estimated_cost("adaptation-work", "adaptation")],
        "economic_link": {"beneficiary": "development-user", "need": target["need"], "status": "internal-use"},
    }


@pytest.mark.parametrize(
    "raw",
    [
        b'{"id":"first","id":"second"}',
        b'{"outer":{"accepted":false,"accepted":true}}',
        b'{"quantity":NaN}',
        b'{"quantity":Infinity}',
        b'{"quantity":-Infinity}',
        b'{"quantity":1.25}',
    ],
)
def test_inert_parser_rejects_ambiguous_or_inexact_json(raw: bytes) -> None:
    with pytest.raises(ValueError):
        contracts.parse(raw)


def test_parser_preserves_exact_rational_quantities() -> None:
    document = contracts.parse(b'{"quantity":"7/3","accepted":false}')
    assert document == {"quantity": "7/3", "accepted": False}
    assert contracts.quantity(document["quantity"]) == Fraction(7, 3)


@pytest.mark.parametrize("value", [True, False, 1, 1.0, "1.0", "1/0", "nan", "-1"])
def test_quantity_refuses_coercion_and_invalid_bounds(value: Any) -> None:
    with pytest.raises(ValueError):
        contracts.quantity(value)


def test_json_size_depth_and_integer_bounds_apply_before_execution() -> None:
    with pytest.raises(ValueError):
        contracts.parse(b" " * (contracts.MAX_BYTES + 1))
    with pytest.raises(ValueError):
        contracts.parse(b'{"n":1000000000000000001}')
    nested: Any = 0
    for _ in range(26):
        nested = [nested]
    with pytest.raises(ValueError):
        contracts.bounded(nested)


@pytest.mark.parametrize("accepted", [1, 0, "true", "false", [], {}, None, False])
def test_checker_acceptance_requires_literal_true(accepted: Any) -> None:
    verdict = {"accepted": accepted, "task_id": "target", "artifact_hash": "a" * 64}
    with pytest.raises(ValueError):
        contracts.strict_acceptance(verdict, "target", "a" * 64)


def test_checker_acceptance_binds_exact_task_and_artifact() -> None:
    verdict = {"accepted": True, "task_id": "target", "artifact_hash": "a" * 64}
    assert contracts.strict_acceptance(verdict, "target", "a" * 64) == verdict
    for key, replacement in [("task_id", "other"), ("artifact_hash", "b" * 64)]:
        changed = copy.deepcopy(verdict)
        changed[key] = replacement
        with pytest.raises(ValueError):
            contracts.strict_acceptance(changed, "target", "a" * 64)


def test_exclusive_artifact_creation_preserves_existing_bytes(tmp_path: Path) -> None:
    output = tmp_path / "artifact.json"
    contracts.write_new(output, {"original": True})
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        contracts.write_new(output, {"replacement": True})
    assert output.read_bytes() == before


def test_input_and_output_symlinks_are_not_followed(tmp_path: Path) -> None:
    original = tmp_path / "source.json"
    original.write_bytes(b'{"original":true}')
    link = tmp_path / "link.json"
    link.symlink_to(original)
    with pytest.raises(ValueError):
        contracts.read(link)
    with pytest.raises(ValueError):
        contracts.write_new(link, {"replacement": True})
    assert original.read_bytes() == b'{"original":true}'


def test_source_operation_is_executed_and_marked_development_only() -> None:
    capture = engine.extract(capacity_source())
    assert capture["observation"]["result"] == {
        "accepted_ids": ["first"],
        "rejected_ids": ["too-large"],
        "capacity": "100",
        "reserved": "40",
        "remaining": "60",
    }
    assert capture["developmental_only"] is True
    assert engine.inspect_capture(capture)["valid"] is True
    assert capture["principle"]["epistemic_status"] == "supported-axiom-instantiated-by-checked-execution"


def test_source_capture_is_isolated_from_subsequent_caller_mutation() -> None:
    source = capacity_source()
    capture = engine.extract(source)
    source["task"]["capacity"] = "999"
    assert capture["source"]["task"]["capacity"] == "100"
    assert engine.inspect_capture(capture)["valid"] is True


def test_source_result_forgery_cannot_be_repaired_by_refreshing_hashes() -> None:
    capture = engine.extract(capacity_source())
    capture["observation"]["result"]["remaining"] = "99"
    changed_hash = contracts.digest(capture["observation"]["result"])
    capture["observation"]["result_hash"] = changed_hash
    capture["principle"]["source_result_hash"] = changed_hash
    capture["observation"]["acceptance"]["artifact_hash"] = changed_hash
    capture["observation"]["acceptance_hash"] = contracts.digest(capture["observation"]["acceptance"])
    rehash_capture(capture)
    with pytest.raises(ValueError):
        engine.inspect_capture(capture)


def test_extraction_method_and_code_binding_are_checked_during_replay() -> None:
    capture = engine.extract(capacity_source())
    capture["principle"]["extraction_code_hash"] = "a" * 64
    rehash_capture(capture)
    with pytest.raises(ValueError):
        engine.inspect_capture(capture)


@pytest.mark.parametrize("field", ["validated", "hidden_labels", "expected_result"])
def test_source_contract_refuses_manual_validation_and_label_leakage(field: str) -> None:
    source = capacity_source()
    source[field] = True
    with pytest.raises(ValueError):
        engine.extract(source)
    source = capacity_source()
    source["task"][field] = True
    with pytest.raises(ValueError):
        engine.extract(source)


def test_evidence_bytes_are_bound_to_the_actual_source_capture(tmp_path: Path) -> None:
    evidence = tmp_path / "source-notes.json"
    evidence.write_bytes(b'{"source":"first"}')
    source = capacity_source()
    source["evidence"] = [
        {"path": str(evidence), "sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(), "role": "source"}
    ]
    capture = engine.extract(source)
    assert engine.inspect_capture(capture)["valid"] is True
    evidence.write_bytes(b'{"source":"changed"}')
    assert engine.inspect_capture(capture)["valid"] is True
    assert base64.b64decode(capture["evidence_capture"][0]["captured_base64"]) == b'{"source":"first"}'
    capture["evidence_capture"][0]["captured_base64"] = base64.b64encode(evidence.read_bytes()).decode()
    rehash_capture(capture)
    with pytest.raises(ValueError):
        engine.inspect_capture(capture)
    assert capture["evidence_capture"][0]["sha256"] == source["evidence"][0]["sha256"]


def test_mapping_uses_roles_and_graph_instead_of_prose(monkeypatch: pytest.MonkeyPatch) -> None:
    principle = engine.extract(capacity_source())["principle"]
    spec = capacity_target_spec()
    monkeypatch.setattr(engine, "_adapters", lambda: SimpleNamespace(adapter_spec=lambda _: spec))
    target = {
        "adapter_id": "test-whitelisted",
        "assumptions": spec["assumptions"],
        "need": "A different domain and text.",
    }
    assert engine.structural_signature(principle) == engine.structural_signature(spec)
    assert engine.validate_mapping(principle, target, capacity_mapping())["valid"] is True


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("source_dimension", "unknown"),
        ("source_unit", "USD"),
        ("target_dimension", "time"),
        ("target_unit", "grams"),
        ("mode", "numerical-conversion"),
        ("mode", "assume-source-physics"),
    ],
)
def test_mapping_rejects_incompatible_or_unsupported_bindings(
    monkeypatch: pytest.MonkeyPatch, field: str, replacement: str
) -> None:
    principle = engine.extract(capacity_source())["principle"]
    spec = capacity_target_spec()
    monkeypatch.setattr(engine, "_adapters", lambda: SimpleNamespace(adapter_spec=lambda _: spec))
    target = {"adapter_id": "test-whitelisted", "assumptions": spec["assumptions"]}
    mapping = capacity_mapping()
    mapping["bindings"][0][field] = replacement
    with pytest.raises(ValueError):
        engine.validate_mapping(principle, target, mapping)


def test_mapping_rejects_causal_role_swap_and_missing_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    principle = engine.extract(capacity_source())["principle"]
    spec = capacity_target_spec()
    monkeypatch.setattr(engine, "_adapters", lambda: SimpleNamespace(adapter_spec=lambda _: spec))
    target = {"adapter_id": "test-whitelisted", "assumptions": spec["assumptions"]}
    swapped = capacity_mapping()
    swapped["variables"]["reserved"] = "free_load"
    swapped["variables"]["remaining"] = "used_load"
    with pytest.raises(ValueError):
        engine.validate_mapping(principle, target, swapped)
    incomplete = capacity_mapping()
    del incomplete["variables"]["remaining"]
    with pytest.raises(ValueError):
        engine.validate_mapping(principle, target, incomplete)


def test_mapping_rejects_reversed_relation_and_unknown_dimension(monkeypatch: pytest.MonkeyPatch) -> None:
    principle = engine.extract(capacity_source())["principle"]
    target = {"adapter_id": "test-whitelisted", "assumptions": capacity_target_spec()["assumptions"]}
    spec = capacity_target_spec()
    monkeypatch.setattr(engine, "_adapters", lambda: SimpleNamespace(adapter_spec=lambda _: spec))
    spec["relations"][0]["inputs"] = ["max_load", "free_load"]
    spec["relations"][0]["output"] = "used_load"
    with pytest.raises(ValueError):
        engine.validate_mapping(principle, target, capacity_mapping())
    spec = capacity_target_spec()
    spec["variables"][0]["dimension"] = "unknown"
    with pytest.raises(ValueError):
        engine.validate_mapping(principle, target, capacity_mapping())


def test_mapping_requires_explicit_target_assumptions(monkeypatch: pytest.MonkeyPatch) -> None:
    principle = engine.extract(capacity_source())["principle"]
    spec = capacity_target_spec()
    monkeypatch.setattr(engine, "_adapters", lambda: SimpleNamespace(adapter_spec=lambda _: spec))
    with pytest.raises(ValueError):
        engine.validate_mapping(principle, {"adapter_id": "test-whitelisted", "assumptions": []}, capacity_mapping())


def estimated_cost(ident: str, stage: str) -> dict[str, str]:
    return {
        "id": ident,
        "stage": stage,
        "quantity": "3/2",
        "quantity_unit": "cpu-second",
        "rate_per_unit": "1/10",
        "currency": "USD",
        "basis": "estimate",
    }


def test_costs_preserve_distinct_work_stages_and_exact_rates() -> None:
    report = engine.validate_costs(
        [estimated_cost(stage + "-cost", stage) for stage in ["source", "retention", "adaptation", "research"]]
    )
    assert report["by_stage"] == {"source": "3/20", "retention": "3/20", "adaptation": "3/20", "research": "3/20"}
    assert report["total"] == "3/5"
    assert report["settled"] is False


def test_duplicate_cost_identity_is_rejected_across_stages() -> None:
    with pytest.raises(ValueError):
        engine.validate_costs([estimated_cost("same-charge", "source"), estimated_cost("same-charge", "adaptation")])


@pytest.mark.parametrize(
    "field,replacement", [("basis", "measured"), ("basis", "customer-demand"), ("currency", "cash")]
)
def test_costs_cannot_claim_unsupported_measurement_or_cash(field: str, replacement: str) -> None:
    cost = estimated_cost("local-cost", "research")
    cost[field] = replacement
    with pytest.raises(ValueError):
        engine.validate_costs([cost])


def test_primary_pipeline_executes_and_replays_each_bound_stage(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fixture_adapter(monkeypatch)
    request = primary_request()
    stages: list[str] = []
    result = engine.run(request, lambda name, _: stages.append(name))
    assert stages == [
        "source-observation",
        "principle-extraction",
        "structural-retrieval",
        "mapping-validation",
        "adaptation-construction",
        "adaptation-execution",
        "independent-acceptance",
        "delivery-economic-link",
    ]
    assert result["artifact"]["accepted_ids"] == ["target-a", "target-b"]
    assert result["artifact"]["remaining"] == "1"
    assert result["delivery"]["task_id"] == request["target"]["id"]
    assert result["delivery"]["artifact_hash"] == contracts.digest(result["artifact"])
    assert engine.verify_result(request, result)["accepted"] is True


@pytest.mark.parametrize("accepted", [1, "true", False, None])
def test_primary_pipeline_does_not_trust_target_checker_truthiness(
    monkeypatch: pytest.MonkeyPatch, accepted: Any
) -> None:
    def misleading_check(
        adapter_id: str, *, target: dict[str, Any], artifact: dict[str, Any], constructed: dict[str, Any]
    ) -> dict[str, Any]:
        verdict = fixture_check(adapter_id, target=target, artifact=artifact, constructed=constructed)
        if target["id"] == "target-use":
            verdict["accepted"] = accepted
        return verdict

    install_fixture_adapter(monkeypatch, misleading_check)
    request = primary_request()
    with pytest.raises(ValueError):
        engine.run(request)


@pytest.mark.parametrize("field,replacement", [("task_id", "source-operation"), ("artifact_hash", "a" * 64)])
def test_primary_pipeline_refuses_checker_identity_substitution(
    monkeypatch: pytest.MonkeyPatch, field: str, replacement: str
) -> None:
    def wrong_identity_check(
        adapter_id: str, *, target: dict[str, Any], artifact: dict[str, Any], constructed: dict[str, Any]
    ) -> dict[str, Any]:
        verdict = fixture_check(adapter_id, target=target, artifact=artifact, constructed=constructed)
        if target["id"] == "target-use":
            verdict[field] = replacement
        return verdict

    install_fixture_adapter(monkeypatch, wrong_identity_check)
    with pytest.raises(ValueError):
        engine.run(primary_request())


def test_development_arithmetic_cannot_be_promoted_to_primary_transfer(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fixture_adapter(monkeypatch)
    request = primary_request()
    request["captures"] = [engine.extract(capacity_source())]
    with pytest.raises(ValueError):
        engine.run(request)
    request["captures"][0]["developmental_only"] = False
    rehash_capture(request["captures"][0])
    with pytest.raises(ValueError):
        engine.run(request)


@pytest.mark.parametrize("status", ["measured-demand", "paid", "newly-learned-successor"])
def test_transfer_cannot_claim_unsupported_demand_payment_or_successor(
    monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    install_fixture_adapter(monkeypatch)
    request = primary_request()
    request["economic_link"]["status"] = status
    with pytest.raises(ValueError):
        engine.run(request)


def test_result_replay_refuses_forged_artifact_with_refreshed_result_hash(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fixture_adapter(monkeypatch)
    request = primary_request()
    result = engine.run(request)
    result["artifact"]["remaining"] = "999"
    result["result_hash"] = contracts.digest({key: value for key, value in result.items() if key != "result_hash"})
    with pytest.raises(ValueError):
        engine.verify_result(request, result)


def test_cli_retains_failed_input_and_completed_stages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fixture_adapter(monkeypatch)
    request = primary_request()
    request["captures"] = [engine.extract(capacity_source())]
    source = tmp_path / "request.json"
    contracts.write_new(source, request)
    output = tmp_path / "failed-run"
    with pytest.raises(ValueError):
        operator.handle(argparse.Namespace(transfer_command="run", file=source, output=output))
    assert contracts.read(output / "request.json") == request
    failure = contracts.read(output / "failure.json")
    assert failure["accepted"] is False
    assert failure["input_hash"] == contracts.digest(request)
    assert [entry["stage"] for entry in failure["completed_stages"]] == [
        "source-observation",
        "principle-extraction",
        "structural-retrieval",
    ]
    assert (output / "stage-01.json").is_file()
    assert not (output / "artifact.json").exists()


def test_cli_rejects_input_output_alias_and_existing_output_without_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.json"
    contracts.write_new(source, capacity_source())
    original = source.read_bytes()
    with pytest.raises(ValueError):
        operator.handle(argparse.Namespace(transfer_command="extract", file=source, output=source))
    assert source.read_bytes() == original
    existing = tmp_path / "existing"
    existing.mkdir()
    marker = existing / "marker.txt"
    marker.write_text("preserve")
    with pytest.raises(FileExistsError):
        operator.handle(argparse.Namespace(transfer_command="extract", file=source, output=existing))
    assert marker.read_text() == "preserve"
    assert list(existing.iterdir()) == [marker]


def test_cli_creates_recheckable_delivery_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    install_fixture_adapter(monkeypatch)
    request = primary_request()
    source = tmp_path / "request.json"
    contracts.write_new(source, request)
    output = tmp_path / "delivery"
    result = operator.handle(argparse.Namespace(transfer_command="run", file=source, output=output))
    assert result["accepted"] is True
    assert contracts.read(output / "artifact.json")["remaining"] == "1"
    checked = operator.handle(argparse.Namespace(transfer_command="check", directory=output))
    assert checked["result_hash"] == result["result_hash"]


def test_generic_mission_runs_review_and_native_export_without_a_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from alpha_factory_v1.core.runtime import engine as mission_engine
    from alpha_factory_v1.core.runtime.models import Mission
    from alpha_factory_v1.core.runtime.store import Journal, digest

    install_fixture_adapter(monkeypatch)

    def forbidden_provider(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("structural transfer must not call a model provider")

    monkeypatch.setattr(mission_engine, "synthesize", forbidden_provider)
    monkeypatch.setattr(mission_engine, "generate_code", forbidden_provider)
    mission = Mission.model_validate(
        {
            "goal": "Execute bounded structural transfer",
            "work": {"kind": "structural-transfer", "request": primary_request()},
        }
    )
    journal = Journal.initialize(tmp_path / "agent")
    submitted = journal.submit(mission)
    runtime = mission_engine.Engine(journal)
    review = runtime.execute(submitted["id"])
    assert review["state"] == "review"
    assert review["verification"]["accepted"] is True
    assert any(stage["role"] == "mapping-validation" for stage in review["stages"])
    completed = runtime.review(
        review["id"], review["revision"], digest(review["result"]), True, "Reviewed exact test artifact."
    )
    assert completed["state"] == "completed"
    exported = runtime.export(review["id"])
    assert mission_engine.verify_export(exported, journal.public)["valid"] is True
