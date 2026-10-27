# SPDX-License-Identifier: Apache-2.0
"""Research delivery cannot promote unknown costs or fictional funds to a sale."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from alpha_factory_v1.core.runtime.store import Conflict, Journal
from alpha_factory_v1.core.runtime.successor.flywheel_execution import operation_key
from alpha_factory_v1.core.runtime.successor.flywheel_learning import ACCEPTANCE_KEY
from alpha_factory_v1.core.runtime.successor.protocol import digest
from contrib.resilient_placement_delivery.runner import (
    OfflineReader,
    _acceptance,
    _run,
    build_execution,
    initialize_research,
    run_research,
    synthetic_conformance,
)
from contrib.resilient_placement_delivery.schema import parse_brief


def brief(identity: str = "delivery-one") -> dict[str, Any]:
    return {
        "brief_id": identity,
        "beneficiary": "Internal systems operator",
        "authorized_inputs": True,
        "rights_basis": "Original authored requirements licensed Apache-2.0",
        "inventory_basis": "Research-authored nonproduction inventory",
        "cost_unit": "relative planning units",
        "hosts": [
            {"id": "mtl-a", "capacity": 4, "failure_domain": "a"},
            {"id": "mtl-b", "capacity": 4, "failure_domain": "b"},
            {"id": "qc-a", "capacity": 4, "failure_domain": "a"},
        ],
        "services": [
            {"id": "api", "demand": 2, "costs": {"mtl-a": 2, "mtl-b": 4, "qc-a": 1}},
            {"id": "worker", "demand": 1, "costs": {"mtl-a": 1, "mtl-b": 2, "qc-a": 5}},
        ],
    }


def test_actual_journal_stays_unknown_while_separate_protocol_ledger_completes(tmp_path: Path) -> None:
    result = run_research(brief(), tmp_path / "delivery")
    assert result["research_acceptance"]["accepted_finite_result"]
    assert result["summary"]["actual_customer_collections_micro_usd"] == 0
    assert result["summary"]["actual_complete_cost_micro_usd"] is None
    assert result["summary"]["actual_profit_micro_usd"] is None
    assert result["actual"]["cost_report"]["bucket_complete"]["A"] is False
    assert result["actual"]["cost_report"]["complete_cost_profit"] is None
    actual = Journal(tmp_path / "delivery/actual/journal")
    assert actual.verify()["valid"]
    with pytest.raises(KeyError):
        actual.latest(ACCEPTANCE_KEY + "delivery-one")
    synthetic = Journal(tmp_path / "delivery/synthetic-conformance/journal")
    assert synthetic.verify()["valid"]
    assert synthetic.latest(ACCEPTANCE_KEY + "delivery-one")["record_digest"]
    stages = result["synthetic_conformance"]["stages"]
    assert stages[0]["report"]["customer_funds_by_mode"]["synthetic"]["earned_revenue"] == 0
    assert stages[-2]["report"]["customer_funds_by_mode"]["synthetic"]["pending_refunds"] > 0
    assert stages[-1]["report"]["customer_funds_by_mode"]["synthetic"]["pending_refunds"] == 0
    assert all(stage["report"]["accepted_service_revenue"] == 0 for stage in stages)
    assert result["synthetic_conformance"]["exact_retry_idempotent"]
    assert result["synthetic_conformance"]["duplicate_earning_refused"]


def test_named_scope_and_independent_outcome_are_bound(tmp_path: Path) -> None:
    raw = brief()
    state = initialize_research(tmp_path / "scope")
    parsed = parse_brief(raw)
    run = _run(state, parsed)
    record = run["execution"]
    assert record["mission"]["inputs"]["placement_brief_digest"] == digest(
        "commercial-placement-brief", parsed.model_dump()
    )
    assert record["mission"]["beneficiary"] == parsed.beneficiary
    assert record["result"]["deliverable"]["cost"] == 8
    assert record["actions"] == 1 and len(record["usage_events"]) == 2
    assert run["duplicate_execution_refused"]
    assert "complete" in run["unknown_cost_native_acceptance_refused"]
    original = state.costs.snapshot()
    wrong = _acceptance(state, parsed, record)
    payload = wrong.payload.copy()
    payload["record"] = {**payload["record"], "output_digest": "0" * 64}
    signed = state.signed("general-acceptance", "acceptance", payload["record"], "bad-output")
    with pytest.raises(ValueError, match="changed execution or output"):
        state.service.accept_general_origin(signed)
    assert state.costs.snapshot() == original


def test_fresh_work_uses_same_profile_and_separate_problem(tmp_path: Path) -> None:
    first, second = parse_brief(brief("first")), brief("second")
    second["services"][0]["costs"]["qc-a"] = 9
    other = parse_brief(second)
    state = initialize_research(tmp_path / "fresh")
    _, first_mission, first_profile, _ = build_execution(state, first)
    _, second_mission, second_profile, _ = build_execution(state, other)
    assert first_profile == second_profile
    assert first_mission.inputs["problem"] != second_mission.inputs["problem"]
    assert first_mission.inputs["placement_brief_digest"] != second_mission.inputs["placement_brief_digest"]


def test_repeat_output_refuses_without_overwriting_evidence(tmp_path: Path) -> None:
    destination = tmp_path / "delivery"
    run_research(brief(), destination)
    before = (destination / "evidence.json").read_bytes()
    with pytest.raises(FileExistsError):
        run_research(brief(), destination)
    assert (destination / "evidence.json").read_bytes() == before


def test_stop_prevents_any_attempt_and_survives_reopening(tmp_path: Path) -> None:
    state = initialize_research(tmp_path / "stopped")
    parsed = parse_brief(brief())
    executor, mission, profile, permit = build_execution(state, parsed)
    state.journal.control(paused=True)
    with state.journal.transaction() as cx:
        state.service.checkpoint.advance(state.journal, cx)
    assert Journal(state.journal.root).latest("@control")["state"] == "paused"
    before = state.costs.snapshot()
    with pytest.raises(Conflict, match="stopped or expired"):
        executor.run(mission, profile, permit)
    assert state.costs.snapshot() == before
    with pytest.raises(KeyError):
        state.journal.latest(operation_key(parsed.brief_id))


def test_offline_identity_never_authenticates_a_typed_name() -> None:
    with pytest.raises(ValueError, match="unavailable"):
        OfflineReader().call("eth_call", [{"name": "one.agent.agi.eth"}])


def test_published_safe_evidence_has_no_private_key_material(tmp_path: Path) -> None:
    destination = tmp_path / "delivery"
    run_research(brief(), destination)
    safe = json.loads((destination / "evidence.json").read_text())
    assert "identity.key" not in json.dumps(safe)
    assert "PRIVATE KEY" not in json.dumps(safe)
    assert not any(key.endswith("private_key") for key in safe)
    assert (destination / "actual/journal/identity.key").is_file()
    assert safe["summary"]["custody_scope"].startswith("local checkpoint")


def test_duplicate_customer_evidence_cannot_create_a_second_receipt(tmp_path: Path) -> None:
    state = initialize_research(tmp_path / "duplicate-funds")
    parsed = parse_brief(brief())
    synthetic_conformance(state, parsed)
    row = state.costs.snapshot()["customer_deposits"]["synthetic-service-deposit"]["terms"]
    changed = copy.deepcopy(row)
    changed["receipt_id"] = "new-receipt-same-evidence"
    before = state.costs.snapshot()
    with pytest.raises(Conflict, match="already allocated"):
        state.account("customer-deposit", changed, "new-deposit-same-evidence")
    assert state.costs.snapshot() == before


def test_incomplete_result_cannot_earn_and_refunds_the_synthetic_deposit(tmp_path: Path) -> None:
    raw = brief("incomplete")
    raw["node_budget"] = 1
    result = run_research(raw, tmp_path / "incomplete")
    assert result["execution"]["result"]["deliverable"]["status"] == "incomplete"
    assert result["summary"]["research_artifact_accepted"] is False
    assert result["synthetic_conformance"]["acceptance"] is None
    final = result["synthetic_conformance"]["stages"][-1]["report"]["customer_funds_by_mode"]["synthetic"]
    assert final["net_cash"] == final["earned_revenue"] == final["customer_obligations"] == 0
    assert final["refunds"] == parse_brief(raw).price_micro_usd
    assert result["actual"]["cost_report"]["complete_cost_profit"] is None


def test_small_positive_price_cannot_create_a_zero_refund(tmp_path: Path) -> None:
    raw = brief("micro-price")
    raw["price_micro_usd"] = 1
    state = initialize_research(tmp_path / "micro-price")
    result = synthetic_conformance(state, parse_brief(raw))
    final = result["stages"][-1]["report"]["customer_funds_by_mode"]["synthetic"]
    assert final["refunds"] == 1
    assert final["net_cash"] == final["earned_revenue"] == final["customer_obligations"] == 0


def test_zero_price_delivers_without_a_payment_or_a_refund(tmp_path: Path) -> None:
    raw = brief("free-research")
    raw["price_micro_usd"] = 0
    result = run_research(raw, tmp_path / "free-research")
    assert result["summary"]["research_artifact_accepted"] is True
    synthetic = result["synthetic_conformance"]
    assert synthetic["acceptance"] is not None
    assert synthetic["payment_status"] == "no-payment: free research deliverable"
    assert synthetic["synthetic_price_hypothesis_micro_usd"] == 0
    assert all(
        stage["report"]["customer_funds_by_mode"]["synthetic"]["gross_collections"] == 0
        for stage in synthetic["stages"]
    )
    assert "noncash synthetic" in result["actual"]["funding_scope"]
    sources = json.loads((tmp_path / "free-research/sources.json").read_text())
    assert "scripts/record_general_flywheel.py" in sources
    assert "alpha_factory_v1/core/runtime/successor/flywheel_execution.py" in sources
