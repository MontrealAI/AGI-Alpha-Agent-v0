# SPDX-License-Identifier: Apache-2.0
"""Engineering regressions; all fixtures exposed, no confirmation or candidate execution."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.invention_automation import specification as spec
from alpha_factory_v1.core.runtime.invention_automation import specification_run as runner
from alpha_factory_v1.core.utils.secure_run import SandboxUnavailable

FIXTURE = Path(__file__).with_name("specification-request.json")


def request() -> dict[str, Any]:
    return json.loads(FIXTURE.read_text())


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


@pytest.mark.parametrize("operator", ["exec", "shell", "open", "network", "wallet", "reserve-hardware", "import"])
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
    monkeypatch.setattr(runner.shutil, "which", lambda _: None)
    calls = []

    def deny(command: Any) -> Any:
        calls.append(command)
        raise SandboxUnavailable("no Docker; host forbidden")

    monkeypatch.setattr(runner, "secure_run", deny)
    result = runner.isolated(request()["proposal"], request()["records"])
    assert result["status"] == "BLOCKED" and result["executed"] is False
    assert len(calls) == 1


def test_mutable_sandbox_image_never_launched(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner.shutil, "which", lambda _: "/usr/bin/docker")
    monkeypatch.setenv("ALPHA_SANDBOX_IMAGE", "python:3.12-slim")
    result = runner.isolated(request()["proposal"], request()["records"])
    assert result["status"] == "BLOCKED" and result["executed"] is False


def test_checkpoint_recovery_refuses_corrupt_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import datetime

    class BeforeCutoff(datetime.datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Any:
            return cls(2026, 10, 29, 13, 0, tzinfo=tz)

    monkeypatch.setattr(runner, "datetime", BeforeCutoff)
    monkeypatch.setattr(
        runner, "independent_criticism", lambda *args: {"critic_validated": True, "confirmation": False}
    )
    monkeypatch.setattr(
        runner,
        "isolated",
        lambda *args: {"status": "BLOCKED", "executed": False, "reason": "test-only boundary; no execution"},
    )
    out = tmp_path / "new"
    value = request()
    result = runner.run(value, out, freeze=tmp_path / "freeze.json")
    assert runner.resume(value, out) == result
    (out / "experience.json").write_text("{}")
    with pytest.raises(ValueError, match="checkpoint corruption"):
        runner.resume(value, out)


def test_request_identity_and_no_evidence_overwrite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import datetime

    class BeforeCutoff(datetime.datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Any:
            return cls(2026, 10, 29, 13, 0, tzinfo=tz)

    monkeypatch.setattr(runner, "datetime", BeforeCutoff)
    monkeypatch.setattr(
        runner, "independent_criticism", lambda *args: {"critic_validated": True, "confirmation": False}
    )
    monkeypatch.setattr(
        runner, "isolated", lambda *args: {"status": "BLOCKED", "executed": False, "reason": "test-only"}
    )
    out = tmp_path / "new"
    value = request()
    runner.run(value, out, freeze=tmp_path / "freeze.json")
    saved = (out / "bundle.json").read_bytes()
    with pytest.raises(FileExistsError):
        runner.run(value, out, freeze=tmp_path / "freeze.json")
    changed = deepcopy(value)
    changed["problem"]["id"] = "different"
    with pytest.raises(ValueError, match="identity mismatch"):
        runner.resume(changed, out)
    assert (out / "bundle.json").read_bytes() == saved


def test_independent_criticism_refusal_prevents_construction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def reject(*args: Any) -> Any:
        raise ValueError("independent criticism rejected")

    def forbidden(*args: Any) -> Any:
        pytest.fail("construction called before criticism acceptance")

    import datetime

    class BeforeCutoff(datetime.datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Any:
            return cls(2026, 10, 29, 13, 0, tzinfo=tz)

    monkeypatch.setattr(runner, "datetime", BeforeCutoff)
    monkeypatch.setattr(runner, "independent_criticism", reject)
    monkeypatch.setattr(spec, "construct", forbidden)
    with pytest.raises(ValueError, match="independent criticism rejected"):
        runner.run(request(), tmp_path / "failed", freeze=tmp_path / "freeze.json")
    failure = json.loads((tmp_path / "failed/failure.json").read_text())
    assert failure["self_cpu_ns"] > 0
    assert (tmp_path / "failed/criticism.json").is_file()
    assert not (tmp_path / "failed/bundle.json").exists()


def test_original_generation_cutoff_is_not_replenished(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import datetime

    class AfterCutoff(datetime.datetime):
        @classmethod
        def now(cls, tz: Any = None) -> Any:
            return cls(2026, 10, 29, 16, 53, tzinfo=tz)

    monkeypatch.setattr(runner, "datetime", AfterCutoff)
    with pytest.raises(ValueError, match="inherited generation cutoff"):
        runner.run(request(), tmp_path / "new", freeze=tmp_path / "freeze.json")
    assert not (tmp_path / "new").exists()
