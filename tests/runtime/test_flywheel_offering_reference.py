# SPDX-License-Identifier: Apache-2.0
"""Versioned pricing hypotheses preserve v1 bytes and all execution gates."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict
from alpha_factory_v1.core.runtime.successor.flywheel_discovery import Discovery, OfferingLink
from alpha_factory_v1.core.runtime.successor.flywheel_enterprise import (
    BuyerValueHypothesis,
    Enterprise,
    Offering,
    OfferingV2,
    parse_offering,
)
from alpha_factory_v1.core.runtime.successor.protocol import canonical, digest
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
import test_flywheel_discovery as d
import test_flywheel_enterprise as e
import test_flywheel_protected as f
import test_flywheel_specialists as s


@pytest.fixture
def setup(tmp_path: Path) -> dict[str, Any]:
    return f.setup.__wrapped__(tmp_path)


def buyer(state: dict[str, Any]) -> BuyerValueHypothesis:
    return BuyerValueHypothesis(
        beneficiary=e.offering(state).beneficiary,
        outside_option="Use an existing consumer-appropriate service or decline this offering",
        basis="Internal buyer-value mechanism hypothesis; no price or buyer interview is observed",
        source_evidence=[d.evidence(state, "@buyer-value-basis")],
        uncertainty="Value and willingness to pay remain unknown; this is not demand evidence",
    )


def v2(state: dict[str, Any]) -> OfferingV2:
    raw = e.offering(state).model_dump()
    raw.update(
        schema_name="flywheel-offering/v2",
        human_reference=None,
        buyer_value_hypothesis=buyer(state).model_dump(),
        price_candidates_micro_usd=[],
    )
    return OfferingV2.model_validate(raw)


def register(state: dict[str, Any], spec: OfferingV2 | None = None) -> dict[str, Any]:
    spec = spec or v2(state)
    return Enterprise(state["service"]).apply(e.command(state, "offering", spec.model_dump(), "v2-offering"))


def test_v1_canonical_serialization_is_preserved() -> None:
    raw = {
        "offering_id": "stable-v1",
        "version": 1,
        "beneficiary": "Beneficiary",
        "useful_outcome": "Useful result",
        "deliverable": "Artifact",
        "scope": "Original scope",
        "acceptance_criteria": ["Original checker"],
        "need_evidence": [{"journal_key": "@need", "record_digest": "0" * 64}],
        "demand_uncertainty": "Unknown demand",
        "human_reference": {
            "service": "Equivalent human service",
            "source": "Explicit illustrative source",
            "basis": "estimated-team-hours",
            "team_hours": 1,
            "hourly_rate_micro_usd": 1_000_000,
            "total_micro_usd": 1_000_000,
        },
        "permitted_tools": ["inspect"],
        "price_policy": "Explicit candidate",
        "price_candidates_micro_usd": [1_000_000],
        "capacity": 1,
        "turnaround_seconds": 60,
        "complete_cost_cap_micro_usd": 1_000_000,
        "risks": ["Unknown demand"],
        "operating_limits": ["No deployment"],
        "mode": "hybrid",
    }
    original = Offering.model_validate(raw)
    reparsed = parse_offering(raw)
    assert type(reparsed) is Offering
    assert canonical(reparsed) == canonical(original)
    assert "buyer_value_hypothesis" not in reparsed.model_dump()
    assert reparsed.model_dump()["schema_name"] == "flywheel-offering/v1"
    assert (
        hashlib.sha256(canonical(reparsed)).hexdigest()
        == "269ddcfb74f7614ef1d474ef048d7aca1763280827b88183c6aedad57aba36ce"
    )
    with pytest.raises(ValueError):
        Offering.model_validate({**raw, "human_reference": None})


def test_v2_unknown_value_and_empty_prices_are_honest_hypotheses(setup: dict[str, Any]) -> None:
    spec = v2(setup)
    assert isinstance(parse_offering(spec.model_dump()), OfferingV2)
    assert spec.human_reference is None and spec.price_candidates_micro_usd == []
    assert spec.buyer_value_hypothesis is not None
    assert spec.buyer_value_hypothesis.value_lower_micro_usd is None
    assert spec.buyer_value_hypothesis.willingness_to_pay_upper_micro_usd is None
    result = register(setup, spec)
    assert result["stage"] == "hypothesis" and result["commercial"] is None
    assert setup["costs"].report()["collected_revenue"] == 0


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "beneficiary",
        "value-partial",
        "value-reversed",
        "wtp-partial",
        "wtp-reversed",
        "negative",
        "accepted-demand",
        "unknown-schema",
        "v1-extra",
    ],
)
def test_pricing_reference_rejects_missing_impossible_or_relabelled_evidence(
    setup: dict[str, Any], attack: str
) -> None:
    raw = v2(setup).model_dump()
    hypothesis = raw["buyer_value_hypothesis"]
    if attack == "missing":
        raw["buyer_value_hypothesis"] = None
    elif attack == "beneficiary":
        hypothesis["beneficiary"] = "Another recipient"
    elif attack == "value-partial":
        hypothesis["value_lower_micro_usd"] = 10
    elif attack == "value-reversed":
        hypothesis.update(value_lower_micro_usd=20, value_upper_micro_usd=10)
    elif attack == "wtp-partial":
        hypothesis["willingness_to_pay_upper_micro_usd"] = 10
    elif attack == "wtp-reversed":
        hypothesis.update(willingness_to_pay_lower_micro_usd=20, willingness_to_pay_upper_micro_usd=10)
    elif attack == "negative":
        hypothesis.update(value_lower_micro_usd=-1, value_upper_micro_usd=10)
    elif attack == "accepted-demand":
        hypothesis["evidence_type"] = "accepted-demand"
    elif attack == "unknown-schema":
        raw["schema_name"] = "flywheel-offering/v3"
    else:
        raw["schema_name"] = "flywheel-offering/v1"
    with pytest.raises(ValueError):
        parse_offering(raw)


def test_v2_can_preserve_primary_human_reference_without_buyer_hypothesis(setup: dict[str, Any]) -> None:
    raw = e.offering(setup).model_dump()
    raw["schema_name"] = "flywheel-offering/v2"
    assert OfferingV2.model_validate(raw).human_reference == e.offering(setup).human_reference


def test_v2_original_prototype_acceptance_and_quote_gates_remain_required(setup: dict[str, Any]) -> None:
    state = setup
    s.funding(state)
    register(state)
    with pytest.raises(ValueError, match="stages cannot be skipped"):
        e.advance(state, "authorized")
    e.decision(state)
    Enterprise(state["service"]).run("first-decision", *e.execution(state))
    executed = state["journal"].latest(operation_key("placement-origin"))
    e.advance(state, "prototype")
    with pytest.raises((ValueError, KeyError)):
        e.advance(state, "technically-qualified")
    e.accept(state, executed)
    e.advance(state, "technically-qualified")
    with pytest.raises(ValueError, match="outside the versioned policy"):
        e.advance(state, "commercially-assessed", e.commercial(state, lower=100))
    assert Enterprise(state["service"]).inspect("offering", "resilient-placement")["stage"] == "technically-qualified"
    with pytest.raises(ValueError):
        e.advance(state, "authorized")


@pytest.mark.parametrize("attack", ["goal", "criteria", "mode"])
def test_v2_prototype_cannot_widen_original_purpose(setup: dict[str, Any], attack: str) -> None:
    state = setup
    s.funding(state)
    register(state)
    e.decision(state)
    executor, mission, profile, permit = e.execution(state)
    changes = (
        {"goal": "Easier work"}
        if attack == "goal"
        else {"acceptance_criteria": ["Plausible result"]}
        if attack == "criteria"
        else {"mode": "simulation"}
    )
    changed = mission.model_copy(update=changes)
    with pytest.raises(ValueError, match="selected offering envelope"):
        Enterprise(state["service"]).run("first-decision", executor, changed, profile, permit)


def test_buyer_hypothesis_sources_are_rechecked_at_decision_and_discovery_link(setup: dict[str, Any]) -> None:
    state = setup
    spec = v2(state)
    registered = register(state, spec)
    d.register_witness(state)
    opportunity = d.opportunity(state)
    link = OfferingLink(
        offering_id=spec.offering_id,
        offering_record_digest=registered["digest"],
        opportunity_id=opportunity.opportunity_id,
        opportunity_spec_digest=digest("discovery-opportunity", opportunity),
    )
    linked = Discovery(state["service"]).apply(d.command(state, "link-offering", link.model_dump(), "v2-link"))
    assert linked["offering_authorization_inherited"] is False
    with state["journal"].transaction() as cx:
        state["journal"].append(cx, "@buyer-value-basis", {"withdrawn": True})
        state["service"].checkpoint.advance(state["journal"], cx)
    with pytest.raises(Conflict, match="stale"):
        e.decision(state)
    with pytest.raises(Conflict, match="stale"):
        Discovery(state["service"]).apply(d.command(state, "link-offering", link.model_dump(), "v2-stale-link"))


def test_v2_registration_refuses_stale_buyer_basis(setup: dict[str, Any]) -> None:
    raw = v2(setup).model_dump()
    raw["buyer_value_hypothesis"]["source_evidence"][0]["record_digest"] = "f" * 64
    with pytest.raises(Conflict, match="stale"):
        register(setup, OfferingV2.model_validate(raw))
