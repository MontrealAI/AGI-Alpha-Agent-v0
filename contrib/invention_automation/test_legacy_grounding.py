# SPDX-License-Identifier: Apache-2.0
"""Legacy admission closure; exposed trusted controls, no candidate execution."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

from alpha_factory_v1.core.runtime.invention_automation import evidence_critic, operator
from alpha_factory_v1.core.runtime.invention_automation import specification as spec
from alpha_factory_v1.core.runtime.invention_automation import specification_run as runner
from contrib.invention_automation import critic_verify, qualify_verify
from contrib.invention_automation.reproduce_field_misbinding import fixed_field_oracle, misbound_request

PROVENANCE = {"kind": "deterministic-engineering-control", "model": "NONE", "usage": "NOT_A_MODEL_CALL"}
F = TypeVar("F", bound=Callable[..., Any])


def parameterize(name: str, values: list[Any]) -> Callable[[F], F]:
    """Keep development-fixture parametrization typed with skipped imports."""
    return cast(Callable[[F], F], pytest.mark.parametrize(name, values))


def request() -> dict[str, Any]:
    """Read the exposed source-screening fixture without executing its AST."""
    return cast(dict[str, Any], json.loads(Path(__file__).with_name("specification-request.json").read_text()))


def context(value: dict[str, Any], start: int, end: int) -> dict[str, Any]:
    """Supply explicit field labels and a bounded source association."""
    labels = {"high_side_voltage": "high-side voltage", "rated_power": "rated power", "frequency": "frequency"}
    return {
        "schema": "agialpha/critic-context/v1",
        "requirements": {
            field: {
                "dimension": dimension,
                "authority": "declared-task",
                "labels": [labels[field]],
                "location": "/requirements/" + field,
            }
            for field, dimension in value["requirements"].items()
        },
        "sources": [
            {
                **{key: source[key] for key in ["id", "sha256", "url"]},
                "version": "exposed frozen engineering fixture",
                "retrieved_utc": "UNKNOWN",
                "method": "provided source excerpt, not publisher authentication",
            }
            for source in value["sources"]
        ],
        "bindings": [
            {
                "record_id": value["records"][0]["id"],
                "field": "high_side_voltage",
                "source_id": value["sources"][0]["id"],
                "start": start,
                "end": end,
            }
        ],
    }


def test_historical_false_match_cannot_reenter_native_qualification(tmp_path: Path) -> None:
    value = misbound_request(request())
    witness = spec.criticize(value)
    historical = qualify_verify.verify_criticism(value, witness)
    assert historical["critic_validated"] is True
    assert historical["qualification"] == "LEGACY_UNQUALIFIED"
    assert historical["source_field_span_grounded"] is historical["current_admission"] is False
    assert fixed_field_oracle(value)["field_association_matches"] is False
    for entry in [runner.run, runner._run]:
        with pytest.raises(ValueError, match="does not bind source fields/spans"):
            entry(value, tmp_path / "refused", freeze=tmp_path / "freeze.json")
    assert not (tmp_path / "refused").exists()


@parameterize("command", ["qualify", "qualify-resume", "qualify-reproduce"])
def test_native_legacy_commands_fail_before_input_or_orchestration(
    command: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    parser = argparse.ArgumentParser()
    operator.add_commands(parser.add_subparsers(dest="command", required=True))
    argv = ["invention", command, str(tmp_path / "misbound.json"), "--output", str(tmp_path / "output")]
    if command == "qualify":
        argv.extend(["--freeze", str(tmp_path / "old-freeze.json")])
    elif command == "qualify-reproduce":
        argv.extend(["--checkpoint", str(tmp_path / "old-checkpoint")])
    args = parser.parse_args(argv)

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("legacy native command read input or entered orchestration")

    monkeypatch.setattr(operator, "read", forbidden)
    for name in ["run", "resume", "reproduce", "_run"]:
        monkeypatch.setattr(runner, name, forbidden)
    with pytest.raises(ValueError, match="Use alpha-agent invention critic-loop with --context"):
        operator.handle(args)
    assert not (tmp_path / "output").exists()


@parameterize("span", ["whole-excerpt", "wrong-field", "correct-field-wrong-reading"])
def test_current_critic_refuses_each_misbound_legacy_witness(span: str) -> None:
    value = misbound_request(request())
    excerpt = value["sources"][0]["excerpt"]
    if span == "whole-excerpt":
        start, end = 0, len(excerpt)
    elif span == "wrong-field":
        start, end = excerpt.index("rated power"), excerpt.index("; frequency")
    else:
        start, end = 0, excerpt.index(";")
    ctx = context(value, start, end)
    finding = evidence_critic.investigate(value, ctx, PROVENANCE)
    assert finding.objections == ()
    assert evidence_critic.bound_literal(value, ctx, ctx["bindings"][0])[0] is False


def test_current_source_bound_defect_remains_supported_and_separately_adjudicated() -> None:
    value = request()
    excerpt = "high-side voltage 34.5 kVA"
    value["sources"][0]["excerpt"] = excerpt
    value["sources"][0]["sha256"] = hashlib.sha256(excerpt.encode()).hexdigest()
    ctx = context(value, 0, len(excerpt))
    finding = evidence_critic.investigate(value, ctx, PROVENANCE)
    assert len(finding.objections) == 1
    receipt = critic_verify.adjudicate(value, ctx, finding.objections[0].to_dict())
    assert receipt["verdict"] == "CONFIRMED"
    assert receipt["candidate_executed"] is False
    assert receipt["technical_activity_accepted"] is False
