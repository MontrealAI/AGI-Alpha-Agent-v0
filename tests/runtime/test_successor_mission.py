# SPDX-License-Identifier: Apache-2.0
"""Execute actual bounded generation, fresh proof and paired renewal; fixtures stay explicit."""

from __future__ import annotations

import copy
import itertools
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.successor.aggregation import BETA, CURRENT, aggregate, beta, current, execute
from alpha_factory_v1.core.runtime.successor.evaluation import (
    comparative_decision,
    current_comparator_manifest,
    evaluate_frozen,
    malformed_cases,
    proof_protocol,
    sequence_digest,
    validate_frozen,
    workload,
)
from alpha_factory_v1.core.runtime.successor.mission import (
    GrammarSupplier,
    OpenAICompatibleSupplier,
    challenge,
    discover,
    examine,
    renew_study,
    run_study,
)
from alpha_factory_v1.core.runtime.successor.protocol import RehearsalRequest, canonical, digest, safe_json_loads


def request(**changes: Any) -> RehearsalRequest:
    return RehearsalRequest.model_validate(
        {
            "request_id": "00000000-0000-4000-8000-000000000001",
            "max_events": 64,
            "formation_trials": 1,
            "max_candidates": 2,
            **changes,
        }
    )


@pytest.fixture(scope="module")
def formation() -> dict[str, Any]:
    return discover(request())


def test_exact_aggregation_unicode_and_integer_semantics() -> None:
    events = [
        {"day": "d", "service": "é", "duration_us": 1_000_000_000, "ok": False},
        {"day": "d", "service": "é", "duration_us": 0, "ok": True},
        {"day": "d", "service": "e\u0301", "duration_us": 7, "ok": True},
        {"day": "d", "service": "\U00010000", "duration_us": 1, "ok": False},
        {"day": "d", "service": "\ue000", "duration_us": 2, "ok": True},
    ]
    expected = [
        {"day": "d", "service": "e\u0301", "count": 1, "total_duration_us": 7, "max_duration_us": 7, "error_count": 0},
        {
            "day": "d",
            "service": "é",
            "count": 2,
            "total_duration_us": 1_000_000_000,
            "max_duration_us": 1_000_000_000,
            "error_count": 1,
        },
        {"day": "d", "service": "\ue000", "count": 1, "total_duration_us": 2, "max_duration_us": 2, "error_count": 0},
        {
            "day": "d",
            "service": "\U00010000",
            "count": 1,
            "total_duration_us": 1,
            "max_duration_us": 1,
            "error_count": 1,
        },
    ]
    assert current(events) == beta(events) == expected
    for layout, cached, update in itertools.product(("tuple", "nested"), (True, False), ("branch", "builtin")):
        program = {"version": 1, "layout": layout, "cache_last": cached, "update": update}
        assert aggregate(events, program) == expected
        assert aggregate([], program) == []


@pytest.mark.parametrize("bad", malformed_cases())
def test_malformed_inputs_reject_entire_record_for_every_architecture(bad: Any) -> None:
    for artifact in [CURRENT, BETA, {"version": 1, "layout": "nested", "cache_last": True, "update": "branch"}]:
        with pytest.raises(ValueError):
            execute(bad, artifact)


def test_closed_language_has_no_effectful_operator_or_host_fallback(tmp_path: Path) -> None:
    target = tmp_path / "should-not-exist"
    program = {"version": 1, "layout": "nested", "cache_last": True, "update": "branch"}
    for field in ("code", "tool", "network", "filesystem"):
        with pytest.raises(ValueError):
            aggregate([], dict(program, **{field: f"open({str(target)!r},'w').write('bad')"}))
    assert not target.exists()
    with pytest.raises(ValueError):
        aggregate([{"day": "d", "service": "s", "duration_us": 1, "ok": True}] * 20_001, program)


def test_foundry_constructs_distinct_challengers_and_world_precedes_measurement(formation: dict[str, Any]) -> None:
    attempts = formation["foundry"]["attempts"]
    assert len(attempts) >= 2
    assert len({item["artifact_digest"] for item in attempts}) == len(attempts)
    assert all(item["construction"]["operators"] and item["observations"]["measurements"] for item in attempts)
    assert all(item["world_prediction"]["prediction_before_observation"] for item in attempts)
    assert (
        digest("world-predictions-before-development", formation["world"]["predictions"])
        == formation["world"]["prediction_commitment"]
    )
    assert formation["freeze"]["manifest"]["program"] == formation["foundry"]["selected_artifact"]
    assert formation["supplier"]["neural_execution"] is False
    assert challenge(formation["freeze"])["effect_attempts_denied"] == 4


def test_current_has_exact_prefrozen_membership_binding(formation: dict[str, Any]) -> None:
    frozen = formation["freeze"]
    binding = current_comparator_manifest(frozen)
    assert binding["manifest"]["artifact"] == CURRENT
    assert binding["manifest"]["trial_release_digest"] == frozen["release_digest"]
    assert binding["manifest"]["comparator_hash"] == digest("comparators", frozen["manifest"]["comparators"])
    assert binding["subject_digest"] == digest("current-comparator", binding["manifest"])


@pytest.mark.parametrize(
    "field", ["program", "supplier", "world", "policy", "tools", "memory", "environment", "comparators", "economics"]
)
def test_changed_behavior_or_economics_cannot_reuse_exact_freeze(formation: dict[str, Any], field: str) -> None:
    frozen = copy.deepcopy(formation["freeze"])
    frozen["manifest"][field] = {"changed": True}
    with pytest.raises(ValueError, match="freeze commitment"):
        validate_frozen(frozen)


@pytest.mark.parametrize("cost", [-1, True, 1.5, 600_000_000_001])
def test_rehashed_untrusted_formation_cost_cannot_improve_verdict(formation: dict[str, Any], cost: Any) -> None:
    frozen = copy.deepcopy(formation["freeze"])
    frozen["manifest"]["formation"]["total_runtime_ns"] = cost
    # Exact builtin types reject bool/int substitution and arbitrary subclasses.
    if type(cost) is float:  # noqa: E721
        with pytest.raises(ValueError):
            digest("release", frozen["manifest"])
    else:
        frozen["release_digest"] = digest("release", frozen["manifest"])
        with pytest.raises(ValueError, match="formation cost"):
            validate_frozen(frozen)


def _timing_fixture(current_ns: int, beta_ns: int, candidate_ns: int) -> list[dict[str, Any]]:
    return [
        {
            "systems": {
                name: {"runtime_ns": duration}
                for name, duration in (("current", current_ns), ("beta", beta_ns), ("candidate", candidate_ns))
            }
        }
        for _ in range(12)
    ]


def test_candidate_faster_than_current_but_slower_than_beta_retains_beta() -> None:
    result = comparative_decision(_timing_fixture(100, 30, 60), [], 0, proof_protocol(64))
    assert result["local_verdict"] == "RETAIN_ALTERNATIVE"
    assert result["best_fixed_comparator"] == "beta"
    assert result["alpha_established"] is False


def test_one_incorrect_result_vetoes_all_speed_advantage() -> None:
    result = comparative_decision(
        _timing_fixture(1000, 900, 1),
        [{"system": "candidate", "case": 7, "gate": "correctness"}],
        0,
        proof_protocol(64),
    )
    assert result["local_verdict"] == "FAIL"
    assert result["qualification_verdict"] == "HOLD"


def test_empty_or_invalid_measurements_never_establish_positive_verdict() -> None:
    assert comparative_decision([], [], 0, proof_protocol(64))["local_verdict"] == "INSUFFICIENT_EVIDENCE"
    for value in (True, -1, 0.5):
        with pytest.raises(ValueError):
            comparative_decision(_timing_fixture(10, 9, value), [], 0, proof_protocol(64))
    with pytest.raises(ValueError):
        comparative_decision(_timing_fixture(10, 9, 2), [], -1, proof_protocol(64))


def test_live_wrong_candidate_is_rejected_by_actual_examination(formation: dict[str, Any], monkeypatch: Any) -> None:
    from alpha_factory_v1.core.runtime.successor import evaluation

    original = evaluation.execute
    program = formation["freeze"]["manifest"]["program"]

    def broken(events: Any, artifact: dict[str, Any]) -> list[dict[str, Any]]:
        result = original(events, artifact)
        if artifact == program and result:
            result[0]["count"] += 1
        return result

    monkeypatch.setattr(evaluation, "execute", broken)
    proof = evaluate_frozen(formation["freeze"])
    assert proof["decision"]["local_verdict"] == "FAIL"
    assert any(item["gate"] == "correctness" for item in proof["failures"])


def test_packaged_verifier_process_fresh_data_and_protocol_binding(formation: dict[str, Any], tmp_path: Path) -> None:
    frozen = formation["freeze"]
    source = tmp_path / "freeze.json"
    output = tmp_path / "report.json"
    source.write_bytes(canonical(frozen))
    subprocess.run(
        [
            sys.executable,
            "-m",
            "alpha_factory_v1.core.runtime.successor.evaluation",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
        check=True,
        timeout=30,
    )
    proof = safe_json_loads(output.read_bytes())
    second = examine(frozen)
    assert proof["protected_evidence_commitment"] != second["protected_evidence_commitment"]
    assert proof["measurement_id"] != second["measurement_id"]
    assert len(proof["units"]) == 12 and len(second["units"]) == 12
    assert proof["release_digest"] == frozen["release_digest"]
    assert proof["protocol_hash"] == digest("proof-protocol", frozen["manifest"]["proof_protocol"])
    assert proof["custody"]["organization_independent"] is False
    assert proof["custody"]["protected_data_exported"] is False
    assert proof["decision"]["qualification_verdict"] == "HOLD"
    assert proof["failures"] == []
    assert frozen["manifest"]["frozen_at_ms"] <= proof["examined_at_ms"] <= proof["issued_at_ms"]


def test_verifier_cli_refuses_existing_or_symlink_output(formation: dict[str, Any], tmp_path: Path) -> None:
    source = tmp_path / "freeze.json"
    source.write_bytes(canonical(formation["freeze"]))
    target = tmp_path / "owned.json"
    target.write_text("preserve")
    linked = tmp_path / "linked.json"
    linked.symlink_to(target)
    for output in (target, linked):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alpha_factory_v1.core.runtime.successor.evaluation",
                "--input",
                str(source),
                "--output",
                str(output),
            ],
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert result.returncode != 0
        assert target.read_text() == "preserve"


def test_full_offline_two_generation_run_dispatches_real_phases() -> None:
    phases = []

    def dispatch(family: str, operation: Any) -> dict[str, Any]:
        phases.append((family, "start"))
        result = operation()
        phases.append((family, "accepted"))
        return result

    result = run_study(request(), phase_hook=dispatch)
    assert phases == [
        (phase, status)
        for phase in ("formation", "challenge", "verification", "renewal")
        for status in ("start", "accepted")
    ]
    assert result["verdict"] == "HOLD"
    second = result["generation_two"]
    assert digest("generation-two-preregistration", second["preregistration"]) == second["preregistration_hash"]
    assert second["summary"]["paired_formation_trials"] == len(second["trials"]) == 1
    arms = second["trials"][0]["arms"]
    assert arms["memory"]["formation"]["freeze"]["manifest"]["memory"]["admitted"] is not None
    assert arms["no_memory"]["formation"]["freeze"]["manifest"]["memory"]["admitted"] is None
    assert (
        arms["memory"]["formation"]["freeze"]["release_digest"]
        != arms["no_memory"]["formation"]["freeze"]["release_digest"]
    )
    for arm in arms.values():
        assert arm["active_proof_inherited"] == arm["active_grants_inherited"] == []
        assert len(arm["proof"]["units"]) == 12
        assert arm["proof"]["failures"] == []
    assert result["costs"]["human_review_ns"] is None
    assert len(canonical(result)) > 1000


def test_supplier_bounds_and_failure_never_fallback_to_fake_success() -> None:
    class ExcessSupplier(GrammarSupplier):
        def propose(
            self, seed: int, limit: int, memory: dict[str, Any] | None
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            return super().propose(seed, 8, memory)

    with pytest.raises(ValueError, match="allowance"):
        discover(request(), supplier=ExcessSupplier())

    class FailingSupplier(GrammarSupplier):
        def propose(
            self, seed: int, limit: int, memory: dict[str, Any] | None
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            raise TimeoutError("supplier unavailable")

    with pytest.raises(TimeoutError, match="supplier unavailable"):
        discover(request(), supplier=FailingSupplier())


def test_renewal_does_not_leak_mutable_supplier_context_between_arms(formation: dict[str, Any]) -> None:
    class RememberingSupplier(GrammarSupplier):
        remembered = False

        def propose(
            self, seed: int, limit: int, memory: dict[str, Any] | None
        ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
            self.remembered = self.remembered or memory is not None
            programs, provenance = super().propose(seed, limit, memory)
            provenance["cached_memory_seen"] = self.remembered
            return programs, provenance

    supplier = RememberingSupplier()
    renewed = renew_study(request(), formation, supplier=supplier)
    arms = renewed["trials"][0]["arms"]
    assert arms["memory"]["formation"]["supplier"]["cached_memory_seen"] is True
    assert arms["no_memory"]["formation"]["supplier"]["cached_memory_seen"] is False
    assert supplier.remembered is False


def test_maximum_valid_output_can_be_committed_without_exceeding_transport_parser() -> None:
    events = workload(82, 20_000, 1)
    result = current(events)
    assert len(result) == 20_000
    assert len(sequence_digest("output", result)) == 64


def test_actual_cancellation_stops_formation() -> None:
    def cancelled() -> None:
        raise InterruptedError("operator cancelled")

    with pytest.raises(InterruptedError, match="operator cancelled"):
        discover(request(), checkpoint=cancelled)


def test_live_supplier_reuses_maintained_transport_and_preserves_unavailability(monkeypatch: Any) -> None:
    from alpha_factory_v1.core.runtime.models import RuntimeConfig
    from alpha_factory_v1.core.runtime.successor import mission

    supplier = OpenAICompatibleSupplier(
        RuntimeConfig(llm_url="http://127.0.0.1:1234/v1", llm_model="operator-selected")
    )

    def unavailable(*args: Any, **kwargs: Any) -> Any:
        raise TimeoutError("configured model did not answer")

    monkeypatch.setattr(mission, "complete_json", unavailable)
    with pytest.raises(TimeoutError, match="configured model did not answer"):
        supplier.propose(42, 2, None)
