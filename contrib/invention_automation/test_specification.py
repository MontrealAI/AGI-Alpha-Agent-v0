# SPDX-License-Identifier: Apache-2.0
"""Engineering regressions; all fixtures exposed, no confirmation or candidate execution."""

import json
import shutil
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

from alpha_factory_v1.core.runtime.invention_automation import specification as spec
from alpha_factory_v1.core.runtime.invention_automation import specification_run as runner
from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

FIXTURE = Path(__file__).with_name("specification-request.json")
F = TypeVar("F", bound=Callable[..., Any])


def parameterize(name: str, values: list[Any]) -> Callable[[F], F]:
    """Keep development-fixture parametrization typed with skipped imports."""
    return cast(Callable[[F], F], pytest.mark.parametrize(name, values))


def request() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(FIXTURE.read_text()))


def test_literal_counterexample_produces_bound_constraint() -> None:
    value = request()
    witness = spec.criticize(value)
    constraint = spec.constrain(value, witness)
    assert witness["observed_unit"] == "kVA"
    assert witness["required_dimension"] == "voltage"
    assert constraint["validated"] is True
    assert "unknown" in witness["uncertainty"]


def test_actual_host_authorship_and_generated_composition_retained() -> None:
    value = request()
    new = spec.construct(value, spec.constrain(value, spec.criticize(value)))
    assert new["origin"] == "host-model"
    assert new["program"] != value["baseline"]
    assert new["candidate_count"] == 7
    assert all(x["status"] == "STATIC_VALID" for x in new["attempts"])
    assert new["runtime_status"] == "NOT_EXECUTED"


@parameterize("operator", ["exec", "shell", "open", "network", "wallet", "reserve-hardware", "import"])
def test_uninstalled_capability_rejected(operator: str) -> None:
    value = request()
    value["proposal"] = {"op": operator}
    with pytest.raises(ValueError, match="uninstalled"):
        spec.validate_request(value)


def test_invalid_mapping_and_negative_transfer_are_not_promoted() -> None:
    value = request()
    wrong = deepcopy(value["proposal"])
    wrong["steps"][1]["test"]["dimension"] = "apparent_power"
    with pytest.raises(ValueError, match="typed grounded"):
        spec.dominance(wrong, value["requirements"], value["budget"])
    witness = spec.criticize(value)
    witness["required_dimension"] = "apparent_power"
    with pytest.raises(ValueError, match="irrelevant or corrupted"):
        spec.constrain(value, witness)


def test_irrelevant_source_quantity_cannot_validate_criticism() -> None:
    value = request()
    value["records"][0]["fields"]["high_side_voltage"]["value"] = "999"
    with pytest.raises(ValueError, match="quantity and unit"):
        spec.criticize(value)


def test_source_corruption_rejected() -> None:
    value = request()
    value["sources"][0]["excerpt"] += " changed"
    with pytest.raises(ValueError, match="corrupt literal"):
        spec.validate_request(value)


def test_hidden_answers_and_budget_tampering_rejected() -> None:
    value = request()
    value["hidden_answers"] = {"x": True}
    with pytest.raises(ValueError, match="schema"):
        spec.validate_request(value)
    value = request()
    value["budget"]["max_candidates"] = True
    with pytest.raises(ValueError, match="bounded integer"):
        spec.validate_request(value)


def test_candidate_search_does_not_reset_allowance() -> None:
    value = request()
    value["budget"]["max_candidates"] = 2
    out = spec.construct(value, spec.constrain(value, spec.criticize(value)))
    assert out["candidate_count"] == 2
    assert len(out["attempts"]) == 2


def test_conventional_reference_retains_all_inputs_and_abstentions() -> None:
    value = request()
    result = spec.inspect_records(value)
    assert [x["id"] for x in result] == [x["id"] for x in value["records"]]
    assert [x["status"] for x in result] == [
        "ABSTAIN",
        "CONSISTENT",
        "CONSISTENT",
        "ABSTAIN",
        "ABSTAIN",
        "ABSTAIN",
        "ABSTAIN",
    ]


def test_conventional_diagnostics_survive_canonical_json_round_trip() -> None:
    value = request()
    canonical = json.loads(json.dumps(value, sort_keys=True))
    assert spec.inspect_records(value) == spec.inspect_records(canonical)


def test_baseline_and_vacuous_proposals_fail_static_acceptance() -> None:
    value = request()
    for program in [value["baseline"], {"op": "emit", "status": "ABSTAIN"}]:
        with pytest.raises(ValueError):
            spec.dominance(program, value["requirements"], value["budget"])


def test_observation_and_path_bounds_enforced() -> None:
    value = request()
    proposal = deepcopy(value["proposal"])
    proposal["steps"] = [proposal["steps"][1]]
    with pytest.raises(ValueError, match="before observation"):
        spec.dominance(proposal, value["requirements"], value["budget"])
    with pytest.raises(ValueError, match="resource bound"):
        spec.shape(value["proposal"], value["requirements"], {**value["budget"], "max_nodes": 2})


def test_repeated_false_test_cannot_fake_reachable_acceptance() -> None:
    value = request()
    p = deepcopy(value["proposal"])
    p["steps"][1]["else"] = deepcopy(value["proposal"])
    with pytest.raises(ValueError, match="repeated predicate"):
        spec.dominance(p, value["requirements"], value["budget"])


def test_no_host_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: None)
    calls = []

    def deny(command: Any) -> Any:
        calls.append(command)
        raise SandboxUnavailable("no Docker; host forbidden")

    monkeypatch.setattr(runner, "secure_run", deny)
    result = runner.isolated(request()["proposal"], request()["records"])
    assert result["status"] == "BLOCKED" and result["executed"] is False
    assert len(calls) == 1


def test_mutable_sandbox_image_never_launched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setenv("ALPHA_SANDBOX_IMAGE", "python:3.12-slim")
    result = runner.isolated(request()["proposal"], request()["records"])
    assert result["status"] == "BLOCKED" and result["executed"] is False


def test_retired_checkpoint_resume_cannot_promote_or_copy_evidence(tmp_path: Path) -> None:
    source = tmp_path / "historical"
    source.mkdir()
    checkpoint = source / "checkpoint.json"
    checkpoint.write_text('{"schema":"agialpha/specification-checkpoint/v1","files":{}}')
    before = checkpoint.read_bytes()
    with pytest.raises(ValueError, match="legacy checkpoints remain unqualified historical evidence"):
        runner.resume(request(), source)
    with pytest.raises(ValueError, match="legacy checkpoints remain unqualified historical evidence"):
        runner.reproduce(request(), source, tmp_path / "replay")
    assert checkpoint.read_bytes() == before
    assert not (tmp_path / "replay").exists()


def test_retired_generation_does_not_overwrite_existing_evidence(tmp_path: Path) -> None:
    out = tmp_path / "existing"
    out.mkdir()
    bundle = out / "bundle.json"
    bundle.write_bytes(b"retained original, not current acceptance")
    before = bundle.read_bytes()
    with pytest.raises(ValueError, match="Legacy specification qualification is retired"):
        runner.run(request(), out, freeze=tmp_path / "freeze.json")
    assert bundle.read_bytes() == before
    assert list(out.iterdir()) == [bundle]


def test_legacy_rejection_precedes_verification_construction_and_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("retired protocol reached a verifier, constructor or candidate runner")

    monkeypatch.setattr(runner, "independent_criticism", forbidden)
    monkeypatch.setattr(spec, "construct", forbidden)
    monkeypatch.setattr(runner, "isolated", forbidden)
    for entry in [runner.run, runner._run]:
        with pytest.raises(ValueError, match="Legacy specification qualification is retired"):
            entry(request(), tmp_path / "new", freeze=tmp_path / "freeze.json")
    assert not (tmp_path / "new").exists()


def test_legacy_protocol_cannot_be_reopened_by_a_new_clock_or_freeze(tmp_path: Path) -> None:
    for value in [request(), {}]:
        with pytest.raises(ValueError, match="freshly frozen critic verifier"):
            runner.run(value, tmp_path / "new", freeze=tmp_path / "unreadable-freeze.json")
    assert not (tmp_path / "new").exists()
