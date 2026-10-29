# SPDX-License-Identifier: Apache-2.0
"""Positive lexical source admission; exposed static controls, no AST execution."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from copy import deepcopy
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

from alpha_factory_v1.core.runtime.invention_automation import evidence_critic
from contrib.invention_automation import critic_verify

F = TypeVar("F", bound=Callable[..., Any])
PROVENANCE = {"kind": "deterministic-engineering-control", "model": "NONE", "usage": "NOT_A_MODEL_CALL"}


def parameterize(name: str, values: list[Any]) -> Callable[[F], F]:
    """Preserve typed development-control parametrization with skipped imports."""
    return cast(Callable[[F], F], pytest.mark.parametrize(name, values))


def fixture(excerpt: str, value: str = "69/2", start: int = 0) -> tuple[dict[str, Any], dict[str, Any]]:
    """Bind a literal exposed excerpt and exact field span to an inert request."""
    request = cast(dict[str, Any], json.loads(Path(__file__).with_name("specification-request.json").read_text()))
    request["sources"][0]["excerpt"] = excerpt
    request["sources"][0]["sha256"] = hashlib.sha256(excerpt.encode()).hexdigest()
    request["records"][0]["fields"]["high_side_voltage"] = {"value": value, "unit": "kVA"}
    labels = {"high_side_voltage": "high-side voltage", "rated_power": "rated power", "frequency": "frequency"}
    context = {
        "schema": "agialpha/critic-context/v1",
        "requirements": {
            field: {
                "dimension": dimension,
                "authority": "declared-task",
                "labels": [labels[field]],
                "location": "/requirements/" + field,
            }
            for field, dimension in request["requirements"].items()
        },
        "sources": [
            {
                **{key: source[key] for key in ["id", "sha256", "url"]},
                "version": "exposed exact excerpt",
                "retrieved_utc": "UNKNOWN",
                "method": "provided source bytes; no publisher authentication",
            }
            for source in request["sources"]
        ],
        "bindings": [
            {
                "record_id": request["records"][0]["id"],
                "field": "high_side_voltage",
                "source_id": request["sources"][0]["id"],
                "start": start,
                "end": len(excerpt),
            }
        ],
    }
    return request, context


def supplied_objection(request: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """Supply a typed host objection even when the current scanner refuses it."""
    base, registered = fixture("high-side voltage of less than 34.5 kVA")
    objection = deepcopy(evidence_critic.investigate(base, registered, PROVENANCE).objections[0].to_dict())
    source = request["sources"][0]
    binding = context["bindings"][0]
    reading = request["records"][0]["fields"]["high_side_voltage"]
    objection["source"] = {
        "source_id": source["id"],
        "sha256": source["sha256"],
        "location": f"/sources/0/excerpt#chars={binding['start']}:{binding['end']}",
    }
    objection["witness"] = {**binding, **reading}
    return cast(dict[str, Any], objection)


@parameterize("bridge", [" ", " of less than ", " is ", ": ", " = ", " requirement ", " at most "])
def test_declared_positive_bridges_preserve_source_bound_static_defect(bridge: str) -> None:
    request, context = fixture("high-side voltage" + bridge + "34.5 kVA")
    finding = evidence_critic.investigate(request, context, PROVENANCE)
    assert len(finding.objections) == 1
    receipt = critic_verify.adjudicate(request, context, finding.objections[0].to_dict())
    assert receipt["verdict"] == "CONFIRMED"
    assert receipt["candidate_executed"] is receipt["technical_activity_accepted"] is False


@parameterize(
    "excerpt",
    [
        "high-side voltage was not reported. The equipment rating is 500 kVA.",
        "No high-side voltage 500 kVA",
        "not high-side voltage 500 kVA",
        "high-side voltage is not 500 kVA",
        "high-side voltage was not 500 kVA",
        "high-side voltage unknown while equipment is 500 kVA",
        "The document omits high-side voltage 500 kVA",
    ],
)
def test_negation_and_arbitrary_prose_remain_inconclusive(excerpt: str) -> None:
    request, context = fixture(excerpt, "500")
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    objection = supplied_objection(request, context)
    assert critic_verify.adjudicate(request, context, objection)["verdict"] == "INCONCLUSIVE"


@parameterize("prefix", ["No ", "not ", "The document omits ", "voltage was not specified as "])
def test_clipping_source_prefix_cannot_remove_negation_or_scope(prefix: str) -> None:
    request, context = fixture(prefix + "high-side voltage 500 kVA", "500", len(prefix))
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    objection = supplied_objection(request, context)
    assert critic_verify.adjudicate(request, context, objection)["verdict"] == "INCONCLUSIVE"


def test_wrong_field_span_cannot_confirm_an_unrelated_source_quantity() -> None:
    excerpt = "high-side voltage 34.5 kV; rated power 500 kVA"
    request, context = fixture(excerpt, "500", excerpt.index("rated power"))
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    assert critic_verify.adjudicate(request, context, supplied_objection(request, context))["verdict"] == "REFUTED"


@parameterize("label", ["equipment rating", "rated power", "unknown observation"])
def test_unknown_or_wrong_dimension_labels_cannot_supply_new_extraction_semantics(label: str) -> None:
    request, context = fixture(label + " 500 kVA", "500")
    context["requirements"]["high_side_voltage"]["labels"] = [label]
    assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is False
    with pytest.raises(ValueError, match="no declared extraction semantics"):
        evidence_critic.investigate(request, context, PROVENANCE)
    objection = supplied_objection(request, context)
    assert critic_verify.adjudicate(request, context, objection)["verdict"] == "INCONCLUSIVE"


def test_clause_start_after_a_real_boundary_remains_supported() -> None:
    prefix = "Unrelated source note. "
    request, context = fixture(prefix + "high-side voltage of less than 34.5 kVA", start=len(prefix))
    finding = evidence_critic.investigate(request, context, PROVENANCE)
    assert len(finding.objections) == 1
    assert critic_verify.adjudicate(request, context, finding.objections[0].to_dict())["verdict"] == "CONFIRMED"


@parameterize("suffix", ["V", "VA", "é", "_tail", "1"])
def test_clipped_unit_suffix_never_creates_a_source_token_boundary(suffix: str) -> None:
    prefix = "high-side voltage is 500 k"
    request, context = fixture(prefix + suffix, "500")
    request["records"][0]["fields"]["high_side_voltage"]["unit"] = "k"
    context["bindings"][0]["end"] = len(prefix)
    assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is False
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    assert critic_verify.adjudicate(request, context, supplied_objection(request, context))["verdict"] == "INCONCLUSIVE"


@parameterize("numeric_prefix", ["5", "50", "500", "500."])
def test_clipped_numeric_literal_cannot_authorize_an_objection(numeric_prefix: str) -> None:
    lead = "high-side voltage is "
    request, context = fixture(lead + "500.5 kV", "500")
    request["records"][0]["fields"]["high_side_voltage"]["unit"] = "k"
    context["bindings"][0]["end"] = len(lead + numeric_prefix)
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    assert critic_verify.adjudicate(request, context, supplied_objection(request, context))["verdict"] == "INCONCLUSIVE"


def test_complete_unit_before_punctuation_remains_admissible() -> None:
    request, context = fixture("high-side voltage is 500 kVA.", "500")
    context["bindings"][0]["end"] -= 1
    finding = evidence_critic.investigate(request, context, PROVENANCE)
    assert len(finding.objections) == 1
    assert critic_verify.adjudicate(request, context, finding.objections[0].to_dict())["verdict"] == "CONFIRMED"
