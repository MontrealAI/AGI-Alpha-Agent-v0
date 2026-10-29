# SPDX-License-Identifier: Apache-2.0
"""Complete-excerpt token boundaries; exposed static checks, no AST execution."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar, cast

import pytest

from alpha_factory_v1.core.runtime.invention_automation import evidence_critic
from alpha_factory_v1.core.runtime.invention_verification import critic_verify
from contrib.invention_automation.test_source_bridge import PROVENANCE, fixture, supplied_objection

F = TypeVar("F", bound=Callable[..., Any])


def parameterize(name: str, values: list[Any]) -> Callable[[F], F]:
    """Keep parametrized engineering controls typed with skipped imports."""
    return cast(Callable[[F], F], pytest.mark.parametrize(name, values))


@parameterize("prefix", ["", "Unrelated source note. "])
def test_clipped_k_from_original_kv_cannot_create_a_confirmed_source_defect(prefix: str) -> None:
    request, context = fixture(prefix + "high-side voltage is 500 kV", "500", start=len(prefix))
    request["records"][0]["fields"]["high_side_voltage"]["unit"] = "k"
    context["bindings"][0]["end"] -= 1
    assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is False
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    objection = supplied_objection(request, context)
    verdict = critic_verify.adjudicate(request, context, objection)
    assert verdict["verdict"] == "REFUTED"
    assert "unit token" in verdict["reason"]
    assert verdict["candidate_executed"] is False


@parameterize("unit", ["kV", "kVA", "MVA", "VA", "Hz", "kV2", "kV_rating", "kVΩ"])
def test_every_partial_source_unit_requires_the_original_token_boundary(unit: str) -> None:
    excerpt = "high-side voltage is 500 " + unit
    token_start = len(excerpt) - len(unit)
    for length in range(1, len(unit)):
        request, context = fixture(excerpt, "500")
        request["records"][0]["fields"]["high_side_voltage"]["unit"] = unit[:length]
        context["bindings"][0]["end"] = token_start + length
        objection = supplied_objection(request, context)
        assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is False
        assert not evidence_critic.investigate(request, context, PROVENANCE).objections
        assert critic_verify.adjudicate(request, context, objection)["verdict"] != "CONFIRMED"


def test_scientific_quantity_suffix_cannot_be_clipped_into_an_invented_unit() -> None:
    excerpt = "high-side voltage is 500e3 kV"
    request, context = fixture(excerpt, "500")
    request["records"][0]["fields"]["high_side_voltage"]["unit"] = "e"
    context["bindings"][0]["end"] = excerpt.index("e3") + 1
    assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is False
    assert not evidence_critic.investigate(request, context, PROVENANCE).objections
    assert critic_verify.adjudicate(request, context, supplied_objection(request, context))["verdict"] != "CONFIRMED"


def test_numeric_and_label_clipping_do_not_bypass_the_source_grammar() -> None:
    for excerpt, value in [
        ("high-side voltage is 5000 kVA", "500"),
        ("high-side voltages is 500 kVA", "500"),
    ]:
        request, context = fixture(excerpt, value)
        assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is False
        assert not evidence_critic.investigate(request, context, PROVENANCE).objections
        assert (
            critic_verify.adjudicate(request, context, supplied_objection(request, context))["verdict"] != "CONFIRMED"
        )


@parameterize("unit", ["V", "kV", "VA", "kVA", "MVA", "Hz"])
def test_complete_known_unit_at_source_end_remains_a_valid_literal_association(unit: str) -> None:
    request, context = fixture("high-side voltage is 500 " + unit, "500")
    request["records"][0]["fields"]["high_side_voltage"]["unit"] = unit
    assert evidence_critic.bound_literal(request, context, context["bindings"][0])[0] is True
    objection = supplied_objection(request, context)
    assert critic_verify.field_literal(request, context, objection["witness"], objection["source"])[0] is True
    expected = "REFUTED" if unit in {"V", "kV"} else "CONFIRMED"
    assert critic_verify.adjudicate(request, context, objection)["verdict"] == expected


def test_doe_control_and_complete_unit_before_source_punctuation_remain_supported() -> None:
    for excerpt, span_end in [
        ("high-side voltage of less than 34.5 kVA", None),
        (
            "high-side voltage of less than 34.5 kVA. Retained source note.",
            len("high-side voltage of less than 34.5 kVA"),
        ),
    ]:
        request, context = fixture(excerpt)
        if span_end is not None:
            context["bindings"][0]["end"] = span_end
        finding = evidence_critic.investigate(request, context, PROVENANCE)
        assert len(finding.objections) == 1
        receipt = critic_verify.adjudicate(request, context, finding.objections[0].to_dict())
        assert receipt["verdict"] == "CONFIRMED"
        assert receipt["candidate_executed"] is receipt["technical_activity_accepted"] is False
